-- ✅ UTC 날짜 기준 vs KST 날짜 기준 배송비 비교

-- 1. UTC 날짜 기준 12월 배송비 합계 (canceled=false만)
SELECT 
    'UTC 날짜 기준 (canceled=false)' AS criteria,
    SUM(shipping_fee) AS total_shipping_fee,
    COUNT(*) AS order_count
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders`
WHERE mall_id = 'piscess1'
  AND DATE(payment_date) BETWEEN '2025-12-01' AND '2025-12-31'
  AND canceled = FALSE;

-- 2. UTC 날짜 기준 12월 배송비 합계 (전체)
SELECT 
    'UTC 날짜 기준 (전체)' AS criteria,
    SUM(shipping_fee) AS total_shipping_fee,
    COUNT(*) AS order_count
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders`
WHERE mall_id = 'piscess1'
  AND DATE(payment_date) BETWEEN '2025-12-01' AND '2025-12-31';

-- 3. KST 날짜 기준 12월 배송비 합계 (canceled=false만)
SELECT 
    'KST 날짜 기준 (canceled=false)' AS criteria,
    SUM(shipping_fee) AS total_shipping_fee,
    COUNT(*) AS order_count
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders`
WHERE mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) BETWEEN '2025-12-01' AND '2025-12-31'
  AND canceled = FALSE;

-- 4. UTC vs KST 비교 (canceled=false만)
WITH utc_based AS (
    SELECT 
        DATE(payment_date) AS payment_date_utc,
        COUNT(*) AS order_count,
        SUM(shipping_fee) AS total_shipping_fee
    FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders`
    WHERE mall_id = 'piscess1'
      AND DATE(payment_date) BETWEEN '2025-12-01' AND '2025-12-31'
      AND canceled = FALSE
    GROUP BY payment_date_utc
),
kst_based AS (
    SELECT 
        DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) AS payment_date_kst,
        COUNT(*) AS order_count,
        SUM(shipping_fee) AS total_shipping_fee
    FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders`
    WHERE mall_id = 'piscess1'
      AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) BETWEEN '2025-12-01' AND '2025-12-31'
      AND canceled = FALSE
    GROUP BY payment_date_kst
)
SELECT 
    'UTC 기준 합계' AS criteria,
    SUM(total_shipping_fee) AS total_shipping_fee,
    SUM(order_count) AS total_orders
FROM utc_based
UNION ALL
SELECT 
    'KST 기준 합계' AS criteria,
    SUM(total_shipping_fee) AS total_shipping_fee,
    SUM(order_count) AS total_orders
FROM kst_based;

-- 5. 월별 요약이 사용하는 기준 확인
-- 카페24 원본 데이터에서 어떤 필터를 사용하는지 추정
-- 153,000원에 가장 가까운 값을 찾기
SELECT 
    '전체 (KST)' AS criteria,
    SUM(shipping_fee) AS total_shipping_fee
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders`
WHERE mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) BETWEEN '2025-12-01' AND '2025-12-31'
UNION ALL
SELECT 
    'canceled=false (KST)' AS criteria,
    SUM(shipping_fee) AS total_shipping_fee
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders`
WHERE mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) BETWEEN '2025-12-01' AND '2025-12-31'
  AND canceled = FALSE
UNION ALL
SELECT 
    'canceled=false (UTC)' AS criteria,
    SUM(shipping_fee) AS total_shipping_fee
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders`
WHERE mall_id = 'piscess1'
  AND DATE(payment_date) BETWEEN '2025-12-01' AND '2025-12-31'
  AND canceled = FALSE
UNION ALL
SELECT 
    '전체 (UTC)' AS criteria,
    SUM(shipping_fee) AS total_shipping_fee
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders`
WHERE mall_id = 'piscess1'
  AND DATE(payment_date) BETWEEN '2025-12-01' AND '2025-12-31';

