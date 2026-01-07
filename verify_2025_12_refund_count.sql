-- ✅ 1단계: cafe24_refunds_table에 수집된 2025-12 환불 데이터 확인
SELECT 
    COUNT(*) AS total_refund_records,
    COUNT(DISTINCT order_id) AS unique_orders,
    SUM(total_refund_amount) AS total_refund_amount
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table`
WHERE mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(refund_date), 'Asia/Seoul')) >= '2025-12-01'
  AND DATE(DATETIME(TIMESTAMP(refund_date), 'Asia/Seoul')) <= '2025-12-31';

-- ✅ 2단계: 일자별 환불 건수 확인
SELECT 
    DATE(DATETIME(TIMESTAMP(refund_date), 'Asia/Seoul')) AS refund_date_kst,
    COUNT(*) AS refund_count,
    COUNT(DISTINCT order_id) AS unique_orders,
    SUM(total_refund_amount) AS refund_amount
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table`
WHERE mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(refund_date), 'Asia/Seoul')) >= '2025-12-01'
  AND DATE(DATETIME(TIMESTAMP(refund_date), 'Asia/Seoul')) <= '2025-12-31'
GROUP BY refund_date_kst
ORDER BY refund_date_kst;

-- ✅ 3단계: order_item_code별로 분리된 건수 확인
-- (하나의 환불이 여러 order_item_code로 분리될 수 있음)
SELECT 
    order_id,
    COUNT(*) AS item_count,
    SUM(total_refund_amount) AS order_refund_amount
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table`
WHERE mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(refund_date), 'Asia/Seoul')) >= '2025-12-01'
  AND DATE(DATETIME(TIMESTAMP(refund_date), 'Asia/Seoul')) <= '2025-12-31'
GROUP BY order_id
ORDER BY order_id;

-- ✅ 4단계: 원래 주문의 payment_date 기준으로 환불 확인
-- (환불은 원래 주문 결제일 기준으로 집계되어야 함)
SELECT 
    DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) AS original_payment_date,
    COUNT(DISTINCT r.order_id) AS refund_order_count,
    SUM(r.total_refund_amount) AS refund_amount
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
JOIN `winged-precept-443218-v8.ngn_dataset.cafe24_orders` o
    ON r.order_id = o.order_id AND r.mall_id = o.mall_id
WHERE r.mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) >= '2025-12-01'
  AND DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) <= '2025-12-31'
GROUP BY original_payment_date
ORDER BY original_payment_date;

