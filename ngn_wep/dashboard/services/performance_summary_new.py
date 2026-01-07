"""
통합 성과 요약 서비스 (CTE 기반 단일 쿼리 최적화)
- 5개 테이블을 하나의 쿼리로 조회하여 BigQuery 비용 절감
- 60초 캐싱으로 반복 조회 최소화
"""
import time
from google.cloud import bigquery
from ..utils.cache_utils import cached_query

# BigQuery 클라이언트 싱글톤
_bq_client = None

def get_bigquery_client():
    """BigQuery 클라이언트 싱글톤 반환"""
    global _bq_client
    if _bq_client is None:
        _bq_client = bigquery.Client()
    return _bq_client


def _build_company_filter(company_name, user_id: str = None, table_alias: str = ""):
    """
    업체 필터 조건 및 파라미터 생성

    Args:
        company_name: 업체명 (문자열 또는 리스트)
        user_id: 사용자 ID (demo 사용자 체크용)
        table_alias: 테이블 별칭 (예: "C." 또는 "")

    Returns:
        (filter_sql, query_params, filtered_company_name)
    """
    query_params = []
    prefix = f"{table_alias}." if table_alias else ""

    if isinstance(company_name, list):
        filtered_companies = [name.lower() for name in company_name]
        if user_id == "demo":
            filtered_companies = ["demo"]
        else:
            filtered_companies = [name for name in filtered_companies if name != "demo"]

        if not filtered_companies:
            return None, [], None

        company_filter = f"LOWER({prefix}company_name) IN UNNEST(@company_name_list)"
        query_params.append(bigquery.ArrayQueryParameter("company_name_list", "STRING", filtered_companies))
        return company_filter, query_params, filtered_companies
    else:
        company_name_lower = company_name.lower()
        if company_name_lower == "demo" and user_id != "demo":
            return None, [], None

        company_filter = f"LOWER({prefix}company_name) = @company_name"
        query_params.append(bigquery.ScalarQueryParameter("company_name", "STRING", company_name_lower))
        return company_filter, query_params, company_name_lower


