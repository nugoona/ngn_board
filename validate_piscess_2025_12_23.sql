-- ✅ piscess 업체 2025-12-23 날짜 검증 쿼리

-- ============================================
-- 1단계: 환불 데이터 확인 (원본 + 집계)
-- ============================================

-- 1-1. 원본 환불 데이터 (cafe24_refunds_table)
SELECT 
    '원본 환불 데이터' AS step,
    r.order_id,
    r.mall_id,
    DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) AS refund_date,
    r.total_refund_amount,
    COUNT(*) OVER (PARTITION BY r.order_id, r.mall_id) AS duplicate_count_per_order
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
JOIN `winged-precept-443218-v8.ngn_dataset.company_info` c
    ON r.mall_id = c.mall_id
WHERE DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) = '2025-12-23'
  AND LOWER(c.company_name) = 'piscess'
ORDER BY r.order_id;

-- 1-2. order_id별 집계된 환불 금액 (refund_summary 내부 로직)
SELECT 
    'order_id별 환불 집계' AS step,
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

-- 1-3. 최종 환불 요약 (refund_summary 결과)
SELECT 
    '최종 환불 요약' AS step,
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
-- 2단계: 주문 데이터 확인 (원본 + 집계)
-- ============================================

-- 2-1. 원본 주문 데이터 (cafe24_orders) - 중복 확인
SELECT 
    '원본 주문 데이터' AS step,
    o.order_id,
    o.mall_id,
    DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) AS payment_date,
    o.payment_amount,
    COUNT(*) OVER (PARTITION BY o.order_id, o.mall_id) AS duplicate_count_per_order
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders` o
JOIN `winged-precept-443218-v8.ngn_dataset.company_info` c
    ON o.mall_id = c.mall_id
WHERE DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) = '2025-12-23'
  AND LOWER(c.company_name) = 'piscess'
ORDER BY o.order_id;

-- 2-2. order_id별 집계된 주문 데이터 (order_summary 결과)
SELECT 
    'order_id별 주문 집계' AS step,
    os.order_id,
    os.mall_id,
    os.payment_date,
    os.payment_amount,
    os.item_product_price,
    os.total_payment_calc
FROM (
    SELECT
        o.mall_id,
        o.order_id,
        DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) AS payment_date,
        MAX(
            CASE 
                WHEN o.order_price_amount = 0 THEN o.payment_amount + o.naverpay_point
                ELSE o.order_price_amount
            END
        ) AS item_product_price,
        MAX(o.payment_amount) AS payment_amount,
        MAX(o.points_spent_amount) AS points_spent_amount,
        MAX(o.naverpay_point) AS naverpay_point,
        MAX(o.payment_amount) + MAX(o.points_spent_amount) + MAX(o.naverpay_point) AS total_payment_calc
    FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders` o
    JOIN `winged-precept-443218-v8.ngn_dataset.company_info` c
        ON o.mall_id = c.mall_id
    WHERE DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) = '2025-12-23'
      AND LOWER(c.company_name) = 'piscess'
    GROUP BY o.mall_id, o.order_id, payment_date
) os
ORDER BY os.order_id;

-- 2-3. 주문 집계 (order_agg 결과)
SELECT 
    '주문 집계 (환불 제외)' AS step,
    os.payment_date,
    os.mall_id,
    c.company_name,
    COUNT(DISTINCT os.order_id) AS total_orders,
    SUM(os.item_product_price) AS item_product_price,
    SUM(os.total_payment_calc) AS total_payment
