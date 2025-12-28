-- ============================================
-- 월간 집계 테이블 데이터 확인 쿼리
-- ============================================
-- Job 실행 후 데이터가 제대로 들어갔는지 확인
-- ============================================

-- 1. mall_sales_monthly 확인
SELECT 
  company_name,
  month_date,
  net_sales,
  total_orders,
  total_first_order,
  total_canceled,
  updated_at
FROM `winged-precept-443218-v8.ngn_dataset.mall_sales_monthly`
WHERE company_name = @company_name
ORDER BY month_date DESC
LIMIT 13;

-- 2. meta_ads_monthly 확인
SELECT 
  company_name,
  month_date,
  spend,
  impressions,
  clicks,
  purchases,
  purchase_value,
  updated_at
FROM `winged-precept-443218-v8.ngn_dataset.meta_ads_monthly`
WHERE company_name = @company_name
ORDER BY month_date DESC
LIMIT 13;

-- 3. ga4_traffic_monthly 확인 (새로 추가된 컬럼 포함)
SELECT 
  company_name,
  month_date,
  total_users,
  screen_page_views,
  event_count,
  add_to_cart_users,
  sign_up_users,
  updated_at
FROM `winged-precept-443218-v8.ngn_dataset.ga4_traffic_monthly`
WHERE company_name = @company_name
ORDER BY month_date DESC
LIMIT 13;

-- 4. ga4_viewitem_monthly_raw 확인
SELECT 
  company_name,
  ym,
  COUNT(*) AS item_count,
  SUM(view_item) AS total_view_item,
  MAX(updated_at) AS last_updated
FROM `winged-precept-443218-v8.ngn_dataset.ga4_viewitem_monthly_raw`
WHERE company_name = @company_name
GROUP BY company_name, ym
ORDER BY ym DESC
LIMIT 13;

-- 5. 최근 3개월 데이터 요약 (모든 테이블)
WITH recent_months AS (
  SELECT DISTINCT month_date
  FROM `winged-precept-443218-v8.ngn_dataset.mall_sales_monthly`
  WHERE company_name = @company_name
  ORDER BY month_date DESC
  LIMIT 3
)
SELECT 
  'mall_sales' AS table_name,
  m.month_date,
  m.net_sales,
  m.total_orders
FROM `winged-precept-443218-v8.ngn_dataset.mall_sales_monthly` m
INNER JOIN recent_months r ON m.month_date = r.month_date
WHERE m.company_name = @company_name

UNION ALL

SELECT 
  'meta_ads' AS table_name,
  m.month_date,
  CAST(m.spend AS FLOAT64) AS net_sales,
  CAST(m.purchases AS INT64) AS total_orders
FROM `winged-precept-443218-v8.ngn_dataset.meta_ads_monthly` m
INNER JOIN recent_months r ON m.month_date = r.month_date
WHERE m.company_name = @company_name

UNION ALL

SELECT 
  'ga4_traffic' AS table_name,
  g.month_date,
  CAST(g.total_users AS FLOAT64) AS net_sales,
  CAST(g.add_to_cart_users AS INT64) AS total_orders
FROM `winged-precept-443218-v8.ngn_dataset.ga4_traffic_monthly` g
INNER JOIN recent_months r ON g.month_date = r.month_date
WHERE g.company_name = @company_name

ORDER BY table_name, month_date DESC;

