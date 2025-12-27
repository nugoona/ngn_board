-- 2025년 8월 파이시스 데이터 존재 여부 확인
-- 사용법: BigQuery에서 실행

SELECT
  DATE(date) AS date,
  company_name,
  ad_media,
  site_revenue,
  total_visitors,
  cart_users,
  signup_count
FROM `winged-precept-443218-v8.ngn_dataset.performance_summary_ngn`
WHERE LOWER(company_name) = 'piscess'
  AND DATE(date) >= DATE('2025-08-01')
  AND DATE(date) <= DATE('2025-08-31')
ORDER BY DATE(date);

