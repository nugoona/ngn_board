import os
import json
import hashlib
import re
from datetime import date, timedelta
from collections import defaultdict
from google.cloud import bigquery

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "winged-precept-443218-v8")
DATASET = "ngn_dataset"

# 광고 기준
TRAFFIC_TOP_MIN_SPEND = 10_000
TOP_LIMIT = 5

# 4축 확장 상수
PRODUCT_TOP_LIMIT = 20
GA4_TRAFFIC_TOP_LIMIT = 5
VIEWITEM_TOP_LIMIT = 20
PRODUCT_ROLLING_WINDOWS = [30, 90]
VIEWITEM_ATTENTION_MIN_VIEW = 300  # attention_without_conversion 기준 최소 조회수


def month_range(year: int, month: int):
    start = date(year, month, 1)
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    end = next_month - timedelta(days=1)
    return start.isoformat(), end.isoformat()


def rolling_range(end_date_iso: str, days: int):
    end_d = date.fromisoformat(end_date_iso)
    start_d = end_d - timedelta(days=days - 1)
    return start_d.isoformat(), end_d.isoformat()


# -----------------------
# 상품명 정규화 (핵심)
# -----------------------
def normalize_item_name(name: str) -> str:
    if name is None:
        return ""

    s = str(name).strip()
    if not s or s == "(not set)":
        return ""

    # [ ] 제거 (단, [SET]은 보호)
    if not s.startswith("[SET]"):
        s = re.sub(r"^\[[^\]]+\]\s*", "", s)

    # 옵션 제거 (_컬러 / _사이즈 / _4Color 등)
    s = re.sub(r"_.*$", "", s)

    # 공백 정리
    s = re.sub(r"\s+", " ", s).strip()

    return s


def _goal_from_campaign_name(campaign_name: str) -> str:
    if not campaign_name:
        return "unknown"

    name = str(campaign_name)
    lower = name.lower()

    if "전환" in name or re.search(r"\bconversion\b", lower):
        return "conversion"
    if "유입" in name or re.search(r"\btraffic\b", lower):
        return "traffic"
    if "도달" in name or re.search(r"\bawareness\b", lower) or re.search(r"\breach\b", lower):
        return "awareness"

    return "unknown"


