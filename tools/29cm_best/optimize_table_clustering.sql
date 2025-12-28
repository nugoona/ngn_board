-- 29CM Best 테이블 클러스터링 최적화 스크립트
-- 실행 방법: BigQuery 콘솔에서 이 SQL을 실행하거나, gcloud bq query로 실행

-- ⚠️ 주의: 이 작업은 테이블을 재생성하므로 기존 데이터를 백업 후 실행 권장
-- 실행 시간: 테이블 크기에 따라 몇 분~몇십 분 소요될 수 있습니다

-- 방법 1: 기존 테이블을 클러스터링 테이블로 변경 (권장)
-- 테이블을 새로 생성하면서 클러스터링 적용
CREATE OR REPLACE TABLE `winged-precept-443218-v8.ngn_dataset.platform_29cm_best_clustered`
CLUSTER BY run_id, period_type
AS
SELECT * FROM `winged-precept-443218-v8.ngn_dataset.platform_29cm_best`;

-- 테이블 이름 변경 (백업 후)
-- ALTER TABLE `winged-precept-443218-v8.ngn_dataset.platform_29cm_best` 
-- RENAME TO `winged-precept-443218-v8.ngn_dataset.platform_29cm_best_backup_YYYYMMDD`;

-- ALTER TABLE `winged-precept-443218-v8.ngn_dataset.platform_29cm_best_clustered`
-- RENAME TO `winged-precept-443218-v8.ngn_dataset.platform_29cm_best`;

-- 방법 2: 기존 테이블에 클러스터링 적용 (데이터 유지)
-- 주의: 이 방법은 기존 테이블을 삭제하고 재생성하므로 데이터 백업 필수
/*
CREATE OR REPLACE TABLE `winged-precept-443218-v8.ngn_dataset.platform_29cm_best`
CLUSTER BY run_id, period_type
AS
SELECT * FROM `winged-precept-443218-v8.ngn_dataset.platform_29cm_best`
*/

-- 클러스터링 적용 확인
SELECT 
  table_name,
  clustering_ordinal_position,
  column_name
FROM `winged-precept-443218-v8.ngn_dataset.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = 'platform_29cm_best'
  AND clustering_ordinal_position IS NOT NULL
ORDER BY clustering_ordinal_position;

