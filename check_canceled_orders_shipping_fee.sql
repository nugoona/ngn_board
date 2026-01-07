-- ✅ 취소된 주문의 배송비 확인

-- 1. 취소된 주문(canceled=true)의 배송비 합계
SELECT 
    canceled,
    COUNT(*) AS order_count,
    SUM(shipping_fee) AS total_shipping_fee
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders`
WHERE mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) BETWEEN '2025-12-01' AND '2025-12-31'
GROUP BY canceled;

-- 2. daily_cafe24_sales_handler.py에서 canceled 주문을 어떻게 처리하는지 확인
-- 현재 로직은 canceled 주문도 포함하는지 확인 필요
SELECT 
    DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) AS payment_date_kst,
    canceled,
    COUNT(*) AS order_count,
    SUM(shipping_fee) AS total_shipping_fee
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders`
WHERE mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) BETWEEN '2025-12-01' AND '2025-12-31'
GROUP BY payment_date_kst, canceled
ORDER BY payment_date_kst, canceled;

-- 3. canceled=false인 주문만 집계했을 때 배송비 합계
SELECT 
    SUM(shipping_fee) AS total_shipping_fee_canceled_false,
    COUNT(*) AS order_count_canceled_false
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders`
WHERE mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) BETWEEN '2025-12-01' AND '2025-12-31'
  AND canceled = FALSE;

-- 4. canceled=true인 주문의 배송비 상세
SELECT 
    DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) AS payment_date_kst,
    order_id,
    shipping_fee,
    payment_amount,
    canceled,
    paid
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders`
WHERE mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) BETWEEN '2025-12-01' AND '2025-12-31'
  AND canceled = TRUE
  AND shipping_fee > 0
ORDER BY payment_date_kst, shipping_fee DESC;

-- 5. 월별 요약에서 153,000원이 어떻게 계산되었는지 추정
-- (canceled=false만 집계 + 추가 주문?)
WITH canceled_false_total AS (
    SELECT SUM(shipping_fee) AS total_shipping_fee
    FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders`
    WHERE mall_id = 'piscess1'
      AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) BETWEEN '2025-12-01' AND '2025-12-31'
      AND canceled = FALSE
),
all_orders_total AS (
    SELECT SUM(shipping_fee) AS total_shipping_fee
    FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders`
    WHERE mall_id = 'piscess1'
      AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) BETWEEN '2025-12-01' AND '2025-12-31'
)
SELECT 
    'canceled=false만 집계' AS criteria,
    c.total_shipping_fee AS shipping_fee
FROM canceled_false_total c
UNION ALL
SELECT 
    '전체 주문 집계' AS criteria,
    a.total_shipping_fee AS shipping_fee
FROM all_orders_total a;

