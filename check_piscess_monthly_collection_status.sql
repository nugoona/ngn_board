-- 파이시스(piscess) 월별 수집 상태 요약 (누락 일수 포함)
-- 사용법: BigQuery에서 실행

WITH date_range AS (
  SELECT date
  FROM UNNEST(GENERATE_DATE_ARRAY(DATE('2024-12-01'), DATE('2025-12-25'), INTERVAL 1 DAY)) AS date
),
monthly_status AS (
  SELECT
    DATE_TRUNC(d.date, MONTH) AS month,
    d.date,
    CASE 
      WHEN p.date IS NULL THEN 0  -- 데이터 없음
      WHEN p.cart_users = 0 AND p.signup_count = 0 THEN 1  -- 0으로 수집됨
      ELSE 2  -- 데이터 있음
    END AS data_status
  FROM date_range d
  LEFT JOIN `winged-precept-443218-v8.ngn_dataset.performance_summary_ngn` p
    ON DATE(d.date) = DATE(p.date)
    AND LOWER(p.company_name) = 'piscess'
)
SELECT
  month,
  COUNT(*) AS total_days_in_month,
  COUNTIF(data_status = 2) AS days_with_data,
  COUNTIF(data_status = 1) AS days_with_zero_data,
  COUNTIF(data_status = 0) AS days_missing,
  ROUND(COUNTIF(data_status = 2) / COUNT(*) * 100, 1) AS collection_rate_percent
FROM monthly_status
GROUP BY month
ORDER BY month;

