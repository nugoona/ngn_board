def get_period_filtered_query(account_name="all", period_unit="daily", limit=15, offset=0):
    date_expression = {
        "daily": "FORMAT_TIMESTAMP('%Y-%m-%d', date)",
        "weekly": "FORMAT_TIMESTAMP('%Y-%m-%d', DATE_TRUNC(date, WEEK(MONDAY)))",
        "monthly": "FORMAT_TIMESTAMP('%Y-%m', DATE_TRUNC(date, MONTH))"
    }.get(period_unit, "FORMAT_TIMESTAMP('%Y-%m-%d', date)")

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
        query += f"WHERE account_name = '{account_name}'\n"

    query += "GROUP BY account_name, period_date\n"
    query += "ORDER BY period_date DESC\n"

    if limit is not None:
        query += f"LIMIT {limit}\n"
    if offset is not None:
        query += f"OFFSET {offset}\n"

    return query
