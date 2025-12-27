-- 파이시스(piscess) 장바구니/회원가입 데이터가 0이거나 없는 날짜 확인
-- 사용법: BigQuery에서 실행

WITH date_range AS (
  SELECT date
  FROM UNNEST(GENERATE_DATE_ARRAY(DATE('2024-12-01'), DATE('2025-12-25'), INTERVAL 1 DAY)) AS date
),
existing_data AS (
  SELECT DISTINCT DATE(date) AS date
  FROM `winged-precept-443218-v8.ngn_dataset.performance_summary_ngn`
  WHERE LOWER(company_name) = 'piscess'
    AND DATE(date) >= DATE('2024-12-01')
    AND DATE(date) <= DATE('2025-12-25')
    AND (cart_users > 0 OR signup_count > 0)
)
SELECT
  d.date,
  CASE 
    WHEN e.date IS NOT NULL THEN '데이터 있음'
    ELSE '데이터 없음'
  END AS status
FROM date_range d
LEFT JOIN existing_data e ON d.date = e.date
WHERE e.date IS NULL  -- 데이터가 없는 날짜만
ORDER BY d.date;

