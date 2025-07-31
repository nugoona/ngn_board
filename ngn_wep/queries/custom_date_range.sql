SELECT 
    account_name,
    COALESCE(SUM(total_spend), 0) AS total_spend,
    COALESCE(ROUND(AVG(roas), 2), 0) AS roas,
    COALESCE(SUM(total_purchases), 0) AS total_purchases,
    COALESCE(ROUND(AVG(conversion_rate), 2), 0) AS conversion_rate,
    COALESCE(SUM(total_purchase_value), 0) AS total_purchase_value,
    COALESCE(ROUND(SUM(total_purchase_value) / NULLIF(SUM(total_purchases), 0), 0), 0) AS average_order_value,
    COALESCE(ROUND(SUM(total_spend) / NULLIF(SUM(total_purchases), 0), 0), 0) AS cost_per_purchase,
    COALESCE(SUM(total_clicks), 0) AS total_clicks,
    COALESCE(ROUND(AVG(cpc), 0), 0) AS cpc,
    COALESCE(ROUND(AVG(ctr), 2), 0) AS ctr,
    COALESCE(SUM(total_impressions), 0) AS total_impressions,
    COALESCE(ROUND((SUM(total_spend) / NULLIF(SUM(total_impressions), 0)) * 1000, 0), 0) AS cpm
FROM `winged-precept-443218-v8.ngn_dataset.highest_spend_data`
WHERE period_date BETWEEN @start_date AND @end_date
  AND (@account_name = "all" OR account_name = @account_name)
GROUP BY account_name
