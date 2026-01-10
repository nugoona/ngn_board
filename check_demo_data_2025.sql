-- ============================================
-- 데모 계정 2025년 데이터 확인 쿼리
-- ============================================

-- 1. daily_cafe24_sales 테이블에서 2025년 데모 데이터 확인
SELECT 
  'daily_cafe24_sales' AS table_name,
  EXTRACT(YEAR FROM payment_date) AS year,
  EXTRACT(MONTH FROM payment_date) AS month,
  COUNT(*) AS record_count,
  SUM(net_sales) AS total_net_sales,
  SUM(total_orders) AS total_orders,
  MIN(payment_date) AS min_date,
  MAX(payment_date) AS max_date
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE LOWER(company_name) = 'demo'
  AND EXTRACT(YEAR FROM payment_date) = 2025
GROUP BY year, month
ORDER BY year, month;

-- 2. mall_sales_monthly 테이블에서 2025년 데모 데이터 확인
SELECT 
  'mall_sales_monthly' AS table_name,
  EXTRACT(YEAR FROM month_date) AS year,
  EXTRACT(MONTH FROM month_date) AS month,
  COUNT(*) AS record_count,
  SUM(net_sales) AS total_net_sales,
  SUM(total_orders) AS total_orders,
  MIN(month_date) AS min_date,
  MAX(month_date) AS max_date
FROM `winged-precept-443218-v8.ngn_dataset.mall_sales_monthly`
WHERE LOWER(company_name) = 'demo'
  AND EXTRACT(YEAR FROM month_date) = 2025
GROUP BY year, month
ORDER BY year, month;

-- 3. meta_ads_account_summary 테이블에서 2025년 데모 데이터 확인
SELECT 
  'meta_ads_account_summary' AS table_name,
  EXTRACT(YEAR FROM date) AS year,
  EXTRACT(MONTH FROM date) AS month,
  COUNT(*) AS record_count,
  SUM(spend) AS total_spend,
  SUM(impressions) AS total_impressions,
  SUM(clicks) AS total_clicks,
  MIN(date) AS min_date,
  MAX(date) AS max_date
FROM `winged-precept-443218-v8.ngn_dataset.meta_ads_account_summary`
WHERE LOWER(company_name) = 'demo'
  AND EXTRACT(YEAR FROM date) = 2025
GROUP BY year, month
ORDER BY year, month;

-- 3-2. meta_ads_monthly 테이블에서 2025년 데모 데이터 확인 (월간 집계)
SELECT 
  'meta_ads_monthly' AS table_name,
  EXTRACT(YEAR FROM month_date) AS year,
  EXTRACT(MONTH FROM month_date) AS month,
  COUNT(*) AS record_count,
  SUM(spend) AS total_spend,
  SUM(impressions) AS total_impressions,
  SUM(clicks) AS total_clicks,
  MIN(month_date) AS min_date,
  MAX(month_date) AS max_date
FROM `winged-precept-443218-v8.ngn_dataset.meta_ads_monthly`
WHERE LOWER(company_name) = 'demo'
  AND EXTRACT(YEAR FROM month_date) = 2025
GROUP BY year, month
ORDER BY year, month;

-- 4. ga4_traffic_ngn 테이블에서 2025년 데모 데이터 확인
-- event_date는 DATE 타입
SELECT 
  'ga4_traffic_ngn' AS table_name,
  EXTRACT(YEAR FROM event_date) AS year,
  EXTRACT(MONTH FROM event_date) AS month,
  COUNT(*) AS record_count,
  SUM(total_users) AS total_users,
  SUM(screen_page_views) AS total_views,
  SUM(event_count) AS total_events,
  MIN(event_date) AS min_date,
  MAX(event_date) AS max_date
FROM `winged-precept-443218-v8.ngn_dataset.ga4_traffic_ngn`
WHERE LOWER(company_name) = 'demo'
  AND EXTRACT(YEAR FROM event_date) = 2025
GROUP BY year, month
ORDER BY year, month;

