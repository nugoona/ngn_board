# File: services/viewitem_summary.py

from google.cloud import bigquery
from ..utils.cache_utils import cached_query

def get_bigquery_client():
    return bigquery.Client()

@cached_query(func_name="viewitem_summary", ttl=600)  # 10분 캐싱
def get_viewitem_summary(company_name, start_date: str, end_date: str, limit: int = 500):
    print(f"[DEBUG] 🔍 get_viewitem_summary 호출됨")
    print(f"[DEBUG] 📊 파라미터: company_name={company_name}, start_date={start_date}, end_date={end_date}, limit={limit}")
    
    if not start_date or not end_date:
        print("[ERROR] ❌ start_date 또는 end_date가 없음")
        raise ValueError("start_date / end_date 값이 없습니다.")

    # ✅ 업체 필터링 분기 처리
    if isinstance(company_name, list):
        company_filter = "LOWER(c.company_name) IN UNNEST(@company_name_list)"
        query_params = [
            bigquery.ArrayQueryParameter("company_name_list", "STRING", company_name),
            bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
            bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
            bigquery.ScalarQueryParameter("limit", "INT64", limit),
        ]
    else:
        company_filter = "LOWER(c.company_name) = LOWER(@company_name)"
        query_params = [
            bigquery.ScalarQueryParameter("company_name", "STRING", company_name),
            bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
            bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
            bigquery.ScalarQueryParameter("limit", "INT64", limit),
        ]

    # ✅ 최적화된 쿼리: LIMIT 추가, REGEXP_REPLACE 최소화, 효율적인 필터링
    query = f"""
    SELECT
      LOWER(c.company_name) AS company_name,
      REGEXP_REPLACE(t.item_name, r'^\\[[^\\]]+\\]\\s*', '') AS product_name_cleaned,

      CASE
        WHEN LOWER(t.first_user_source) LIKE '%instagram%' OR LOWER(t.first_user_source) LIKE '%insta%' 
             OR t.first_user_source IN ('linktr.ee', 'ig', 'l.instagram.com', 'LOOKBOOK') THEN 'instagram'
        WHEN t.first_user_source = '인트로 MDGT' THEN 'from madgoat'
        WHEN t.first_user_source = 'naver' THEN 'naver.com'
        WHEN LOWER(t.first_user_source) IN ('파이시스', 'piscess') THEN '(direct)'
        ELSE t.first_user_source
      END AS source_raw,

      t.country,
      SUM(t.view_item) AS total_view_item

    FROM `winged-precept-443218-v8.ngn_dataset.ga4_viewitem_ngn` t
    JOIN `winged-precept-443218-v8.ngn_dataset.company_info` c
      ON t.ga4_property_id = c.ga4_property_id
    WHERE DATE(t.event_date) BETWEEN @start_date AND @end_date
      AND {company_filter}
      AND t.item_name IS NOT NULL
      AND t.item_name != ''
      AND t.item_name != '(not set)'
      AND t.view_item > 0

    GROUP BY company_name, t.item_name, source_raw, t.country
    HAVING total_view_item > 0
    ORDER BY total_view_item DESC
    LIMIT @limit
    """

    print("[DEBUG] ViewItem Summary 쿼리 (최적화됨):\n", query)

    try:
        client = get_bigquery_client()
        print(f"[DEBUG] 🚀 BigQuery 쿼리 실행 시작")
        rows = client.query(query, job_config=bigquery.QueryJobConfig(query_parameters=query_params)).result()
        data = [dict(row) for row in rows]
        print(f"[DEBUG] ✅ ViewItem Summary 결과 {len(data)}건")
        print(f"[DEBUG] 📋 첫 번째 데이터 샘플: {data[0] if data else 'None'}")
        return data
    except Exception as ex:
        print(f"[ERROR] ❌ viewitem_summary 오류: {ex}")
        print(f"[ERROR] 🔍 오류 타입: {type(ex)}")
        return []

