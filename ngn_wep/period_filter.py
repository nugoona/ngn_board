from google.cloud import bigquery

def get_period_filtered_query(account_name="all", period_unit="daily", limit=15, offset=0):
    """
    특정 계정과 기간에 따른 데이터를 필터링하는 쿼리와 파라미터를 생성합니다.
    Returns: (query_string, query_params)
    """
    date_expression = {
        "daily": "FORMAT_TIMESTAMP('%Y-%m-%d', date)",
        "weekly": "FORMAT_TIMESTAMP('%Y-%m-%d', DATE_TRUNC(date, WEEK(MONDAY)))",
        "monthly": "FORMAT_TIMESTAMP('%Y-%m', DATE_TRUNC(date, MONTH))"
    }.get(period_unit, "FORMAT_TIMESTAMP('%Y-%m-%d', date)")

    query_params = []

    query = f"""
    SELECT
        account_name,
        {date_expression} AS period_date,
        COALESCE(ROUND(SUM(total_spend), 0), 0) AS total_spend,
        COALESCE(ROUND((SUM(total_purchase_value) / NULLIF(SUM(total_spend), 0)) * 100, 2), 0) AS roas,
        COALESCE(SUM(total_purchases), 0) AS total_purchases,
        COALESCE(ROUND(SUM(total_purchases) / NULLIF(SUM(total_clicks), 0), 2), 0) AS conversion_rate,
        COALESCE(SUM(total_purchase_value), 0) AS total_purchase_value,
        COALESCE(ROUND(SUM(total_purchase_value) / NULLIF(SUM(total_purchases), 0), 0), 0) AS average_order_value,
        COALESCE(ROUND(SUM(total_spend) / NULLIF(SUM(total_purchases), 0), 0), 0) AS cost_per_purchase,
        COALESCE(SUM(total_clicks), 0) AS total_clicks,
        COALESCE(ROUND(SUM(total_spend) / NULLIF(SUM(total_clicks), 0), 0), 0) AS cpc,
        COALESCE(ROUND(SUM(total_clicks) / NULLIF(SUM(total_impressions), 0), 2), 0) AS ctr,
        COALESCE(SUM(total_impressions), 0) AS total_impressions,
        COALESCE(ROUND((SUM(total_spend) / NULLIF(SUM(total_impressions), 0)) * 1000, 0), 0) AS cpm
    FROM `winged-precept-443218-v8.ngn_dataset.highest_spend_data`
    """

    if account_name != "all":
        query += "WHERE account_name = @account_name\n"
        query_params.append(bigquery.ScalarQueryParameter("account_name", "STRING", account_name))

    query += "GROUP BY account_name, period_date\n"
    query += "ORDER BY period_date DESC\n"

    if limit is not None:
        query += "LIMIT @limit\n"
        query_params.append(bigquery.ScalarQueryParameter("limit", "INT64", limit))
    if offset is not None:
        query += "OFFSET @offset\n"
        query_params.append(bigquery.ScalarQueryParameter("offset", "INT64", offset))

    return query, query_params
