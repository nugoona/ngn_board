import os
import sys
import json
import hashlib
import re
import statistics
from datetime import date, timedelta
from decimal import Decimal
from collections import defaultdict
from google.cloud import bigquery
from google.cloud import storage

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "winged-precept-443218-v8")
DATASET = "ngn_dataset"
GCS_BUCKET = os.environ.get("GCS_BUCKET", "winged-precept-443218-v8.appspot.com")

# 광고 기준
TRAFFIC_TOP_MIN_SPEND = 10_000
TOP_LIMIT = 5

# 4축 확장 상수
PRODUCT_TOP_LIMIT = 50
GA4_TRAFFIC_TOP_LIMIT = 5
VIEWITEM_TOP_LIMIT = 50
PRODUCT_ROLLING_WINDOWS = [30, 90]
VIEWITEM_ATTENTION_MIN_VIEW = 300  # attention_without_conversion 기준 최소 조회수
VIEWITEM_EFFICIENT_MIN_VIEW = 120  # efficient_conversion 기준 최소 조회수
VIEWITEM_EFFICIENT_MIN_QTY_PER_VIEW = 0.010  # efficient_conversion 기준 최소 구매율

# 비교 기준 threshold
MALL_SALES_BASE_SMALL_THRESHOLD = 500000
META_ADS_BASE_SMALL_THRESHOLD = 100000
GA4_TRAFFIC_BASE_SMALL_THRESHOLD = 100

# Viewitem 스킵 플래그
SKIP_VIEWITEM = os.environ.get("SKIP_VIEWITEM", "0") == "1"
SKIP_META_ADS_GOALS = os.environ.get("SKIP_META_ADS_GOALS", "0") == "1"


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


def _goal_from_campaign_name(campaign_name: str) -> str:
    """캠페인명에서 목표 추출: conversion/traffic/awareness/unknown"""
    if not campaign_name:
        return "unknown"
    
    name_lower = campaign_name.lower()
    
    # 전환 (conversion)
    if "전환" in campaign_name or "conversion" in name_lower:
        return "conversion"
    
    # 유입 (traffic)
    if "유입" in campaign_name or "traffic" in name_lower:
        return "traffic"
    
    # 도달 (awareness)
    if "도달" in campaign_name or "awareness" in name_lower or "reach" in name_lower:
        return "awareness"
    
    return "unknown"


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
        # None 값도 유지 (특히 meta_ads_goals 같은 필수 키)
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


