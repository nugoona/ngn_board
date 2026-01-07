-- ============================================
-- piscess 2025년 12월 데이터 누락 확인 쿼리
-- ============================================

-- 1. cafe24_orders에서 일자별 주문 분포 확인
SELECT 
  DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) AS payment_date,
  COUNT(DISTINCT order_id) AS order_count,
  SUM(
    CASE 
      WHEN order_price_amount = 0 THEN payment_amount + naverpay_point
      ELSE order_price_amount
    END
  ) AS product_sales
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders`
WHERE mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) >= '2025-12-01'
  AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) <= '2025-12-31'
GROUP BY payment_date
ORDER BY payment_date;

-- 2. daily_cafe24_sales에 있는 일자 확인
SELECT 
  payment_date,
  total_orders,
  item_product_price,
  total_payment
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE company_name = 'piscess'
  AND payment_date >= '2025-12-01' AND payment_date <= '2025-12-31'
ORDER BY payment_date;

-- 3. 누락된 일자 찾기 (cafe24_orders에는 있는데 daily_cafe24_sales에는 없는 날짜)
WITH orders_by_date AS (
  SELECT 
    DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) AS payment_date,
    COUNT(DISTINCT order_id) AS order_count
  FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders`
  WHERE mall_id = 'piscess1'
    AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) >= '2025-12-01'
    AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) <= '2025-12-31'
  GROUP BY payment_date
),
sales_by_date AS (
  SELECT 
    payment_date,
    total_orders
  FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
  WHERE company_name = 'piscess'
    AND payment_date >= '2025-12-01' AND payment_date <= '2025-12-31'
)
SELECT 
  o.payment_date,
  o.order_count AS orders_in_source,
  COALESCE(s.total_orders, 0) AS orders_in_summary
FROM orders_by_date o
LEFT JOIN sales_by_date s ON o.payment_date = s.payment_date
WHERE s.payment_date IS NULL
ORDER BY o.payment_date;

