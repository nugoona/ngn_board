-- 파이시스(piscess) 장바구니/회원가입 데이터 누락 날짜 상세 확인
-- 사용법: BigQuery에서 실행

WITH date_range AS (
  SELECT date
  FROM UNNEST(GENERATE_DATE_ARRAY(DATE('2024-12-01'), DATE('2025-12-25'), INTERVAL 1 DAY)) AS date
),
existing_data AS (
  SELECT 
    DATE(date) AS date,
    cart_users,
    signup_count
  FROM `winged-precept-443218-v8.ngn_dataset.performance_summary_ngn`
  WHERE LOWER(company_name) = 'piscess'
    AND DATE(date) >= DATE('2024-12-01')
    AND DATE(date) <= DATE('2025-12-25')
)
SELECT
  d.date,
  CASE 
    WHEN e.date IS NULL THEN '데이터 없음 (테이블에 행 자체가 없음)'
    WHEN e.cart_users = 0 AND e.signup_count = 0 THEN '데이터 있으나 모두 0'
    ELSE '데이터 있음'
  END AS status,
  COALESCE(e.cart_users, 0) AS cart_users,
  COALESCE(e.signup_count, 0) AS signup_count
FROM date_range d
LEFT JOIN existing_data e ON d.date = e.date
WHERE e.date IS NULL OR (e.cart_users = 0 AND e.signup_count = 0)
ORDER BY d.date;

