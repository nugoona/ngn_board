-- ✅ 54,000원 차이 원인 찾기

-- 1. 월별 요약 153,000원이 어떤 기준인지 확인
-- 혹시 다른 업체나 다른 필터가 적용되었는지
SELECT 
    canceled,
    paid,
    COUNT(*) AS order_count,
    SUM(shipping_fee) AS total_shipping_fee
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders`
WHERE mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) BETWEEN '2025-12-01' AND '2025-12-31'
GROUP BY canceled, paid
ORDER BY canceled, paid;

-- 2. 혹시 다른 월의 데이터가 포함되었는지 확인
-- 11월 마지막 주문이 12월로 분류되었는지
SELECT 
    DATE(payment_date) AS payment_date_utc,
    DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) AS payment_date_kst,
    COUNT(*) AS order_count,
    SUM(shipping_fee) AS total_shipping_fee
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders`
WHERE mall_id = 'piscess1'
  AND (
    -- 11월 마지막 UTC 날짜
    DATE(payment_date) = '2025-11-30'
    OR
    -- 12월 전체
    DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) BETWEEN '2025-12-01' AND '2025-12-31'
  )
GROUP BY payment_date_utc, payment_date_kst
HAVING payment_date_utc != payment_date_kst
   OR payment_date_kst = '2025-12-01'
ORDER BY payment_date_utc;

-- 3. 11월 30일 주문 중 12월로 분류된 주문의 배송비
SELECT 
    DATE(payment_date) AS payment_date_utc,
    DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) AS payment_date_kst,
    COUNT(*) AS order_count,
    SUM(shipping_fee) AS total_shipping_fee
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders`
WHERE mall_id = 'piscess1'
  AND DATE(payment_date) = '2025-11-30'
  AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) = '2025-12-01'
GROUP BY payment_date_utc, payment_date_kst;

-- 4. 혹시 월별 요약이 카페24에서 직접 가져온 최신 데이터인지 확인
-- (우리 daily_cafe24_sales는 과거 수집 데이터)
-- 최근 업데이트된 주문이 있는지 확인하기 어렵지만, 배송비가 큰 주문 확인
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
  AND shipping_fee >= 3000  -- 배송비가 있는 주문만
ORDER BY shipping_fee DESC, payment_date_kst
LIMIT 50;

-- 5. 일자별 배송비 합계 (canceled=false만)와 daily_cafe24_sales 비교
WITH canceled_false_daily AS (
    SELECT 
        DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) AS payment_date_kst,
        SUM(shipping_fee) AS total_shipping_fee,
        COUNT(*) AS order_count
    FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders`
    WHERE mall_id = 'piscess1'
      AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) BETWEEN '2025-12-01' AND '2025-12-31'
      AND canceled = FALSE
    GROUP BY payment_date_kst
),
daily_sales_data AS (
    SELECT 
        payment_date,
        total_shipping_fee,
        total_orders
    FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
    WHERE payment_date BETWEEN '2025-12-01' AND '2025-12-31'
      AND LOWER(company_name) = 'piscess'
)
SELECT 
    COALESCE(c.payment_date_kst, d.payment_date) AS date,
    COALESCE(c.total_shipping_fee, 0) AS shipping_fee_canceled_false,
    COALESCE(d.total_shipping_fee, 0) AS shipping_fee_daily_sales,
    COALESCE(c.total_shipping_fee, 0) - COALESCE(d.total_shipping_fee, 0) AS diff
FROM canceled_false_daily c
FULL OUTER JOIN daily_sales_data d ON c.payment_date_kst = d.payment_date
WHERE COALESCE(c.total_shipping_fee, 0) != COALESCE(d.total_shipping_fee, 0)
ORDER BY date;

