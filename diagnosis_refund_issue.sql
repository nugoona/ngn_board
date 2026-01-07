-- ✅ 1단계: 환불 데이터와 원래 주문의 결제일 확인
SELECT 
    r.order_id,
    DATE(DATETIME(TIMESTAMP(r.order_date), 'Asia/Seoul')) AS refund_order_date,
    DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) AS refund_date_kst,
    r.total_refund_amount,
    DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) AS original_payment_date,
    o.order_price_amount,
    o.payment_amount
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
JOIN `winged-precept-443218-v8.ngn_dataset.cafe24_orders` o
    ON r.order_id = o.order_id 
    AND r.mall_id = o.mall_id
WHERE r.mall_id = 'piscess1'
  AND r.order_date >= '2026-01-01' 
  AND r.order_date <= '2026-01-31';

-- ✅ 2단계: daily_cafe24_sales에서 해당 payment_date의 환불 데이터 확인
-- (위 쿼리 결과의 original_payment_date를 기준으로 확인)
SELECT 
    payment_date,
    company_name,
    total_orders,
    total_payment,
    total_refund_amount,
    net_sales
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE LOWER(company_name) = 'piscess'
  AND payment_date >= '2025-12-01'  -- 원래 주문일이 과거일 수 있으므로 넓게 확인
  AND payment_date <= '2026-01-31'
ORDER BY payment_date;

-- ✅ 3단계: refund_summary CTE 로직 테스트 (2026-01-01 기준)
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
    WHERE DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) = '2026-01-01'
      AND r.mall_id = 'piscess1'
    GROUP BY r.mall_id, c.company_name, payment_date, r.order_id
) refund_with_payment
GROUP BY refund_with_payment.mall_id, refund_with_payment.company_name, refund_with_payment.payment_date;