def run(company_name: str, year: int, month: int, upsert_flag: bool = False, save_to_gcs_flag: bool = False):
    client = bigquery.Client(project=PROJECT_ID)
    
    report_month = month_to_ym(year, month)
    this_start, this_end = month_range(year, month)
    
    if month == 1:
        prev_y, prev_m = year - 1, 12
    else:
        prev_y, prev_m = year, month - 1
    prev_start, prev_end = month_range(prev_y, prev_m)
    prev_month = month_to_ym(prev_y, prev_m)
    
    yoy_y, yoy_m = year - 1, month
    yoy_start, yoy_end = month_range(yoy_y, yoy_m)
    yoy_month = month_to_ym(yoy_y, yoy_m)
    
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
    
    # ✅ 최적화 1단계: 월간 집계 테이블에서 this/prev/yoy 추출 (raw 테이블 조회 제거)
    # 월간 집계 테이블 사용 (성능 최적화) - 먼저 조회
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
    
    # monthly_13m에서 this/prev/yoy 추출
    def get_monthly_data_from_13m(monthly_list, target_ym):
        """monthly_13m 리스트에서 특정 월 데이터 추출. 없으면 None 반환"""
        for item in monthly_list:
            if item.get("ym") == target_ym:
                return item
        # 데이터가 없으면 None 반환 (실제 수집되지 않은 경우)
        return None
    
    sales_this_data = get_monthly_data_from_13m(monthly_13m, report_month)
    sales_prev_data = get_monthly_data_from_13m(monthly_13m, prev_month)
    sales_yoy_data = get_monthly_data_from_13m(monthly_13m, yoy_month)
    
    # 데이터가 있으면 사용, 없으면 None (실제 수집되지 않은 경우)
    sales_this = {
        "net_sales": float(sales_this_data.get("net_sales", 0)) if sales_this_data else None,
        "total_orders": int(sales_this_data.get("total_orders", 0)) if sales_this_data else None,
        "total_first_order": int(sales_this_data.get("total_first_order", 0)) if sales_this_data else None,
        "total_canceled": int(sales_this_data.get("total_canceled", 0)) if sales_this_data else None,
    } if sales_this_data else None
    
    sales_prev = {
        "net_sales": float(sales_prev_data.get("net_sales", 0)) if sales_prev_data else None,
        "total_orders": int(sales_prev_data.get("total_orders", 0)) if sales_prev_data else None,
        "total_first_order": int(sales_prev_data.get("total_first_order", 0)) if sales_prev_data else None,
        "total_canceled": int(sales_prev_data.get("total_canceled", 0)) if sales_prev_data else None,
    } if sales_prev_data else None
    
    sales_yoy = {
        "net_sales": float(sales_yoy_data.get("net_sales", 0)) if sales_yoy_data else None,
        "total_orders": int(sales_yoy_data.get("total_orders", 0)) if sales_yoy_data else None,
        "total_first_order": int(sales_yoy_data.get("total_first_order", 0)) if sales_yoy_data else None,
        "total_canceled": int(sales_yoy_data.get("total_canceled", 0)) if sales_yoy_data else None,
    } if sales_yoy_data else None
    
    # 일자별 성과 데이터 (daily는 여전히 raw 테이블 사용 - 2단계에서 최적화)
    q_sales_daily = f"""
    SELECT
        payment_date AS date,
        SUM(net_sales) AS net_sales,
        SUM(total_orders) AS total_orders,
        SUM(total_first_order) AS total_first_order,
        SUM(total_canceled) AS total_canceled
    FROM `{PROJECT_ID}.{DATASET}.daily_cafe24_sales`
    WHERE company_name = @company_name
      AND payment_date BETWEEN @start_date AND @end_date
    GROUP BY payment_date
    ORDER BY payment_date
    """
    
    def get_sales_daily(s, e):
        rows = list(
            client.query(
                q_sales_daily,
                job_config=bigquery.QueryJobConfig(
                    query_parameters=[
                        bigquery.ScalarQueryParameter("company_name", "STRING", company_name),
                        bigquery.ScalarQueryParameter("start_date", "DATE", s),
                        bigquery.ScalarQueryParameter("end_date", "DATE", e),
                    ]
                ),
            ).result()
        )
        
        return [
            {
                "date": row.date.isoformat() if row.date else None,
                "net_sales": float(row.net_sales or 0),
                "total_orders": int(row.total_orders or 0),
                "total_first_order": int(row.total_first_order or 0),
                "total_canceled": int(row.total_canceled or 0),
            }
            for row in rows
        ]
    
    daily_this = get_sales_daily(this_start, this_end)
    daily_prev = get_sales_daily(prev_start, prev_end)
    daily_yoy = get_sales_daily(yoy_start, yoy_end)
    
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
    
    # ✅ 최적화 1단계: 월간 집계 테이블에서 this/prev/yoy 추출 (raw 테이블 조회 제거)
    # 월간 집계 테이블 사용 (성능 최적화) - 먼저 조회
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
    
    # monthly_13m_meta에서 this/prev/yoy 추출
    def get_monthly_meta_from_13m(monthly_list, target_ym):
        """monthly_13m_meta 리스트에서 특정 월 데이터 추출. 없으면 None 반환"""
        for item in monthly_list:
            if item.get("ym") == target_ym:
                return item
        # 데이터가 없으면 None 반환 (실제 수집되지 않은 경우)
        return None
    
    meta_ads_this_data = get_monthly_meta_from_13m(monthly_13m_meta, report_month)
    meta_ads_prev_data = get_monthly_meta_from_13m(monthly_13m_meta, prev_month)
    meta_ads_yoy_data = get_monthly_meta_from_13m(monthly_13m_meta, yoy_month)
    
    # 데이터가 있으면 사용, 없으면 None (실제 수집되지 않은 경우)
    meta_ads_this = {
        "spend": float(meta_ads_this_data.get("spend", 0)) if meta_ads_this_data else None,
        "impressions": int(meta_ads_this_data.get("impressions", 0)) if meta_ads_this_data else None,
        "clicks": int(meta_ads_this_data.get("clicks", 0)) if meta_ads_this_data else None,
        "purchases": int(meta_ads_this_data.get("purchases", 0)) if meta_ads_this_data else None,
        "purchase_value": float(meta_ads_this_data.get("purchase_value", 0)) if meta_ads_this_data else None,
        "roas": meta_ads_this_data.get("roas") if meta_ads_this_data else None,
        "cpc": meta_ads_this_data.get("cpc") if meta_ads_this_data else None,
        "ctr": meta_ads_this_data.get("ctr") if meta_ads_this_data else None,
        "cvr": meta_ads_this_data.get("cvr") if meta_ads_this_data else None,
    } if meta_ads_this_data else None
    
    meta_ads_prev = {
        "spend": float(meta_ads_prev_data.get("spend", 0)) if meta_ads_prev_data else None,
        "impressions": int(meta_ads_prev_data.get("impressions", 0)) if meta_ads_prev_data else None,
        "clicks": int(meta_ads_prev_data.get("clicks", 0)) if meta_ads_prev_data else None,
        "purchases": int(meta_ads_prev_data.get("purchases", 0)) if meta_ads_prev_data else None,
        "purchase_value": float(meta_ads_prev_data.get("purchase_value", 0)) if meta_ads_prev_data else None,
        "roas": meta_ads_prev_data.get("roas") if meta_ads_prev_data else None,
        "cpc": meta_ads_prev_data.get("cpc") if meta_ads_prev_data else None,
        "ctr": meta_ads_prev_data.get("ctr") if meta_ads_prev_data else None,
        "cvr": meta_ads_prev_data.get("cvr") if meta_ads_prev_data else None,
    } if meta_ads_prev_data else None
    
    meta_ads_yoy = {
        "spend": float(meta_ads_yoy_data.get("spend", 0)) if meta_ads_yoy_data else None,
        "impressions": int(meta_ads_yoy_data.get("impressions", 0)) if meta_ads_yoy_data else None,
        "clicks": int(meta_ads_yoy_data.get("clicks", 0)) if meta_ads_yoy_data else None,
        "purchases": int(meta_ads_yoy_data.get("purchases", 0)) if meta_ads_yoy_data else None,
        "purchase_value": float(meta_ads_yoy_data.get("purchase_value", 0)) if meta_ads_yoy_data else None,
        "roas": meta_ads_yoy_data.get("roas") if meta_ads_yoy_data else None,
        "cpc": meta_ads_yoy_data.get("cpc") if meta_ads_yoy_data else None,
        "ctr": meta_ads_yoy_data.get("ctr") if meta_ads_yoy_data else None,
        "cvr": meta_ads_yoy_data.get("cvr") if meta_ads_yoy_data else None,
    } if meta_ads_yoy_data else None
    
    # -----------------------
    # Meta Ads Goals (목표별 분해 및 Top Ad)
    # -----------------------
    def get_meta_ads_goals(s, e):
        """목표별 분해 및 Top Ad 조회 (단일 기간)"""
        if SKIP_META_ADS_GOALS:
            return {
                "by_goal": {
                    "conversion": {"spend": 0.0, "impressions": 0, "clicks": 0, "purchases": 0, "purchase_value": 0.0, "roas": None, "cpc": None, "ctr": None, "cvr": None, "spend_share_pct": None},
                    "traffic": {"spend": 0.0, "impressions": 0, "clicks": 0, "purchases": 0, "purchase_value": 0.0, "roas": None, "cpc": None, "ctr": None, "cvr": None, "spend_share_pct": None},
                    "awareness": {"spend": 0.0, "impressions": 0, "clicks": 0, "purchases": 0, "purchase_value": 0.0, "roas": None, "cpc": None, "ctr": None, "cvr": None, "spend_share_pct": None},
                    "unknown": {"spend": 0.0, "impressions": 0, "clicks": 0, "purchases": 0, "purchase_value": 0.0, "roas": None, "cpc": None, "ctr": None, "cvr": None, "spend_share_pct": None},
                },
                "top_ads": {
                    "conversion_top_by_purchases": [],
                    "traffic_top_by_ctr": [],
                    "awareness_top_by_spend": [],
                }
            }
        
        q_meta_ads_goals = f"""
        SELECT
            ad_id,
            ad_name,
            campaign_name,
            SUM(spend) AS spend,
            SUM(impressions) AS impressions,
            SUM(clicks) AS clicks,
            SUM(purchases) AS purchases,
            SUM(purchase_value) AS purchase_value
        FROM `{PROJECT_ID}.{DATASET}.meta_ads_ad_summary`
        WHERE company_name = @company_name
          AND date BETWEEN @start_date AND @end_date
        GROUP BY ad_id, ad_name, campaign_name
        """
        
        rows = list(
            client.query(
                q_meta_ads_goals,
                job_config=bigquery.QueryJobConfig(
                    query_parameters=[
                        bigquery.ScalarQueryParameter("company_name", "STRING", company_name),
                        bigquery.ScalarQueryParameter("start_date", "DATE", s),
                        bigquery.ScalarQueryParameter("end_date", "DATE", e),
                    ]
                ),
            ).result()
        )
        
        # 목표별 집계
        by_goal = defaultdict(lambda: {
            "spend": 0.0,
            "impressions": 0,
            "clicks": 0,
            "purchases": 0,
            "purchase_value": 0.0,
        })
        
        # Top Ad 후보
        conversion_ads = []
        traffic_ads = []
        awareness_ads = []
        
        total_spend = 0.0
        
        for row in rows:
            goal = _goal_from_campaign_name(row.campaign_name or "")
            spend = float(row.spend or 0)
            impressions = int(row.impressions or 0)
            clicks = int(row.clicks or 0)
            purchases = int(row.purchases or 0)
            purchase_value = float(row.purchase_value or 0)
            
            by_goal[goal]["spend"] += spend
            by_goal[goal]["impressions"] += impressions
            by_goal[goal]["clicks"] += clicks
            by_goal[goal]["purchases"] += purchases
            by_goal[goal]["purchase_value"] += purchase_value
            total_spend += spend
            
            # Top Ad 후보 추가
            ad_data = {
                "ad_id": str(row.ad_id) if row.ad_id else None,
                "ad_name": row.ad_name or "",
                "campaign_name": row.campaign_name or "",
                "spend": spend,
                "impressions": impressions,
                "clicks": clicks,
                "purchases": purchases,
                "purchase_value": purchase_value,
            }
            
            if goal == "conversion":
                conversion_ads.append(ad_data)
            elif goal == "traffic":
                traffic_ads.append(ad_data)
            elif goal == "awareness":
                awareness_ads.append(ad_data)
        
        # 목표별 지표 계산
        result_by_goal = {}
        for goal in ["conversion", "traffic", "awareness", "unknown"]:
            data = by_goal[goal]
            spend = data["spend"]
            impressions = data["impressions"]
            clicks = data["clicks"]
            purchases = data["purchases"]
            purchase_value = data["purchase_value"]
            
            result_by_goal[goal] = {
                "spend": spend,
                "impressions": impressions,
                "clicks": clicks,
                "purchases": purchases,
                "purchase_value": purchase_value,
                "roas": (purchase_value / spend * 100) if spend > 0 else None,
                "cpc": (spend / clicks) if clicks > 0 else None,
                "ctr": (clicks / impressions * 100) if impressions > 0 else None,
                "cvr": (purchases / clicks * 100) if clicks > 0 else None,
                "spend_share_pct": (spend / total_spend * 100) if total_spend > 0 else None,
            }
        
        # Top Ad 정렬 및 선택
        # 전환: purchases DESC (동률이면 purchase_value DESC, spend DESC)
        conversion_ads.sort(key=lambda x: (-x["purchases"], -x["purchase_value"], -x["spend"]))
        conversion_top = []
        for ad in conversion_ads[:TOP_LIMIT]:
            ad_spend = ad["spend"]
            ad_clicks = ad["clicks"]
            ad_purchases = ad["purchases"]
            ad_purchase_value = ad["purchase_value"]
            conversion_top.append({
                "ad_id": ad["ad_id"],
                "ad_name": ad["ad_name"],
                "campaign_name": ad["campaign_name"],
                "spend": ad_spend,
                "purchases": ad_purchases,
                "purchase_value": ad_purchase_value,
                "roas": (ad_purchase_value / ad_spend * 100) if ad_spend > 0 else None,
                "cpa": (ad_spend / ad_purchases) if ad_purchases > 0 else None,
                "cvr": (ad_purchases / ad_clicks * 100) if ad_clicks > 0 else None,
                "clicks": ad["clicks"],
                "impressions": ad["impressions"],
            })
        
        # 유입: CTR DESC (단 spend >= TRAFFIC_TOP_MIN_SPEND, 동률이면 clicks DESC)
        traffic_ads_filtered = [ad for ad in traffic_ads if ad["spend"] >= TRAFFIC_TOP_MIN_SPEND]
        for ad in traffic_ads_filtered:
            ad["ctr"] = (ad["clicks"] / ad["impressions"] * 100) if ad["impressions"] > 0 else 0
            ad["cpc"] = (ad["spend"] / ad["clicks"]) if ad["clicks"] > 0 else None
        traffic_ads_filtered.sort(key=lambda x: (-x["ctr"], -x["clicks"]))
        traffic_top = []
        for ad in traffic_ads_filtered[:TOP_LIMIT]:
            traffic_top.append({
                "ad_id": ad["ad_id"],
                "ad_name": ad["ad_name"],
                "campaign_name": ad["campaign_name"],
                "spend": ad["spend"],
                "ctr": round(ad["ctr"], 2),
                "cpc": round(ad["cpc"], 2) if ad["cpc"] is not None else None,
                "clicks": ad["clicks"],
                "impressions": ad["impressions"],
            })
        
        # 도달: spend DESC
        awareness_ads.sort(key=lambda x: -x["spend"])
        awareness_top = []
        for ad in awareness_ads[:TOP_LIMIT]:
            ad_spend = ad["spend"]
            ad_impressions = ad["impressions"]
            awareness_top.append({
                "ad_id": ad["ad_id"],
                "ad_name": ad["ad_name"],
                "campaign_name": ad["campaign_name"],
                "spend": ad_spend,
                "impressions": ad_impressions,
                "cpm": (ad_spend / ad_impressions * 1000) if ad_impressions > 0 else None,
            })
        
        return {
            "by_goal": result_by_goal,
            "top_ads": {
                "conversion_top_by_purchases": conversion_top,
                "traffic_top_by_ctr": traffic_top,
                "awareness_top_by_spend": awareness_top,
            }
        }
    
    def get_meta_ads_goals_multi(ranges):
        """✅ 최적화: this/prev/yoy를 한 번에 조회 후 Python에서 분해
        ranges: {"this": (start, end), "prev": (start, end), "yoy": (start, end)} 형태
        """
        if SKIP_META_ADS_GOALS:
            empty_result = {
                "by_goal": {
                    "conversion": {"spend": 0.0, "impressions": 0, "clicks": 0, "purchases": 0, "purchase_value": 0.0, "roas": None, "cpc": None, "ctr": None, "cvr": None, "spend_share_pct": None},
                    "traffic": {"spend": 0.0, "impressions": 0, "clicks": 0, "purchases": 0, "purchase_value": 0.0, "roas": None, "cpc": None, "ctr": None, "cvr": None, "spend_share_pct": None},
                    "awareness": {"spend": 0.0, "impressions": 0, "clicks": 0, "purchases": 0, "purchase_value": 0.0, "roas": None, "cpc": None, "ctr": None, "cvr": None, "spend_share_pct": None},
                    "unknown": {"spend": 0.0, "impressions": 0, "clicks": 0, "purchases": 0, "purchase_value": 0.0, "roas": None, "cpc": None, "ctr": None, "cvr": None, "spend_share_pct": None},
                },
                "top_ads": {
                    "conversion_top_by_purchases": [],
                    "traffic_top_by_ctr": [],
                    "awareness_top_by_spend": [],
                }
            }
            return {
                "this": empty_result,
                "prev": empty_result,
                "yoy": empty_result if "yoy" in ranges else None
            }
        
        # 전체 기간(this/prev/yoy) 최소~최대 날짜 계산
        all_dates = []
        for key, (s, e) in ranges.items():
            if s and e:
                all_dates.extend([s, e])
        
        if not all_dates:
            return {"this": None, "prev": None, "yoy": None}
        
        min_date = min(all_dates)
        max_date = max(all_dates)
        
        # 전체 기간을 한 번에 조회
        q_meta_ads_goals_multi = f"""
        SELECT
            FORMAT_DATE('%Y-%m', date) AS ym,
            ad_id,
            ad_name,
            campaign_name,
            SUM(spend) AS spend,
            SUM(impressions) AS impressions,
            SUM(clicks) AS clicks,
            SUM(purchases) AS purchases,
            SUM(purchase_value) AS purchase_value
        FROM `{PROJECT_ID}.{DATASET}.meta_ads_ad_summary`
        WHERE company_name = @company_name
          AND date >= @min_date
          AND date <= @max_date
        GROUP BY ym, ad_id, ad_name, campaign_name
        """
        
        rows = list(
            client.query(
                q_meta_ads_goals_multi,
                job_config=bigquery.QueryJobConfig(
                    query_parameters=[
                        bigquery.ScalarQueryParameter("company_name", "STRING", company_name),
                        bigquery.ScalarQueryParameter("min_date", "DATE", min_date),
                        bigquery.ScalarQueryParameter("max_date", "DATE", max_date),
                    ]
                ),
            ).result()
        )
        
        # 각 기간별로 분류 (월(ym) 기준)
        period_ym_map = {}
        for period_key, (period_start, _period_end) in ranges.items():
            if period_start:
                period_ym_map[period_key] = period_start[:7]  # "YYYY-MM"
        
        rows_by_period = defaultdict(list)
        for row in rows:
            row_ym = row.ym  # "YYYY-MM"
            for period_key, target_ym in period_ym_map.items():
                if row_ym == target_ym:
                    rows_by_period[period_key].append(row)
                    break
        
        # 각 기간별로 get_meta_ads_goals와 동일한 로직 적용
        result = {}
        for period_key in ["this", "prev", "yoy"]:
            if period_key not in ranges or not ranges[period_key][0]:
                result[period_key] = None
                continue
            
            period_rows = rows_by_period.get(period_key, [])
            if not period_rows:
                result[period_key] = None
                continue
            
            # 목표별 집계
            by_goal = defaultdict(lambda: {
                "spend": 0.0,
                "impressions": 0,
                "clicks": 0,
                "purchases": 0,
                "purchase_value": 0.0,
            })
            
            # Top Ad 후보
            conversion_ads = []
            traffic_ads = []
            awareness_ads = []
            
            total_spend = 0.0
            
            for row in period_rows:
                goal = _goal_from_campaign_name(row.campaign_name or "")
                spend = float(row.spend or 0)
                impressions = int(row.impressions or 0)
                clicks = int(row.clicks or 0)
                purchases = int(row.purchases or 0)
                purchase_value = float(row.purchase_value or 0)
                
                by_goal[goal]["spend"] += spend
                by_goal[goal]["impressions"] += impressions
                by_goal[goal]["clicks"] += clicks
                by_goal[goal]["purchases"] += purchases
                by_goal[goal]["purchase_value"] += purchase_value
                total_spend += spend
                
                # Top Ad 후보 추가
                ad_data = {
                    "ad_id": str(row.ad_id) if row.ad_id else None,
                    "ad_name": row.ad_name or "",
                    "campaign_name": row.campaign_name or "",
                    "spend": spend,
                    "impressions": impressions,
                    "clicks": clicks,
                    "purchases": purchases,
                    "purchase_value": purchase_value,
                }
                
                if goal == "conversion":
                    conversion_ads.append(ad_data)
                elif goal == "traffic":
                    traffic_ads.append(ad_data)
                elif goal == "awareness":
                    awareness_ads.append(ad_data)
            
            # 목표별 지표 계산
            result_by_goal = {}
            for goal in ["conversion", "traffic", "awareness", "unknown"]:
                data = by_goal[goal]
                spend = data["spend"]
                impressions = data["impressions"]
                clicks = data["clicks"]
                purchases = data["purchases"]
                purchase_value = data["purchase_value"]
                
                result_by_goal[goal] = {
                    "spend": spend,
                    "impressions": impressions,
                    "clicks": clicks,
                    "purchases": purchases,
                    "purchase_value": purchase_value,
                    "roas": (purchase_value / spend * 100) if spend > 0 else None,
                    "cpc": (spend / clicks) if clicks > 0 else None,
                    "ctr": (clicks / impressions * 100) if impressions > 0 else None,
                    "cvr": (purchases / clicks * 100) if clicks > 0 else None,
                    "spend_share_pct": (spend / total_spend * 100) if total_spend > 0 else None,
                }
            
            # Top Ad 정렬 및 선택
            conversion_ads.sort(key=lambda x: (-x["purchases"], -x["purchase_value"], -x["spend"]))
            conversion_top = []
            for ad in conversion_ads[:TOP_LIMIT]:
                ad_spend = ad["spend"]
                ad_clicks = ad["clicks"]
                ad_purchases = ad["purchases"]
                ad_purchase_value = ad["purchase_value"]
                conversion_top.append({
                    "ad_id": ad["ad_id"],
                    "ad_name": ad["ad_name"],
                    "campaign_name": ad["campaign_name"],
                    "spend": ad_spend,
                    "purchases": ad_purchases,
                    "purchase_value": ad_purchase_value,
                    "roas": (ad_purchase_value / ad_spend * 100) if ad_spend > 0 else None,
                    "cpa": (ad_spend / ad_purchases) if ad_purchases > 0 else None,
                    "cvr": (ad_purchases / ad_clicks * 100) if ad_clicks > 0 else None,
                    "clicks": ad["clicks"],
                    "impressions": ad["impressions"],
                })
            
            traffic_ads_filtered = [ad for ad in traffic_ads if ad["spend"] >= TRAFFIC_TOP_MIN_SPEND]
            for ad in traffic_ads_filtered:
                ad["ctr"] = (ad["clicks"] / ad["impressions"] * 100) if ad["impressions"] > 0 else 0
                ad["cpc"] = (ad["spend"] / ad["clicks"]) if ad["clicks"] > 0 else None
            traffic_ads_filtered.sort(key=lambda x: (-x["ctr"], -x["clicks"]))
            traffic_top = []
            for ad in traffic_ads_filtered[:TOP_LIMIT]:
                traffic_top.append({
                    "ad_id": ad["ad_id"],
                    "ad_name": ad["ad_name"],
                    "campaign_name": ad["campaign_name"],
                    "spend": ad["spend"],
                    "ctr": round(ad["ctr"], 2),
                    "cpc": round(ad["cpc"], 2) if ad["cpc"] is not None else None,
                    "clicks": ad["clicks"],
                    "impressions": ad["impressions"],
                })
            
            awareness_ads.sort(key=lambda x: -x["spend"])
            awareness_top = []
            for ad in awareness_ads[:TOP_LIMIT]:
                ad_spend = ad["spend"]
                ad_impressions = ad["impressions"]
                awareness_top.append({
                    "ad_id": ad["ad_id"],
                    "ad_name": ad["ad_name"],
                    "campaign_name": ad["campaign_name"],
                    "spend": ad_spend,
                    "impressions": ad_impressions,
                    "cpm": (ad_spend / ad_impressions * 1000) if ad_impressions > 0 else None,
                })
            
            result[period_key] = {
                "by_goal": result_by_goal,
                "top_ads": {
                    "conversion_top_by_purchases": conversion_top,
                    "traffic_top_by_ctr": traffic_top,
                    "awareness_top_by_spend": awareness_top,
                }
            }
        
        return result
    
    # -----------------------
    # Meta Ads Goals (목표별 분해 및 Top Ad) - SKIP_META_ADS_GOALS 체크
    # -----------------------
    # meta_ads_yoy_available은 comparisons에서도 사용되므로 먼저 초기화
    meta_ads_yoy_available = False
    
    if SKIP_META_ADS_GOALS:
        meta_ads_goals_this = None
        meta_ads_goals_prev = None
        meta_ads_goals_yoy = None
        meta_ads_benchmarks = None
    else:
        # (B) YoY rows 존재 체크
        q_meta_ads_exists = f"""
        SELECT COUNT(1) AS cnt
        FROM `{PROJECT_ID}.{DATASET}.meta_ads_account_summary`
        WHERE company_name = @company_name
          AND date BETWEEN @start_date AND @end_date
        """
        
        def has_meta_ads_rows(s, e):
            rows = list(
                client.query(
                    q_meta_ads_exists,
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
                return False
            return int(rows[0].cnt or 0) > 0
        
        meta_ads_yoy_available = has_meta_ads_rows(yoy_start, yoy_end)
        
        # ✅ 최적화: this/prev/yoy를 한 번에 조회
        ranges = {
            "this": (this_start, this_end),
            "prev": (prev_start, prev_end),
            "yoy": (yoy_start, yoy_end) if meta_ads_yoy_available else None
        }
        if ranges["yoy"] is None:
            del ranges["yoy"]
        
        goals_multi = get_meta_ads_goals_multi(ranges)
        meta_ads_goals_this = goals_multi.get("this")
        meta_ads_goals_prev = goals_multi.get("prev")
        meta_ads_goals_yoy = goals_multi.get("yoy") if meta_ads_yoy_available else None
        
        # -----------------------
        # Meta Ads Benchmarks (최근 6개월 기준치)
        # -----------------------
        def build_meta_ads_benchmarks_from_monthly_13m(monthly_13m_data):
            """최근 6개월 기준치 계산 (monthly_13m_meta 기반, goal별 분해는 ad_summary에서)"""
            # ✅ 최적화: 6개월 전체를 한 번에 조회 후 Python에서 월별 분해
            # 최근 6개월 YM 목록
            end_ym = report_month
            month_yms = [shift_month(end_ym, -i) for i in range(6)]
            
            # 6개월 전체 기간 계산
            start_ym = shift_month(end_ym, -5)
            start_date_iso, _ = month_range_exclusive(start_ym)
            end_excl_iso, _ = month_range_exclusive(shift_month(end_ym, 1))
            
            # 6개월 전체를 한 번에 조회
            q_6m_goals = f"""
            SELECT
                FORMAT_DATE('%Y-%m', date) AS ym,
                campaign_name,
                SUM(spend) AS spend,
                SUM(impressions) AS impressions,
                SUM(clicks) AS clicks,
                SUM(purchases) AS purchases,
                SUM(purchase_value) AS purchase_value
            FROM `{PROJECT_ID}.{DATASET}.meta_ads_ad_summary`
            WHERE company_name = @company_name
              AND date >= @start_date
              AND date < @end_exclusive_date
            GROUP BY ym, campaign_name
            """
            
            rows = list(
                client.query(
                    q_6m_goals,
                    job_config=bigquery.QueryJobConfig(
                        query_parameters=[
                            bigquery.ScalarQueryParameter("company_name", "STRING", company_name),
                            bigquery.ScalarQueryParameter("start_date", "DATE", start_date_iso),
                            bigquery.ScalarQueryParameter("end_exclusive_date", "DATE", end_excl_iso),
                        ]
                    ),
                ).result()
            )
            
            # 월별로 그룹화
            by_month = defaultdict(list)
            for r in rows:
                by_month[r.ym].append(r)
            
            # 각 월별 goal 집계
            traffic_cpcs = []
            traffic_ctrs = []
            conversion_cvrs = []
            conversion_cpas = []
            count_months = 0
            
            for ym in month_yms:
                month_rows = by_month.get(ym, [])
                if not month_rows:
                    continue
                
                count_months += 1
                
                # 목표별 집계
                traffic_data = {"spend": 0.0, "clicks": 0, "impressions": 0}
                conversion_data = {"spend": 0.0, "clicks": 0, "purchases": 0}
                
                for row in month_rows:
                    goal = _goal_from_campaign_name(row.campaign_name or "")
                    spend = float(row.spend or 0)
                    clicks = int(row.clicks or 0)
                    impressions = int(row.impressions or 0)
                    purchases = int(row.purchases or 0)
                    
                    if goal == "traffic":
                        traffic_data["spend"] += spend
                        traffic_data["clicks"] += clicks
                        traffic_data["impressions"] += impressions
                    elif goal == "conversion":
                        conversion_data["spend"] += spend
                        conversion_data["clicks"] += clicks
                        conversion_data["purchases"] += purchases
                
                # Traffic: CPC, CTR
                if traffic_data["clicks"] > 0:
                    cpc = traffic_data["spend"] / traffic_data["clicks"]
                    traffic_cpcs.append(cpc)
                if traffic_data["impressions"] > 0:
                    ctr = (traffic_data["clicks"] / traffic_data["impressions"]) * 100
                    traffic_ctrs.append(ctr)
                
                # Conversion: CVR, CPA
                if conversion_data["clicks"] > 0:
                    cvr = (conversion_data["purchases"] / conversion_data["clicks"]) * 100
                    conversion_cvrs.append(cvr)
                if conversion_data["purchases"] > 0:
                    cpa = conversion_data["spend"] / conversion_data["purchases"]
                    conversion_cpas.append(cpa)
            
            # 평균/중앙값 계산
            traffic_avg_cpc = statistics.mean(traffic_cpcs) if traffic_cpcs else None
            traffic_median_cpc = statistics.median(traffic_cpcs) if traffic_cpcs else None
            traffic_avg_ctr = statistics.mean(traffic_ctrs) if traffic_ctrs else None
            
            conversion_avg_cvr = statistics.mean(conversion_cvrs) if conversion_cvrs else None
            conversion_median_cvr = statistics.median(conversion_cvrs) if conversion_cvrs else None
            conversion_avg_cpa = statistics.mean(conversion_cpas) if conversion_cpas else None
            conversion_median_cpa = statistics.median(conversion_cpas) if conversion_cpas else None
            
            return {
                "last_6m": {
                    "traffic": {
                        "avg_cpc": round(traffic_avg_cpc, 2) if traffic_avg_cpc is not None else None,
                        "median_cpc": round(traffic_median_cpc, 2) if traffic_median_cpc is not None else None,
                        "avg_ctr": round(traffic_avg_ctr, 2) if traffic_avg_ctr is not None else None,
                        "count_months": count_months,
                    },
                    "conversion": {
                        "avg_cvr": round(conversion_avg_cvr, 2) if conversion_avg_cvr is not None else None,
                        "median_cvr": round(conversion_median_cvr, 2) if conversion_median_cvr is not None else None,
                        "avg_cpa": round(conversion_avg_cpa, 2) if conversion_avg_cpa is not None else None,
                        "median_cpa": round(conversion_median_cpa, 2) if conversion_median_cpa is not None else None,
                        "count_months": count_months,
                    }
                }
            }
        
        # (D) 6개월 벤치마크는 monthly_13m_meta 기반으로 계산
        meta_ads_benchmarks = build_meta_ads_benchmarks_from_monthly_13m(monthly_13m_meta)
    
    # -----------------------
    # GA4 traffic
    # -----------------------
    q_ga4_traffic = f"""
    WITH ga4_totals AS (
        SELECT
            SUM(total_users) AS total_users,
            SUM(screen_page_views) AS screen_page_views,
            SUM(event_count) AS event_count
        FROM `{PROJECT_ID}.{DATASET}.ga4_traffic_ngn`
        WHERE company_name = @company_name
          AND event_date BETWEEN @start_date AND @end_date
    ),
    cart_signup_totals AS (
        SELECT
            COALESCE(SUM(cart_users), 0) AS add_to_cart_users,
            COALESCE(SUM(signup_count), 0) AS sign_up_users
        FROM `{PROJECT_ID}.{DATASET}.performance_summary_ngn`
        WHERE company_name = @company_name
          AND DATE(date) BETWEEN @start_date AND @end_date
    )
    SELECT
        COALESCE(g.total_users, 0) AS total_users,
        COALESCE(g.screen_page_views, 0) AS screen_page_views,
        COALESCE(g.event_count, 0) AS event_count,
        COALESCE(c.add_to_cart_users, 0) AS add_to_cart_users,
        COALESCE(c.sign_up_users, 0) AS sign_up_users
    FROM (SELECT 1 AS dummy) dummy
    LEFT JOIN ga4_totals g ON TRUE
    LEFT JOIN cart_signup_totals c ON TRUE
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
                "add_to_cart_users": 0,
                "sign_up_users": 0,
            }
        
        row = rows[0]
        return {
            "total_users": int(row.total_users or 0),
            "screen_page_views": int(row.screen_page_views or 0),
            "event_count": int(row.event_count or 0),
            "add_to_cart_users": int(row.add_to_cart_users or 0),
            "sign_up_users": int(row.sign_up_users or 0),
        }
    
    q_ga4_top_sources = f"""
    SELECT
        first_user_source AS source,
        SUM(total_users) AS total_users,
        SUM(screen_page_views) AS screen_page_views,
        -- 이탈율 가중평균 계산
        SAFE_DIVIDE(
            SUM(IFNULL(bounce_rate, 0) * total_users),
            SUM(total_users)
        ) AS bounce_rate
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
                "bounce_rate": round(float(r.bounce_rate or 0), 2) if r.bounce_rate is not None else None,
            }
            for r in rows
        ]
    
    # ✅ 최적화 1단계: 월간 집계 테이블에서 this/prev/yoy 추출 (raw 테이블 조회 제거)
    # 월간 집계 테이블 사용 (성능 최적화) - 먼저 조회
    monthly_13m_ga4_raw = query_monthly_13m_from_monthly_table(
        client,
        f"{PROJECT_ID}.{DATASET}.ga4_traffic_monthly",
        company_name,
        report_month,
        """
        SUM(total_users) AS total_users,
        SUM(screen_page_views) AS screen_page_views,
        SUM(event_count) AS event_count,
        SUM(add_to_cart_users) AS add_to_cart_users,
        SUM(sign_up_users) AS sign_up_users
        """
    )
    
    monthly_13m_ga4 = [
        {"ym": ym, **metrics}
        for ym, metrics in sorted(monthly_13m_ga4_raw.items())
    ]
    
    # monthly_13m_ga4에서 this/prev/yoy totals 추출
    def get_monthly_ga4_from_13m(monthly_list, target_ym):
        """monthly_13m_ga4 리스트에서 특정 월 데이터 추출. 없으면 None 반환"""
        for item in monthly_list:
            if item.get("ym") == target_ym:
                return item
        # 데이터가 없으면 None 반환 (실제 수집되지 않은 경우)
        return None
    
    ga4_this_data = get_monthly_ga4_from_13m(monthly_13m_ga4, report_month)
    ga4_prev_data = get_monthly_ga4_from_13m(monthly_13m_ga4, prev_month)
    ga4_yoy_data = get_monthly_ga4_from_13m(monthly_13m_ga4, yoy_month)
    
    # ✅ 최적화: 모든 totals 데이터를 월간 집계 테이블에서 가져옴 (raw 테이블 조회 제거)
    # 데이터가 있으면 사용, 없으면 None (실제 수집되지 않은 경우)
    ga4_this_totals = {
        "total_users": int(ga4_this_data.get("total_users", 0)) if ga4_this_data else None,
        "screen_page_views": int(ga4_this_data.get("screen_page_views", 0)) if ga4_this_data else None,
        "event_count": int(ga4_this_data.get("event_count", 0)) if ga4_this_data else None,
        "add_to_cart_users": int(ga4_this_data.get("add_to_cart_users", 0)) if ga4_this_data else None,
        "sign_up_users": int(ga4_this_data.get("sign_up_users", 0)) if ga4_this_data else None,
    } if ga4_this_data else None
    
    ga4_prev_totals = {
        "total_users": int(ga4_prev_data.get("total_users", 0)) if ga4_prev_data else None,
        "screen_page_views": int(ga4_prev_data.get("screen_page_views", 0)) if ga4_prev_data else None,
        "event_count": int(ga4_prev_data.get("event_count", 0)) if ga4_prev_data else None,
        "add_to_cart_users": int(ga4_prev_data.get("add_to_cart_users", 0)) if ga4_prev_data else None,
        "sign_up_users": int(ga4_prev_data.get("sign_up_users", 0)) if ga4_prev_data else None,
    } if ga4_prev_data else None
    
    # YoY 데이터 존재 여부 확인 (top_sources는 여전히 raw 테이블 필요)
    ga4_yoy_available = has_rows(
        client,
        f"{PROJECT_ID}.{DATASET}.ga4_traffic_ngn",
        "event_date",
        company_name,
        yoy_start,
        yoy_end
    )
    
    if ga4_yoy_available and ga4_yoy_data:
        ga4_yoy_totals = {
            "total_users": int(ga4_yoy_data.get("total_users", 0)),
            "screen_page_views": int(ga4_yoy_data.get("screen_page_views", 0)),
            "event_count": int(ga4_yoy_data.get("event_count", 0)),
            "add_to_cart_users": int(ga4_yoy_data.get("add_to_cart_users", 0)),
            "sign_up_users": int(ga4_yoy_data.get("sign_up_users", 0)),
        }
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
            
            # 효율성 플래그
            efficient_conversion = (
                total_view_item >= VIEWITEM_EFFICIENT_MIN_VIEW and
                qty_per_view is not None and
                qty_per_view >= VIEWITEM_EFFICIENT_MIN_QTY_PER_VIEW
            )
            
            high_attention_and_high_conversion = (
                total_view_item >= VIEWITEM_ATTENTION_MIN_VIEW and
                qty_per_view is not None and
                qty_per_view >= VIEWITEM_EFFICIENT_MIN_QTY_PER_VIEW
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
                "efficient_conversion": efficient_conversion,
                "high_attention_and_high_conversion": high_attention_and_high_conversion,
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
    
    # meta_ads_yoy_available은 goals 블록에서 체크됨
    # SKIP_META_ADS_GOALS=1일 때는 False로 유지됨
    # comparisons에서 사용하기 위해 goals 블록 밖에서도 체크 필요
    if SKIP_META_ADS_GOALS:
        # SKIP_META_ADS_GOALS=1일 때만 여기서 체크 (goals 블록이 실행되지 않으므로)
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
    def build_meta_ads_goals_comparisons(meta_ads_goals_this, meta_ads_goals_prev, meta_ads_goals_yoy):
        """Meta Ads Goals별 비교 생성"""
        if meta_ads_goals_this is None or meta_ads_goals_prev is None:
            return None
        
        by_goal_this = meta_ads_goals_this.get("by_goal", {})
        by_goal_prev = meta_ads_goals_prev.get("by_goal", {})
        by_goal_yoy = meta_ads_goals_yoy.get("by_goal", {}) if meta_ads_goals_yoy else {}
        
        # 모든 goal 키 수집 (conversion, traffic, awareness, unknown)
        all_goals = set(["conversion", "traffic", "awareness", "unknown"])
        all_goals.update(by_goal_this.keys())
        all_goals.update(by_goal_prev.keys())
        if meta_ads_goals_yoy:
            all_goals.update(by_goal_yoy.keys())
        
        result_mom = {}
        result_yoy = {} if meta_ads_goals_yoy else None
        
        for goal in sorted(all_goals):
            goal_this = by_goal_this.get(goal, {})
            goal_prev = by_goal_prev.get(goal, {})
            goal_yoy = by_goal_yoy.get(goal, {}) if meta_ads_goals_yoy else {}
            
            # 기본값 설정
            def get_value(data, key, default=0):
                return data.get(key, default) if data else default
            
            def get_rate(data, key):
                return data.get(key) if data else None
            
            # MoM 비교
            goal_mom = {}
            
            # spend
            spend_this = get_value(goal_this, "spend", 0.0)
            spend_prev = get_value(goal_prev, "spend", 0.0)
            goal_mom["spend"] = delta(spend_this, spend_prev)
            
            # purchases
            purchases_this = get_value(goal_this, "purchases", 0)
            purchases_prev = get_value(goal_prev, "purchases", 0)
            goal_mom["purchases"] = delta(purchases_this, purchases_prev)
            
            # purchase_value
            purchase_value_this = get_value(goal_this, "purchase_value", 0.0)
            purchase_value_prev = get_value(goal_prev, "purchase_value", 0.0)
            goal_mom["purchase_value"] = delta(purchase_value_this, purchase_value_prev)
            
            # clicks
            clicks_this = get_value(goal_this, "clicks", 0)
            clicks_prev = get_value(goal_prev, "clicks", 0)
            goal_mom["clicks"] = delta(clicks_this, clicks_prev)
            
            # impressions
            impressions_this = get_value(goal_this, "impressions", 0)
            impressions_prev = get_value(goal_prev, "impressions", 0)
            goal_mom["impressions"] = delta(impressions_this, impressions_prev)
            
            # rate류: base가 None이면 delta도 None
            # ctr
            ctr_this = get_rate(goal_this, "ctr")
            ctr_prev = get_rate(goal_prev, "ctr")
            goal_mom["ctr"] = delta(ctr_this, ctr_prev) if (ctr_this is not None and ctr_prev is not None) else None
            
            # cpc
            cpc_this = get_rate(goal_this, "cpc")
            cpc_prev = get_rate(goal_prev, "cpc")
            goal_mom["cpc"] = delta(cpc_this, cpc_prev) if (cpc_this is not None and cpc_prev is not None) else None
            
            # cvr
            cvr_this = get_rate(goal_this, "cvr")
            cvr_prev = get_rate(goal_prev, "cvr")
            goal_mom["cvr"] = delta(cvr_this, cvr_prev) if (cvr_this is not None and cvr_prev is not None) else None
            
            # cpa (purchases가 있으면 계산)
            cpa_this = (spend_this / purchases_this) if purchases_this > 0 else None
            cpa_prev = (spend_prev / purchases_prev) if purchases_prev > 0 else None
            goal_mom["cpa"] = delta(cpa_this, cpa_prev) if (cpa_this is not None and cpa_prev is not None) else None
            
            # roas
            roas_this = get_rate(goal_this, "roas")
            roas_prev = get_rate(goal_prev, "roas")
            goal_mom["roas"] = delta(roas_this, roas_prev) if (roas_this is not None and roas_prev is not None) else None
            
            # base_small 플래그
            goal_mom["note_if_base_small_spend"] = note_if_base_small(spend_prev, META_ADS_BASE_SMALL_THRESHOLD)
            
            result_mom[goal] = goal_mom
            
            # YoY 비교 (meta_ads_goals_yoy가 있으면)
            if meta_ads_goals_yoy:
                goal_yoy_dict = {}
                
                # spend
                spend_yoy_val = get_value(goal_yoy, "spend", 0.0)
                goal_yoy_dict["spend"] = delta(spend_this, spend_yoy_val)
                
                # purchases
                purchases_yoy = get_value(goal_yoy, "purchases", 0)
                goal_yoy_dict["purchases"] = delta(purchases_this, purchases_yoy)
                
                # purchase_value
                purchase_value_yoy = get_value(goal_yoy, "purchase_value", 0.0)
                goal_yoy_dict["purchase_value"] = delta(purchase_value_this, purchase_value_yoy)
                
                # clicks
                clicks_yoy = get_value(goal_yoy, "clicks", 0)
                goal_yoy_dict["clicks"] = delta(clicks_this, clicks_yoy)
                
                # impressions
                impressions_yoy = get_value(goal_yoy, "impressions", 0)
                goal_yoy_dict["impressions"] = delta(impressions_this, impressions_yoy)
                
                # rate류
                ctr_yoy = get_rate(goal_yoy, "ctr")
                goal_yoy_dict["ctr"] = delta(ctr_this, ctr_yoy) if (ctr_this is not None and ctr_yoy is not None) else None
                
                cpc_yoy = get_rate(goal_yoy, "cpc")
                goal_yoy_dict["cpc"] = delta(cpc_this, cpc_yoy) if (cpc_this is not None and cpc_yoy is not None) else None
                
                cvr_yoy = get_rate(goal_yoy, "cvr")
                goal_yoy_dict["cvr"] = delta(cvr_this, cvr_yoy) if (cvr_this is not None and cvr_yoy is not None) else None
                
                cpa_yoy = (spend_yoy_val / purchases_yoy) if purchases_yoy > 0 else None
                goal_yoy_dict["cpa"] = delta(cpa_this, cpa_yoy) if (cpa_this is not None and cpa_yoy is not None) else None
                
                roas_yoy = get_rate(goal_yoy, "roas")
                goal_yoy_dict["roas"] = delta(roas_this, roas_yoy) if (roas_this is not None and roas_yoy is not None) else None
                
                # base_small 플래그
                goal_yoy_dict["note_if_base_small_spend"] = note_if_base_small(spend_yoy_val, META_ADS_BASE_SMALL_THRESHOLD)
                
                result_yoy[goal] = goal_yoy_dict
        
        return {
            "mom": result_mom,
            "yoy": result_yoy,
        }
    
    def build_comparisons():
        comparisons = {}
        
        # mall_sales
        net_sales_mom = delta(sales_this["net_sales"], sales_prev["net_sales"]) if (sales_this and sales_prev) else None
        net_sales_yoy = delta(sales_this["net_sales"], sales_yoy["net_sales"]) if (mall_sales_yoy_available and sales_yoy and sales_this) else None
        comparisons["mall_sales"] = {
            "net_sales_mom": net_sales_mom,
            "net_sales_yoy": net_sales_yoy,
            "note_if_base_small_mom": note_if_base_small(sales_prev["net_sales"], MALL_SALES_BASE_SMALL_THRESHOLD) if sales_prev else None,
        }
        
        # meta_ads
        spend_mom = delta(meta_ads_this["spend"], meta_ads_prev["spend"]) if (meta_ads_this and meta_ads_prev) else None
        spend_yoy = delta(meta_ads_this["spend"], meta_ads_yoy["spend"]) if (meta_ads_yoy_available and meta_ads_yoy and meta_ads_this) else None
        roas_mom = delta(meta_ads_this["roas"] or 0, meta_ads_prev["roas"] or 0) if (meta_ads_this["roas"] is not None and meta_ads_prev["roas"] is not None) else None
        cvr_mom = delta(meta_ads_this["cvr"] or 0, meta_ads_prev["cvr"] or 0) if (meta_ads_this["cvr"] is not None and meta_ads_prev["cvr"] is not None) else None
        comparisons["meta_ads"] = {
            "spend_mom": spend_mom,
            "spend_yoy": spend_yoy,
            "roas_mom": roas_mom,
            "cvr_mom": cvr_mom,
            "note_if_base_small_mom": note_if_base_small(meta_ads_prev["spend"], META_ADS_BASE_SMALL_THRESHOLD) if meta_ads_prev else None,
        }
        
        # meta_ads_goals
        meta_ads_goals_comparisons = build_meta_ads_goals_comparisons(
            meta_ads_goals_this,
            meta_ads_goals_prev,
            meta_ads_goals_yoy
        )
        if meta_ads_goals_comparisons:
            comparisons["meta_ads_goals"] = meta_ads_goals_comparisons
        
        # ga4_traffic
        total_users_mom = delta(ga4_this_totals["total_users"], ga4_prev_totals["total_users"]) if (ga4_this_totals and ga4_prev_totals) else None
        total_users_yoy = delta(ga4_this_totals["total_users"], ga4_yoy_totals["total_users"]) if (ga4_yoy_available and ga4_yoy_totals and ga4_this_totals) else None
        comparisons["ga4_traffic"] = {
            "total_users_mom": total_users_mom,
            "total_users_yoy": total_users_yoy,
            "note_if_base_small_mom": note_if_base_small(ga4_prev_totals["total_users"], GA4_TRAFFIC_BASE_SMALL_THRESHOLD) if ga4_prev_totals else None,
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
        
        # efficient_conversion_exists
        signals["efficient_conversion_exists"] = any(
            item.get("efficient_conversion", False) for item in viewitem_items
        )
        
        # high_attention_and_high_conversion_exists
        signals["high_attention_and_high_conversion_exists"] = any(
            item.get("high_attention_and_high_conversion", False) for item in viewitem_items
        )
        
        # meta_ads_interpretable_monthly
        if sales_this and meta_ads_this and (sales_this.get("net_sales") or 0) > 0:
            signals["meta_ads_interpretable_monthly"] = (
                (meta_ads_this.get("spend") or 0) >= (sales_this.get("net_sales") or 0) * 0.1
            )
        else:
            signals["meta_ads_interpretable_monthly"] = False
        
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
        net_this = (sales_this or {}).get("net_sales", 0)
        net_prev = (sales_prev or {}).get("net_sales", 0)
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
                "daily_this": daily_this,
                "daily_prev": daily_prev,
                "daily_yoy": daily_yoy,
            },
            "meta_ads": {
                "this": meta_ads_this,
                "prev": meta_ads_prev,
                "yoy": meta_ads_yoy,
                "monthly_13m": monthly_13m_meta,
            },
            "meta_ads_goals": {
                "this": meta_ads_goals_this,
                "prev": meta_ads_goals_prev,
                "yoy": meta_ads_goals_yoy,
            },
            "meta_ads_benchmarks": meta_ads_benchmarks,
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
    # Save to GCS (optional)
    # -----------------------
    def save_snapshot_to_gcs(company_name, year, month, snapshot_data):
        """스냅샷을 GCS 버킷에 저장"""
        try:
            client = storage.Client(project=PROJECT_ID)
            bucket = client.bucket(GCS_BUCKET)
            
            # 경로: ai-reports/monthly/{company}/{year}-{month:02d}/snapshot.json
            blob_path = f"ai-reports/monthly/{company_name}/{year}-{month:02d}/snapshot.json"
            blob = bucket.blob(blob_path)
            
            snapshot_json_str = json.dumps(snapshot_data, ensure_ascii=False, indent=2, sort_keys=True)
            blob.upload_from_string(
                snapshot_json_str,
                content_type='application/json; charset=utf-8'
            )
            
            gcs_url = f"gs://{GCS_BUCKET}/{blob_path}"
            print(f"✅ 스냅샷이 GCS에 저장되었습니다: {gcs_url}", file=sys.stderr)
            return gcs_url
        except Exception as e:
            print(f"❌ GCS 저장 실패: {e}", file=sys.stderr)
            return None
    
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
    
    if save_to_gcs_flag:
        save_snapshot_to_gcs(company_name, year, month, out_safe)
    
    print(json.dumps(out_safe, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python3 bq_monthly_snapshot.py <company_name> <year> <month> [--upsert] [--save-to-gcs]")
        sys.exit(1)
    
    company_name = sys.argv[1]
    year = int(sys.argv[2])
    month = int(sys.argv[3])
    upsert_flag = "--upsert" in sys.argv
    save_to_gcs_flag = "--save-to-gcs" in sys.argv
    
    run(company_name, year, month, upsert_flag, save_to_gcs_flag)
