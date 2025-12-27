-- 파이시스(piscess) 장바구니/회원가입 데이터 월별 집계
-- 사용법: BigQuery에서 실행

SELECT
  DATE_TRUNC(DATE(date), MONTH) AS month,
  COUNT(DISTINCT DATE(date)) AS days_collected,
  SUM(cart_users) AS total_cart_users,
  SUM(signup_count) AS total_signup_count,
  AVG(cart_users) AS avg_cart_users_per_day,
  AVG(signup_count) AS avg_signup_count_per_day,
  MAX(cart_users) AS max_cart_users,
  MAX(signup_count) AS max_signup_count,
  MIN(cart_users) AS min_cart_users,
  MIN(signup_count) AS min_signup_count
FROM `winged-precept-443218-v8.ngn_dataset.performance_summary_ngn`
WHERE LOWER(company_name) = 'piscess'
  AND DATE(date) >= DATE('2024-12-01')
  AND DATE(date) <= DATE('2025-12-25')
GROUP BY month
ORDER BY month;