@cached_query(func_name="performance_summary_new", ttl=60)
def get_performance_summary_new(company_name, start_date: str, end_date: str, user_id: str = None, account_id: str = None):
    """
    통합 성과 요약 API (CTE 기반 단일 쿼리 최적화)

    5개 테이블을 하나의 쿼리로 조회:
    - daily_cafe24_sales: 매출, 주문수
    - meta_ads_account_summary: 광고비, 클릭, 구매
    - ga4_traffic_ngn: 방문자 수
    - ga4_viewitem_ngn: 상품 조회수
    - performance_summary_ngn: 장바구니, 회원가입

    Args:
        company_name: 업체명 (문자열 또는 리스트)
        start_date: 시작일 (YYYY-MM-DD)
        end_date: 종료일 (YYYY-MM-DD)
        user_id: 사용자 ID
        account_id: Meta 광고 계정 ID (선택적)

    Returns:
        [{"date_range": "...", "site_revenue": ..., ...}]
    """
    print(f"[PERF] get_performance_summary_new 호출 - company: {company_name}, period: {start_date}~{end_date}")

    if not start_date or not end_date:
        raise ValueError("start_date / end_date가 없습니다.")

    start_time = time.time()

    try:
        # 업체 필터 생성
        company_filter, base_params, filtered_company = _build_company_filter(company_name, user_id)

        if company_filter is None:
            print("[PERF] 조회 가능한 업체 없음 - 기본값 반환")
            return [_get_default_result(start_date, end_date)]

        # 쿼리 파라미터 설정
        query_params = base_params.copy()
        query_params.extend([
            bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
            bigquery.ScalarQueryParameter("end_date", "DATE", end_date)
        ])

        # Meta 광고 계정 필터 (선택적)
        meta_account_filter = ""
        if account_id:
            meta_account_filter = "AND A.account_id = @account_id"
            query_params.append(bigquery.ScalarQueryParameter("account_id", "STRING", account_id))

        # Meta 광고용 company_filter (테이블 별칭 L 사용)
        if isinstance(filtered_company, list):
            meta_company_filter = "LOWER(L.company_name) IN UNNEST(@company_name_list)"
        else:
            meta_company_filter = "LOWER(L.company_name) = @company_name"

        # CTE 기반 통합 쿼리
        query = f"""
        WITH
        -- 1. 카페24 매출 데이터
        cafe24_summary AS (
            SELECT
                COALESCE(SUM(net_sales), 0) AS total_revenue,
                COALESCE(SUM(total_orders), 0) AS total_orders,
                MAX(updated_at) AS updated_at
            FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
            WHERE payment_date BETWEEN @start_date AND @end_date
              AND {company_filter}
        ),

        -- 2. Meta 광고 최신 계정 정보
        latest_meta_accounts AS (
            SELECT account_id, account_name, company_name
            FROM (
                SELECT account_id, account_name, company_name,
                       ROW_NUMBER() OVER (PARTITION BY account_id ORDER BY updated_at DESC) AS rn
                FROM `winged-precept-443218-v8.ngn_dataset.meta_ads_account_summary`
            )
            WHERE rn = 1
        ),

        -- 3. Meta 광고 성과 집계
        meta_summary AS (
            SELECT
                COALESCE(SUM(A.spend), 0) AS total_spend,
                COALESCE(SUM(A.clicks), 0) AS total_clicks,
                COALESCE(SUM(A.purchases), 0) AS total_purchases,
                COALESCE(SUM(A.purchase_value), 0) AS total_purchase_value,
                MAX(A.updated_at) AS updated_at
            FROM `winged-precept-443218-v8.ngn_dataset.meta_ads_account_summary` A
            LEFT JOIN latest_meta_accounts L ON A.account_id = L.account_id
            WHERE A.date BETWEEN @start_date AND @end_date
              AND L.company_name IS NOT NULL
              AND {meta_company_filter}
              {meta_account_filter}
        ),

        -- 4. GA4 방문자 수
        ga4_visitors AS (
            SELECT COALESCE(SUM(total_users), 0) AS total_visitors
            FROM `winged-precept-443218-v8.ngn_dataset.ga4_traffic_ngn`
            WHERE {company_filter}
              AND event_date BETWEEN @start_date AND @end_date
              AND total_users > 0
              AND first_user_source NOT IN ('(not set)', 'not set')
              AND first_user_source IS NOT NULL
        ),

        -- 5. GA4 상품 조회수
        ga4_viewitem AS (
            SELECT COALESCE(SUM(view_item), 0) AS product_views
            FROM `winged-precept-443218-v8.ngn_dataset.ga4_viewitem_ngn`
            WHERE {company_filter}
              AND event_date BETWEEN @start_date AND @end_date
              AND view_item > 0
        ),

        -- 6. 장바구니/회원가입 (performance_summary_ngn)
        cart_signup AS (
            SELECT
                COALESCE(SUM(cart_users), 0) AS cart_users,
                COALESCE(SUM(signup_count), 0) AS signup_count
            FROM `winged-precept-443218-v8.ngn_dataset.performance_summary_ngn`
            WHERE {company_filter}
              AND DATE(date) BETWEEN @start_date AND @end_date
        )

        -- 최종 결과 조합
        SELECT
            c.total_revenue,
            c.total_orders,
            m.total_spend,
            m.total_clicks,
            m.total_purchases,
            m.total_purchase_value,
            c.updated_at,
            g.total_visitors,
            v.product_views,
            cs.cart_users,
            cs.signup_count
        FROM cafe24_summary c
        CROSS JOIN meta_summary m
        CROSS JOIN ga4_visitors g
        CROSS JOIN ga4_viewitem v
        CROSS JOIN cart_signup cs
        """

        # 쿼리 실행
        client = get_bigquery_client()
        job_config = bigquery.QueryJobConfig(query_parameters=query_params)
        result = client.query(query, job_config=job_config).result()

        rows = list(result)
        elapsed = time.time() - start_time

        if not rows:
            print(f"[PERF] 쿼리 결과 없음 ({elapsed:.2f}초)")
            return [_get_default_result(start_date, end_date)]

        row = rows[0]

        # 결과 변환
        site_revenue = float(row.total_revenue or 0)
        total_orders = int(row.total_orders or 0)
        ad_spend = float(row.total_spend or 0)
        total_clicks = int(row.total_clicks or 0)
        total_purchases = int(row.total_purchases or 0)
        total_purchase_value = float(row.total_purchase_value or 0)
        total_visitors = int(row.total_visitors or 0)
        product_views = int(row.product_views or 0)
        cart_users = int(row.cart_users or 0)
        signup_count = int(row.signup_count or 0)
        updated_at = row.updated_at
        print(f"[DEBUG] updated_at 값: {updated_at}, 타입: {type(updated_at)}")

        # 계산 (0으로 나누기 방지)
        roas_percentage = (total_purchase_value / ad_spend * 100) if ad_spend > 0 else 0
        avg_cpc = (ad_spend / total_clicks) if total_clicks > 0 else 0
        ad_spend_ratio = (ad_spend / site_revenue * 100) if site_revenue > 0 else 0
        ad_media = "meta" if ad_spend > 0 else "없음"

        result_data = {
            "date_range": f"{start_date} ~ {end_date}",
            "ad_media": ad_media,
            "ad_spend": round(ad_spend, 2),
            "total_clicks": total_clicks,
            "total_purchases": total_purchases,
            "total_purchase_value": round(total_purchase_value, 2),
            "roas_percentage": round(roas_percentage, 2),
            "avg_cpc": round(avg_cpc, 2),
            "site_revenue": round(site_revenue, 2),
            "total_orders": total_orders,
            "total_visitors": total_visitors,
            "product_views": product_views,
            "ad_spend_ratio": round(ad_spend_ratio, 2),
            "cart_users": cart_users,
            "signup_count": signup_count,
            "updated_at": updated_at
        }

        print(f"[PERF] 통합 쿼리 완료 ({elapsed:.2f}초) - 매출: {site_revenue:,.0f}, 광고비: {ad_spend:,.0f}, 방문자: {total_visitors:,}")
        return [result_data]

    except Exception as e:
        elapsed = time.time() - start_time
        print(f"[ERROR] performance_summary_new 오류 ({elapsed:.2f}초): {e}")
        import traceback
        traceback.print_exc()
        return [_get_default_result(start_date, end_date)]


