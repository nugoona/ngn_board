-- ✅ 일자별 배송비 차이 확인

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

