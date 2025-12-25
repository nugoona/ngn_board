import os
import json
import hashlib
import re
import statistics
from datetime import date, timedelta
from decimal import Decimal
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

# 비교 기준 threshold
MALL_SALES_BASE_SMALL_THRESHOLD = 500000
META_ADS_BASE_SMALL_THRESHOLD = 100000
GA4_TRAFFIC_BASE_SMALL_THRESHOLD = 100

# Viewitem 스킵 플래그
SKIP_VIEWITEM = os.environ.get("SKIP_VIEWITEM", "0") == "1"


# -----------------------
# 날짜 헬퍼
# -----------------------
def month_range(year: int, month: int):
    """월 시작~월말(end inclusive)"""
    start = date(year, month, 1)
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    end = next_month - timedelta(days=1)
    return start.isoformat(), end.isoformat()


def month_to_ym(year: int, month: int) -> str:
    """YYYY-MM 형식으로 변환"""
    return f"{year:04d}-{month:02d}"


def shift_month(ym: str, delta: int) -> str:
    """YYYY-MM 형식에서 delta개월 이동"""
    y, m = map(int, ym.split("-"))
    m += delta
    while m > 12:
        m -= 12
        y += 1
    while m < 1:
        m += 12
        y -= 1
    return f"{y:04d}-{m:02d}"


def month_range_exclusive(ym: str):
    """YYYY-MM 형식에서 start_date (inclusive), end_date (exclusive) 반환"""
    y, m = map(int, ym.split("-"))
    start = date(y, m, 1)
    if m == 12:
        end_exclusive = date(y + 1, 1, 1)
    else:
        end_exclusive = date(y, m + 1, 1)
    return start.isoformat(), end_exclusive.isoformat()


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


# -----------------------
# 공통 헬퍼
# -----------------------
def delta(curr, base):
    """변화량 계산: {"abs": ..., "pct": ...} (base==0이면 pct None)"""
    abs_diff = curr - base
    pct = (abs_diff / base * 100) if base != 0 else None
    return {"abs": abs_diff, "pct": pct}


def note_if_base_small(base_value, threshold):
    """기준값이 작은지 여부"""
    return base_value < threshold


def json_safe(obj):
    """Decimal 및 기타 JSON 직렬화 불가능한 타입을 안전하게 변환"""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [json_safe(v) for v in obj]
    return obj


def has_rows(client, table_fq, date_col, company_name, start_date, end_date):
    """특정 기간에 데이터가 존재하는지 확인"""
    query = f"""
    SELECT COUNT(1) AS cnt
    FROM `{table_fq}`
    WHERE company_name = @company_name
      AND {date_col} >= @start_date
      AND {date_col} <= @end_date
    LIMIT 1
    """
    
    rows = list(
        client.query(
            query,
            job_config=bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("company_name", "STRING", company_name),
                    bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
                    bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
                ]
            ),
        ).result()
    )
    
    if not rows:
        return False
    
    return int(rows[0].cnt or 0) > 0


def query_monthly_13m_generic(client, table_fq, date_col, company_name, end_report_month_ym, select_exprs, where_extra=""):
    """
    13개월 월별 집계 공통 함수 (daily 테이블용)
    반환: dict[ym] = metrics
    """
    start_ym = shift_month(end_report_month_ym, -12)
    start_date, _ = month_range_exclusive(start_ym)
    end_exclusive_date, _ = month_range_exclusive(shift_month(end_report_month_ym, 1))
    
    query = f"""
    SELECT 
        FORMAT_DATE('%Y-%m', {date_col}) AS ym,
        {select_exprs}
    FROM `{table_fq}`
    WHERE company_name = @company_name
      AND {date_col} >= @start_date
      AND {date_col} < @end_exclusive_date
      {where_extra}
    GROUP BY ym
    ORDER BY ym
    """
    
    rows = list(
        client.query(
            query,
            job_config=bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("company_name", "STRING", company_name),
                    bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
                    bigquery.ScalarQueryParameter("end_exclusive_date", "DATE", end_exclusive_date),
                ]
            ),
        ).result()
    )
    
    result = {}
    for row in rows:
        ym = row.ym
        metrics = {}
        for field in row.keys():
            if field != "ym":
                value = getattr(row, field)
                if isinstance(value, (int, float)):
                    metrics[field] = float(value) if isinstance(value, float) else int(value)
                else:
                    metrics[field] = value
        result[ym] = metrics
    
    return result


