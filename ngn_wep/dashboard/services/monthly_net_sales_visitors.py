from google.cloud import bigquery
from ..utils.cache_utils import cached_query

def get_bigquery_client():
    return bigquery.Client()

@cached_query(func_name="monthly_net_sales_visitors", ttl=3600)  # 1시간 캐싱
def get_monthly_net_sales_visitors(company_name):
    """
    ✅ 오늘 포함 월부터 13개월 전까지 (총 14개월)
    - company_name이 리스트이면 IN UNNEST 처리
    - net_sales, total_visitors 출력
    """

    # ✅ 업체 필터 분기 처리
    if isinstance(company_name, list):
        company_filter_cte = "LOWER(company_name) IN UNNEST(@company_name_list)"
        company_filter_final = "LOWER(s.company_name) IN UNNEST(@company_name_list)"
        query_params = [
            bigquery.ArrayQueryParameter("company_name_list", "STRING", company_name)
        ]
    else:
        company_filter_cte = "LOWER(company_name) = LOWER(@company_name)"
        company_filter_final = "LOWER(s.company_name) = LOWER(@company_name)"
        query_params = [
            bigquery.ScalarQueryParameter("company_name", "STRING", company_name)
        ]

    query = f"""
    WITH
      monthly_sales AS (
        SELECT
          company_name,
          FORMAT_DATE('%Y-%m', payment_date) AS month,
          SUM(net_sales) AS net_sales
        FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
        WHERE payment_date BETWEEN DATE_SUB(DATE_TRUNC(CURRENT_DATE(), MONTH), INTERVAL 13 MONTH)
                               AND CURRENT_DATE()
          AND {company_filter_cte}
          AND company_name IS NOT NULL
        GROUP BY company_name, month
      ),
      monthly_traffic AS (
        SELECT
          company_name,
          FORMAT_DATE('%Y-%m', event_date) AS month,
          SUM(total_users) AS total_visitors
        FROM `winged-precept-443218-v8.ngn_dataset.ga4_traffic_ngn`
        WHERE event_date BETWEEN DATE_SUB(DATE_TRUNC(CURRENT_DATE(), MONTH), INTERVAL 13 MONTH)
                             AND CURRENT_DATE()  -- ✅ 오늘 포함되도록 수정
          AND total_users > 0
          AND company_name IS NOT NULL
          AND (first_user_source != '(not set)' AND first_user_source != 'not set' AND first_user_source IS NOT NULL)
        GROUP BY company_name, month
      )
    SELECT
      s.company_name,
      s.month AS date,
      s.net_sales,
      COALESCE(t.total_visitors, 0) AS total_visitors
    FROM monthly_sales s
    LEFT JOIN monthly_traffic t
      ON s.company_name = t.company_name
      AND s.month = t.month
    WHERE {company_filter_final}
    ORDER BY s.month ASC
    """

    print("[DEBUG] monthly_net_sales_visitors 쿼리:\n", query)

    try:
        client = get_bigquery_client()
        rows = client.query(query, job_config=bigquery.QueryJobConfig(query_parameters=query_params)).result()
        data = [dict(row) for row in rows]
        print(f"[DEBUG] monthly_net_sales_visitors 결과: {len(data)} 건")
        return data
    except Exception as ex:
        print("[ERROR] get_monthly_net_sales_visitors 오류:", ex)
        return []
