-- ✅ 배송비 차이 확인

-- 1. 원본 주문 데이터의 배송비 합계 (일자별)
WITH orders_daily AS (
    SELECT 
        DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) AS payment_date_kst,
        COUNT(DISTINCT order_id) AS order_count,
        SUM(shipping_fee) AS total_shipping_fee,
        SUM(payment_amount + points_spent_amount + naverpay_point) AS total_payment
    FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders`
    WHERE mall_id = 'piscess1'
      AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) BETWEEN '2025-12-01' AND '2025-12-31'
    GROUP BY payment_date_kst
),
sales_daily AS (
    SELECT 
        payment_date,
        total_orders,
        total_shipping_fee,
        total_payment
    FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
    WHERE payment_date BETWEEN '2025-12-01' AND '2025-12-31'
      AND LOWER(company_name) = 'piscess'
)
SELECT 
    COALESCE(o.payment_date_kst, s.payment_date) AS date,
    COALESCE(o.order_count, 0) AS orders_in_source,
    COALESCE(s.total_orders, 0) AS orders_in_sales,
    COALESCE(o.order_count, 0) - COALESCE(s.total_orders, 0) AS order_diff,
    COALESCE(o.total_shipping_fee, 0) AS shipping_fee_in_source,
    COALESCE(s.total_shipping_fee, 0) AS shipping_fee_in_sales,
    COALESCE(o.total_shipping_fee, 0) - COALESCE(s.total_shipping_fee, 0) AS shipping_fee_diff,
    COALESCE(o.total_payment, 0) AS payment_in_source,
    COALESCE(s.total_payment, 0) AS payment_in_sales,
    COALESCE(o.total_payment, 0) - COALESCE(s.total_payment, 0) AS payment_diff
FROM orders_daily o
FULL OUTER JOIN sales_daily s ON o.payment_date_kst = s.payment_date
WHERE COALESCE(o.total_shipping_fee, 0) != COALESCE(s.total_shipping_fee, 0)
   OR COALESCE(o.order_count, 0) != COALESCE(s.total_orders, 0)
ORDER BY date;

-- 2. 전체 배송비 합계 비교
WITH orders_total AS (
    SELECT 
        SUM(shipping_fee) AS total_shipping_fee,
        COUNT(DISTINCT order_id) AS total_orders
    FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders`
    WHERE mall_id = 'piscess1'
      AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) BETWEEN '2025-12-01' AND '2025-12-31'
),
sales_total AS (
    SELECT 
        SUM(total_shipping_fee) AS total_shipping_fee,
        SUM(total_orders) AS total_orders
    FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
    WHERE payment_date BETWEEN '2025-12-01' AND '2025-12-31'
      AND LOWER(company_name) = 'piscess'
)
SELECT 
    '원본 주문 데이터' AS source,
    o.total_shipping_fee AS shipping_fee,
    o.total_orders AS orders
FROM orders_total o
UNION ALL
SELECT 
    'daily_cafe24_sales' AS source,
    s.total_shipping_fee AS shipping_fee,
    s.total_orders AS orders
FROM sales_total s;

-- 3. 주문별 배송비 확인 (중복 체크)
SELECT 
    order_id,
    payment_date,
    DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) AS payment_date_kst,
    shipping_fee,
    payment_amount,
    order_price_amount
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders`
WHERE mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) BETWEEN '2025-12-01' AND '2025-12-31'
ORDER BY payment_date_kst, order_id;

-- 4. daily_cafe24_sales_handler.py의 배송비 집계 로직 확인
-- order_summary에서 MAX(o.shipping_fee)를 사용하는데, 같은 order_id에 여러 행이 있을 수 있는지 확인
SELECT 
    order_id,
    COUNT(*) AS row_count,
    COUNT(DISTINCT shipping_fee) AS distinct_shipping_fees,
    STRING_AGG(DISTINCT CAST(shipping_fee AS STRING), ', ') AS shipping_fee_values
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders`
WHERE mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) BETWEEN '2025-12-01' AND '2025-12-31'
GROUP BY order_id
HAVING COUNT(*) > 1 OR COUNT(DISTINCT shipping_fee) > 1
ORDER BY row_count DESC
LIMIT 20;

