-- ✅ piscess 2025-12-23 환불 문제 진단 쿼리

-- ============================================
-- 1. daily_cafe24_sales 테이블에 실제 저장된 값 확인
-- ============================================
SELECT 
    'daily_cafe24_sales 테이블 값' AS check_type,
    payment_date,
    company_name,
    total_payment,
    total_refund_amount,
    net_sales,
    total_orders,
    updated_at
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE DATE(payment_date) = '2025-12-23'
  AND LOWER(company_name) = 'piscess';

-- ============================================
-- 2. cafe24_refunds_table 원본 데이터 확인 (중복 체크)
-- ============================================
SELECT 
    '환불 테이블 원본 데이터' AS check_type,
    r.order_id,
    r.mall_id,
    DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) AS refund_date,
    r.total_refund_amount,
    COUNT(*) OVER (PARTITION BY r.order_id, r.mall_id) AS duplicate_count,
    c.company_name
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
JOIN `winged-precept-443218-v8.ngn_dataset.company_info` c
    ON r.mall_id = c.mall_id
WHERE DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) = '2025-12-23'
  AND LOWER(c.company_name) = 'piscess'
ORDER BY r.order_id;

-- ============================================
-- 3. 환불 테이블 order_id별 집계 (수정된 코드 로직 확인)
-- ============================================
SELECT 
    'order_id별 환불 집계' AS check_type,
    refund_agg.order_id,
    refund_agg.mall_id,
    refund_agg.company_name,
    refund_agg.refund_date,
    refund_agg.total_refund_amount AS refund_per_order
FROM (
    SELECT
        r.mall_id,
        c.company_name,
        DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) AS refund_date,
        r.order_id,
        SUM(r.total_refund_amount) AS total_refund_amount
    FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
    JOIN `winged-precept-443218-v8.ngn_dataset.company_info` c
        ON r.mall_id = c.mall_id
    WHERE DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) = '2025-12-23'
      AND LOWER(c.company_name) = 'piscess'
    GROUP BY r.mall_id, c.company_name, refund_date, r.order_id
) refund_agg
ORDER BY refund_agg.order_id;

-- ============================================
-- 4. 최종 환불 요약 (refund_summary 결과)
-- ============================================
SELECT 
    '최종 환불 요약' AS check_type,
    refund_agg.mall_id,
    refund_agg.company_name,
    refund_agg.refund_date,
    SUM(refund_agg.total_refund_amount) AS total_refund_amount,
    COUNT(DISTINCT refund_agg.order_id) AS refund_order_count
FROM (
    SELECT
        r.mall_id,
        c.company_name,
        DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) AS refund_date,
        r.order_id,
        SUM(r.total_refund_amount) AS total_refund_amount
    FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
    JOIN `winged-precept-443218-v8.ngn_dataset.company_info` c
        ON r.mall_id = c.mall_id
    WHERE DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) = '2025-12-23'
      AND LOWER(c.company_name) = 'piscess'
    GROUP BY r.mall_id, c.company_name, refund_date, r.order_id
) refund_agg
GROUP BY refund_agg.mall_id, refund_agg.company_name, refund_agg.refund_date;

-- ============================================
-- 5. cafe24_orders 테이블 중복 확인
-- ============================================
SELECT 
    '주문 테이블 중복 확인' AS check_type,
    o.order_id,
    o.mall_id,
    DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) AS payment_date,
    COUNT(*) AS order_count,
    MAX(o.payment_amount) AS payment_amount,
    c.company_name
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders` o
JOIN `winged-precept-443218-v8.ngn_dataset.company_info` c
    ON o.mall_id = c.mall_id
WHERE DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) = '2025-12-23'
  AND LOWER(c.company_name) = 'piscess'
GROUP BY o.order_id, o.mall_id, payment_date, c.company_name
HAVING COUNT(*) > 1
ORDER BY order_count DESC;

-- ============================================
-- 6. 환불과 주문 조인 시 중복 발생 여부 확인
-- ============================================
WITH refund_summary AS (
    SELECT
        refund_agg.mall_id,
        refund_agg.company_name,
        refund_agg.refund_date,
        SUM(refund_agg.total_refund_amount) AS total_refund_amount
    FROM (
        SELECT
            r.mall_id,
            c.company_name,
            DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) AS refund_date,
            r.order_id,
            SUM(r.total_refund_amount) AS total_refund_amount
        FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
        JOIN `winged-precept-443218-v8.ngn_dataset.company_info` c
            ON r.mall_id = c.mall_id
        WHERE DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) = '2025-12-23'
          AND LOWER(c.company_name) = 'piscess'
        GROUP BY r.mall_id, c.company_name, refund_date, r.order_id
    ) refund_agg
    GROUP BY refund_agg.mall_id, refund_agg.company_name, refund_agg.refund_date
),
order_summary AS (
    SELECT
        o.mall_id,
        o.order_id,
        DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) AS payment_date
    FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders` o
    JOIN `winged-precept-443218-v8.ngn_dataset.company_info` c
        ON o.mall_id = c.mall_id
    WHERE DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) = '2025-12-23'
      AND LOWER(c.company_name) = 'piscess'
    GROUP BY o.mall_id, o.order_id, payment_date
)
SELECT 
    '조인 결과 확인' AS check_type,
    os.payment_date,
    os.mall_id,
    COUNT(DISTINCT os.order_id) AS order_count,
    r.total_refund_amount,
    r.total_refund_amount * COUNT(DISTINCT os.order_id) AS potential_duplicate_refund
FROM order_summary os
LEFT JOIN refund_summary r
    ON os.mall_id = r.mall_id
    AND os.payment_date = r.refund_date
GROUP BY os.payment_date, os.mall_id, r.total_refund_amount;
















