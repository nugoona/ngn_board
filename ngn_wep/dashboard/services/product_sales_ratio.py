from google.cloud import bigquery

def get_bigquery_client():
    return bigquery.Client()

def get_product_sales_ratio(company_name, start_date: str, end_date: str):
    """
    ✅ 기간: start_date ~ end_date
    ✅ 업체명: company_name (리스트 or 문자열)
    ✅ cleaned_product_name 기준 그룹화
    ✅ 매출 총합 대비 비중 계산 (%)
    ✅ 날짜는 "YYYY-MM-DD ~ YYYY-MM-DD" 형식
    """
    if not start_date or not end_date:
        raise ValueError("start_date / end_date 값이 없습니다.")

    # ✅ 업체명 필터 분기 처리
    if isinstance(company_name, list):
        company_filter = "LOWER(company_name) IN UNNEST(@company_name_list)"
        query_params = [
            bigquery.ArrayQueryParameter("company_name_list", "STRING", company_name),
            bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
            bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
        ]
    else:
        company_filter = "LOWER(company_name) = LOWER(@company_name)"
        query_params = [
            bigquery.ScalarQueryParameter("company_name", "STRING", company_name),
            bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
            bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
        ]

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
        r'["\\'“”‘’]', ''                                            -- 따옴표 제거
      ) AS cleaned_product_name,
      SUM(item_quantity) AS item_quantity,
      SUM(item_product_sales) AS item_product_sales,
      ROUND(SUM(item_product_sales) * 100.0 / SUM(SUM(item_product_sales)) OVER (), 1) AS sales_ratio_percent
    FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_items`
    WHERE payment_date BETWEEN @start_date AND @end_date
      AND {company_filter}
    GROUP BY report_period, company_name, cleaned_product_name
    ORDER BY item_product_sales DESC
    """

    print("[DEBUG] product_sales_ratio 쿼리:\n", query)

    try:
        client = get_bigquery_client()
        rows = client.query(query, job_config=bigquery.QueryJobConfig(query_parameters=query_params)).result()
        data = [dict(row) for row in rows]
        print(f"[DEBUG] product_sales_ratio 결과: {len(data)} 건")
        return data
    except Exception as ex:
        print("[ERROR] get_product_sales_ratio 오류:", ex)
        return []
