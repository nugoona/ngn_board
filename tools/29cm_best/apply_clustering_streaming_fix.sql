-- ============================================
-- 29CM Best 테이블 클러스터링 적용 (스트리밍 버퍼 문제 해결)
-- ============================================
-- 문제: 스트리밍 버퍼가 있어서 RENAME이 불가능
-- 해결: 기존 테이블 삭제 후 새 테이블을 원래 이름으로 변경
-- ============================================

-- Step 1: 클러스터링된 새 테이블 생성 (이미 완료되었다면 생략)
-- CREATE OR REPLACE TABLE `winged-precept-443218-v8.ngn_dataset.platform_29cm_best_new`
-- CLUSTER BY run_id, period_type
-- AS
-- SELECT * FROM `winged-precept-443218-v8.ngn_dataset.platform_29cm_best`;

-- Step 2: 데이터 확인 (행 수 및 최신 데이터 확인)
-- SELECT 
--   (SELECT COUNT(*) FROM `winged-precept-443218-v8.ngn_dataset.platform_29cm_best`) AS original_count,
--   (SELECT COUNT(*) FROM `winged-precept-443218-v8.ngn_dataset.platform_29cm_best_new`) AS new_count,
--   (SELECT MAX(collected_at) FROM `winged-precept-443218-v8.ngn_dataset.platform_29cm_best`) AS original_max_date,
--   (SELECT MAX(collected_at) FROM `winged-precept-443218-v8.ngn_dataset.platform_29cm_best_new`) AS new_max_date;

-- Step 3: 기존 테이블 삭제 (주의: 데이터 백업 확인 후 실행)
-- ⚠️ 스트리밍 버퍼가 있으면 삭제가 실패할 수 있음 (몇 시간 대기 필요)
-- DROP TABLE `winged-precept-443218-v8.ngn_dataset.platform_29cm_best`;

-- Step 4: 새 테이블을 원래 이름으로 변경
ALTER TABLE `winged-precept-443218-v8.ngn_dataset.platform_29cm_best_new`
RENAME TO platform_29cm_best;

-- Step 5: 클러스터링 확인
SELECT 
  table_name,
  clustering_ordinal_position,
  column_name
FROM `winged-precept-443218-v8.ngn_dataset.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = 'platform_29cm_best'
  AND clustering_ordinal_position IS NOT NULL
ORDER BY clustering_ordinal_position;

-- ============================================
-- 스트리밍 버퍼 대기 방법 (DROP이 실패하는 경우)
-- ============================================
-- 스트리밍 버퍼는 마지막 스트리밍 insert 후 약 30분~2시간 후에 비워집니다.
-- 
-- 버퍼 상태 확인:
-- SELECT 
--   creation_time,
--   last_modified_time,
--   num_bytes,
--   num_rows
-- FROM `winged-precept-443218-v8.ngn_dataset.__TABLES__`
-- WHERE table_id = 'platform_29cm_best';
--
-- 몇 시간 후에 다시 Step 3 (DROP)과 Step 4 (RENAME)를 시도하세요.