def _get_default_result(start_date: str, end_date: str) -> dict:
    """기본 결과값 반환"""
    return {
        "date_range": f"{start_date} ~ {end_date}",
        "ad_media": "없음",
        "ad_spend": 0,
        "total_clicks": 0,
        "total_purchases": 0,
        "total_purchase_value": 0,
        "roas_percentage": 0,
        "avg_cpc": 0,
        "site_revenue": 0,
        "total_orders": 0,
        "total_visitors": 0,
        "product_views": 0,
        "ad_spend_ratio": 0,
        "cart_users": 0,
        "signup_count": 0,
        "updated_at": None
    }


# ============================================================
# 하위 호환성을 위한 개별 함수 (deprecated, 단일 쿼리로 대체됨)
# ============================================================

def get_cafe24_summary_simple(company_name, start_date: str, end_date: str, user_id: str = None):
    """[Deprecated] 개별 카페24 조회 - get_performance_summary_new 사용 권장"""
    company_filter, query_params, _ = _build_company_filter(company_name, user_id)
    if company_filter is None:
        return {"total_revenue": 0, "total_orders": 0}

    query_params.extend([
        bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
        bigquery.ScalarQueryParameter("end_date", "DATE", end_date)
    ])

    query = f"""
        SELECT
            COALESCE(SUM(net_sales), 0) AS total_revenue,
            COALESCE(SUM(total_orders), 0) AS total_orders
        FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
        WHERE payment_date BETWEEN @start_date AND @end_date
          AND {company_filter}
    """

    try:
        client = get_bigquery_client()
        result = client.query(query, job_config=bigquery.QueryJobConfig(query_parameters=query_params)).result()
        row = list(result)[0]
        return {"total_revenue": row.total_revenue or 0, "total_orders": row.total_orders or 0}
    except Exception as e:
        print(f"[ERROR] 카페24 요약 조회 오류: {e}")
        return {"total_revenue": 0, "total_orders": 0}


def get_meta_ads_summary_simple(company_name, start_date: str, end_date: str, account_id: str = None):
    """[Deprecated] 개별 Meta 광고 조회 - get_performance_summary_new 사용 권장"""
    query_params = []

    if isinstance(company_name, list):
        if len(company_name) == 1:
            company_name = company_name[0]
            company_filter = "LOWER(L.company_name) = @company_name"
            query_params.append(bigquery.ScalarQueryParameter("company_name", "STRING", company_name.lower()))
        else:
            filtered_companies = [name.lower() for name in company_name]
            company_filter = "LOWER(L.company_name) IN UNNEST(@company_name_list)"
            query_params.append(bigquery.ArrayQueryParameter("company_name_list", "STRING", filtered_companies))
    else:
        company_name = company_name.lower()
        company_filter = "LOWER(L.company_name) = @company_name"
        query_params.append(bigquery.ScalarQueryParameter("company_name", "STRING", company_name))

    query_params.extend([
        bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
        bigquery.ScalarQueryParameter("end_date", "DATE", end_date)
    ])

    account_filter = ""
    if account_id:
        account_filter = "AND A.account_id = @account_id"
        query_params.append(bigquery.ScalarQueryParameter("account_id", "STRING", account_id))

    query = f"""
        WITH latest_accounts AS (
          SELECT * EXCEPT(rn) FROM (
            SELECT account_id, account_name, company_name,
                   ROW_NUMBER() OVER (PARTITION BY account_id ORDER BY updated_at DESC) AS rn
            FROM `winged-precept-443218-v8.ngn_dataset.meta_ads_account_summary`
          )
          WHERE rn = 1
        )
        SELECT
            COALESCE(SUM(A.spend), 0) AS total_spend,
            COALESCE(SUM(A.clicks), 0) AS total_clicks,
            COALESCE(SUM(A.purchases), 0) AS total_purchases,
            COALESCE(SUM(A.purchase_value), 0) AS total_purchase_value,
            MAX(A.updated_at) AS updated_at
        FROM `winged-precept-443218-v8.ngn_dataset.meta_ads_account_summary` A
        LEFT JOIN latest_accounts L ON A.account_id = L.account_id
        WHERE A.date BETWEEN @start_date AND @end_date
          AND L.company_name IS NOT NULL
          AND {company_filter}
          {account_filter}
    """

    try:
        client = get_bigquery_client()
        result = client.query(query, job_config=bigquery.QueryJobConfig(query_parameters=query_params)).result()
        rows = list(result)
        if rows:
            row = rows[0]
            return {
                "total_spend": row.total_spend or 0,
                "total_clicks": row.total_clicks or 0,
                "total_purchases": row.total_purchases or 0,
                "total_purchase_value": row.total_purchase_value or 0,
                "updated_at": row.updated_at
            }
    except Exception as e:
        print(f"[ERROR] 메타 광고 요약 조회 오류: {e}")

    return {"total_spend": 0, "total_clicks": 0, "total_purchases": 0, "total_purchase_value": 0, "updated_at": None}


