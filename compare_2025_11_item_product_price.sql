-- ✅ 2025년 11월 item_product_price 비교 (원본 vs 집계)

-- 1. daily_cafe24_sales의 2025년 11월 piscess 합계
SELECT 
    'daily_cafe24_sales (집계)' AS source,
    SUM(item_product_price) AS total_item_product_price,
    SUM(total_orders) AS total_orders,
    SUM(total_payment) AS total_payment,
    SUM(total_refund_amount) AS total_refund_amount,
    SUM(net_sales) AS net_sales
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE payment_date >= '2025-11-01'
  AND payment_date <= '2025-11-30'
  AND LOWER(company_name) = 'piscess';

-- 2. cafe24_orders 원본의 2025년 11월 piscess1 합계
SELECT 
    'cafe24_orders (원본)' AS source,
    SUM(
        CASE 
            WHEN order_price_amount = 0 THEN payment_amount + naverpay_point
            ELSE order_price_amount
        END
    ) AS total_item_product_price,
    COUNT(DISTINCT order_id) AS total_orders,
    SUM(payment_amount + points_spent_amount + naverpay_point) AS total_payment,
    0 AS total_refund_amount,
    SUM(payment_amount + points_spent_amount + naverpay_point) AS net_sales
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders`
WHERE mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) >= '2025-11-01'
  AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) <= '2025-11-30';

-- 3. 일자별 비교 (차이가 있는 날짜 찾기)
WITH daily_sales AS (
    SELECT 
        payment_date,
        item_product_price AS aggregated_price,
        total_orders AS aggregated_orders
    FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
    WHERE payment_date >= '2025-11-01'
      AND payment_date <= '2025-11-30'
      AND LOWER(company_name) = 'piscess'
),
original_orders AS (
    SELECT 
        DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) AS payment_date,
        SUM(
            CASE 
                WHEN order_price_amount = 0 THEN payment_amount + naverpay_point
                ELSE order_price_amount
            END
        ) AS original_price,
        COUNT(DISTINCT order_id) AS original_orders
    FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders`
    WHERE mall_id = 'piscess1'
      AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) >= '2025-11-01'
      AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) <= '2025-11-30'
    GROUP BY payment_date
)
SELECT 
    COALESCE(ds.payment_date, oo.payment_date) AS payment_date,
    COALESCE(ds.aggregated_price, 0) AS aggregated_item_product_price,
    COALESCE(oo.original_price, 0) AS original_item_product_price,
    COALESCE(oo.original_price, 0) - COALESCE(ds.aggregated_price, 0) AS difference,
    ROUND((COALESCE(oo.original_price, 0) - COALESCE(ds.aggregated_price, 0)) / NULLIF(oo.original_price, 0) * 100, 2) AS diff_percentage,
    COALESCE(ds.aggregated_orders, 0) AS aggregated_orders,
    COALESCE(oo.original_orders, 0) AS original_orders
FROM daily_sales ds
FULL OUTER JOIN original_orders oo ON ds.payment_date = oo.payment_date
WHERE COALESCE(ds.aggregated_price, 0) != COALESCE(oo.original_price, 0)
   OR ds.payment_date IS NULL
   OR oo.payment_date IS NULL
ORDER BY COALESCE(ds.payment_date, oo.payment_date);

-- 4. order_price_amount = 0인 주문 확인 (payment_amount + naverpay_point로 계산되는 경우)
SELECT 
    DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) AS payment_date,
    COUNT(*) AS orders_with_zero_price_amount,
    SUM(payment_amount + naverpay_point) AS total_price_from_payment,
    COUNT(*) AS total_orders,
    SUM(
        CASE 
            WHEN order_price_amount = 0 THEN payment_amount + naverpay_point
            ELSE order_price_amount
        END
    ) AS calculated_item_product_price
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders`
WHERE mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) >= '2025-11-01'
  AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) <= '2025-11-30'
GROUP BY payment_date
ORDER BY payment_date;

-- 5. daily_cafe24_sales_handler.py의 order_summary 로직 재확인용 쿼리
WITH order_summary AS (
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
        MAX(o.payment_amount) AS payment_amount,
        MAX(o.points_spent_amount) AS points_spent_amount,
        MAX(o.naverpay_point) AS naverpay_point
    FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders` AS o
    WHERE DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) >= '2025-11-01'
      AND DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) <= '2025-11-30'
      AND o.mall_id = 'piscess1'
    GROUP BY o.mall_id, o.order_id, payment_date
),
order_agg AS (
    SELECT
        os.payment_date,
        os.mall_id,
        COUNT(DISTINCT os.order_id) AS total_orders,
        SUM(os.item_product_price) AS item_product_price,
        SUM(os.payment_amount) + SUM(os.points_spent_amount) + SUM(os.naverpay_point) AS total_payment
    FROM order_summary AS os
    GROUP BY os.payment_date, os.mall_id
)
SELECT 
    payment_date,
    total_orders,
    item_product_price,
    total_payment
FROM order_agg
ORDER BY payment_date;

