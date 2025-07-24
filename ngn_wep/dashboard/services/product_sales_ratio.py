from google.cloud import bigquery
from ..utils.cache_utils import cached_query

def get_bigquery_client():
    return bigquery.Client()

@cached_query(func_name="product_sales_ratio", ttl=900)  # 15분 캐싱
def get_product_sales_ratio(company_name, start_date: str, end_date: str, limit: int = 50, user_id=None):
    """
    ✅ 상품별 매출 비율 조회 (최적화됨)
    """
    
    print(f"[DEBUG] product_sales_ratio 호출됨: company_name={company_name}, start_date={start_date}, end_date={end_date}")

    if not start_date or not end_date:
        raise ValueError("start_date / end_date 값이 없습니다.")

    # ✅ 업체 필터 처리 (cafe24_service.py와 동일한 패턴)
    query_params_base = []
    
    if company_name == "all":
        if user_id == "demo":
            company_filter = "LOWER(company_name) = 'demo'"
        else:
            company_filter = "LOWER(company_name) != 'demo'"
    elif isinstance(company_name, list):
        filtered_companies = [name.lower() for name in company_name]
        
        if user_id == "demo":
            filtered_companies = ["demo"]
        else:
            filtered_companies = [name for name in filtered_companies if name != "demo"]
            
        if not filtered_companies:
            print("[DEBUG] 필터링된 company_name 리스트 없음 → 빈 결과 반환")
            return []
            
        company_filter = "LOWER(company_name) IN UNNEST(@company_name_list)"
        query_params_base.append(
            bigquery.ArrayQueryParameter("company_name_list", "STRING", filtered_companies)
        )
        print(f"[DEBUG] company_name이 리스트: {filtered_companies}")
    else:
        company_name = company_name.lower()
        if company_name == "demo" and user_id != "demo":
            print("[DEBUG] demo 계정 아님 + demo 요청 → 빈 결과 반환")
            return []
            
        company_filter = "LOWER(company_name) = LOWER(@company_name)"
        query_params_base.append(
            bigquery.ScalarQueryParameter("company_name", "STRING", company_name)
        )
        print(f"[DEBUG] company_name이 문자열: {company_name}")

    # ✅ 날짜 및 페이징 파라미터
    query_params_common = [
        bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
        bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
        bigquery.ScalarQueryParameter("limit", "INT64", limit),
    ]
    query_params = query_params_base + query_params_common

    print(f"[DEBUG] 최종 필터 조건: {company_filter}")
    print(f"[DEBUG] 날짜 범위: {start_date} ~ {end_date}")

    # ✅ 최적화된 쿼리: LIMIT 추가, 필터링 조건 강화
    query = f"""
    SELECT
      FORMAT_DATE('%Y-%m-%d', @start_date) || ' ~ ' || FORMAT_DATE('%Y-%m-%d', @end_date) AS report_period,
      company_name,
      REGEXP_REPLACE(
        REGEXP_REPLACE(
          REGEXP_REPLACE(product_name, r'^\\[[^\\]]+\\]\\s*', ''),  -- [브랜드] 제거
          r'_[^_]+$',                                                -- _컬러 제거
          ''
        ),
        r'["\\'""'']', ''                                            -- 따옴표 제거
      ) AS cleaned_product_name,
      SUM(item_quantity) AS item_quantity,
      SUM(item_product_sales) AS item_product_sales,
      ROUND(SUM(item_product_sales) * 100.0 / SUM(SUM(item_product_sales)) OVER (), 1) AS sales_ratio_percent
    FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_items`
    WHERE payment_date BETWEEN @start_date AND @end_date
      AND {company_filter}
      AND item_product_sales > 0
      AND product_name IS NOT NULL
    GROUP BY report_period, company_name, cleaned_product_name
    HAVING item_product_sales > 0
    ORDER BY item_product_sales DESC
    LIMIT @limit
    """

    print("[DEBUG] product_sales_ratio 쿼리 (최적화됨):\n", query)

    try:
        client = get_bigquery_client()
        rows = client.query(query, job_config=bigquery.QueryJobConfig(query_parameters=query_params)).result()
        data = [dict(row) for row in rows]
        print(f"[DEBUG] product_sales_ratio 결과: {len(data)} 건")
        
        # 결과가 없을 때 디버깅을 위한 추가 정보
        if len(data) == 0:
            print(f"[DEBUG] ⚠️ 데이터 없음 - 조건 확인:")
            print(f"  - company_name: {company_name}")
            print(f"  - start_date: {start_date}")
            print(f"  - end_date: {end_date}")
            print(f"  - company_filter: {company_filter}")
            
            # 데이터 존재 여부 확인 쿼리
            check_query = f"""
            SELECT COUNT(*) as total_count
            FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_items`
            WHERE payment_date BETWEEN @start_date AND @end_date
              AND {company_filter}
              AND item_product_sales > 0
              AND product_name IS NOT NULL
            """
            check_result = client.query(check_query, job_config=bigquery.QueryJobConfig(query_parameters=query_params)).result()
            total_count = next(check_result).total_count
            print(f"  - 조건에 맞는 총 레코드 수: {total_count}")
        
        return data
    except Exception as ex:
        print("[ERROR] get_product_sales_ratio 오류:", ex)
        return []
