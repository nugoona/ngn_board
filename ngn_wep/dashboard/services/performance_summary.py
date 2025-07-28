from google.cloud import bigquery
from ..utils.cache_utils import cached_query

def get_bigquery_client():
    return bigquery.Client()

@cached_query(func_name="performance_summary", ttl=300)  # 5분 캐싱
def get_performance_summary(company_name, start_date: str, end_date: str, user_id: str = None):
    """
    ✅ meta_ads_ad_summary 테이블에서 업체 + 기간 필터로 요약 1줄 가져오기
    - demo 계정: demo 업체만 조회
    - 일반 계정: demo 업체 제외
    - 메타 광고 성과와 동일한 데이터 소스 사용
    """
    print(f"[DEBUG] get_performance_summary 호출 - company_name: {company_name}, start_date: {start_date}, end_date: {end_date}, user_id: {user_id}")
    
    if not start_date or not end_date:
        raise ValueError("start_date / end_date가 없습니다.")

    query_params = []

    # ✅ 업체 필터 처리
    if isinstance(company_name, list):
        filtered_companies = [name.lower() for name in company_name]
        filtered_companies = (
            ["demo"] if user_id == "demo"
            else [name for name in filtered_companies if name != "demo"]
        )
        if not filtered_companies:
            print("[DEBUG] 필터링된 company_name 리스트 없음 → 빈 결과 반환")
            return []
        company_filter = "LOWER(company_name) IN UNNEST(@company_name_list)"
        query_params.append(bigquery.ArrayQueryParameter("company_name_list", "STRING", filtered_companies))
    else:
        company_name = company_name.lower()
        if company_name == "demo" and user_id != "demo":
            print("[DEBUG] demo 계정 아님 + demo 요청 → 빈 결과 반환")
            return []
        company_filter = "LOWER(company_name) = @company_name"
        query_params.append(bigquery.ScalarQueryParameter("company_name", "STRING", company_name))

    # ✅ 날짜 파라미터
    query_params.extend([
        bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
        bigquery.ScalarQueryParameter("end_date", "DATE", end_date)
    ])

    # ✅ 쿼리문 구성 (meta_ads_ad_summary 테이블 사용)
    query = f"""
        WITH ranked_data AS (
            SELECT
                ap.*,
                COALESCE(LOWER(ci.company_name), LOWER(ap.account_name), 'unknown') AS company_name,
                ROW_NUMBER() OVER (PARTITION BY ap.account_name, ap.date ORDER BY ap.spend DESC) AS row_num
            FROM `winged-precept-443218-v8.ngn_dataset.ads_performance` ap
            LEFT JOIN `winged-precept-443218-v8.ngn_dataset.company_info` ci
                ON ap.account_name = ci.meta_acc
        )
        SELECT
          FORMAT_DATE('%Y-%m-%d', @start_date) || ' ~ ' || FORMAT_DATE('%Y-%m-%d', @end_date) AS date_range,
          'meta' AS ad_media,
          COALESCE(SUM(spend), 0) AS ad_spend,
          COALESCE(SUM(clicks), 0) AS total_clicks,
          COALESCE(SUM(purchases), 0) AS total_purchases,
          COALESCE(SUM(purchase_value), 0) AS total_purchase_value,
          COALESCE(ROUND(SUM(purchase_value) / NULLIF(SUM(purchases), 0), 2), 0) AS avg_order_value,
          COALESCE(ROUND(SUM(purchase_value) / NULLIF(SUM(spend), 0) * 100, 2), 0) AS roas_percentage,
          COALESCE(ROUND(SUM(spend) / NULLIF(SUM(clicks), 0), 2), 0) AS avg_cpc,
          COALESCE(ROUND(SUM(clicks) / NULLIF(SUM(impressions), 0) * 100, 2), 0) AS click_through_rate,
          COALESCE(ROUND(SUM(purchases) / NULLIF(SUM(clicks), 0) * 100, 2), 0) AS conversion_rate,
          0 AS site_revenue,  -- 사이트 매출은 별도 조회 필요
          0 AS total_visitors,  -- 방문자 수는 별도 조회 필요
          0 AS product_views,  -- 상품 조회는 별도 조회 필요
          0 AS views_per_visit,  -- 방문당 조회는 별도 조회 필요
          0 AS ad_spend_ratio,  -- 광고비 비율은 별도 조회 필요
          CURRENT_TIMESTAMP() AS updated_at
        FROM ranked_data
        WHERE row_num = 1
          AND date BETWEEN @start_date AND @end_date
          AND {company_filter}
          AND date IS NOT NULL
          AND (campaign_name IS NULL OR NOT LOWER(campaign_name) LIKE '%instagram%')
        GROUP BY ad_media
    """

    print("[DEBUG] performance_summary (meta_ads_ad_summary) Query:\n", query)

    try:
        client = get_bigquery_client()
        result = client.query(query, job_config=bigquery.QueryJobConfig(query_parameters=query_params)).result()
        rows = [dict(row) for row in result]
        print(f"[DEBUG] performance_summary 결과: {len(rows)}개")
        return rows
    except Exception as e:
        print("[ERROR] performance_summary 오류:", e)
        return [] 
