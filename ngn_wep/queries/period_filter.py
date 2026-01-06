from google.cloud import bigquery

def get_period_filtered_query(account_name="all", period_unit="daily", limit=15, offset=0):
    """
    특정 계정과 기간에 따른 데이터를 필터링하는 쿼리와 파라미터를 생성합니다.
    Returns: (query_string, query_params)
    """
    # 날짜 표현식 정의
    date_expression = {
        "daily": "FORMAT_TIMESTAMP('%Y-%m-%d', date)",
        "weekly": "FORMAT_TIMESTAMP('%Y-%m-%d', DATE_TRUNC(date, WEEK(MONDAY)))",
        "monthly": "FORMAT_TIMESTAMP('%Y-%m', DATE_TRUNC(date, MONTH))"
    }.get(period_unit, "FORMAT_TIMESTAMP('%Y-%m-%d', date)")

    query_params = []

    # 기본 쿼리
    base_query = f"""
    SELECT
        account_name,
        {date_expression} AS period_date,
        COALESCE(ROUND(SUM(total_spend)), 0) AS total_spend,
        COALESCE(ROUND(AVG(roas), 2), 0) AS roas,
        COALESCE(ROUND(SUM(total_purchases)), 0) AS total_purchases,
        COALESCE(ROUND(AVG(conversion_rate), 2), 0) AS conversion_rate,
        COALESCE(ROUND(SUM(total_purchase_value)), 0) AS total_purchase_value,
        COALESCE(ROUND(SUM(total_spend) / NULLIF(SUM(total_purchases), 0), 0), 0) AS cost_per_purchase,
        COALESCE(ROUND(SUM(total_purchase_value) / NULLIF(SUM(total_purchases), 0), 0), 0) AS average_order_value,
        COALESCE(ROUND(SUM(total_clicks)), 0) AS total_clicks,
        COALESCE(ROUND(SUM(total_spend) / NULLIF(SUM(total_clicks), 0), 0), 0) AS cpc,
        COALESCE(ROUND(AVG(ctr), 2), 0) AS ctr,
        COALESCE(ROUND(SUM(total_impressions)), 0) AS total_impressions,
        COALESCE(ROUND((SUM(total_spend) / NULLIF(SUM(total_impressions), 0)) * 1000, 0), 0) AS cpm
    FROM `winged-precept-443218-v8.ngn_dataset.highest_spend_data`
    """

    # 계정 필터링 (파라미터화)
    if account_name != "all":
        base_query += "WHERE account_name = @account_name\n"
        query_params.append(bigquery.ScalarQueryParameter("account_name", "STRING", account_name))

    # 그룹화 및 정렬
    base_query += "GROUP BY account_name, period_date\n"
    base_query += "ORDER BY period_date DESC\n"

    # 페이지네이션 (파라미터화)
    if limit is not None:
        base_query += "LIMIT @limit\n"
        query_params.append(bigquery.ScalarQueryParameter("limit", "INT64", limit))
    if offset is not None:
        base_query += "OFFSET @offset\n"
        query_params.append(bigquery.ScalarQueryParameter("offset", "INT64", offset))

    return base_query, query_params


def get_total_records_query(account_name="all", period_unit="daily"):
    """
    특정 계정과 기간에 따른 전체 레코드 수를 계산하는 쿼리와 파라미터를 생성합니다.
    Returns: (query_string, query_params)
    """
    # 날짜 표현식 정의
    date_expression = {
        "daily": "FORMAT_TIMESTAMP('%Y-%m-%d', date)",
        "weekly": "FORMAT_TIMESTAMP('%Y-%m-%d', DATE_TRUNC(date, WEEK(MONDAY)))",
        "monthly": "FORMAT_TIMESTAMP('%Y-%m', DATE_TRUNC(date, MONTH))"
    }.get(period_unit, "FORMAT_TIMESTAMP('%Y-%m-%d', date)")

    query_params = []

    # 기본 쿼리
    query = f"""
    SELECT COUNT(*) AS total_records
    FROM (
        SELECT DISTINCT account_name, {date_expression} AS period_date
        FROM `winged-precept-443218-v8.ngn_dataset.highest_spend_data`
    )
    """

    # 계정 필터링 (파라미터화)
    if account_name != "all":
        query += "WHERE account_name = @account_name"
        query_params.append(bigquery.ScalarQueryParameter("account_name", "STRING", account_name))

    return query, query_params

