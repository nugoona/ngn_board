-- ============================================
-- 올바른 중복 제거 쿼리 (refund_code NULL 처리 포함)
-- ============================================
-- refund_code가 NULL인 경우도 고려하여 수정

-- Step 1: refund_code가 NULL인 경우도 포함하여 중복 제거
CREATE OR REPLACE TABLE `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table_cleaned_v2` AS
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
            PARTITION BY 
                mall_id, 
                order_id, 
                COALESCE(refund_code, CAST(refund_date AS STRING), CAST(order_item_code AS STRING))
            ORDER BY refund_date DESC, order_item_code
        ) AS rn
    FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table`
)
WHERE rn = 1;

-- Step 2: 또는 refund_code가 NULL인 경우 order_item_code로 대체
-- CREATE OR REPLACE TABLE `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table_cleaned_v2` AS
-- SELECT 
--     mall_id,
--     order_id,
--     order_item_code,
--     order_date,
--     refund_date,
--     actual_refund_amount,
--     quantity,
--     used_points,
--     used_credits,
--     total_refund_amount,
--     refund_code
-- FROM (
--     SELECT 
--         *,
--         ROW_NUMBER() OVER (
--             PARTITION BY 
--                 mall_id, 
--                 order_id, 
--                 COALESCE(refund_code, order_item_code)
--             ORDER BY refund_date DESC
--         ) AS rn
--     FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table`
-- )
-- WHERE rn = 1;

-- Step 3: 레코드 수 비교
SELECT 
    '원본 테이블' AS table_name,
    COUNT(*) AS total_records
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table`
UNION ALL
SELECT 
    '정리된 테이블 v2' AS table_name,
    COUNT(*) AS total_records
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table_cleaned_v2`;












