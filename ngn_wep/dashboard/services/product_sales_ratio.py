from google.cloud import bigquery
from utils.cache_utils import cached_query

def get_bigquery_client():
    return bigquery.Client()

@cached_query(func_name="product_sales_ratio", ttl=900)  # 15분 캐싱
def get_product_sales_ratio(company_name, start_date: str, end_date: str, limit: int = 50):
    """
    ✅ 상품별 매출 비율 조회 (최적화됨)
    """

    if not start_date or not end_date:
        raise ValueError("start_date / end_date 값이 없습니다.")

    # ✅ 업체 필터 처리
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
        return data
    except Exception as ex:
        print("[ERROR] get_product_sales_ratio 오류:", ex)
        return []
