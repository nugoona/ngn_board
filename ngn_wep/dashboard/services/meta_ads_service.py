from google.cloud import bigquery

def get_bigquery_client():
    """ ✅ BigQuery Client 생성 """
    return bigquery.Client()

def get_meta_ads_data(company_name, period, start_date, end_date, date_type="summary", date_sort="desc"):
    """
    ✅ Meta Ads 광고 데이터 조회 (기간합 / 일자별 선택 가능) + 날짜 정렬 + AOV & CPC 포함
    """
    if not start_date or not end_date:
        raise ValueError("[ERROR] get_meta_ads_data() - start_date 또는 end_date가 누락됨")

    client = get_bigquery_client()

    # ✅ company_name 파라미터 분기 처리
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

    print(f"[DEBUG] get_meta_ads_data 내부 - company_name: {company_name}, start_date: {start_date}, end_date: {end_date}, date_type: {date_type}, date_sort: {date_sort}")

    order_by_clause = f"ORDER BY report_date {date_sort.upper()}, company_name" if date_type == "daily" else "ORDER BY company_name"

    query = f"""
    WITH ranked_data AS (
        SELECT
            ap.*,
            COALESCE(LOWER(ci.company_name), LOWER(ap.account_name), 'unknown') AS company_name,
            ROW_NUMBER() OVER (PARTITION BY ap.account_name, ap.date ORDER BY ap.spend DESC) AS row_num
        FROM `winged-precept-443218-v8.ngn_dataset.ads_performance` ap
        LEFT JOIN `winged-precept-443218-v8.ngn_dataset.company_info` ci
            ON ap.account_name = ci.meta_acc
    ),

    daily_data AS (
        SELECT 
            company_name,
            FORMAT_DATE('%Y-%m-%d', DATE(TIMESTAMP(date), 'UTC')) AS report_date,
            COALESCE(SUM(spend), 0) AS total_spend,
            COALESCE(SUM(impressions), 0) AS total_impressions,
            COALESCE(SUM(clicks), 0) AS total_clicks,
            COALESCE(SUM(purchases), 0) AS total_purchases,
            COALESCE(SUM(purchase_value), 0) AS total_purchase_value,
            COALESCE(ROUND(SUM(purchase_value) / NULLIF(SUM(purchases), 0), 2), 0.00) AS average_order_value,
            COALESCE(ROUND(SUM(spend) / NULLIF(SUM(clicks), 0), 2), 0.00) AS cpc,
            COALESCE(ROUND(SUM(purchase_value) / NULLIF(SUM(spend), 0) * 100, 2), 0.00) AS roas,
            CAST(ROUND(SUM(purchases) / NULLIF(SUM(clicks), 0) * 100, 2) AS FLOAT64) AS conversion_rate,
            CAST(ROUND(SUM(clicks) / NULLIF(SUM(impressions), 0) * 100, 2) AS FLOAT64) AS ctr,
            COALESCE(ROUND(SUM(spend) / NULLIF(SUM(impressions), 0) * 1000, 2), 0.00) AS cpm,
            COALESCE(ROUND(SUM(spend) / NULLIF(SUM(purchases), 0), 2), 0.00) AS cost_per_purchase
        FROM ranked_data
        WHERE row_num = 1
            AND date BETWEEN @start_date AND @end_date
            AND {company_filter}
            AND date IS NOT NULL
        GROUP BY company_name, report_date
    ),

    summary_data AS (
        SELECT 
            company_name,
            @start_date || ' ~ ' || @end_date AS report_date,
            COALESCE(SUM(spend), 0) AS total_spend,
            COALESCE(SUM(impressions), 0) AS total_impressions,
            COALESCE(SUM(clicks), 0) AS total_clicks,
            COALESCE(SUM(purchases), 0) AS total_purchases,
            COALESCE(SUM(purchase_value), 0) AS total_purchase_value,
            COALESCE(ROUND(SUM(purchase_value) / NULLIF(SUM(purchases), 0), 2), 0.00) AS average_order_value,
            COALESCE(ROUND(SUM(spend) / NULLIF(SUM(clicks), 0), 2), 0.00) AS cpc,
            COALESCE(ROUND(SUM(purchase_value) / NULLIF(SUM(spend), 0) * 100, 2), 0.00) AS roas,
            CAST(ROUND(SUM(purchases) / NULLIF(SUM(clicks), 0) * 100, 2) AS FLOAT64) AS conversion_rate,
            CAST(ROUND(SUM(clicks) / NULLIF(SUM(impressions), 0) * 100, 2) AS FLOAT64) AS ctr,
            COALESCE(ROUND(SUM(spend) / NULLIF(SUM(impressions), 0) * 1000, 2), 0.00) AS cpm,
            COALESCE(ROUND(SUM(spend) / NULLIF(SUM(purchases), 0), 2), 0.00) AS cost_per_purchase
        FROM ranked_data
        WHERE row_num = 1
            AND date BETWEEN @start_date AND @end_date
            AND {company_filter}
            AND date IS NOT NULL
        GROUP BY company_name
    )

    SELECT * FROM { "daily_data" if date_type == "daily" else "summary_data" }
    {order_by_clause};
    """

    print("\n[DEBUG] Meta Ads 데이터 쿼리 실행:\n", query)

    try:
        results = client.query(query, job_config=bigquery.QueryJobConfig(query_parameters=query_params)).result()
        data = [dict(row) for row in results]
        print(f"[DEBUG] Meta Ads API 응답 데이터: {data}")
        return data
    except Exception as e:
        print(f"[ERROR] BigQuery 실행 오류: {e}")
        return []