def run(company_name: str, year: int, month: int):
    client = bigquery.Client(project=PROJECT_ID)

    this_start, this_end = month_range(year, month)

    if month == 1:
        prev_y, prev_m = year - 1, 12
    else:
        prev_y, prev_m = year, month - 1
    prev_start, prev_end = month_range(prev_y, prev_m)

    yoy_y, yoy_m = year - 1, month
    yoy_start, yoy_end = month_range(yoy_y, yoy_m)

    # -----------------------
    # Mall sales
    # -----------------------
    q_sales = f"""
    SELECT
        SUM(net_sales) AS net_sales,
        SUM(total_orders) AS total_orders,
        SUM(total_first_order) AS total_first_order,
        SUM(total_canceled) AS total_canceled
    FROM `{PROJECT_ID}.{DATASET}.daily_cafe24_sales`
    WHERE company_name = @company_name
      AND payment_date BETWEEN @start_date AND @end_date
    """

    def get_sales(s, e):
        # 빈 데이터 안전 처리: SUM 쿼리는 보통 1 row 반환하지만 방어 코드 추가
        rows = list(
            client.query(
                q_sales,
                job_config=bigquery.QueryJobConfig(
                    query_parameters=[
                        bigquery.ScalarQueryParameter("company_name", "STRING", company_name),
                        bigquery.ScalarQueryParameter("start_date", "DATE", s),
                        bigquery.ScalarQueryParameter("end_date", "DATE", e),
                    ]
                ),
            ).result()
        )
        
        # SUM 쿼리는 데이터가 없어도 1 row (NULL 값) 반환하지만, 방어 코드 추가
        if not rows:
            return {
                "net_sales": 0.0,
                "total_orders": 0,
                "total_first_order": 0,
                "total_canceled": 0,
            }
        
        row = rows[0]
        return {
            "net_sales": float(row.net_sales or 0),
            "total_orders": int(row.total_orders or 0),
            "total_first_order": int(row.total_first_order or 0),
            "total_canceled": int(row.total_canceled or 0),
        }

    # -----------------------
    # Products (30d / 90d)
    # -----------------------
    q_products = f"""
    SELECT
      product_no,
      product_name,
      ANY_VALUE(product_url) AS product_url,
      SUM(item_quantity) AS quantity,
      SUM(item_product_sales) AS sales
    FROM `{PROJECT_ID}.{DATASET}.daily_cafe24_items`
    WHERE company_name = @company_name
      AND payment_date BETWEEN @start_date AND @end_date
    GROUP BY product_no, product_name
    HAVING SUM(item_product_sales) > 0
    ORDER BY sales DESC
    LIMIT @limit
    """

    def get_products_block(end_date_iso):
        # 빈 데이터 안전 처리: rolling_top 키 누락 방지
        block = {"rolling": {}}
        rolling_top = {}

        for days in PRODUCT_ROLLING_WINDOWS:
            s, e = rolling_range(end_date_iso, days)

            rows = list(
                client.query(
                    q_products,
                    job_config=bigquery.QueryJobConfig(
                        query_parameters=[
                            bigquery.ScalarQueryParameter("company_name", "STRING", company_name),
                            bigquery.ScalarQueryParameter("start_date", "DATE", s),
                            bigquery.ScalarQueryParameter("end_date", "DATE", e),
                            bigquery.ScalarQueryParameter("limit", "INT64", PRODUCT_TOP_LIMIT),
                        ]
                    ),
                ).result()
            )

            rolling_top[days] = [
                {
                    "product_no": int(r.product_no),
                    "product_name": r.product_name,
                    "product_url": r.product_url,
                    "quantity": int(r.quantity),
                    "sales": float(r.sales),
                }
                for r in rows
            ]

        s90, e90 = rolling_range(end_date_iso, 90)
        net90 = get_sales(s90, e90)["net_sales"]
        
        # 30일 데이터 가져오기 (core/hit 상품 보강용)
        products_30d_map = {}
        for p in rolling_top.get(30, []):
            products_30d_map[p["product_no"]] = {
                "quantity": p["quantity"],
                "sales": p["sales"],
            }

        # rolling_top[90]이 없을 수 있으므로 .get() 사용
        for p in rolling_top.get(90, []):
            share = (p["sales"] / net90 * 100) if net90 else None
            p["share_of_net_sales_pct_90d"] = share
            if share is None:
                p["role_90d"] = "unknown"
            elif share >= 20:
                p["role_90d"] = "core"
            elif share >= 10:
                p["role_90d"] = "hit"
            else:
                p["role_90d"] = "normal"
            
            # core/hit 상품에 대해서만 추가 필드
            if p["role_90d"] in ["core", "hit"]:
                p30d = products_30d_map.get(p["product_no"])
                if p30d:
                    p["quantity_30d"] = p30d["quantity"]
                    p["sales_30d"] = p30d["sales"]
                    # 90일 평균 대비 30일 매출 비교
                    avg_90d_sales = p["sales"] / 90
                    avg_30d_sales = p30d["sales"] / 30
                    p["is_declining"] = avg_30d_sales < avg_90d_sales
                else:
                    p["quantity_30d"] = None
                    p["sales_30d"] = None
                    p["is_declining"] = None

        # rolling_top[30], rolling_top[90]이 없을 수 있으므로 .get() 사용하여 기본값 제공
        block["rolling"]["d30"] = {"top_products_by_sales": rolling_top.get(30, [])}
        block["rolling"]["d90"] = {"top_products_by_sales_with_role": rolling_top.get(90, [])}

        return block

    # -----------------------
    # GA4 view_item
    # -----------------------
    q_viewitem = f"""
    SELECT item_name, SUM(view_item) AS view_item
    FROM `{PROJECT_ID}.{DATASET}.ga4_viewitem_ngn`
    WHERE company_name = @company_name
      AND event_date BETWEEN @start_date AND @end_date
    GROUP BY item_name
    ORDER BY view_item DESC
    LIMIT @limit
    """

    def get_viewitem_block(s, e, products_30d):
        # products_30d 매칭 맵 생성 (normalize_item_name 기준, 30일 기준)
        # 매칭 기준: normalize_item_name(product_name) == normalize_item_name(item_name)
        # 상품 1개당 1 key 매칭 (fuzzy, 광고명, 부분매칭 제외)
        sales_map = {}
        if products_30d:
            for p in products_30d:
                if isinstance(p, dict):
                    product_name = p.get("product_name")
                    if product_name:
                        key = normalize_item_name(product_name)
                        if key:
                            # 동일 key가 이미 있으면 덮어쓰지 않음 (첫 매칭만 유지)
                            if key not in sales_map:
                                sales_map[key] = p

        # GA4 view_item 쿼리 실행 (products_30d와 무관하게 항상 실행)
        rows = list(
            client.query(
                q_viewitem,
                job_config=bigquery.QueryJobConfig(
                    query_parameters=[
                        bigquery.ScalarQueryParameter("company_name", "STRING", company_name),
                        bigquery.ScalarQueryParameter("start_date", "DATE", s),
                        bigquery.ScalarQueryParameter("end_date", "DATE", e),
                        bigquery.ScalarQueryParameter("limit", "INT64", VIEWITEM_TOP_LIMIT * 3),  # 통합을 위해 더 많이 가져오기
                    ]
                ),
            ).result()
        )

        # normalize_item_name 기준으로 통합 (Python에서 group by)
        aggregated = defaultdict(lambda: {"total_view_item": 0, "matched": None})
        
        for r in rows:
            raw = r.item_name or ""
            view_item_count = int(r.view_item or 0)
            
            # view_item = 0 제외
            if view_item_count == 0:
                continue
            
            key = normalize_item_name(raw)
            
            # item_name_normalized == "" 제외 (normalize 단계에서 이미 제거됨)
            if not key:
                continue
            
            aggregated[key]["total_view_item"] += view_item_count
            
            # 매칭 정보는 첫 번째 매칭된 것만 저장 (normalize_item_name 기준)
            if aggregated[key]["matched"] is None:
                matched = sales_map.get(key)
                if matched:
                    aggregated[key]["matched"] = matched

        # 통합된 결과를 리스트로 변환 (정확한 구조만 유지)
        items = []
        for key, data in aggregated.items():
            matched = data["matched"]
            total_view_item = data["total_view_item"]
            
            # view_item = 0 제외 (이미 위에서 처리했지만 이중 체크)
            if total_view_item == 0:
                continue
            
            matched_product_no = matched.get("product_no") if matched else None
            matched_quantity_30d = matched.get("quantity") if matched else None
            matched_sales_30d = matched.get("sales") if matched else None
            
            # qty_per_view, sales_per_view 계산
            qty_per_view = (matched_quantity_30d / total_view_item) if (matched_quantity_30d and total_view_item > 0) else None
            sales_per_view = (matched_sales_30d / total_view_item) if (matched_sales_30d and total_view_item > 0) else None
            
            # attention_without_conversion 플래그 계산
            # 기준: total_view_item >= 300 AND (matched_quantity_30d is None OR matched_quantity_30d == 0)
            attention_without_conversion = (
                total_view_item >= VIEWITEM_ATTENTION_MIN_VIEW and
                (matched_quantity_30d is None or matched_quantity_30d == 0)
            )
            
            items.append({
                "item_name_normalized": key,
                "total_view_item": total_view_item,
                "matched_product_no": matched_product_no,
                "matched_quantity_30d": matched_quantity_30d,
                "matched_sales_30d": matched_sales_30d,
                "qty_per_view": round(qty_per_view, 4) if qty_per_view is not None else None,
                "sales_per_view": round(sales_per_view, 2) if sales_per_view is not None else None,
                "attention_without_conversion": attention_without_conversion,
            })

        # total_view_item 기준으로 정렬
        items.sort(key=lambda x: x["total_view_item"], reverse=True)

        return {"top_items_by_view_item": items}

    # -----------------------
    # Signals 계산
    # -----------------------
    def calculate_signals(sales_this, products_this, viewitem_this):
        signals = {}
        
        # 기존 signals
        net_this = sales_this.get("net_sales", 0)
        net_prev = get_sales(prev_start, prev_end).get("net_sales", 0)
        mom_pct = (net_this - net_prev) / net_prev * 100 if net_prev else None
        
        if mom_pct is None:
            signals["sales_signal"] = "unknown"
        elif mom_pct >= 3:
            signals["sales_signal"] = "increase"
        elif mom_pct <= -3:
            signals["sales_signal"] = "decrease"
        else:
            signals["sales_signal"] = "flat"
        
        # attention_without_conversion_exists
        viewitem_items = viewitem_this.get("top_items_by_view_item", [])
        signals["attention_without_conversion_exists"] = any(
            item.get("attention_without_conversion", False) for item in viewitem_items
        )
        
        # core_product_risk
        products_90d = products_this.get("rolling", {}).get("d90", {}).get("top_products_by_sales_with_role", [])
        core_products = [p for p in products_90d if p.get("role_90d") == "core"]
        signals["core_product_risk"] = any(
            p.get("is_declining") is True for p in core_products
        )
        
        # new_product_dependency
        products_30d = products_this.get("rolling", {}).get("d30", {}).get("top_products_by_sales", [])
        first_order_products = []
        total_30d_sales = sum(p.get("sales", 0) for p in products_30d)
        
        # 첫 판매 상품 판별 (간단히 30일 데이터만 있고 90일에는 없는 상품)
        products_90d_map = {p.get("product_no"): p for p in products_90d}
        for p in products_30d:
            product_no = p.get("product_no")
            if product_no not in products_90d_map:
                first_order_products.append(p)
        
        first_order_sales = sum(p.get("sales", 0) for p in first_order_products)
        signals["new_product_dependency"] = (
            (first_order_sales / total_30d_sales * 100) >= 30
        ) if total_30d_sales > 0 else False
        
        return signals

    # -----------------------
    # Summary sentences 생성
    # -----------------------
    def generate_summary_sentences(signals, viewitem_this, products_this):
        sentences = []
        
        # attention_without_conversion_exists
        if signals.get("attention_without_conversion_exists"):
            sentences.append("조회수 대비 판매 연결이 낮은 상품이 일부 관측되었습니다.")
        
        # core_product_risk
        if signals.get("core_product_risk"):
            sentences.append("주력 상품 중 일부는 최근 30일 기준 판매 둔화 신호가 나타납니다.")
        
        # new_product_dependency
        if signals.get("new_product_dependency"):
            sentences.append("최근 30일 첫 판매 상품이 전체 매출에서 높은 비중을 차지하고 있습니다.")
        
        # sales_signal
        sales_signal = signals.get("sales_signal")
        if sales_signal == "increase":
            sentences.append("전월 대비 매출 증가 추세가 확인되었습니다.")
        elif sales_signal == "decrease":
            sentences.append("전월 대비 매출 감소 추세가 확인되었습니다.")
        
        return sentences[:4]  # 최대 4문장

    # -----------------------
    # Fetch
    # -----------------------
    sales_this = get_sales(this_start, this_end)
    products_this = get_products_block(this_end)
    products_30d = products_this.get("rolling", {}).get("d30", {}).get("top_products_by_sales", [])
    viewitem_this = get_viewitem_block(
        this_start,
        this_end,
        products_30d,
    )
    
    signals = calculate_signals(sales_this, products_this, viewitem_this)
    summary_sentences = generate_summary_sentences(signals, viewitem_this, products_this)

    out = {
        "report_meta": {
            "company_name": company_name,
            "period_this": {"from": this_start, "to": this_end},
        },
        "facts": {
            "mall_sales": {"this": sales_this},
            "products": {"this": products_this},
            "viewitem": {"this": viewitem_this},
        },
        "signals": signals,
        "summary_sentences": summary_sentences,
    }

    snapshot_str = json.dumps(out, ensure_ascii=False, sort_keys=True)
    snapshot_hash = hashlib.sha256(snapshot_str.encode("utf-8")).hexdigest()

    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    import sys
    run(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]))
