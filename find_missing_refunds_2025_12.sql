-- ✅ 1단계: payment_date 기준 12월 환불 데이터 상세 확인
SELECT 
    DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) AS payment_date_kst,
    DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) AS refund_date_kst,
    r.order_id,
    r.total_refund_amount,
    o.order_price_amount,
    o.payment_amount
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
JOIN `winged-precept-443218-v8.ngn_dataset.cafe24_orders` o
    ON r.order_id = o.order_id AND r.mall_id = o.mall_id
WHERE r.mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) >= '2025-12-01'
  AND DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) <= '2025-12-31'
ORDER BY payment_date_kst, r.order_id;

-- ✅ 2단계: order_item_code별 분리 전 원본 환불 건수 확인
-- (현재 28건이지만 실제 원본 환불 건수가 몇 건인지 확인)
SELECT 
    COUNT(DISTINCT refund_code) AS unique_refund_codes,
    COUNT(*) AS total_records,
    COUNT(DISTINCT order_id) AS unique_orders,
    SUM(total_refund_amount) AS total_refund_amount
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table`
WHERE mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(refund_date), 'Asia/Seoul')) >= '2025-12-01'
  AND DATE(DATETIME(TIMESTAMP(refund_date), 'Asia/Seoul')) <= '2025-12-31';

-- ✅ 3단계: payment_date 12월 주문 중 환불이 있는 주문 확인
SELECT 
    DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) AS payment_date_kst,
    COUNT(DISTINCT o.order_id) AS total_orders,
    COUNT(DISTINCT r.order_id) AS refunded_orders,
    SUM(o.payment_amount) AS total_payment,
    SUM(r.total_refund_amount) AS total_refund
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders` o
LEFT JOIN `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
    ON o.order_id = r.order_id AND o.mall_id = r.mall_id
WHERE o.mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) >= '2025-12-01'
  AND DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) <= '2025-12-31'
GROUP BY payment_date_kst
ORDER BY payment_date_kst;

-- ✅ 4단계: 누락 가능성 확인 - 환불이지만 주문 테이블에 없는 경우
SELECT 
    r.order_id,
    r.refund_date,
    r.total_refund_amount,
    o.order_id AS order_exists
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
LEFT JOIN `winged-precept-443218-v8.ngn_dataset.cafe24_orders` o
    ON r.order_id = o.order_id AND r.mall_id = o.mall_id
WHERE r.mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) >= '2025-12-01'
  AND DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) <= '2025-12-31'
  AND o.order_id IS NULL;

