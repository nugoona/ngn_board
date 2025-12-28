-- ============================================
-- 모든 월간 집계 테이블 데이터 채우기 (2024-12 ~ 2025-12)
-- ============================================
-- 한 번에 실행하면 모든 과거 데이터가 채워집니다
-- ============================================

-- 1. mall_sales_monthly 채우기
MERGE `winged-precept-443218-v8.ngn_dataset.mall_sales_monthly` T
USING (
  SELECT
    company_name,
    DATE_TRUNC(payment_date, MONTH) AS month_date,
    CAST(SUM(net_sales) AS NUMERIC) AS net_sales,
    SUM(total_orders) AS total_orders,
    SUM(total_first_order) AS total_first_order,
    SUM(total_canceled) AS total_canceled,
    CURRENT_TIMESTAMP() AS updated_at
  FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
  WHERE payment_date >= '2024-12-01'
    AND payment_date < '2026-01-01'
    AND company_name IS NOT NULL
  GROUP BY company_name, month_date
) S
ON T.company_name = S.company_name AND T.month_date = S.month_date
WHEN MATCHED THEN UPDATE SET
  net_sales=S.net_sales,
  total_orders=S.total_orders,
  total_first_order=S.total_first_order,
  total_canceled=S.total_canceled,
  updated_at=S.updated_at
WHEN NOT MATCHED THEN INSERT (
  company_name, month_date, net_sales, total_orders, total_first_order, total_canceled, updated_at
) VALUES (
  S.company_name, S.month_date, S.net_sales, S.total_orders, S.total_first_order, S.total_canceled, S.updated_at
);

-- 2. meta_ads_monthly 채우기
MERGE `winged-precept-443218-v8.ngn_dataset.meta_ads_monthly` T
USING (
  SELECT
    company_name,
    DATE_TRUNC(date, MONTH) AS month_date,
    CAST(SUM(spend) AS NUMERIC) AS spend,
    SUM(impressions) AS impressions,
    SUM(clicks) AS clicks,
    SUM(purchases) AS purchases,
    CAST(SUM(purchase_value) AS NUMERIC) AS purchase_value,
    CURRENT_TIMESTAMP() AS updated_at
  FROM `winged-precept-443218-v8.ngn_dataset.meta_ads_account_summary`
  WHERE date >= '2024-12-01'
    AND date < '2026-01-01'
    AND company_name IS NOT NULL
  GROUP BY company_name, month_date
) S
ON T.company_name = S.company_name AND T.month_date = S.month_date
WHEN MATCHED THEN UPDATE SET
  spend=S.spend,
  impressions=S.impressions,
  clicks=S.clicks,
  purchases=S.purchases,
  purchase_value=S.purchase_value,
  updated_at=S.updated_at
WHEN NOT MATCHED THEN INSERT (
  company_name, month_date, spend, impressions, clicks, purchases, purchase_value, updated_at
) VALUES (
  S.company_name, S.month_date, S.spend, S.impressions, S.clicks, S.purchases, S.purchase_value, S.updated_at
);

-- 3. ga4_traffic_monthly 채우기 (add_to_cart_users, sign_up_users 포함)
MERGE `winged-precept-443218-v8.ngn_dataset.ga4_traffic_monthly` T
USING (
  WITH ga4_monthly AS (
    SELECT
      company_name,
      DATE_TRUNC(event_date, MONTH) AS month_date,
      SUM(total_users) AS total_users,
      SUM(screen_page_views) AS screen_page_views,
      SUM(event_count) AS event_count
    FROM `winged-precept-443218-v8.ngn_dataset.ga4_traffic_ngn`
    WHERE event_date >= '2024-12-01'
      AND event_date < '2026-01-01'
      AND company_name IS NOT NULL
    GROUP BY company_name, month_date
  ),
  cart_signup_monthly AS (
    SELECT
      company_name,
      DATE_TRUNC(DATE(date), MONTH) AS month_date,
      COALESCE(SUM(cart_users), 0) AS add_to_cart_users,
      COALESCE(SUM(signup_count), 0) AS sign_up_users
    FROM `winged-precept-443218-v8.ngn_dataset.performance_summary_ngn`
    WHERE DATE(date) >= '2024-12-01'
      AND DATE(date) < '2026-01-01'
      AND company_name IS NOT NULL
    GROUP BY company_name, month_date
  )
  SELECT
    COALESCE(g.company_name, c.company_name) AS company_name,
    COALESCE(g.month_date, c.month_date) AS month_date,
    COALESCE(g.total_users, 0) AS total_users,
    COALESCE(g.screen_page_views, 0) AS screen_page_views,
    COALESCE(g.event_count, 0) AS event_count,
    COALESCE(c.add_to_cart_users, 0) AS add_to_cart_users,
    COALESCE(c.sign_up_users, 0) AS sign_up_users,
    CURRENT_TIMESTAMP() AS updated_at
  FROM ga4_monthly g
  FULL OUTER JOIN cart_signup_monthly c
    ON g.company_name = c.company_name
    AND g.month_date = c.month_date
) S
ON T.company_name = S.company_name AND T.month_date = S.month_date
WHEN MATCHED THEN UPDATE SET
  total_users=S.total_users,
  screen_page_views=S.screen_page_views,
  event_count=S.event_count,
  add_to_cart_users=S.add_to_cart_users,
  sign_up_users=S.sign_up_users,
  updated_at=S.updated_at
WHEN NOT MATCHED THEN INSERT (
  company_name, month_date, total_users, screen_page_views, event_count, add_to_cart_users, sign_up_users, updated_at
) VALUES (
  S.company_name, S.month_date, S.total_users, S.screen_page_views, S.event_count, S.add_to_cart_users, S.sign_up_users, S.updated_at
);

-- 4. 확인 쿼리
SELECT 
  'mall_sales_monthly' AS table_name,
  COUNT(*) AS total_rows,
  MIN(month_date) AS earliest_month,
  MAX(month_date) AS latest_month
FROM `winged-precept-443218-v8.ngn_dataset.mall_sales_monthly`

UNION ALL

SELECT 
  'meta_ads_monthly' AS table_name,
  COUNT(*) AS total_rows,
  MIN(month_date) AS earliest_month,
  MAX(month_date) AS latest_month
FROM `winged-precept-443218-v8.ngn_dataset.meta_ads_monthly`

UNION ALL

SELECT 
  'ga4_traffic_monthly' AS table_name,
  COUNT(*) AS total_rows,
  MIN(month_date) AS earliest_month,
  MAX(month_date) AS latest_month
FROM `winged-precept-443218-v8.ngn_dataset.ga4_traffic_monthly`;

