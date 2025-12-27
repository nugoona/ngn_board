-- 파이시스(piscess) 장바구니/회원가입 데이터 월별 상세 집계 (0인 날짜 포함)
-- 사용법: BigQuery에서 실행

WITH date_range AS (
  SELECT date
  FROM UNNEST(GENERATE_DATE_ARRAY(DATE('2024-12-01'), DATE('2025-12-25'), INTERVAL 1 DAY)) AS date
),
monthly_summary AS (
  SELECT
    DATE_TRUNC(d.date, MONTH) AS month,
    d.date,
    COALESCE(MAX(p.cart_users), 0) AS cart_users,
    COALESCE(MAX(p.signup_count), 0) AS signup_count
  FROM date_range d
  LEFT JOIN `winged-precept-443218-v8.ngn_dataset.performance_summary_ngn` p
    ON DATE(d.date) = DATE(p.date)
    AND LOWER(p.company_name) = 'piscess'
  GROUP BY month, d.date
)
SELECT
  month,
  COUNT(*) AS total_days,
  COUNTIF(cart_users > 0 OR signup_count > 0) AS days_with_data,
  COUNTIF(cart_users = 0 AND signup_count = 0) AS days_without_data,
  SUM(cart_users) AS total_cart_users,
  SUM(signup_count) AS total_signup_count,
  AVG(cart_users) AS avg_cart_users,
  AVG(signup_count) AS avg_signup_count,
  MAX(cart_users) AS max_cart_users,
  MAX(signup_count) AS max_signup_count
FROM monthly_summary
GROUP BY month
ORDER BY month;

