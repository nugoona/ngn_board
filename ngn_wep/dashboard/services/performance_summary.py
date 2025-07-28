from google.cloud import bigquery
from ..utils.cache_utils import cached_query

def get_bigquery_client():
    return bigquery.Client()

@cached_query(func_name="performance_summary", ttl=300)  # 5분 캐싱
def get_performance_summary(company_name, start_date: str, end_date: str, user_id: str = None):
    """
    ✅ 메타 광고 성과의 '계정' 레벨과 정확히 동일한 쿼리 사용
    - demo 계정: demo 업체만 조회
    - 일반 계정: demo 업체 제외
    - 메타 광고 성과와 정확히 동일한 데이터
    """
    print(f"[DEBUG] get_performance_summary 호출 - company_name: {company_name}, start_date: {start_date}, end_date: {end_date}, user_id: {user_id}")
    
    if not start_date or not end_date:
        raise ValueError("start_date / end_date가 없습니다.")

    # ✅ 메타 광고 성과의 '계정' 레벨과 정확히 동일한 쿼리 사용
    base_tbl = "meta_ads_account_summary"
    latest_alias = "acc_latest"
    
    # 업체 필터 처리
    if isinstance(company_name, list):
        companies = ", ".join(f"'{c.lower()}'" for c in company_name)
        company_filter = f"LOWER({latest_alias}.company_name) IN ({companies})"
    else:
        company_name = company_name.lower()
        company_filter = f"LOWER({latest_alias}.company_name) = LOWER('{company_name}')"

    # ✅ 메타 광고 성과의 '계정' 레벨과 동일한 쿼리 구조
    query = f"""
      SELECT
        '{start_date} ~ {end_date}' AS date_range,
        'meta' AS ad_media,
        SUM(A.spend) AS ad_spend,
        SUM(A.impressions) AS total_impressions,
        SUM(A.clicks) AS total_clicks,
        SUM(A.purchases) AS total_purchases,
        SUM(A.purchase_value) AS total_purchase_value,
        COALESCE(ROUND(SUM(A.purchase_value) / NULLIF(SUM(A.purchases), 0), 2), 0) AS avg_order_value,
        COALESCE(ROUND(SUM(A.purchase_value) / NULLIF(SUM(A.spend), 0) * 100, 2), 0) AS roas_percentage,
        COALESCE(ROUND(SUM(A.spend) / NULLIF(SUM(A.clicks), 0), 2), 0) AS avg_cpc,
        COALESCE(ROUND(SUM(A.clicks) / NULLIF(SUM(A.impressions), 0) * 100, 2), 0) AS click_through_rate,
        COALESCE(ROUND(SUM(A.purchases) / NULLIF(SUM(A.clicks), 0) * 100, 2), 0) AS conversion_rate,
        COALESCE((
            SELECT SUM(total_revenue)
            FROM `winged-precept-443218-v8.ngn_dataset.cafe24_sales_summary` CS
            WHERE CS.date BETWEEN '{start_date}' AND '{end_date}'
              AND LOWER(CS.company_name) IN ({company_filter.replace(f"LOWER({latest_alias}.company_name)", "LOWER(CS.company_name)")})
        ), 0) AS site_revenue,
        COALESCE((
            SELECT SUM(visitors)
            FROM `winged-precept-443218-v8.ngn_dataset.ga4_traffic_summary` GA
            WHERE GA.date BETWEEN '{start_date}' AND '{end_date}'
              AND LOWER(GA.company_name) IN ({company_filter.replace(f"LOWER({latest_alias}.company_name)", "LOWER(GA.company_name)")})
        ), 0) AS total_visitors,
        0 AS product_views,  -- 상품 조회는 별도 조회 필요
        0 AS views_per_visit,  -- 방문당 조회는 별도 조회 필요
        CASE 
            WHEN COALESCE((
                SELECT SUM(total_revenue)
                FROM `winged-precept-443218-v8.ngn_dataset.cafe24_sales_summary` CS
                WHERE CS.date BETWEEN '{start_date}' AND '{end_date}'
                  AND LOWER(CS.company_name) IN ({company_filter.replace(f"LOWER({latest_alias}.company_name)", "LOWER(CS.company_name)")})
            ), 0) > 0 THEN
                ROUND(SUM(A.spend) / COALESCE((
                    SELECT SUM(total_revenue)
                    FROM `winged-precept-443218-v8.ngn_dataset.cafe24_sales_summary` CS
                    WHERE CS.date BETWEEN '{start_date}' AND '{end_date}'
                      AND LOWER(CS.company_name) IN ({company_filter.replace(f"LOWER({latest_alias}.company_name)", "LOWER(CS.company_name)")})
                ), 0) * 100, 2)
            ELSE 0
        END AS ad_spend_ratio,
        CURRENT_TIMESTAMP() AS updated_at
      FROM `winged-precept-443218-v8.ngn_dataset.{base_tbl}` A
      LEFT JOIN (
          SELECT * EXCEPT(rn) FROM (
              SELECT account_id,
                     account_name,
                     company_name,
                     ROW_NUMBER() OVER (PARTITION BY account_id ORDER BY updated_at DESC) AS rn
              FROM `winged-precept-443218-v8.ngn_dataset.{base_tbl}`
          )
          WHERE rn = 1
      ) AS {latest_alias}
      ON A.account_id = {latest_alias}.account_id
      WHERE A.date BETWEEN '{start_date}' AND '{end_date}'
        AND {company_filter}
      GROUP BY ad_media
      HAVING SUM(A.spend) > 0
    """

    print("[DEBUG] performance_summary (계정 레벨과 동일) Query:\n", query)

    try:
        client = get_bigquery_client()
        result = client.query(query).result()
        rows = [dict(row) for row in result]
        print(f"[DEBUG] performance_summary 결과: {len(rows)}개")
        return rows
    except Exception as e:
        print("[ERROR] performance_summary 오류:", e)
        return [] 
