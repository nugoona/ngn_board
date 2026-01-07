-- ✅ 2026-01-02 날짜의 daily_cafe24_sales 데이터 확인
SELECT 
    payment_date,
    company_name,
    total_orders,
    total_payment,
    total_refund_amount,
    net_sales,
    updated_at
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE payment_date = '2026-01-02'
  AND LOWER(company_name) = 'piscess';

-- ✅ refund_summary가 제대로 생성되는지 확인 (2026-01-02 기준)
SELECT
    refund_with_payment.mall_id,
    refund_with_payment.company_name,
    refund_with_payment.payment_date,
    SUM(refund_with_payment.total_refund_amount) AS total_refund_amount
FROM (
    SELECT
        r.mall_id,
        c.company_name,
        DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) AS payment_date,
        r.order_id,
        SUM(r.total_refund_amount) AS total_refund_amount
    FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
    JOIN `winged-precept-443218-v8.ngn_dataset.cafe24_orders` o
        ON r.order_id = o.order_id AND r.mall_id = o.mall_id
    JOIN `winged-precept-443218-v8.ngn_dataset.company_info` c
        ON r.mall_id = c.mall_id
    WHERE DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) = '2026-01-02'
      AND r.mall_id = 'piscess1'
    GROUP BY r.mall_id, c.company_name, payment_date, r.order_id
) refund_with_payment
GROUP BY refund_with_payment.mall_id, refund_with_payment.company_name, refund_with_payment.payment_date;

