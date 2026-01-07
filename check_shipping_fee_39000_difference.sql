-- ✅ 배송비 차이 39,000원 원인 확인

-- 1. 11월 마지막 주문 중 12월로 잘못 분류될 수 있는 주문 확인
-- (2025-11-30 15:00 UTC ~ 23:59 UTC = 2025-12-01 00:00 KST ~ 08:59 KST)
SELECT 
    payment_date,
    DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) AS payment_date_kst,
    DATE(payment_date) AS payment_date_utc_date,
    order_id,
    shipping_fee,
    payment_amount
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders`
WHERE mall_id = 'piscess1'
  AND (
    -- 11월 마지막 UTC 날짜인데 KST로는 12월 1일
    (DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) = '2025-12-01'
     AND DATE(payment_date) = '2025-11-30')
    OR
    -- 12월 마지막 UTC 날짜인데 KST로는 내년 1월 1일
    (DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) = '2026-01-01'
     AND DATE(payment_date) = '2025-12-31')
  )
ORDER BY payment_date;

-- 2. 1월 초 주문 중 12월로 잘못 분류될 수 있는 주문 확인
SELECT 
    payment_date,
    DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) AS payment_date_kst,
    DATE(payment_date) AS payment_date_utc_date,
    order_id,
    shipping_fee,
    payment_amount
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders`
WHERE mall_id = 'piscess1'
  AND DATE(payment_date) BETWEEN '2025-12-31' AND '2026-01-01'
ORDER BY payment_date;

-- 3. 12월 전체 배송비 합계 (UTC 날짜 기준 vs KST 날짜 기준 비교)
WITH utc_based AS (
    SELECT 
        DATE(payment_date) AS payment_date_utc,
        SUM(shipping_fee) AS total_shipping_fee,
        COUNT(DISTINCT order_id) AS order_count
    FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders`
    WHERE mall_id = 'piscess1'
      AND DATE(payment_date) BETWEEN '2025-12-01' AND '2025-12-31'
    GROUP BY payment_date_utc
),
kst_based AS (
    SELECT 
        DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) AS payment_date_kst,
        SUM(shipping_fee) AS total_shipping_fee,
        COUNT(DISTINCT order_id) AS order_count
    FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders`
    WHERE mall_id = 'piscess1'
      AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) BETWEEN '2025-12-01' AND '2025-12-31'
    GROUP BY payment_date_kst
)
SELECT 
    'UTC 날짜 기준 합계' AS criteria,
    SUM(total_shipping_fee) AS total_shipping_fee,
    SUM(order_count) AS total_orders
FROM utc_based
UNION ALL
SELECT 
    'KST 날짜 기준 합계' AS criteria,
    SUM(total_shipping_fee) AS total_shipping_fee,
    SUM(order_count) AS total_orders
FROM kst_based;

-- 4. 11월 30일 주문 중 KST로 12월 1일인 주문의 배송비 확인
SELECT 
    payment_date,
    DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) AS payment_date_kst,
    order_id,
    shipping_fee,
    payment_amount
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders`
WHERE mall_id = 'piscess1'
  AND DATE(payment_date) = '2025-11-30'
  AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) = '2025-12-01'
ORDER BY payment_date;

-- 5. 혹시 취소된 주문이나 다른 상태의 주문이 포함되었는지 확인
SELECT 
    DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) AS payment_date_kst,
    canceled,
    paid,
    COUNT(*) AS order_count,
    SUM(shipping_fee) AS total_shipping_fee
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders`
WHERE mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) BETWEEN '2025-12-01' AND '2025-12-31'
GROUP BY payment_date_kst, canceled, paid
ORDER BY payment_date_kst, canceled, paid;

