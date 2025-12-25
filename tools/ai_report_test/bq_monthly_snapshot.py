import os
import json
import hashlib
import re
from datetime import date, timedelta
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

    q_products_total = f"""
    SELECT
      COUNT(DISTINCT product_no) AS products_sold_cnt,
      SUM(item_quantity) AS total_quantity,
      SUM(item_product_sales) AS total_sales
    FROM `{PROJECT_ID}.{DATASET}.daily_cafe24_items`
    WHERE company_name = @company_name
      AND payment_date BETWEEN @start_date AND @end_date
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
        # 핵심: GA4 view_item 결과는 products_30d와 무관하게 항상 출력되어야 함
        # sales_map은 선택적 매칭 용도로만 사용 (products_30d가 빈 리스트여도 viewitem 결과는 출력)
        
        # 선택적 매칭 맵 생성 (products_30d가 없거나 빈 리스트여도 문제없음)
        sales_map = {}
        if products_30d:
            for p in products_30d:
                if isinstance(p, dict):
                    product_name = p.get("product_name")
                    if product_name:
                        key = normalize_item_name(product_name)
                        if key:
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
                        bigquery.ScalarQueryParameter("limit", "INT64", VIEWITEM_TOP_LIMIT),
                    ]
                ),
            ).result()
        )

        # 모든 GA4 view_item 결과를 항상 출력 (매칭 여부와 무관)
        items = []
        for r in rows:
            raw = r.item_name or ""
            key = normalize_item_name(raw)
            # sales_map에서 선택적 매칭 시도 (없어도 결과는 출력)
            matched = sales_map.get(key) if key else None

            items.append({
                "item_name": raw,
                "item_name_normalized": key,
                "view_item": int(r.view_item or 0),
                "matched_product_no": matched.get("product_no") if matched else None,
                "match_type": "normalized_name" if matched else "none",
            })

        # 반환 구조 유지: BigQuery 결과가 0 row여도 빈 리스트 반환
        return {"top_items_by_view_item": items}

    # -----------------------
    # Fetch
    # -----------------------
    sales_this = get_sales(this_start, this_end)
    products_this = get_products_block(this_end)
    # products_this["rolling"]["d30"]["top_products_by_sales"]가 없을 수 있으므로 안전하게 접근
    products_30d = products_this.get("rolling", {}).get("d30", {}).get("top_products_by_sales", [])
    viewitem_this = get_viewitem_block(
        this_start,
        this_end,
        products_30d,
    )

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
    }

    snapshot_str = json.dumps(out, ensure_ascii=False, sort_keys=True)
    snapshot_hash = hashlib.sha256(snapshot_str.encode("utf-8")).hexdigest()

    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    import sys
    run(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]))
