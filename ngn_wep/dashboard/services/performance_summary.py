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

    # ✅ 백업 파일의 원래 쿼리 사용 (performance_summary_ngn 테이블)
    # 🔥 광고비 조건 추가: 광고비가 0보다 크면 'meta', 아니면 '없음'
    query = f"""
        SELECT
          FORMAT_DATE('%Y-%m-%d', @start_date) || ' ~ ' || FORMAT_DATE('%Y-%m-%d', @end_date) AS date_range,
          CASE 
            WHEN SUM(ad_spend) > 0 THEN 'meta'
            ELSE '없음'
          END AS ad_media,
          SUM(ad_spend) AS ad_spend,
          SUM(total_clicks) AS total_clicks,
          SUM(total_purchases) AS total_purchases,
          SUM(total_purchase_value) AS total_purchase_value,
          ROUND(SAFE_DIVIDE(SUM(total_purchase_value), SUM(total_purchases)), 2) AS avg_order_value,
          ROUND(SAFE_DIVIDE(SUM(total_purchase_value), SUM(ad_spend)) * 100, 2) AS roas_percentage,
          ROUND(SAFE_DIVIDE(SUM(ad_spend * avg_cpc), SUM(ad_spend)), 2) AS avg_cpc,
          ROUND(SAFE_DIVIDE(SUM(total_clicks * click_through_rate), SUM(total_clicks)), 2) AS click_through_rate,
          ROUND(SAFE_DIVIDE(SUM(total_clicks * conversion_rate), SUM(total_clicks)), 2) AS conversion_rate,
          SUM(site_revenue) AS site_revenue,
          SUM(total_visitors) AS total_visitors,
          SUM(product_views) AS product_views,
          ROUND(SAFE_DIVIDE(SUM(product_views), SUM(total_visitors)), 2) AS views_per_visit,
          ROUND(SAFE_DIVIDE(SUM(ad_spend), SUM(site_revenue)) * 100, 2) AS ad_spend_ratio,
          MAX(updated_at) AS updated_at
        FROM winged-precept-443218-v8.ngn_dataset.performance_summary_ngn
        WHERE {company_filter}
          AND DATE(date) BETWEEN @start_date AND @end_date
        GROUP BY CASE 
          WHEN SUM(ad_spend) > 0 THEN 'meta'
          ELSE '없음'
        END
    """

    print("[DEBUG] performance_summary_ngn Query:\n", query)

    try:
        client = get_bigquery_client()
        result = client.query(query, job_config=bigquery.QueryJobConfig(query_parameters=query_params)).result()
        rows = [dict(row) for row in result]
        print(f"[DEBUG] performance_summary 결과: {len(rows)}개")
        return rows
    except Exception as e:
        print("[ERROR] performance_summary 오류:", e)
        return [] 
