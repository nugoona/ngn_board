-- ============================================
-- mall_sales_monthly 데이터 확인 및 daily_cafe24_sales 기반 분석
-- ============================================

-- 1. mall_sales_monthly 테이블: piscess와 demo의 데이터 현황 확인
SELECT 
  company_name,
  month_date,
  net_sales,
  total_orders,
  total_first_order,
  total_canceled,
  updated_at
FROM `winged-precept-443218-v8.ngn_dataset.mall_sales_monthly`
WHERE company_name IN ('piscess', 'demo')
  AND month_date >= '2024-04-01'
  AND month_date < '2025-01-01'
ORDER BY company_name, month_date;

-- 2. daily_cafe24_sales 테이블: piscess의 2024-12 데이터 확인
SELECT 
  'piscess' AS company_name,
  MIN(payment_date) AS min_date,
  MAX(payment_date) AS max_date,
  COUNT(DISTINCT DATE_TRUNC(payment_date, MONTH)) AS months_count,
  COUNT(*) AS total_rows,
  CAST(SUM(net_sales) AS NUMERIC) AS total_net_sales
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE company_name = 'piscess'
  AND payment_date >= '2024-12-01'
  AND payment_date < '2025-01-01'

UNION ALL

-- 3. daily_cafe24_sales 테이블: demo의 2024-04~2024-12 데이터 확인
SELECT 
  'demo' AS company_name,
  MIN(payment_date) AS min_date,
  MAX(payment_date) AS max_date,
  COUNT(DISTINCT DATE_TRUNC(payment_date, MONTH)) AS months_count,
  COUNT(*) AS total_rows,
  CAST(SUM(net_sales) AS NUMERIC) AS total_net_sales
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE company_name = 'demo'
  AND payment_date >= '2024-04-01'
  AND payment_date < '2025-01-01';

-- 4. 월별 집계: piscess 2024-12 데이터가 daily에 있는지 확인
SELECT 
  company_name,
  DATE_TRUNC(payment_date, MONTH) AS month_date,
  CAST(SUM(net_sales) AS NUMERIC) AS net_sales,
  SUM(total_orders) AS total_orders,
  SUM(total_first_order) AS total_first_order,
  SUM(total_canceled) AS total_canceled,
  COUNT(*) AS daily_rows_count
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE company_name = 'piscess'
  AND payment_date >= '2024-12-01'
  AND payment_date < '2025-01-01'
GROUP BY company_name, month_date;

-- 5. 월별 집계: demo 2024-04~2024-12 데이터가 daily에 있는지 확인
SELECT 
  company_name,
  DATE_TRUNC(payment_date, MONTH) AS month_date,
  CAST(SUM(net_sales) AS NUMERIC) AS net_sales,
  SUM(total_orders) AS total_orders,
  SUM(total_first_order) AS total_first_order,
  SUM(total_canceled) AS total_canceled,
  COUNT(*) AS daily_rows_count
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE company_name = 'demo'
  AND payment_date >= '2024-04-01'
  AND payment_date < '2025-01-01'
GROUP BY company_name, month_date
ORDER BY month_date;
