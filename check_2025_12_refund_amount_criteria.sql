-- ✅ 1단계: refund_date 기준 12월 환불 금액 (환불 발생일 기준)
SELECT 
    'refund_date 기준' AS criteria,
    SUM(total_refund_amount) AS total_refund_amount,
    COUNT(*) AS refund_records,
    COUNT(DISTINCT order_id) AS unique_orders
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table`
WHERE mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(refund_date), 'Asia/Seoul')) >= '2025-12-01'
  AND DATE(DATETIME(TIMESTAMP(refund_date), 'Asia/Seoul')) <= '2025-12-31';

-- ✅ 2단계: payment_date 기준 12월 환불 금액 (원래 주문 결제일 기준)
SELECT 
    'payment_date 기준' AS criteria,
    SUM(r.total_refund_amount) AS total_refund_amount,
    COUNT(*) AS refund_records,
    COUNT(DISTINCT r.order_id) AS unique_orders
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
JOIN `winged-precept-443218-v8.ngn_dataset.cafe24_orders` o
    ON r.order_id = o.order_id AND r.mall_id = o.mall_id
WHERE r.mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) >= '2025-12-01'
  AND DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) <= '2025-12-31';

-- ✅ 3단계: refund_date 기준이지만 원래 주문 payment_date가 12월인 경우만
SELECT 
    'refund_date 12월 + payment_date 12월' AS criteria,
    SUM(r.total_refund_amount) AS total_refund_amount,
    COUNT(*) AS refund_records,
    COUNT(DISTINCT r.order_id) AS unique_orders
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
JOIN `winged-precept-443218-v8.ngn_dataset.cafe24_orders` o
    ON r.order_id = o.order_id AND r.mall_id = o.mall_id
WHERE r.mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) >= '2025-12-01'
  AND DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) <= '2025-12-31'
  AND DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) >= '2025-12-01'
  AND DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) <= '2025-12-31';

-- ✅ 4단계: 일자별 상세 비교
SELECT 
    DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) AS refund_date_kst,
    DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) AS payment_date_kst,
    COUNT(*) AS refund_records,
    SUM(r.total_refund_amount) AS refund_amount
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
JOIN `winged-precept-443218-v8.ngn_dataset.cafe24_orders` o
    ON r.order_id = o.order_id AND r.mall_id = o.mall_id
WHERE r.mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) >= '2025-12-01'
  AND DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) <= '2025-12-31'
GROUP BY refund_date_kst, payment_date_kst
ORDER BY refund_date_kst, payment_date_kst;

