-- ✅ 환불 데이터와 원래 주문의 결제일 확인
SELECT 
    r.order_id,
    r.refund_date,
    r.total_refund_amount,
    o.payment_date AS original_payment_date,
    DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) AS payment_date_kst,
    o.order_price_amount,
    o.payment_amount
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
JOIN `winged-precept-443218-v8.ngn_dataset.cafe24_orders` o
    ON r.order_id = o.order_id 
    AND r.mall_id = o.mall_id
WHERE r.mall_id = 'piscess1'
  AND r.order_date >= '2026-01-01' 
  AND r.order_date <= '2026-01-31'
ORDER BY r.refund_date;

-- ✅ daily_cafe24_sales에 환불 데이터가 제대로 반영되었는지 확인
SELECT 
    payment_date,
    company_name,
    total_orders,
    total_payment,
    total_refund_amount,
    net_sales
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE payment_date BETWEEN '2026-01-01' AND '2026-01-07'
  AND LOWER(company_name) = 'piscess'
ORDER BY payment_date;

