-- ✅ 1단계: refund_date 기준 일자별 환불 (환불 발생일)
SELECT 
    DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) AS refund_date_kst,
    COUNT(*) AS refund_records,
    COUNT(DISTINCT r.order_id) AS unique_refund_orders,
    SUM(r.total_refund_amount) AS total_refund_amount
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
WHERE r.mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) >= '2025-12-01'
  AND DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) <= '2025-12-31'
GROUP BY refund_date_kst
ORDER BY refund_date_kst;

-- ✅ 2단계: payment_date 기준 일자별 환불 (원래 주문 결제일)
SELECT 
    DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) AS payment_date_kst,
    COUNT(*) AS refund_records,
    COUNT(DISTINCT r.order_id) AS unique_refund_orders,
    SUM(r.total_refund_amount) AS total_refund_amount
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
JOIN `winged-precept-443218-v8.ngn_dataset.cafe24_orders` o
    ON r.order_id = o.order_id AND r.mall_id = o.mall_id
WHERE r.mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) >= '2025-12-01'
  AND DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) <= '2025-12-31'
GROUP BY payment_date_kst
ORDER BY payment_date_kst;

-- ✅ 3단계: refund_date와 payment_date 비교 (상세)
SELECT 
    DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) AS refund_date_kst,
    DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) AS payment_date_kst,
    COUNT(*) AS refund_records,
    COUNT(DISTINCT r.order_id) AS unique_refund_orders,
    SUM(r.total_refund_amount) AS total_refund_amount
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
JOIN `winged-precept-443218-v8.ngn_dataset.cafe24_orders` o
    ON r.order_id = o.order_id AND r.mall_id = o.mall_id
WHERE r.mall_id = 'piscess1'
  AND (
    DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) >= '2025-12-01'
    OR DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) >= '2025-12-01'
  )
  AND (
    DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) <= '2025-12-31'
    OR DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) <= '2025-12-31'
  )
GROUP BY refund_date_kst, payment_date_kst
ORDER BY refund_date_kst, payment_date_kst;

-- ✅ 4단계: payment_date 기준 일자별 상세 (주문 정보 포함)
SELECT 
    DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) AS payment_date_kst,
    DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) AS refund_date_kst,
    r.order_id,
    r.order_item_code,
    r.total_refund_amount,
    o.order_price_amount AS original_order_amount,
    o.payment_amount AS original_payment_amount
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
JOIN `winged-precept-443218-v8.ngn_dataset.cafe24_orders` o
    ON r.order_id = o.order_id AND r.mall_id = o.mall_id
WHERE r.mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) >= '2025-12-01'
  AND DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) <= '2025-12-31'
ORDER BY payment_date_kst, r.order_id, r.order_item_code;

-- ✅ 5단계: 일자별 합계 비교 (refund_date vs payment_date)
SELECT 
    'refund_date 기준' AS criteria,
    DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) AS date_kst,
    COUNT(*) AS refund_records,
    COUNT(DISTINCT r.order_id) AS unique_orders,
    SUM(r.total_refund_amount) AS total_refund_amount
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
WHERE r.mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) >= '2025-12-01'
  AND DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) <= '2025-12-31'
GROUP BY date_kst

UNION ALL

SELECT 
    'payment_date 기준' AS criteria,
    DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) AS date_kst,
    COUNT(*) AS refund_records,
    COUNT(DISTINCT r.order_id) AS unique_orders,
    SUM(r.total_refund_amount) AS total_refund_amount
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
JOIN `winged-precept-443218-v8.ngn_dataset.cafe24_orders` o
    ON r.order_id = o.order_id AND r.mall_id = o.mall_id
WHERE r.mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) >= '2025-12-01'
  AND DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) <= '2025-12-31'
GROUP BY date_kst

ORDER BY date_kst, criteria;

