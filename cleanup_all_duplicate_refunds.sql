-- ============================================
-- 전체 테이블 중복 데이터 제거
-- ============================================
-- 기준: mall_id, order_id, refund_code 조합으로 그룹화
-- 각 그룹에서 refund_date가 가장 최신인 것만 유지

-- ============================================
-- Step 1: 전체 중복 데이터 확인
-- ============================================
-- 이 쿼리로 전체 테이블에서 중복이 얼마나 있는지 확인하세요

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

-- 전체 중복 레코드 수 확인
SELECT 
    COUNT(*) AS total_duplicate_records
FROM (
    SELECT 
        mall_id,
        order_id,
        refund_code,
        COUNT(*) AS cnt
    FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table`
    GROUP BY mall_id, order_id, refund_code
    HAVING COUNT(*) > 1
);

-- ============================================
-- Step 2: 삭제될 레코드 수 확인
-- ============================================
-- 실제로 삭제될 레코드 수를 확인하세요

SELECT 
    COUNT(*) AS will_be_deleted_count,
    COUNT(DISTINCT CONCAT(mall_id, '|', order_id, '|', refund_code)) AS duplicate_groups
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r1
WHERE EXISTS (
    SELECT 1
    FROM (
        SELECT 
            mall_id,
            order_id,
            refund_code,
            refund_date,
            ROW_NUMBER() OVER (
                PARTITION BY mall_id, order_id, refund_code
                ORDER BY refund_date DESC
            ) AS rn
        FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table`
    ) r2
    WHERE r1.mall_id = r2.mall_id
      AND r1.order_id = r2.order_id
      AND r1.refund_code = r2.refund_code
      AND r1.refund_date = r2.refund_date
      AND r2.rn > 1
);

-- ============================================
-- Step 3: 중복 제거된 임시 테이블 생성
-- ============================================
-- ⚠️ BigQuery에서는 DELETE에서 같은 테이블 참조가 제한되므로
-- 임시 테이블을 만들어서 교체하는 방식을 사용합니다

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
-- Step 4: 임시 테이블 확인
-- ============================================

-- 레코드 수 비교
SELECT 
    '원본 테이블' AS table_name,
    COUNT(*) AS total_records
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table`
UNION ALL
SELECT 
    '정리된 테이블' AS table_name,
    COUNT(*) AS total_records
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table_cleaned`;

-- 중복 확인 (결과가 없어야 함)
SELECT 
    mall_id,
    order_id,
    refund_code,
    COUNT(*) AS record_count
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table_cleaned`
GROUP BY mall_id, order_id, refund_code
HAVING COUNT(*) > 1
LIMIT 100;

-- ============================================
-- Step 5: 원본 테이블 백업 (선택사항)
-- ============================================

-- CREATE OR REPLACE TABLE `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table_backup` AS
-- SELECT * FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table`;

-- ============================================
-- Step 6: 원본 테이블을 정리된 테이블로 교체
-- ============================================
-- ⚠️ 주의: 이 쿼리는 원본 테이블을 완전히 교체합니다!
-- Step 4로 확인한 후에만 실행하세요!

-- CREATE OR REPLACE TABLE `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` AS
-- SELECT * FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table_cleaned`;

-- ============================================
-- Step 4: 삭제 후 확인
-- ============================================

-- 4-1: 중복이 완전히 제거되었는지 확인 (결과가 없어야 함)
SELECT 
    mall_id,
    order_id,
    refund_code,
    COUNT(*) AS record_count
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table`
GROUP BY mall_id, order_id, refund_code
HAVING COUNT(*) > 1
LIMIT 100;

-- 4-2: 전체 레코드 수 확인
SELECT 
    COUNT(*) AS total_records
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table`;

-- 4-3: 최근 날짜별 레코드 수 확인 (2025-12-23 예시)
SELECT 
    DATE(DATETIME(TIMESTAMP(refund_date), 'Asia/Seoul')) AS refund_date,
    COUNT(*) AS record_count,
    COUNT(DISTINCT CONCAT(mall_id, '|', order_id, '|', refund_code)) AS unique_refunds
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table`
WHERE DATE(DATETIME(TIMESTAMP(refund_date), 'Asia/Seoul')) >= '2025-12-20'
GROUP BY refund_date
ORDER BY refund_date DESC;

