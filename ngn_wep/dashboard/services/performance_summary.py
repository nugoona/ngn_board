from google.cloud import bigquery
from ..utils.cache_utils import cached_query

def get_bigquery_client():
    return bigquery.Client()

@cached_query(func_name="performance_summary", ttl=300)  # 5분 캐싱
def get_performance_summary(company_name, start_date: str, end_date: str, user_id: str = None):
    """
    ✅ 총 광고 성과: 메타 광고 계정 테이블에서 직접 조회
    ✅ 사이트 성과 요약: performance_summary_ngn 테이블에서 조회
    - demo 계정: demo 업체만 조회
    - 일반 계정: demo 업체 제외
    """
    print(f"[DEBUG] get_performance_summary 호출 - company_name: {company_name}, start_date: {start_date}, end_date: {end_date}, user_id: {user_id}")
    
    if not start_date or not end_date:
        raise ValueError("start_date / end_date가 없습니다.")

    query_params = []

    # 업체 필터 처리
    if isinstance(company_name, list):
        filtered_companies = [name.lower() for name in company_name]
        filtered_companies = (
            ["demo"] if user_id == "demo"
            else [name for name in filtered_companies if name != "demo"]
        )
        if not filtered_companies:
            print("[DEBUG] 필터링된 company_name 리스트가 없음 - 빈 결과 반환")
            return []
        company_filter = "LOWER(company_name) IN UNNEST(@company_name_list)"
        query_params.append(bigquery.ArrayQueryParameter("company_name_list", "STRING", filtered_companies))
    else:
        company_name = company_name.lower()
        if company_name == "demo" and user_id != "demo":
            print("[DEBUG] demo 계정 접근 + demo 업체 제외 - 빈 결과 반환")
            return []
        company_filter = "LOWER(company_name) = @company_name"
        query_params.append(bigquery.ScalarQueryParameter("company_name", "STRING", company_name))

    # 날짜 파라미터
    query_params.extend([
        bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
        bigquery.ScalarQueryParameter("end_date", "DATE", end_date)
    ])

    # ✅ 총 광고 성과: 메타 광고 계정 테이블에서 직접 조회
    # ✅ 사이트 성과 요약: performance_summary_ngn 테이블에서 조회
    query = f"""
      WITH meta_ads_data AS (
          -- 총 광고 성과: 메타 광고 계정 테이블에서 직접 조회
          SELECT
              ap.*,
              COALESCE(LOWER(ci.company_name), LOWER(ap.account_name), 'unknown') AS company_name,
              ROW_NUMBER() OVER (PARTITION BY ap.account_name, ap.date ORDER BY ap.spend DESC) AS row_num
          FROM `winged-precept-443218-v8.ngn_dataset.ads_performance` ap
          LEFT JOIN `winged-precept-443218-v8.ngn_dataset.company_info` ci
              ON ap.account_name = ci.meta_acc
      ),
      site_performance_data AS (
          -- 사이트 성과 요약: performance_summary_ngn 테이블에서 조회
          SELECT
              company_name,
              SUM(site_revenue) AS site_revenue,
              SUM(total_visitors) AS total_visitors,
              SUM(product_views) AS product_views,
              ROUND(SAFE_DIVIDE(SUM(product_views), SUM(total_visitors)), 2) AS views_per_visit,
              MAX(updated_at) AS updated_at
          FROM `winged-precept-443218-v8.ngn_dataset.performance_summary_ngn`
          WHERE {company_filter}
            AND DATE(date) BETWEEN @start_date AND @end_date
          GROUP BY company_name
      )
      SELECT
        FORMAT_DATE('%Y-%m-%d', @start_date) || ' ~ ' || FORMAT_DATE('%Y-%m-%d', @end_date) AS date_range,
        'meta' AS ad_media,
        -- 총 광고 성과 (메타 광고 계정 테이블에서)
        COALESCE(SUM(m.spend), 0) AS ad_spend,
        COALESCE(SUM(m.impressions), 0) AS total_impressions,
        COALESCE(SUM(m.clicks), 0) AS total_clicks,
        COALESCE(SUM(m.purchases), 0) AS total_purchases,
        COALESCE(SUM(m.purchase_value), 0) AS total_purchase_value,
        COALESCE(ROUND(SUM(m.purchase_value) / NULLIF(SUM(m.purchases), 0), 2), 0) AS avg_order_value,
        COALESCE(ROUND(SUM(m.purchase_value) / NULLIF(SUM(m.spend), 0) * 100, 2), 0) AS roas_percentage,
        COALESCE(ROUND(SUM(m.spend) / NULLIF(SUM(m.clicks), 0), 2), 0) AS avg_cpc,
        COALESCE(ROUND(SUM(m.clicks) / NULLIF(SUM(m.impressions), 0) * 100, 2), 0) AS click_through_rate,
        COALESCE(ROUND(SUM(m.purchases) / NULLIF(SUM(m.clicks), 0) * 100, 2), 0) AS conversion_rate,
        -- 사이트 성과 요약 (performance_summary_ngn 테이블에서)
        COALESCE(s.site_revenue, 0) AS site_revenue,
        COALESCE(s.total_visitors, 0) AS total_visitors,
        COALESCE(s.product_views, 0) AS product_views,
        COALESCE(s.views_per_visit, 0) AS views_per_visit,
        CASE WHEN COALESCE(s.site_revenue, 0) = 0 THEN 0
             ELSE ROUND(COALESCE(SUM(m.spend), 0) / s.site_revenue * 100, 2)
        END AS ad_spend_ratio,
        COALESCE(s.updated_at, CURRENT_TIMESTAMP()) AS updated_at
      FROM meta_ads_data m
      LEFT JOIN site_performance_data s ON LOWER(m.company_name) = LOWER(s.company_name)
      WHERE m.row_num = 1
        AND m.date BETWEEN @start_date AND @end_date
        AND {company_filter}
        AND m.date IS NOT NULL
      GROUP BY ad_media, s.site_revenue, s.total_visitors, s.product_views, s.views_per_visit, s.updated_at
    """

    print("[DEBUG] performance_summary (총 광고 성과: 메타 계정 테이블 + 사이트 성과: performance_summary_ngn) Query:\n", query)

    try:
        client = get_bigquery_client()
        result = client.query(query, job_config=bigquery.QueryJobConfig(query_parameters=query_params)).result()
        rows = [dict(row) for row in result]
        print(f"[DEBUG] performance_summary 결과: {len(rows)}개")
        return rows
    except Exception as e:
        print("[ERROR] performance_summary 오류:", e)
        return [] 
