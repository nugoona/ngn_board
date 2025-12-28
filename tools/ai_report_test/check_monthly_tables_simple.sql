-- ============================================
-- 월간 집계 테이블 간단 확인 쿼리
-- ============================================
-- @company_name 파라미터에 회사명 입력 (예: 'piscess')
-- ============================================

-- 최근 3개월 데이터 확인
SELECT 
  'mall_sales_monthly' AS table_name,
  company_name,
  month_date,
  net_sales,
  total_orders,
  updated_at
FROM `winged-precept-443218-v8.ngn_dataset.mall_sales_monthly`
WHERE company_name = @company_name
ORDER BY month_date DESC
LIMIT 3;

SELECT 
  'meta_ads_monthly' AS table_name,
  company_name,
  month_date,
  spend,
  purchases,
  purchase_value,
  updated_at
FROM `winged-precept-443218-v8.ngn_dataset.meta_ads_monthly`
WHERE company_name = @company_name
ORDER BY month_date DESC
LIMIT 3;

SELECT 
  'ga4_traffic_monthly' AS table_name,
  company_name,
  month_date,
  total_users,
  add_to_cart_users,
  sign_up_users,
  updated_at
FROM `winged-precept-443218-v8.ngn_dataset.ga4_traffic_monthly`
WHERE company_name = @company_name
ORDER BY month_date DESC
LIMIT 3;

-- 테이블별 최신 업데이트 시간 확인
SELECT 
  'mall_sales_monthly' AS table_name,
  MAX(updated_at) AS last_updated,
  COUNT(*) AS total_rows
FROM `winged-precept-443218-v8.ngn_dataset.mall_sales_monthly`
WHERE company_name = @company_name

UNION ALL

SELECT 
  'meta_ads_monthly' AS table_name,
  MAX(updated_at) AS last_updated,
  COUNT(*) AS total_rows
FROM `winged-precept-443218-v8.ngn_dataset.meta_ads_monthly`
WHERE company_name = @company_name

UNION ALL

SELECT 
  'ga4_traffic_monthly' AS table_name,
  MAX(updated_at) AS last_updated,
  COUNT(*) AS total_rows
FROM `winged-precept-443218-v8.ngn_dataset.ga4_traffic_monthly`
WHERE company_name = @company_name;

