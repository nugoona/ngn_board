-- performance_summary_ngn 테이블에 파이시스 데이터가 있는 날짜 확인
-- 사용법: BigQuery에서 실행

SELECT
  DATE(date) AS date,
  COUNT(*) AS row_count,
  STRING_AGG(DISTINCT company_name, ', ') AS companies
FROM `winged-precept-443218-v8.ngn_dataset.performance_summary_ngn`
WHERE DATE(date) >= DATE('2025-08-02')
  AND DATE(date) <= DATE('2025-08-09')
GROUP BY DATE(date)
ORDER BY DATE(date);

