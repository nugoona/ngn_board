-- ============================================
-- 29CM Best 테이블 클러스터링 적용 (최종 방법)
-- ============================================
-- 문제: 
-- 1. 스트리밍 버퍼가 있어서 RENAME/DROP 불가
-- 2. CREATE OR REPLACE로 클러스터링 스펙 변경 불가
-- 
-- 해결 방법:
-- 1. 스트리밍 버퍼가 비워질 때까지 대기 (마지막 insert 후 30분~2시간)
-- 2. 그 후 DROP + RENAME 실행
-- ============================================

-- ⏰ Step 1: 스트리밍 버퍼 상태 확인
-- 마지막 스트리밍 insert 후 30분~2시간이 지났는지 확인
SELECT 
  creation_time,
  last_modified_time,
  TIMESTAMP_MILLIS(last_modified_time) AS last_modified_timestamp,
  TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), TIMESTAMP_MILLIS(last_modified_time), MINUTE) AS minutes_since_last_modify,
  size_bytes,
  row_count
FROM `winged-precept-443218-v8.ngn_dataset.__TABLES__`
WHERE table_id = 'platform_29cm_best';

-- ⏰ Step 2: 스트리밍 버퍼가 비워진 후 (30분~2시간 경과 후) 다음 쿼리 실행
-- ⚠️ 주의: 이 쿼리들은 스트리밍 버퍼가 비워진 후에만 실행 가능

-- 2-1. 기존 테이블 삭제
DROP TABLE `winged-precept-443218-v8.ngn_dataset.platform_29cm_best`;

-- 2-2. 새 테이블을 원래 이름으로 변경
ALTER TABLE `winged-precept-443218-v8.ngn_dataset.platform_29cm_best_new`
RENAME TO platform_29cm_best;

-- Step 3: 클러스터링 확인
SELECT 
  table_name,
  clustering_ordinal_position,
  column_name
FROM `winged-precept-443218-v8.ngn_dataset.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = 'platform_29cm_best'
  AND clustering_ordinal_position IS NOT NULL
ORDER BY clustering_ordinal_position;

-- ============================================
-- 임시 해결책 (스트리밍 버퍼 대기 중일 때)
-- ============================================
-- 만약 지금 당장 클러스터링 효과를 받고 싶다면:
-- 1. 새 테이블 (platform_29cm_best_new)에 데이터 적재를 계속 진행
-- 2. 애플리케이션 코드에서 테이블 이름을 'platform_29cm_best_new'로 임시 변경
-- 3. 스트리밍 버퍼가 비워진 후 Step 2 실행
--
-- 또는:
-- 1. 새 테이블을 계속 사용
-- 2. 나중에 기존 테이블 삭제 후 새 테이블 이름 변경
-- ============================================

