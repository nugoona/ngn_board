-- ============================================
-- 29CM Best 테이블 클러스터링 적용 (수정됨)
-- ============================================
-- 주의: ALTER TABLE RENAME TO는 테이블 이름만 사용 (전체 경로 사용 불가)
-- ============================================

-- Step 1: 클러스터링된 새 테이블 생성
CREATE OR REPLACE TABLE `winged-precept-443218-v8.ngn_dataset.platform_29cm_best_new`
CLUSTER BY run_id, period_type
AS
SELECT * FROM `winged-precept-443218-v8.ngn_dataset.platform_29cm_best`;

-- Step 2: 데이터 확인 (행 수 비교)
SELECT 
  (SELECT COUNT(*) FROM `winged-precept-443218-v8.ngn_dataset.platform_29cm_best`) AS original_count,
  (SELECT COUNT(*) FROM `winged-precept-443218-v8.ngn_dataset.platform_29cm_best_new`) AS new_count;

-- Step 3: 기존 테이블 백업 (이름 변경)
-- ⚠️ 주의: 테이블 이름만 사용 (데이터셋명 제외)
ALTER TABLE `winged-precept-443218-v8.ngn_dataset.platform_29cm_best`
RENAME TO platform_29cm_best_old;

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

