-- ============================================
-- 데모 계정 2025년 daily_cafe24_items 데이터 확인
-- ============================================

-- 1. daily_cafe24_items 테이블에서 2025년 데모 데이터 확인 (월별)
SELECT 
  'daily_cafe24_items' AS table_name,
  EXTRACT(YEAR FROM payment_date) AS year,
  EXTRACT(MONTH FROM payment_date) AS month,
  COUNT(*) AS record_count,
  COUNT(DISTINCT product_no) AS distinct_products,
  SUM(item_quantity) AS total_quantity,
  SUM(item_product_sales) AS total_sales,
  MIN(payment_date) AS min_date,
  MAX(payment_date) AS max_date
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_items`
WHERE LOWER(company_name) = 'demo'
  AND EXTRACT(YEAR FROM payment_date) = 2025
GROUP BY year, month
ORDER BY year, month;

-- 2. 전체 요약: daily_cafe24_items에 2025년 데모 데이터 존재 여부
SELECT 
  'daily_cafe24_items' AS table_name,
  COUNT(*) AS total_records_2025,
  COUNT(DISTINCT payment_date) AS distinct_dates,
  COUNT(DISTINCT product_no) AS distinct_products,
  SUM(item_quantity) AS total_quantity,
  SUM(item_product_sales) AS total_sales,
  MIN(payment_date) AS earliest_date,
  MAX(payment_date) AS latest_date
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_items`
WHERE LOWER(company_name) = 'demo'
  AND EXTRACT(YEAR FROM payment_date) = 2025;

-- 3. daily_cafe24_sales와 비교 (데이터 보충 후 확인용)
SELECT 
  'daily_cafe24_sales' AS table_name,
  COUNT(*) AS total_records_2025,
  COUNT(DISTINCT payment_date) AS distinct_dates,
  MIN(payment_date) AS earliest_date,
  MAX(payment_date) AS latest_date
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE LOWER(company_name) = 'demo'
  AND EXTRACT(YEAR FROM payment_date) = 2025

UNION ALL

SELECT 
  'daily_cafe24_items' AS table_name,
  COUNT(*) AS total_records_2025,
  COUNT(DISTINCT payment_date) AS distinct_dates,
  MIN(payment_date) AS earliest_date,
  MAX(payment_date) AS latest_date
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_items`
WHERE LOWER(company_name) = 'demo'
  AND EXTRACT(YEAR FROM payment_date) = 2025;