def query_monthly_13m_from_monthly_table(client, table_fq, company_name, end_report_month_ym, select_exprs):
    """
    13개월 월별 집계 함수 (월간 집계 테이블용)
    반환: dict[ym] = metrics
    중복행에도 안전하도록 GROUP BY ym으로 집계
    """
    start_ym = shift_month(end_report_month_ym, -12)
    start_date, _ = month_range_exclusive(start_ym)
    end_exclusive_date, _ = month_range_exclusive(shift_month(end_report_month_ym, 1))
    
    query = f"""
    SELECT 
        FORMAT_DATE('%Y-%m', month_date) AS ym,
        {select_exprs}
    FROM `{table_fq}`
    WHERE company_name = @company_name
      AND month_date >= @start_date
      AND month_date < @end_exclusive_date
    GROUP BY ym
    ORDER BY ym
    """
    
    rows = list(
        client.query(
            query,
            job_config=bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("company_name", "STRING", company_name),
                    bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
                    bigquery.ScalarQueryParameter("end_exclusive_date", "DATE", end_exclusive_date),
                ]
            ),
        ).result()
    )
    
    result = {}
    for row in rows:
        ym = row.ym
        metrics = {}
        for field in row.keys():
            if field != "ym":
                value = getattr(row, field)
                if isinstance(value, (int, float)):
                    metrics[field] = float(value) if isinstance(value, float) else int(value)
                else:
                    metrics[field] = value
        result[ym] = metrics
    
    return result


