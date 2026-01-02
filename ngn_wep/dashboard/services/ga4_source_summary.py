from google.cloud import bigquery
from ..utils.cache_utils import cached_query

def get_bigquery_client():
    return bigquery.Client()

# @cached_query(func_name="ga4_source_summary", ttl=60)  # 캐시 비활성화
def get_ga4_source_summary(company_name, start_date: str, end_date: str, limit: int = 100, _cache_buster: int = None):
    """
    ✅ GA4 트래픽 테이블(ga4_traffic_ngn) 기준 소스별 유입수 요약 (최적화됨)
    - company_name: 문자열 또는 리스트
    - 기준 컬럼: first_user_source → source, total_users → 유입수
    """

    print(f"[DEBUG] GA4 소스 요약 호출 - company: {company_name}, start: {start_date}, end: {end_date}, limit: {limit}, cache_buster: {_cache_buster}")
    print(f"[DEBUG] GA4 소스 요약 파라미터 타입 - company: {type(company_name)}, start: {type(start_date)}, end: {type(end_date)}")

    if not start_date or not end_date:
        print(f"[ERROR] start_date 또는 end_date가 없습니다. start_date: {start_date}, end_date: {end_date}")
        raise ValueError("start_date / end_date 값이 없습니다.")

    # ✅ 업체명 필터 처리 ("all" 처리 포함)
    company_filter = ""
    query_params = [
        bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
        bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
        bigquery.ScalarQueryParameter("limit", "INT64", limit),
    ]

    # company_name이 "all"이 아닌 경우에만 필터 추가
    if isinstance(company_name, list):
        # 리스트에 "all"이 포함되어 있으면 필터를 적용하지 않음
        if "all" not in [str(c).lower() for c in company_name]:
            company_filter = "AND LOWER(company_name) IN UNNEST(@company_name_list)"
            query_params.insert(0, bigquery.ArrayQueryParameter("company_name_list", "STRING", company_name))
            print(f"[DEBUG] 리스트 필터 적용: {company_name}")
        else:
            print(f"[DEBUG] 리스트에 'all' 포함되어 필터 제외: {company_name}")
    else:
        if str(company_name).lower() != "all":
            company_filter = "AND LOWER(company_name) = LOWER(@company_name)"
            query_params.insert(0, bigquery.ScalarQueryParameter("company_name", "STRING", company_name))
            print(f"[DEBUG] 단일 필터 적용: {company_name}")
        else:
            print(f"[DEBUG] 'all'이므로 필터 제외: {company_name}")

    # ✅ 최적화된 쿼리: LIMIT 추가, 필터링 조건 강화, 이탈율 추가
    query = f"""
    SELECT
      company_name,
      CASE
        -- Instagram 관련 통합
        WHEN LOWER(first_user_source) LIKE '%instagram%' 
             OR LOWER(first_user_source) LIKE '%insta%'
             OR LOWER(first_user_source) IN ('ig', 'linktr.ee', 'lookbook', 'igshopping') THEN 'instagram'
        -- Naver 관련 통합
        WHEN LOWER(first_user_source) LIKE '%naver%' THEN 'naver.com'
        -- Meta Ad 관련 (별도 유지)
        WHEN LOWER(first_user_source) LIKE '%meta_ad%' THEN 'meta_ad'
        -- Facebook 관련 통합 (facebook.com, m.facebook.com 등)
        WHEN LOWER(first_user_source) LIKE '%facebook%'
             OR LOWER(first_user_source) = 'fb' THEN 'facebook'
        -- YouTube 관련 통합
        WHEN LOWER(first_user_source) LIKE '%youtube%' THEN 'youtube.com'
        -- TikTok
        WHEN LOWER(first_user_source) LIKE '%tiktok%' 
             OR LOWER(first_user_source) LIKE '%tt.%' THEN 'tiktok'
        -- Direct 관련 통합
        WHEN LOWER(first_user_source) IN ('(direct)', 'direct')
             OR LOWER(first_user_source) LIKE '%piscess%'
             OR LOWER(first_user_source) = '파이시스' THEN '(direct)'
        -- Google 관련 통합
        WHEN LOWER(first_user_source) LIKE '%google%' THEN 'google'
        -- Daum
        WHEN LOWER(first_user_source) = 'daum' THEN 'daum'
        -- Cafe24 관련 통합
        WHEN LOWER(first_user_source) LIKE '%cafe24%' THEN 'cafe24.com'
        -- 특수 케이스
        WHEN LOWER(first_user_source) = '인트로 mdgt' THEN 'from madgoat'
        WHEN LOWER(first_user_source) IN ('(data not available)', 'data not available') THEN '(data not available)'
        -- 나머지는 원본 유지
        ELSE LOWER(first_user_source)
      END AS source,
      SUM(total_users) AS total_users,
      -- 이탈율 가중평균 계산 (bounce_rate가 NULL이 아닌 경우만 계산)
      SAFE_DIVIDE(
        SUM(IFNULL(bounce_rate, 0) * total_users),
        SUM(total_users)
      ) AS bounce_rate
    FROM `winged-precept-443218-v8.ngn_dataset.ga4_traffic_ngn`
    WHERE
      event_date BETWEEN @start_date AND @end_date
      {company_filter}
      AND first_user_source IS NOT NULL
      AND first_user_source != ''
      AND first_user_source != '(not set)'
      AND first_user_source != 'not set'
      AND total_users > 0
    GROUP BY company_name, source
    HAVING total_users > 0
    ORDER BY total_users DESC
    LIMIT @limit
    """

    print("[DEBUG] GA4 소스 요약 쿼리 (최적화됨):\n", query)
    print(f"[DEBUG] 쿼리 파라미터: {query_params}")

    try:
        client = get_bigquery_client()
        rows = client.query(query, job_config=bigquery.QueryJobConfig(query_parameters=query_params)).result()
        data = [dict(row) for row in rows]
        print(f"[DEBUG] GA4 소스 요약 결과 {len(data)}건")
        if len(data) > 0:
            print(f"[DEBUG] 첫 번째 결과: {data[0]}")
        else:
            print("[DEBUG] 결과가 없습니다. 날짜 범위를 확인해주세요.")
        return data
    except Exception as ex:
        print("[ERROR] ga4_source_summary 오류:", ex)
        print(f"[ERROR] 오류 상세: {type(ex).__name__}: {str(ex)}")
        # 빈 데이터 반환으로 서버 오류 방지
        return []
