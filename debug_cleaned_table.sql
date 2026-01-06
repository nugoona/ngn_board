-- ============================================
-- 정리된 테이블 디버깅 쿼리
-- ============================================

-- Step 1: 원본 테이블의 고유 조합 개수 확인
SELECT 
    COUNT(DISTINCT CONCAT(mall_id, '|', order_id, '|', refund_code)) AS unique_combinations
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table`;

-- Step 2: 정리된 테이블의 고유 조합 개수 확인
SELECT 
    COUNT(DISTINCT CONCAT(mall_id, '|', order_id, '|', refund_code)) AS unique_combinations
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table_cleaned`;

-- Step 3: 원본 테이블 샘플 확인
SELECT 
    mall_id,
    order_id,
    refund_code,
    refund_date,
    total_refund_amount,
    COUNT(*) OVER (PARTITION BY mall_id, order_id, refund_code) AS duplicate_count
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table`
WHERE DATE(refund_date) >= '2025-12-20'
ORDER BY mall_id, order_id, refund_code, refund_date DESC
LIMIT 100;

-- Step 4: 정리된 테이블 샘플 확인
SELECT 
    mall_id,
    order_id,
    refund_code,
    refund_date,
    total_refund_amount
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table_cleaned`
WHERE DATE(refund_date) >= '2025-12-20'
ORDER BY mall_id, order_id, refund_code
LIMIT 100;

-- Step 5: 원본 테이블의 NULL 값 확인
SELECT 
    COUNT(*) AS total_records,
    COUNT(mall_id) AS mall_id_not_null,
    COUNT(order_id) AS order_id_not_null,
    COUNT(refund_code) AS refund_code_not_null
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table`;

-- Step 6: refund_code가 NULL인 레코드 수 확인
SELECT 
    COUNT(*) AS null_refund_code_count
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table`
WHERE refund_code IS NULL;

-- Step 7: refund_code가 NULL인 경우의 처리 확인
SELECT 
    mall_id,
    order_id,
    refund_code,
    COUNT(*) AS record_count
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table`
WHERE refund_code IS NULL
GROUP BY mall_id, order_id, refund_code
LIMIT 100;