def get_ga4_visitors_simple(company_name, start_date: str, end_date: str, user_id: str = None):
    """[Deprecated] 개별 GA4 방문자 조회 - get_performance_summary_new 사용 권장"""
    company_filter, query_params, _ = _build_company_filter(company_name, user_id)
    if company_filter is None:
        return 0

    query_params.extend([
        bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
        bigquery.ScalarQueryParameter("end_date", "DATE", end_date)
    ])

    query = f"""
        SELECT COALESCE(SUM(total_users), 0) AS total_visitors
        FROM `winged-precept-443218-v8.ngn_dataset.ga4_traffic_ngn`
        WHERE {company_filter}
          AND event_date BETWEEN @start_date AND @end_date
          AND total_users > 0
          AND first_user_source NOT IN ('(not set)', 'not set')
          AND first_user_source IS NOT NULL
    """

    try:
        client = get_bigquery_client()
        result = client.query(query, job_config=bigquery.QueryJobConfig(query_parameters=query_params)).result()
        row = list(result)[0]
        return row.total_visitors or 0
    except Exception as e:
        print(f"[ERROR] GA4 방문자 조회 오류: {e}")
        return 0


def get_ga4_product_views_simple(company_name, start_date: str, end_date: str, user_id: str = None):
    """[Deprecated] 개별 GA4 상품조회수 - get_performance_summary_new 사용 권장"""
    company_filter, query_params, _ = _build_company_filter(company_name, user_id)
    if company_filter is None:
        return 0

    query_params.extend([
        bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
        bigquery.ScalarQueryParameter("end_date", "DATE", end_date)
    ])

    query = f"""
        SELECT COALESCE(SUM(view_item), 0) AS product_views
        FROM `winged-precept-443218-v8.ngn_dataset.ga4_viewitem_ngn`
        WHERE {company_filter}
          AND event_date BETWEEN @start_date AND @end_date
          AND view_item > 0
    """

    try:
        client = get_bigquery_client()
        result = client.query(query, job_config=bigquery.QueryJobConfig(query_parameters=query_params)).result()
        row = list(result)[0]
        return row.product_views or 0
    except Exception as e:
        print(f"[ERROR] GA4 상품 조회수 조회 오류: {e}")
        return 0


def get_cart_signup_from_summary_table(company_name, start_date: str, end_date: str, user_id: str = None):
    """[Deprecated] 개별 장바구니/회원가입 조회 - get_performance_summary_new 사용 권장"""
    company_filter, query_params, _ = _build_company_filter(company_name, user_id)
    if company_filter is None:
        return {'cart_users': 0, 'signup_count': 0}

    query_params.extend([
        bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
        bigquery.ScalarQueryParameter("end_date", "DATE", end_date)
    ])

    query = f"""
        SELECT
            COALESCE(SUM(cart_users), 0) AS cart_users,
            COALESCE(SUM(signup_count), 0) AS signup_count
        FROM `winged-precept-443218-v8.ngn_dataset.performance_summary_ngn`
        WHERE {company_filter}
          AND DATE(date) BETWEEN @start_date AND @end_date
    """

    try:
        client = get_bigquery_client()
        result = client.query(query, job_config=bigquery.QueryJobConfig(query_parameters=query_params)).result()
        row = list(result)[0]
        return {'cart_users': int(row.cart_users or 0), 'signup_count': int(row.signup_count or 0)}
    except Exception as e:
        print(f"[ERROR] 장바구니/회원가입 데이터 조회 오류: {e}")
        return {'cart_users': 0, 'signup_count': 0}


# 하위 호환성을 위한 별칭
combine_performance_data_parallel = None  # 더 이상 사용되지 않음
