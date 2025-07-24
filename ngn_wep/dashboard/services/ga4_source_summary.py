from google.cloud import bigquery
from utils.cache_utils import cached_query

def get_bigquery_client():
    return bigquery.Client()

@cached_query(func_name="ga4_source_summary", ttl=600)  # 10분 캐싱
def get_ga4_source_summary(company_name, start_date: str, end_date: str, limit: int = 100):
    """
    ✅ GA4 트래픽 테이블(ga4_traffic_ngn) 기준 소스별 유입수 요약 (최적화됨)
    - company_name: 문자열 또는 리스트
    - 기준 컬럼: first_user_source → source, total_users → 유입수
    """

    if not start_date or not end_date:
        raise ValueError("start_date / end_date 값이 없습니다.")

    # ✅ 업체명 필터 처리
    if isinstance(company_name, list):
        company_filter = "LOWER(company_name) IN UNNEST(@company_name_list)"
        query_params = [
            bigquery.ArrayQueryParameter("company_name_list", "STRING", company_name),
            bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
            bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
            bigquery.ScalarQueryParameter("limit", "INT64", limit),
        ]
    else:
        company_filter = "LOWER(company_name) = LOWER(@company_name)"
        query_params = [
            bigquery.ScalarQueryParameter("company_name", "STRING", company_name),
            bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
            bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
            bigquery.ScalarQueryParameter("limit", "INT64", limit),
        ]

    # ✅ 최적화된 쿼리: LIMIT 추가, 필터링 조건 강화
    query = f"""
    SELECT
      company_name,
      CASE
        WHEN LOWER(first_user_source) IN ('insta_linktree', 'linktr.ee', 'ig', 'l.instagram.com', 'instagram.com', 'lookbook') THEN 'instagram'
        WHEN LOWER(first_user_source) = '인트로 mdgt' THEN 'from madgoat'
        WHEN LOWER(first_user_source) = 'naver' THEN 'naver.com'
        WHEN LOWER(first_user_source) IN ('파이시스', 'piscess') THEN '(direct)'
        ELSE LOWER(first_user_source)
      END AS source,
      SUM(total_users) AS total_users
    FROM `winged-precept-443218-v8.ngn_dataset.ga4_traffic_ngn`
    WHERE
      event_date BETWEEN @start_date AND @end_date
      AND {company_filter}
      AND first_user_source IS NOT NULL
      AND first_user_source != ''
      AND total_users > 0
    GROUP BY company_name, source
    HAVING total_users > 0
    ORDER BY total_users DESC
    LIMIT @limit
    """

    print("[DEBUG] GA4 소스 요약 쿼리 (최적화됨):\n", query)

    try:
        client = get_bigquery_client()
        rows = client.query(query, job_config=bigquery.QueryJobConfig(query_parameters=query_params)).result()
        data = [dict(row) for row in rows]
        print(f"[DEBUG] GA4 소스 요약 결과 {len(data)}건")
        return data
    except Exception as ex:
        print("[ERROR] ga4_source_summary 오류:", ex)
        return []