-- 4-2. ga4_traffic_monthly 테이블에서 2025년 데모 데이터 확인 (월간 집계)
SELECT 
  'ga4_traffic_monthly' AS table_name,
  EXTRACT(YEAR FROM month_date) AS year,
  EXTRACT(MONTH FROM month_date) AS month,
  COUNT(*) AS record_count,
  SUM(total_users) AS total_users,
  SUM(screen_page_views) AS total_views,
  SUM(event_count) AS total_events,
  MIN(month_date) AS min_date,
  MAX(month_date) AS max_date
FROM `winged-precept-443218-v8.ngn_dataset.ga4_traffic_monthly`
WHERE LOWER(company_name) = 'demo'
  AND EXTRACT(YEAR FROM month_date) = 2025
GROUP BY year, month
ORDER BY year, month;

-- 5. 전체 요약: 데모 계정 2025년 데이터 존재 여부
SELECT 
  'daily_cafe24_sales' AS table_name,
  COUNT(*) AS total_records_2025,
  COUNT(DISTINCT DATE(payment_date)) AS distinct_dates,
  MIN(payment_date) AS earliest_date,
  MAX(payment_date) AS latest_date
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE LOWER(company_name) = 'demo'
  AND EXTRACT(YEAR FROM payment_date) = 2025

UNION ALL

SELECT 
  'mall_sales_monthly' AS table_name,
  COUNT(*) AS total_records_2025,
  COUNT(DISTINCT month_date) AS distinct_dates,
  CAST(MIN(month_date) AS DATE) AS earliest_date,
  CAST(MAX(month_date) AS DATE) AS latest_date
FROM `winged-precept-443218-v8.ngn_dataset.mall_sales_monthly`
WHERE LOWER(company_name) = 'demo'
  AND EXTRACT(YEAR FROM month_date) = 2025

UNION ALL

SELECT 
  'meta_ads_account_summary' AS table_name,
  COUNT(*) AS total_records_2025,
  COUNT(DISTINCT date) AS distinct_dates,
  CAST(MIN(date) AS DATE) AS earliest_date,
  CAST(MAX(date) AS DATE) AS latest_date
FROM `winged-precept-443218-v8.ngn_dataset.meta_ads_account_summary`
WHERE LOWER(company_name) = 'demo'
  AND EXTRACT(YEAR FROM date) = 2025

UNION ALL

SELECT 
  'meta_ads_monthly' AS table_name,
  COUNT(*) AS total_records_2025,
  COUNT(DISTINCT month_date) AS distinct_dates,
  CAST(MIN(month_date) AS DATE) AS earliest_date,
  CAST(MAX(month_date) AS DATE) AS latest_date
FROM `winged-precept-443218-v8.ngn_dataset.meta_ads_monthly`
WHERE LOWER(company_name) = 'demo'
  AND EXTRACT(YEAR FROM month_date) = 2025

UNION ALL

SELECT 
  'ga4_traffic_ngn' AS table_name,
  COUNT(*) AS total_records_2025,
  COUNT(DISTINCT event_date) AS distinct_dates,
  CAST(MIN(event_date) AS DATE) AS earliest_date,
  CAST(MAX(event_date) AS DATE) AS latest_date
FROM `winged-precept-443218-v8.ngn_dataset.ga4_traffic_ngn`
WHERE LOWER(company_name) = 'demo'
  AND EXTRACT(YEAR FROM event_date) = 2025

UNION ALL

SELECT 
  'ga4_traffic_monthly' AS table_name,
  COUNT(*) AS total_records_2025,
  COUNT(DISTINCT month_date) AS distinct_dates,
  CAST(MIN(month_date) AS DATE) AS earliest_date,
  CAST(MAX(month_date) AS DATE) AS latest_date
FROM `winged-precept-443218-v8.ngn_dataset.ga4_traffic_monthly`
WHERE LOWER(company_name) = 'demo'
  AND EXTRACT(YEAR FROM month_date) = 2025
ORDER BY table_name;

-- 6. 데모 계정이 존재하는 모든 company_name 값 확인
SELECT DISTINCT company_name, COUNT(*) AS count
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE LOWER(company_name) LIKE '%demo%'
GROUP BY company_name;
