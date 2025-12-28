-- ============================================
-- 29CM Best 테이블 클러스터링 적용
-- ============================================
-- 실행 전 주의사항:
-- 1. 이 쿼리는 기존 테이블을 백업하고 클러스터링된 새 테이블을 생성합니다
-- 2. 실행 시간: 테이블 크기에 따라 몇 분~몇십 분 소요될 수 있습니다
-- 3. 실행 중 테이블 사용이 제한될 수 있으므로 점검 시간에 실행 권장
-- ============================================

-- Step 1: 기존 테이블 백업 (선택사항 - 안전을 위해)
-- CREATE TABLE `winged-precept-443218-v8.ngn_dataset.platform_29cm_best_backup_20250124`
-- AS SELECT * FROM `winged-precept-443218-v8.ngn_dataset.platform_29cm_best`;

-- Step 2: 클러스터링된 새 테이블 생성
CREATE OR REPLACE TABLE `winged-precept-443218-v8.ngn_dataset.platform_29cm_best_new`
CLUSTER BY run_id, period_type
AS
SELECT * FROM `winged-precept-443218-v8.ngn_dataset.platform_29cm_best`;

-- Step 3: 데이터 일치 확인 (행 수 비교)
-- SELECT 
--   (SELECT COUNT(*) FROM `winged-precept-443218-v8.ngn_dataset.platform_29cm_best`) AS original_count,
--   (SELECT COUNT(*) FROM `winged-precept-443218-v8.ngn_dataset.platform_29cm_best_new`) AS new_count;

-- Step 4: 기존 테이블 백업으로 이름 변경
-- ALTER TABLE `winged-precept-443218-v8.ngn_dataset.platform_29cm_best`
-- RENAME TO `winged-precept-443218-v8.ngn_dataset.platform_29cm_best_old`;

-- Step 5: 새 테이블을 원래 이름으로 변경
-- ALTER TABLE `winged-precept-443218-v8.ngn_dataset.platform_29cm_best_new`
-- RENAME TO `winged-precept-443218-v8.ngn_dataset.platform_29cm_best`;

-- Step 6: 클러스터링 확인
-- SELECT 
--   table_name,
--   clustering_ordinal_position,
--   column_name
-- FROM `winged-precept-443218-v8.ngn_dataset.INFORMATION_SCHEMA.COLUMNS`
-- WHERE table_name = 'platform_29cm_best'
--   AND clustering_ordinal_position IS NOT NULL
-- ORDER BY clustering_ordinal_position;

-- ============================================
-- 한 번에 실행하는 버전 (더 간단하지만 위험할 수 있음)
-- ============================================
-- CREATE OR REPLACE TABLE `winged-precept-443218-v8.ngn_dataset.platform_29cm_best`
-- CLUSTER BY run_id, period_type
-- AS
-- SELECT * FROM `winged-precept-443218-v8.ngn_dataset.platform_29cm_best`;

