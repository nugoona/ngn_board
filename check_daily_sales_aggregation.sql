-- ============================================
-- daily_cafe24_sales 집계 확인 및 비교 쿼리
-- ============================================

-- 1. cafe24_orders 전체 합계 (piscess1)
SELECT 
  'cafe24_orders (전체)' AS source,
  COUNT(DISTINCT order_id) AS total_orders,
  SUM(
    CASE 
      WHEN order_price_amount = 0 THEN payment_amount + naverpay_point
      ELSE order_price_amount
    END
  ) AS total_product_sales,
  SUM(shipping_fee) AS total_shipping_fee,
  SUM(coupon_discount_price) AS total_coupon_discount,
  SUM(payment_amount + points_spent_amount + naverpay_point) AS total_payment
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders`
WHERE mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) >= '2025-12-01'
  AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) <= '2025-12-31';

-- 2. daily_cafe24_sales 합계 (piscess)
SELECT 
  'daily_cafe24_sales (집계)' AS source,
  SUM(total_orders) AS total_orders,
  SUM(item_product_price) AS total_product_sales,
  SUM(total_shipping_fee) AS total_shipping_fee,
  SUM(total_coupon_discount) AS total_coupon_discount,
  SUM(total_payment) AS total_payment
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE company_name = 'piscess'
  AND payment_date >= '2025-12-01' AND payment_date <= '2025-12-31';

-- 3. daily_cafe24_sales에 중복된 payment_date가 있는지 확인
SELECT 
  payment_date,
  company_name,
  COUNT(*) AS duplicate_count,
  SUM(total_orders) AS sum_orders
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE company_name = 'piscess'
  AND payment_date >= '2025-12-01' AND payment_date <= '2025-12-31'
GROUP BY payment_date, company_name
HAVING COUNT(*) > 1
ORDER BY payment_date;

-- 4. 일자별 비교 (cafe24_orders vs daily_cafe24_sales)
WITH orders_daily AS (
  SELECT 
    DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) AS payment_date,
    COUNT(DISTINCT order_id) AS orders,
    SUM(
      CASE 
        WHEN order_price_amount = 0 THEN payment_amount + naverpay_point
        ELSE order_price_amount
      END
    ) AS product_sales,
    SUM(payment_amount + points_spent_amount + naverpay_point) AS total_payment
  FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders`
  WHERE mall_id = 'piscess1'
    AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) >= '2025-12-01'
    AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) <= '2025-12-31'
  GROUP BY payment_date
),
sales_daily AS (
  SELECT 
    payment_date,
    SUM(total_orders) AS orders,
    SUM(item_product_price) AS product_sales,
    SUM(total_payment) AS total_payment
  FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
  WHERE company_name = 'piscess'
    AND payment_date >= '2025-12-01' AND payment_date <= '2025-12-31'
  GROUP BY payment_date
)
SELECT 
  COALESCE(o.payment_date, s.payment_date) AS payment_date,
  COALESCE(o.orders, 0) AS orders_in_source,
  COALESCE(s.orders, 0) AS orders_in_sales,
  COALESCE(o.orders, 0) - COALESCE(s.orders, 0) AS orders_diff,
  COALESCE(o.product_sales, 0) AS sales_in_source,
  COALESCE(s.product_sales, 0) AS sales_in_sales,
  COALESCE(o.product_sales, 0) - COALESCE(s.product_sales, 0) AS sales_diff
FROM orders_daily o
FULL OUTER JOIN sales_daily s ON o.payment_date = s.payment_date
ORDER BY payment_date;