FROM (
    SELECT
        o.mall_id,
        o.order_id,
        DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) AS payment_date,
        MAX(
            CASE 
                WHEN o.order_price_amount = 0 THEN o.payment_amount + o.naverpay_point
                ELSE o.order_price_amount
            END
        ) AS item_product_price,
        MAX(o.payment_amount) + MAX(o.points_spent_amount) + MAX(o.naverpay_point) AS total_payment_calc
    FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders` o
    JOIN `winged-precept-443218-v8.ngn_dataset.company_info` c
        ON o.mall_id = c.mall_id
    WHERE DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) = '2025-12-23'
      AND LOWER(c.company_name) = 'piscess'
    GROUP BY o.mall_id, o.order_id, payment_date
) os
JOIN `winged-precept-443218-v8.ngn_dataset.company_info` c
    ON os.mall_id = c.mall_id
GROUP BY os.payment_date, os.mall_id, c.company_name;

-- ============================================
-- 3단계: 최종 결과 (수정된 코드 로직)
-- ============================================

WITH company_mall_ids AS (
    SELECT mall_id, company_name
    FROM `winged-precept-443218-v8.ngn_dataset.company_info`
    WHERE LOWER(company_name) = 'piscess'
),
refund_summary AS (
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
        JOIN company_mall_ids c
            ON r.mall_id = c.mall_id
        WHERE DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) = '2025-12-23'
        GROUP BY r.mall_id, c.company_name, refund_date, r.order_id
    ) refund_agg
    GROUP BY refund_agg.mall_id, refund_agg.company_name, refund_agg.refund_date
),
order_summary AS (
    SELECT
        o.mall_id,
        o.order_id,
        DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) AS payment_date,
        MAX(
            CASE 
                WHEN o.order_price_amount = 0 THEN o.payment_amount + o.naverpay_point
                ELSE o.order_price_amount
            END
        ) AS item_product_price,
        MAX(o.shipping_fee) AS shipping_fee,
        MAX(o.coupon_discount_price) AS coupon_discount_price,
        MAX(o.payment_amount) AS payment_amount,
        MAX(o.points_spent_amount) AS points_spent_amount,
        MAX(o.naverpay_point) AS naverpay_point,
        MAX(CASE WHEN LOWER(o.payment_method) LIKE '%선불금%' THEN 1 ELSE 0 END) AS is_prepayment,
        MAX(CASE WHEN o.first_order = TRUE THEN 1 ELSE 0 END) AS is_first_order,
        MAX(CASE WHEN o.canceled = TRUE THEN 1 ELSE 0 END) AS is_canceled,
        MAX(CASE WHEN o.naverpay_payment_information = 'N' THEN 1 ELSE 0 END) AS is_naverpay_payment_info
    FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders` o
    JOIN company_mall_ids c
        ON o.mall_id = c.mall_id
    WHERE DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) = '2025-12-23'
    GROUP BY o.mall_id, o.order_id, payment_date
),
order_agg AS (
    SELECT
        os.payment_date,
        os.mall_id,
        c.company_name,
        COUNT(DISTINCT os.order_id) AS total_orders,
        SUM(os.item_product_price) AS item_product_price,
        SUM(os.shipping_fee) AS total_shipping_fee,
        SUM(os.coupon_discount_price) AS total_coupon_discount,
        SUM(os.payment_amount) + SUM(os.points_spent_amount) + SUM(os.naverpay_point) AS total_payment,
        SUM(os.naverpay_point) AS total_naverpay_point,
        SUM(os.is_prepayment) AS total_prepayment,
        SUM(os.is_first_order) AS total_first_order,
        SUM(os.is_canceled) AS total_canceled,
        SUM(os.is_naverpay_payment_info) AS total_naverpay_payment_info
    FROM order_summary os
    JOIN `winged-precept-443218-v8.ngn_dataset.company_info` c
        ON os.mall_id = c.mall_id
    GROUP BY os.payment_date, os.mall_id, c.company_name
)
SELECT 
    '✅ 수정된 코드 최종 결과' AS step,
    oa.payment_date,
    oa.mall_id,
    oa.company_name,
    oa.total_orders,
    oa.item_product_price,
    oa.total_payment,
    COALESCE(r.total_refund_amount, 0) AS total_refund_amount,
    (oa.total_payment - COALESCE(r.total_refund_amount, 0)) AS net_sales
FROM order_agg oa
LEFT JOIN refund_summary r
    ON oa.mall_id = r.mall_id
    AND oa.payment_date = r.refund_date;

-- ============================================
-- 4단계: 기존 테이블과 비교
-- ============================================

SELECT 
    '❌ 기존 daily_cafe24_sales 테이블 값' AS step,
    payment_date,
    company_name,
    total_orders,
    item_product_price,
    total_payment,
    total_refund_amount,
    net_sales
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE DATE(payment_date) = '2025-12-23'
  AND LOWER(company_name) = 'piscess';

-- ============================================
-- 5단계: 비교 요약
-- ============================================

SELECT 
    '📊 비교 요약' AS step,
    '수정된 코드 결과' AS source_type,
    oa.total_orders,
    oa.total_payment,
    COALESCE(r.total_refund_amount, 0) AS total_refund_amount,
    (oa.total_payment - COALESCE(r.total_refund_amount, 0)) AS net_sales
FROM (
    SELECT
        os.payment_date,
        os.mall_id,
        c.company_name,
        COUNT(DISTINCT os.order_id) AS total_orders,
        SUM(os.payment_amount) + SUM(os.points_spent_amount) + SUM(os.naverpay_point) AS total_payment
    FROM (
        SELECT
            o.mall_id,
            o.order_id,
            DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) AS payment_date,
            MAX(o.payment_amount) AS payment_amount,
            MAX(o.points_spent_amount) AS points_spent_amount,
            MAX(o.naverpay_point) AS naverpay_point
        FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders` o
        JOIN `winged-precept-443218-v8.ngn_dataset.company_info` c
            ON o.mall_id = c.mall_id
        WHERE DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) = '2025-12-23'
          AND LOWER(c.company_name) = 'piscess'
        GROUP BY o.mall_id, o.order_id, payment_date
    ) os
    JOIN `winged-precept-443218-v8.ngn_dataset.company_info` c
        ON os.mall_id = c.mall_id
    GROUP BY os.payment_date, os.mall_id, c.company_name
) oa
LEFT JOIN (
    SELECT
        refund_agg.mall_id,
        refund_agg.refund_date,
        SUM(refund_agg.total_refund_amount) AS total_refund_amount
    FROM (
        SELECT
            r.mall_id,
            DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) AS refund_date,
            r.order_id,
            SUM(r.total_refund_amount) AS total_refund_amount
        FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
        JOIN `winged-precept-443218-v8.ngn_dataset.company_info` c
            ON r.mall_id = c.mall_id
        WHERE DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) = '2025-12-23'
          AND LOWER(c.company_name) = 'piscess'
        GROUP BY r.mall_id, refund_date, r.order_id
    ) refund_agg
    GROUP BY refund_agg.mall_id, refund_agg.refund_date
) r
    ON oa.mall_id = r.mall_id
    AND oa.payment_date = r.refund_date

UNION ALL

SELECT 
    '📊 비교 요약' AS step,
    '기존 테이블 값' AS source_type,
    total_orders,
    total_payment,
    total_refund_amount,
    net_sales
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE DATE(payment_date) = '2025-12-23'
  AND LOWER(company_name) = 'piscess';









