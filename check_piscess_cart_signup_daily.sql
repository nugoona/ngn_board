-- 파이시스(piscess) 장바구니/회원가입 데이터 일별 조회
-- 사용법: BigQuery에서 실행

SELECT
  DATE(date) AS date,
  company_name,
  cart_users,
  signup_count,
  updated_at
FROM `winged-precept-443218-v8.ngn_dataset.performance_summary_ngn`
WHERE LOWER(company_name) = 'piscess'
  AND DATE(date) >= DATE('2024-12-01')
  AND DATE(date) <= DATE('2025-12-25')
ORDER BY date;