def run(company_name: str, year: int, month: int, upsert_flag: bool = False):
    client = bigquery.Client(project=PROJECT_ID)
    
    report_month = month_to_ym(year, month)
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
    
    # Mall sales: this/prev/yoy + monthly_13m
    sales_this = get_sales(this_start, this_end)
    sales_prev = get_sales(prev_start, prev_end)
    sales_yoy = get_sales(yoy_start, yoy_end)
    
    # 월간 집계 테이블 사용 (성능 최적화)
    monthly_13m_raw = query_monthly_13m_from_monthly_table(
        client,
        f"{PROJECT_ID}.{DATASET}.mall_sales_monthly",
        company_name,
        report_month,
        """
        SUM(net_sales) AS net_sales,
        SUM(total_orders) AS total_orders,
        SUM(total_first_order) AS total_first_order,
        SUM(total_canceled) AS total_canceled
        """
    )
    
    monthly_13m = [
        {"ym": ym, **metrics}
        for ym, metrics in sorted(monthly_13m_raw.items())
    ]
    
    # -----------------------
    # Meta ads
    # -----------------------
    q_meta_ads = f"""
    SELECT
        SUM(spend) AS spend,
        SUM(impressions) AS impressions,
        SUM(clicks) AS clicks,
        SUM(purchases) AS purchases,
        SUM(purchase_value) AS purchase_value
    FROM `{PROJECT_ID}.{DATASET}.meta_ads_account_summary`
    WHERE company_name = @company_name
      AND date BETWEEN @start_date AND @end_date
    """
    
    def get_meta_ads(s, e):
        rows = list(
            client.query(
                q_meta_ads,
                job_config=bigquery.QueryJobConfig(
                    query_parameters=[
                        bigquery.ScalarQueryParameter("company_name", "STRING", company_name),
                        bigquery.ScalarQueryParameter("start_date", "DATE", s),
                        bigquery.ScalarQueryParameter("end_date", "DATE", e),
                    ]
                ),
            ).result()
        )
        
        if not rows:
            return {
                "spend": 0.0,
                "impressions": 0,
                "clicks": 0,
                "purchases": 0,
                "purchase_value": 0.0,
                "roas": None,
                "cpc": None,
                "ctr": None,
                "cvr": None,
            }
        
        row = rows[0]
        spend = float(row.spend or 0)
        impressions = int(row.impressions or 0)
        clicks = int(row.clicks or 0)
        purchases = int(row.purchases or 0)
        purchase_value = float(row.purchase_value or 0)
        
        return {
            "spend": spend,
            "impressions": impressions,
            "clicks": clicks,
            "purchases": purchases,
            "purchase_value": purchase_value,
            "roas": (purchase_value / spend * 100) if spend > 0 else None,
            "cpc": (spend / clicks) if clicks > 0 else None,
            "ctr": (clicks / impressions * 100) if impressions > 0 else None,
            "cvr": (purchases / clicks * 100) if clicks > 0 else None,
        }
    
    meta_ads_this = get_meta_ads(this_start, this_end)
    meta_ads_prev = get_meta_ads(prev_start, prev_end)
    meta_ads_yoy = get_meta_ads(yoy_start, yoy_end)
    
    # 월간 집계 테이블 사용 (성능 최적화)
    monthly_13m_meta_raw = query_monthly_13m_from_monthly_table(
        client,
        f"{PROJECT_ID}.{DATASET}.meta_ads_monthly",
        company_name,
        report_month,
        """
        SUM(spend) AS spend,
        SUM(impressions) AS impressions,
        SUM(clicks) AS clicks,
        SUM(purchases) AS purchases,
        SUM(purchase_value) AS purchase_value
        """
    )
    
    monthly_13m_meta = []
    for ym, metrics in sorted(monthly_13m_meta_raw.items()):
        spend = metrics.get("spend", 0)
        impressions = metrics.get("impressions", 0)
        clicks = metrics.get("clicks", 0)
        purchases = metrics.get("purchases", 0)
        purchase_value = metrics.get("purchase_value", 0)
        
        monthly_13m_meta.append({
            "ym": ym,
            "spend": spend,
            "impressions": impressions,
            "clicks": clicks,
            "purchases": purchases,
            "purchase_value": purchase_value,
            "roas": (purchase_value / spend * 100) if spend > 0 else None,
            "cpc": (spend / clicks) if clicks > 0 else None,
            "ctr": (clicks / impressions * 100) if impressions > 0 else None,
            "cvr": (purchases / clicks * 100) if clicks > 0 else None,
        })
    
    # -----------------------
    # GA4 traffic
    # -----------------------
    q_ga4_traffic = f"""
    SELECT
        SUM(total_users) AS total_users,
        SUM(screen_page_views) AS screen_page_views,
        SUM(event_count) AS event_count
    FROM `{PROJECT_ID}.{DATASET}.ga4_traffic_ngn`
    WHERE company_name = @company_name
      AND event_date BETWEEN @start_date AND @end_date
    """
    
    def get_ga4_traffic_totals(s, e):
        rows = list(
            client.query(
                q_ga4_traffic,
                job_config=bigquery.QueryJobConfig(
                    query_parameters=[
                        bigquery.ScalarQueryParameter("company_name", "STRING", company_name),
                        bigquery.ScalarQueryParameter("start_date", "DATE", s),
                        bigquery.ScalarQueryParameter("end_date", "DATE", e),
                    ]
                ),
            ).result()
        )
        
        if not rows:
            return {
                "total_users": 0,
                "screen_page_views": 0,
                "event_count": 0,
            }
        
        row = rows[0]
        return {
            "total_users": int(row.total_users or 0),
            "screen_page_views": int(row.screen_page_views or 0),
            "event_count": int(row.event_count or 0),
        }
    
    q_ga4_top_sources = f"""
    SELECT
        first_user_source AS source,
        SUM(total_users) AS total_users,
        SUM(screen_page_views) AS screen_page_views
    FROM `{PROJECT_ID}.{DATASET}.ga4_traffic_ngn`
    WHERE company_name = @company_name
      AND event_date BETWEEN @start_date AND @end_date
      AND first_user_source IS NOT NULL
      AND first_user_source != '(not set)'
    GROUP BY source
    ORDER BY total_users DESC
    LIMIT @top_n
    """
    
    def get_ga4_top_sources(s, e, top_n=10):
        rows = list(
            client.query(
                q_ga4_top_sources,
                job_config=bigquery.QueryJobConfig(
                    query_parameters=[
                        bigquery.ScalarQueryParameter("company_name", "STRING", company_name),
                        bigquery.ScalarQueryParameter("start_date", "DATE", s),
                        bigquery.ScalarQueryParameter("end_date", "DATE", e),
                        bigquery.ScalarQueryParameter("top_n", "INT64", top_n),
                    ]
                ),
            ).result()
        )
        
        return [
            {
                "source": r.source,
                "total_users": int(r.total_users or 0),
                "screen_page_views": int(r.screen_page_views or 0),
            }
            for r in rows
        ]
    
    ga4_this_totals = get_ga4_traffic_totals(this_start, this_end)
    ga4_prev_totals = get_ga4_traffic_totals(prev_start, prev_end)
    
    # YoY 데이터 존재 여부 확인
    ga4_yoy_available = has_rows(
        client,
        f"{PROJECT_ID}.{DATASET}.ga4_traffic_ngn",
        "event_date",
        company_name,
        yoy_start,
        yoy_end
    )
    
    if ga4_yoy_available:
        ga4_yoy_totals = get_ga4_traffic_totals(yoy_start, yoy_end)
        ga4_yoy = {
            "totals": ga4_yoy_totals,
            "top_sources": get_ga4_top_sources(yoy_start, yoy_end),
        }
    else:
        ga4_yoy = {
            "totals": None,
            "top_sources": [],
        }
    
    ga4_this = {
        "totals": ga4_this_totals,
        "top_sources": get_ga4_top_sources(this_start, this_end),
    }
    ga4_prev = {
        "totals": ga4_prev_totals,
        "top_sources": get_ga4_top_sources(prev_start, prev_end),
    }
    
    # 월간 집계 테이블 사용 (성능 최적화)
    monthly_13m_ga4_raw = query_monthly_13m_from_monthly_table(
        client,
        f"{PROJECT_ID}.{DATASET}.ga4_traffic_monthly",
        company_name,
        report_month,
        """
        SUM(total_users) AS total_users,
        SUM(screen_page_views) AS screen_page_views,
        SUM(event_count) AS event_count
        """
    )
    
    monthly_13m_ga4 = [
        {"ym": ym, **metrics}
        for ym, metrics in sorted(monthly_13m_ga4_raw.items())
    ]
    
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
        
        products_30d_map = {}
        for p in rolling_top.get(30, []):
            products_30d_map[p["product_no"]] = {
                "quantity": p["quantity"],
                "sales": p["sales"],
            }
        
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
            
            if p["role_90d"] in ["core", "hit"]:
                p30d = products_30d_map.get(p["product_no"])
                if p30d:
                    p["quantity_30d"] = p30d["quantity"]
                    p["sales_30d"] = p30d["sales"]
                    avg_90d_sales = p["sales"] / 90
                    avg_30d_sales = p30d["sales"] / 30
                    p["is_declining"] = avg_30d_sales < avg_90d_sales
                else:
                    p["quantity_30d"] = None
                    p["sales_30d"] = None
                    p["is_declining"] = None
        
        block["rolling"]["d30"] = {"top_products_by_sales": rolling_top.get(30, [])}
        block["rolling"]["d90"] = {"top_products_by_sales_with_role": rolling_top.get(90, [])}
        
        return block
    
    products_this = get_products_block(this_end)
    
    # -----------------------
    # GA4 view_item (월간 집계 테이블 사용)
    # -----------------------
    q_viewitem_monthly = f"""
    SELECT
      item_name,
      view_item
    FROM `{PROJECT_ID}.{DATASET}.ga4_viewitem_monthly_raw`
    WHERE company_name = @company_name
      AND ym = @ym
    ORDER BY view_item DESC
    LIMIT @limit
    """
    
    def get_viewitem_block(ym, products_30d):
        sales_map = {}
        if products_30d:
            for p in products_30d:
                if isinstance(p, dict):
                    product_name = p.get("product_name")
                    if product_name:
                        key = normalize_item_name(product_name)
                        if key:
                            if key not in sales_map:
                                sales_map[key] = p
        
        rows = list(
            client.query(
                q_viewitem_monthly,
                job_config=bigquery.QueryJobConfig(
                    query_parameters=[
                        bigquery.ScalarQueryParameter("company_name", "STRING", company_name),
                        bigquery.ScalarQueryParameter("ym", "STRING", ym),
                        bigquery.ScalarQueryParameter("limit", "INT64", VIEWITEM_TOP_LIMIT * 3),
                    ]
                ),
            ).result()
        )
        
        aggregated = defaultdict(lambda: {"total_view_item": 0, "matched": None})
        
        for r in rows:
            raw = r.item_name or ""
            view_item_count = int(r.view_item or 0)
            
            if view_item_count == 0:
                continue
            
            key = normalize_item_name(raw)
            
            if not key:
                continue
            
            aggregated[key]["total_view_item"] += view_item_count
            
            if aggregated[key]["matched"] is None:
                matched = sales_map.get(key)
                if matched:
                    aggregated[key]["matched"] = matched
        
        items = []
        for key, data in aggregated.items():
            matched = data["matched"]
            total_view_item = data["total_view_item"]
            
            if total_view_item == 0:
                continue
            
            matched_product_no = matched.get("product_no") if matched else None
            matched_quantity_30d = matched.get("quantity") if matched else None
            matched_sales_30d = matched.get("sales") if matched else None
            
            qty_per_view = (matched_quantity_30d / total_view_item) if (matched_quantity_30d and total_view_item > 0) else None
            sales_per_view = (matched_sales_30d / total_view_item) if (matched_sales_30d and total_view_item > 0) else None
            
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
        
        items.sort(key=lambda x: x["total_view_item"], reverse=True)
        
        return {"top_items_by_view_item": items}
    
    products_30d = products_this.get("rolling", {}).get("d30", {}).get("top_products_by_sales", [])
    if SKIP_VIEWITEM:
        viewitem_this = {"top_items_by_view_item": []}
    else:
        viewitem_this = get_viewitem_block(report_month, products_30d)
    
    # -----------------------
    # YoY 데이터 존재 여부 확인
    # -----------------------
    mall_sales_yoy_available = has_rows(
        client,
        f"{PROJECT_ID}.{DATASET}.daily_cafe24_sales",
        "payment_date",
        company_name,
        yoy_start,
        yoy_end
    )
    
    meta_ads_yoy_available = has_rows(
        client,
        f"{PROJECT_ID}.{DATASET}.meta_ads_account_summary",
        "date",
        company_name,
        yoy_start,
        yoy_end
    )
    
    # -----------------------
    # Comparisons
    # -----------------------
    def build_comparisons():
        comparisons = {}
        
        # mall_sales
        net_sales_mom = delta(sales_this["net_sales"], sales_prev["net_sales"])
        net_sales_yoy = delta(sales_this["net_sales"], sales_yoy["net_sales"]) if mall_sales_yoy_available else None
        comparisons["mall_sales"] = {
            "net_sales_mom": net_sales_mom,
            "net_sales_yoy": net_sales_yoy,
            "note_if_base_small_mom": note_if_base_small(sales_prev["net_sales"], MALL_SALES_BASE_SMALL_THRESHOLD),
        }
        
        # meta_ads
        spend_mom = delta(meta_ads_this["spend"], meta_ads_prev["spend"])
        spend_yoy = delta(meta_ads_this["spend"], meta_ads_yoy["spend"]) if meta_ads_yoy_available else None
        roas_mom = delta(meta_ads_this["roas"] or 0, meta_ads_prev["roas"] or 0) if (meta_ads_this["roas"] is not None and meta_ads_prev["roas"] is not None) else None
        cvr_mom = delta(meta_ads_this["cvr"] or 0, meta_ads_prev["cvr"] or 0) if (meta_ads_this["cvr"] is not None and meta_ads_prev["cvr"] is not None) else None
        comparisons["meta_ads"] = {
            "spend_mom": spend_mom,
            "spend_yoy": spend_yoy,
            "roas_mom": roas_mom,
            "cvr_mom": cvr_mom,
            "note_if_base_small_mom": note_if_base_small(meta_ads_prev["spend"], META_ADS_BASE_SMALL_THRESHOLD),
        }
        
        # ga4_traffic
        total_users_mom = delta(ga4_this_totals["total_users"], ga4_prev_totals["total_users"])
        total_users_yoy = delta(ga4_this_totals["total_users"], ga4_yoy_totals["total_users"]) if ga4_yoy_available and ga4_yoy_totals else None
        comparisons["ga4_traffic"] = {
            "total_users_mom": total_users_mom,
            "total_users_yoy": total_users_yoy,
            "note_if_base_small_mom": note_if_base_small(ga4_prev_totals["total_users"], GA4_TRAFFIC_BASE_SMALL_THRESHOLD),
        }
        
        return comparisons
    
    comparisons = build_comparisons()
    
    # -----------------------
    # Forecast next month
    # -----------------------
    def build_forecast_next_month():
        next_report_month = shift_month(report_month, 1)
        next_month_num = int(next_report_month.split("-")[1])
        
        forecast = {
            "month": next_report_month,
            "mall_sales": {},
            "meta_ads": {},
            "ga4_traffic": {},
        }
        
        # 같은 월(month-of-year) 표본 수집
        mall_sales_same_month = []
        meta_ads_same_month = []
        ga4_traffic_same_month = []
        
        for item in monthly_13m:
            item_month = int(item["ym"].split("-")[1])
            if item_month == next_month_num:
                mall_sales_same_month.append(item.get("net_sales", 0))
        
        for item in monthly_13m_meta:
            item_month = int(item["ym"].split("-")[1])
            if item_month == next_month_num:
                meta_ads_same_month.append(item.get("spend", 0))
        
        for item in monthly_13m_ga4:
            item_month = int(item["ym"].split("-")[1])
            if item_month == next_month_num:
                ga4_traffic_same_month.append(item.get("total_users", 0))
        
        def calc_stats(values):
            if not values:
                return {"count": 0, "min": None, "max": None, "median": None}
            return {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "median": statistics.median(values) if len(values) > 0 else None,
            }
        
        forecast["mall_sales"]["net_sales_same_month_stats"] = calc_stats(mall_sales_same_month)
        forecast["meta_ads"]["spend_same_month_stats"] = calc_stats(meta_ads_same_month)
        forecast["ga4_traffic"]["total_users_same_month_stats"] = calc_stats(ga4_traffic_same_month)
        
        return forecast
    
    forecast_next_month = build_forecast_next_month()
    
    # -----------------------
    # Signals (bool/수치만, 판단 단어 금지)
    # -----------------------
    def calculate_signals():
        signals = {}
        
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
        
        products_90d_map = {p.get("product_no"): p for p in products_90d}
        for p in products_30d:
            product_no = p.get("product_no")
            if product_no not in products_90d_map:
                first_order_products.append(p)
        
        first_order_sales = sum(p.get("sales", 0) for p in first_order_products)
        signals["new_product_dependency"] = (
            (first_order_sales / total_30d_sales * 100) >= 30
        ) if total_30d_sales > 0 else False
        
        # mall_sales_mom_pct (수치만)
        net_this = sales_this.get("net_sales", 0)
        net_prev = sales_prev.get("net_sales", 0)
        signals["mall_sales_mom_pct"] = ((net_this - net_prev) / net_prev * 100) if net_prev else None
        
        # note_if_base_small_mom
        signals["note_if_base_small_mom"] = note_if_base_small(net_prev, MALL_SALES_BASE_SMALL_THRESHOLD)
        
        return signals
    
    signals = calculate_signals()
    
    out = {
        "report_meta": {
            "company_name": company_name,
            "report_month": report_month,
            "period_this": {"from": this_start, "to": this_end},
            "period_prev": {"from": prev_start, "to": prev_end},
            "period_yoy": {"from": yoy_start, "to": yoy_end},
            "yoy_available": {
                "mall_sales": mall_sales_yoy_available,
                "meta_ads": meta_ads_yoy_available,
                "ga4_traffic": ga4_yoy_available,
            },
        },
        "facts": {
            "mall_sales": {
                "this": sales_this,
                "prev": sales_prev,
                "yoy": sales_yoy,
                "monthly_13m": monthly_13m,
            },
            "meta_ads": {
                "this": meta_ads_this,
                "prev": meta_ads_prev,
                "yoy": meta_ads_yoy,
                "monthly_13m": monthly_13m_meta,
            },
            "ga4_traffic": {
                "this": ga4_this,
                "prev": ga4_prev,
                "yoy": ga4_yoy,
                "monthly_13m": monthly_13m_ga4,
            },
            "products": {
                "this": products_this,
            },
            "viewitem": {
                "this": viewitem_this,
            },
            "comparisons": comparisons,
            "forecast_next_month": forecast_next_month,
        },
        "signals": signals,
    }
    
    # -----------------------
    # Upsert to BigQuery (optional)
    # -----------------------
    def upsert_snapshot(client, company_name, month_date_iso, snapshot_data):
        """스냅샷을 BigQuery에 upsert"""
        snapshot_data_safe = json_safe(snapshot_data)
        snapshot_json_str = json.dumps(snapshot_data_safe, ensure_ascii=False, sort_keys=True)
        snapshot_hash = hashlib.sha256(snapshot_json_str.encode('utf-8')).hexdigest()
        
        query = f"""
        MERGE `{PROJECT_ID}.{DATASET}.report_monthly_snapshot` T
        USING (
            SELECT
                @company_name AS company_name,
                DATE(@month_date) AS month,
                PARSE_JSON(@snapshot_json) AS snapshot_json,
                @snapshot_hash AS snapshot_hash,
                CURRENT_TIMESTAMP() AS updated_at
        ) S
        ON T.company_name = S.company_name AND T.month = S.month
        WHEN MATCHED THEN UPDATE SET
            snapshot_json = S.snapshot_json,
            snapshot_hash = S.snapshot_hash,
            updated_at = S.updated_at
        WHEN NOT MATCHED THEN
            INSERT (company_name, month, snapshot_json, snapshot_hash, updated_at)
            VALUES (S.company_name, S.month, S.snapshot_json, S.snapshot_hash, S.updated_at)
        """
        
        client.query(
            query,
            job_config=bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("company_name", "STRING", company_name),
                    bigquery.ScalarQueryParameter("month_date", "STRING", month_date_iso),
                    bigquery.ScalarQueryParameter("snapshot_json", "STRING", snapshot_json_str),
                    bigquery.ScalarQueryParameter("snapshot_hash", "STRING", snapshot_hash),
                ]
            ),
        ).result()
    
    # JSON 안전화 적용
    out_safe = json_safe(out)
    
    if upsert_flag:
        month_date_iso = date(year, month, 1).isoformat()
        upsert_snapshot(client, company_name, month_date_iso, out)
    
    print(json.dumps(out_safe, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 4:
        print("Usage: python3 bq_monthly_snapshot.py <company_name> <year> <month> [--upsert]")
        sys.exit(1)
    
    company_name = sys.argv[1]
    year = int(sys.argv[2])
    month = int(sys.argv[3])
    upsert_flag = "--upsert" in sys.argv
    
    run(company_name, year, month, upsert_flag)
