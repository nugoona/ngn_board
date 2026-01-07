-- performance_summary_ngn 테이블 중복 데이터 확인
-- 사용법: BigQuery에서 실행

-- 1. 날짜별, 업체별, ad_media별 중복 확인
SELECT
  DATE(date) AS date,
  company_name,
  ad_media,
  COUNT(*) AS duplicate_count
FROM `winged-precept-443218-v8.ngn_dataset.performance_summary_ngn`
WHERE DATE(date) >= DATE('2024-12-01')
  AND DATE(date) <= DATE('2025-12-25')
GROUP BY DATE(date), company_name, ad_media
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC, DATE(date) DESC;
















