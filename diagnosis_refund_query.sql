-- ✅ 오늘(2025-12-23) 환불 데이터 진단 쿼리

-- 1. cafe24_refunds_table에서 오늘 환불 데이터 확인
SELECT 
    r.order_id,
    r.mall_id,
    DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) AS refund_date,
    COUNT(*) AS refund_records_count,
    SUM(r.total_refund_amount) AS total_refund_amount_per_order
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
WHERE DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) = '2025-12-23'
GROUP BY r.order_id, r.mall_id, refund_date
ORDER BY total_refund_amount_per_order DESC;

-- 2. daily_cafe24_sales에 저장된 환불 금액 확인
SELECT 
    payment_date,
    company_name,
    total_payment,
    total_refund_amount,
    net_sales,
    total_orders
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE DATE(payment_date) = '2025-12-23'
ORDER BY total_refund_amount DESC;

-- 3. order_id별 주문 중복 확인
SELECT 
    o.order_id,
    o.mall_id,
    DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) AS payment_date,
    COUNT(*) AS order_records_count,
    MAX(o.payment_amount) AS payment_amount
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders` o
WHERE DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) = '2025-12-23'
GROUP BY o.order_id, o.mall_id, payment_date
HAVING COUNT(*) > 1
ORDER BY order_records_count DESC;










