-- ============================================
-- 1단계: 중복 데이터 확인 (2025-12-23 piscess)
-- ============================================
-- 먼저 이 쿼리로 중복이 얼마나 있는지 확인하세요

SELECT 
    r.order_id,
    r.mall_id,
    DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) AS refund_date,
    r.refund_code,
    COUNT(*) AS duplicate_count,
    MAX(r.total_refund_amount) AS single_refund_amount,
    COUNT(*) * MAX(r.total_refund_amount) AS duplicated_total_amount
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
JOIN `winged-precept-443218-v8.ngn_dataset.company_info` c
    ON r.mall_id = c.mall_id
WHERE DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) = '2025-12-23'
  AND LOWER(c.company_name) = 'piscess'
GROUP BY r.order_id, r.mall_id, refund_date, r.refund_code
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC;

-- ============================================
-- 2단계: 중복 데이터 제거 (수정된 버전)
-- ============================================
-- ⚠️ 주의: 이 쿼리는 실제로 데이터를 삭제합니다!

-- Step 2-1: 먼저 확인 (실제 삭제는 하지 않음)
-- 이 쿼리로 삭제될 레코드 수를 확인하세요

SELECT 
    COUNT(*) AS will_be_deleted_count
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

-- Step 2-2: 실제 삭제 실행 (2-1 확인 후 실행)
-- NOT EXISTS를 사용하여 중복이 아닌 것만 남기는 방식

DELETE FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table`
WHERE NOT EXISTS (
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
    WHERE `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table`.mall_id = r2.mall_id
      AND `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table`.order_id = r2.order_id
      AND `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table`.refund_code = r2.refund_code
      AND `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table`.refund_date = r2.refund_date
      AND r2.rn = 1
);

-- ============================================
-- 3단계: daily_cafe24_sales 오류 데이터 삭제
-- ============================================
-- Step 3-1: 삭제할 데이터 확인 (실행 필수)

SELECT 
    payment_date,
    company_name,
    total_payment,
    total_refund_amount,
    net_sales,
    updated_at
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE DATE(payment_date) = '2025-12-23'
  AND LOWER(company_name) = 'piscess';

-- Step 3-2: 실제 삭제 실행 (3-1 확인 후 실행)

DELETE FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE DATE(payment_date) = '2025-12-23'
  AND LOWER(company_name) = 'piscess';

-- ============================================
-- 4단계: 정리 후 확인 및 재수집
-- ============================================

-- 4-1: 환불 테이블 중복 확인 (결과가 없어야 함)
SELECT 
    r.order_id,
    r.mall_id,
    DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) AS refund_date,
    r.refund_code,
    COUNT(*) AS record_count
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
JOIN `winged-precept-443218-v8.ngn_dataset.company_info` c
    ON r.mall_id = c.mall_id
WHERE DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) = '2025-12-23'
  AND LOWER(c.company_name) = 'piscess'
GROUP BY r.order_id, r.mall_id, refund_date, r.refund_code
HAVING COUNT(*) > 1;

-- 4-2: 환불 금액 합계 확인 (77,450원이 나와야 함)
SELECT 
    SUM(refund_agg.total_refund_amount) AS total_refund_amount,
    COUNT(DISTINCT refund_agg.order_id) AS refund_order_count
FROM (
    SELECT
        r.order_id,
        SUM(r.total_refund_amount) AS total_refund_amount
    FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
    JOIN `winged-precept-443218-v8.ngn_dataset.company_info` c
        ON r.mall_id = c.mall_id
    WHERE DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) = '2025-12-23'
      AND LOWER(c.company_name) = 'piscess'
    GROUP BY r.order_id
) refund_agg;

-- 4-3: daily_cafe24_sales 테이블 확인 (데이터가 없어야 함)
SELECT 
    payment_date,
    company_name,
    total_refund_amount
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE DATE(payment_date) = '2025-12-23'
  AND LOWER(company_name) = 'piscess';














