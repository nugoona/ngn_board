-- ============================================
-- GA4 트래픽 데이터 재수집을 위한 준비 작업
-- 2025-12-26 ~ 현재까지 데이터 삭제
-- ============================================

-- 1. ga4_traffic 테이블에서 해당 기간 데이터 삭제
DELETE FROM `winged-precept-443218-v8.ngn_dataset.ga4_traffic`
WHERE DATE(event_date) BETWEEN DATE("2025-12-26") AND CURRENT_DATE();

-- 2. ga4_traffic_ngn 테이블에서 해당 기간 데이터 삭제
DELETE FROM `winged-precept-443218-v8.ngn_dataset.ga4_traffic_ngn`
WHERE DATE(event_date) BETWEEN DATE("2025-12-26") AND CURRENT_DATE();

-- 3. 삭제된 행 수 확인
SELECT 
    'ga4_traffic' AS table_name,
    COUNT(*) AS remaining_rows,
    MIN(event_date) AS min_date,
    MAX(event_date) AS max_date
FROM `winged-precept-443218-v8.ngn_dataset.ga4_traffic`
WHERE DATE(event_date) BETWEEN DATE("2025-12-26") AND CURRENT_DATE()

UNION ALL

SELECT 
    'ga4_traffic_ngn' AS table_name,
    COUNT(*) AS remaining_rows,
    MIN(event_date) AS min_date,
    MAX(event_date) AS max_date
FROM `winged-precept-443218-v8.ngn_dataset.ga4_traffic_ngn`
WHERE DATE(event_date) BETWEEN DATE("2025-12-26") AND CURRENT_DATE();




