-- ============================================
-- 전체 테이블 중복 데이터 제거 (수정된 버전)
-- ============================================
-- BigQuery에서는 DELETE에서 같은 테이블 참조가 제한되므로
-- 임시 테이블 방식을 사용합니다.

-- ============================================
-- Step 1: 전체 중복 데이터 확인
-- ============================================

SELECT 
    mall_id,
    order_id,
    refund_code,
    COUNT(*) AS duplicate_count,
    MIN(refund_date) AS earliest_date,
    MAX(refund_date) AS latest_date
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table`
GROUP BY mall_id, order_id, refund_code
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC
LIMIT 100;

-- ============================================
-- Step 2: 중복 제거된 데이터로 임시 테이블 생성
-- ============================================
-- ⚠️ 이 쿼리는 임시 테이블을 생성합니다 (데이터 삭제 안함)

CREATE OR REPLACE TABLE `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table_cleaned` AS
SELECT 
    mall_id,
    order_id,
    order_item_code,
    order_date,
    refund_date,
    actual_refund_amount,
    quantity,
    used_points,
    used_credits,
    total_refund_amount,
    refund_code
FROM (
    SELECT 
        *,
        ROW_NUMBER() OVER (
            PARTITION BY mall_id, order_id, refund_code
            ORDER BY refund_date DESC
        ) AS rn
    FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table`
)
WHERE rn = 1;

-- ============================================
-- Step 3: 임시 테이블 확인
-- ============================================

-- 3-1: 레코드 수 비교
SELECT 
    '원본 테이블' AS table_name,
    COUNT(*) AS total_records
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table`
UNION ALL
SELECT 
    '정리된 테이블' AS table_name,
    COUNT(*) AS total_records
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table_cleaned`;

-- 3-2: 중복 확인 (결과가 없어야 함)
SELECT 
    mall_id,
    order_id,
    refund_code,
    COUNT(*) AS record_count
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table_cleaned`
GROUP BY mall_id, order_id, refund_code
HAVING COUNT(*) > 1
LIMIT 100;

-- 3-3: 샘플 데이터 확인
SELECT *
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table_cleaned`
WHERE DATE(refund_date) = '2025-12-23'
  AND mall_id = 'piscess1'
LIMIT 10;

-- ============================================
-- Step 4: 원본 테이블 백업 (선택사항)
-- ============================================

-- CREATE OR REPLACE TABLE `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table_backup_before_cleanup` AS
-- SELECT * FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table`;

-- ============================================
-- Step 5: 원본 테이블을 정리된 테이블로 교체
-- ============================================
-- ⚠️ 주의: 이 쿼리는 원본 테이블을 완전히 교체합니다!
-- Step 3으로 확인한 후에만 실행하세요!

-- CREATE OR REPLACE TABLE `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` AS
-- SELECT * FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table_cleaned`;

-- ============================================
-- Step 6: 임시 테이블 삭제
-- ============================================
-- Step 5 실행 후, 확인이 끝나면 임시 테이블을 삭제하세요

-- DROP TABLE IF EXISTS `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table_cleaned`;

-- ============================================
-- Step 7: 최종 확인
-- ============================================

-- 7-1: 중복 확인 (결과가 없어야 함)
-- SELECT 
--     mall_id,
--     order_id,
--     refund_code,
--     COUNT(*) AS record_count
-- FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table`
-- GROUP BY mall_id, order_id, refund_code
-- HAVING COUNT(*) > 1
-- LIMIT 100;

-- 7-2: 전체 레코드 수
-- SELECT 
--     COUNT(*) AS total_records
-- FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table`;













