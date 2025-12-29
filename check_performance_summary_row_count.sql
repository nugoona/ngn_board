-- performance_summary_ngn 테이블 총 행 수 확인
-- 사용법: BigQuery에서 실행

SELECT
  DATE_TRUNC(DATE(date), MONTH) AS month,
  COUNT(*) AS total_rows,
  COUNT(DISTINCT CONCAT(CAST(DATE(date) AS STRING), '-', company_name, '-', ad_media)) AS unique_keys,
  COUNT(*) - COUNT(DISTINCT CONCAT(CAST(DATE(date) AS STRING), '-', company_name, '-', ad_media)) AS duplicate_rows
FROM `winged-precept-443218-v8.ngn_dataset.performance_summary_ngn`
WHERE DATE(date) >= DATE('2024-12-01')
  AND DATE(date) <= DATE('2025-12-25')
GROUP BY month
ORDER BY month;



