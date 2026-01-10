-- ============================================
-- demo 계정 섹션3: 장바구니 데이터 확인
-- performance_summary_ngn 테이블에서 cart_users 확인
-- ============================================

-- 1. performance_summary_ngn에서 demo 계정의 장바구니 데이터 확인
SELECT 
  date,
  company_name,
  cart_users,
  signup_count,
  total_visitors,
  site_revenue,
  ad_spend,
  total_clicks,
  total_purchases
FROM `winged-precept-443218-v8.ngn_dataset.performance_summary_ngn`
WHERE LOWER(company_name) = 'demo'
  AND DATE(date) >= '2024-12-01'
  AND DATE(date) <= '2026-12-31'
ORDER BY date DESC
LIMIT 30;

-- 2. 최근 7일 집계 확인
SELECT 
  DATE_TRUNC(DATE(date), WEEK) AS week_start,
  SUM(cart_users) AS total_cart_users,
  SUM(signup_count) AS total_signup_count,
  SUM(total_visitors) AS total_visitors,
  COUNT(*) AS record_count
FROM `winged-precept-443218-v8.ngn_dataset.performance_summary_ngn`
WHERE LOWER(company_name) = 'demo'
  AND DATE(date) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY week_start
ORDER BY week_start DESC;

-- 3. 날짜별 상세 확인 (최근 10일)
SELECT 
  date,
  company_name,
  cart_users,
  signup_count,
  CASE 
    WHEN cart_users > 0 THEN 'OK'
    ELSE 'MISSING'
  END AS status
FROM `winged-precept-443218-v8.ngn_dataset.performance_summary_ngn`
WHERE LOWER(company_name) = 'demo'
  AND DATE(date) >= DATE_SUB(CURRENT_DATE(), INTERVAL 10 DAY)
ORDER BY date DESC;

-- 4. get_performance_summary_new 쿼리 시뮬레이션
-- (실제 API에서 사용하는 쿼리와 동일)
SELECT
  COALESCE(SUM(cart_users), 0) AS cart_users,
  COALESCE(SUM(signup_count), 0) AS signup_count
FROM `winged-precept-443218-v8.ngn_dataset.performance_summary_ngn`
WHERE LOWER(company_name) = 'demo'
  AND DATE(date) BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY) AND CURRENT_DATE();

-- 5. 월별 집계 확인
SELECT 
  DATE_TRUNC(DATE(date), MONTH) AS month_date,
  SUM(cart_users) AS total_cart_users,
  SUM(signup_count) AS total_signup_count,
  AVG(cart_users) AS avg_cart_users_per_day,
  COUNT(*) AS record_count
FROM `winged-precept-443218-v8.ngn_dataset.performance_summary_ngn`
WHERE LOWER(company_name) = 'demo'
  AND DATE(date) >= '2024-12-01'
  AND DATE(date) <= '2026-12-31'
GROUP BY month_date
ORDER BY month_date DESC;
