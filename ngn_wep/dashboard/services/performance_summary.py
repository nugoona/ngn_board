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

    # ✅ 백업 파일의 원래 쿼리 사용하되, 메타 광고 성과는 meta_ads_account_summary에서 가져오기
    query = f"""
        SELECT
          FORMAT_DATE('%Y-%m-%d', @start_date) || ' ~ ' || FORMAT_DATE('%Y-%m-%d', @end_date) AS date_range,
          'meta' AS ad_media,
          -- 메타 광고 성과 (meta_ads_account_summary에서)
          COALESCE(m.ad_spend, 0) AS ad_spend,
          COALESCE(m.total_impressions, 0) AS total_impressions,
          COALESCE(m.total_clicks, 0) AS total_clicks,
          COALESCE(m.total_purchases, 0) AS total_purchases,
          COALESCE(m.total_purchase_value, 0) AS total_purchase_value,
          COALESCE(m.avg_order_value, 0) AS avg_order_value,
          COALESCE(m.roas_percentage, 0) AS roas_percentage,
          COALESCE(m.avg_cpc, 0) AS avg_cpc,
          COALESCE(m.click_through_rate, 0) AS click_through_rate,
          COALESCE(m.conversion_rate, 0) AS conversion_rate,
          -- 사이트 성과 요약 (performance_summary_ngn에서)
          SUM(site_revenue) AS site_revenue,
          SUM(total_visitors) AS total_visitors,
          SUM(product_views) AS product_views,
          ROUND(SAFE_DIVIDE(SUM(product_views), SUM(total_visitors)), 2) AS views_per_visit,
          ROUND(SAFE_DIVIDE(COALESCE(m.ad_spend, 0), SUM(site_revenue)) * 100, 2) AS ad_spend_ratio,
          MAX(updated_at) AS updated_at
        FROM winged-precept-443218-v8.ngn_dataset.performance_summary_ngn p
        LEFT JOIN (
          -- 메타 광고 계정 성과
          SELECT
            COALESCE(SUM(spend), 0) AS ad_spend,
            COALESCE(SUM(impressions), 0) AS total_impressions,
            COALESCE(SUM(clicks), 0) AS total_clicks,
            COALESCE(SUM(purchases), 0) AS total_purchases,
            COALESCE(SUM(purchase_value), 0) AS total_purchase_value,
            COALESCE(ROUND(SUM(purchase_value) / NULLIF(SUM(purchases), 0), 2), 0) AS avg_order_value,
            COALESCE(ROUND(SUM(purchase_value) / NULLIF(SUM(spend), 0) * 100, 2), 0) AS roas_percentage,
            COALESCE(ROUND(SUM(spend) / NULLIF(SUM(clicks), 0), 2), 0) AS avg_cpc,
            COALESCE(ROUND(SUM(clicks) / NULLIF(SUM(impressions), 0) * 100, 2), 0) AS click_through_rate,
            COALESCE(ROUND(SUM(purchases) / NULLIF(SUM(clicks), 0) * 100, 2), 0) AS conversion_rate
          FROM `winged-precept-443218-v8.ngn_dataset.meta_ads_account_summary` ap
          LEFT JOIN (
              SELECT * EXCEPT(rn) FROM (
                  SELECT account_id,
                         account_name,
                         company_name,
                         ROW_NUMBER() OVER (PARTITION BY account_id ORDER BY updated_at DESC) AS rn
                  FROM `winged-precept-443218-v8.ngn_dataset.meta_ads_account_summary`
              )
              WHERE rn = 1
          ) AS acc_latest
          ON ap.account_id = acc_latest.account_id
          WHERE ap.date BETWEEN @start_date AND @end_date
            AND {company_filter}
            AND ap.date IS NOT NULL
        ) m ON 1=1
        WHERE {company_filter}
          AND DATE(p.date) BETWEEN @start_date AND @end_date
        GROUP BY ad_media, m.ad_spend, m.total_impressions, m.total_clicks, m.total_purchases, 
                 m.total_purchase_value, m.avg_order_value, m.roas_percentage, m.avg_cpc, 
                 m.click_through_rate, m.conversion_rate
    """

    print("[DEBUG] performance_summary (메타 광고: meta_ads_account_summary + 사이트 성과: performance_summary_ngn) Query:\n", query)

    # 디버그: 메타 광고 계정 테이블에서 구매 데이터 확인
    debug_query = f"""
      SELECT 
        COUNT(*) as total_rows,
        SUM(CASE WHEN purchases > 0 THEN 1 ELSE 0 END) as rows_with_purchases,
        SUM(CASE WHEN purchase_value > 0 THEN 1 ELSE 0 END) as rows_with_purchase_value,
        SUM(purchases) as total_purchases,
        SUM(purchase_value) as total_purchase_value
      FROM `winged-precept-443218-v8.ngn_dataset.meta_ads_account_summary` ap
      LEFT JOIN (
          SELECT * EXCEPT(rn) FROM (
              SELECT account_id,
                     account_name,
                     company_name,
                     ROW_NUMBER() OVER (PARTITION BY account_id ORDER BY updated_at DESC) AS rn
              FROM `winged-precept-443218-v8.ngn_dataset.meta_ads_account_summary`
          )
          WHERE rn = 1
      ) AS acc_latest
      ON ap.account_id = acc_latest.account_id
      WHERE ap.date BETWEEN @start_date AND @end_date
        AND {company_filter}
        AND ap.date IS NOT NULL
    """
    
    try:
        client = get_bigquery_client()
        debug_result = client.query(debug_query, job_config=bigquery.QueryJobConfig(query_parameters=query_params)).result()
        debug_row = next(debug_result)
        print(f"[DEBUG] 메타 광고 계정 테이블 구매 데이터 확인:")
        print(f"  전체 행 수: {debug_row.get('total_rows', 0)}")
        print(f"  구매가 있는 행 수: {debug_row.get('rows_with_purchases', 0)}")
        print(f"  구매액이 있는 행 수: {debug_row.get('rows_with_purchase_value', 0)}")
        print(f"  총 구매 수: {debug_row.get('total_purchases', 0)}")
        print(f"  총 구매액: {debug_row.get('total_purchase_value', 0)}")
    except Exception as e:
        print(f"[DEBUG] 메타 광고 계정 테이블 디버그 쿼리 오류: {e}")

    # 디버그: company_filter 확인
    print(f"[DEBUG] company_filter: {company_filter}")
    print(f"[DEBUG] company_name: {company_name}")
    print(f"[DEBUG] start_date: {start_date}, end_date: {end_date}")

    # 디버그: performance_summary_ngn 테이블 확인
    site_debug_query = f"""
      SELECT 
        COUNT(*) as total_rows,
        SUM(site_revenue) as total_site_revenue,
        SUM(total_visitors) as total_visitors,
        SUM(product_views) as total_product_views
      FROM `winged-precept-443218-v8.ngn_dataset.performance_summary_ngn`
      WHERE {company_filter}
        AND DATE(date) BETWEEN @start_date AND @end_date
    """
    
    try:
        site_debug_result = client.query(site_debug_query, job_config=bigquery.QueryJobConfig(query_parameters=query_params)).result()
        site_debug_row = next(site_debug_result)
        print(f"[DEBUG] performance_summary_ngn 테이블 확인:")
        print(f"  전체 행 수: {site_debug_row.get('total_rows', 0)}")
        print(f"  총 사이트 매출: {site_debug_row.get('total_site_revenue', 0)}")
        print(f"  총 방문자: {site_debug_row.get('total_visitors', 0)}")
        print(f"  총 상품 조회: {site_debug_row.get('total_product_views', 0)}")
    except Exception as e:
        print(f"[DEBUG] performance_summary_ngn 테이블 디버그 쿼리 오류: {e}")

    try:
        client = get_bigquery_client()
        result = client.query(query, job_config=bigquery.QueryJobConfig(query_parameters=query_params)).result()
        rows = [dict(row) for row in result]
        print(f"[DEBUG] performance_summary 결과: {len(rows)}개")
        return rows
    except Exception as e:
        print("[ERROR] performance_summary 오류:", e)
        return [] 
