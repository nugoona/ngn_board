-- ✅ 카페24 원본 데이터 vs daily_cafe24_sales 비교

-- 1. 카페24 원본 주문 데이터 집계 (2025-12 전체)
WITH cafe24_original AS (
    SELECT 
        COUNT(DISTINCT order_id) AS total_orders,
        SUM(shipping_fee) AS total_shipping_fee,
        SUM(
            CASE 
                WHEN order_price_amount = 0 THEN payment_amount + naverpay_point
                ELSE order_price_amount
            END
        ) AS item_product_price,
        SUM(coupon_discount_price) AS total_coupon_discount,
        SUM(payment_amount + points_spent_amount + naverpay_point) AS total_payment
    FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders`
    WHERE mall_id = 'piscess1'
      AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) BETWEEN '2025-12-01' AND '2025-12-31'
),
daily_sales_summary AS (
    SELECT 
        SUM(total_orders) AS total_orders,
        SUM(total_shipping_fee) AS total_shipping_fee,
        SUM(item_product_price) AS item_product_price,
        SUM(total_coupon_discount) AS total_coupon_discount,
        SUM(total_payment) AS total_payment,
        SUM(total_refund_amount) AS total_refund_amount
    FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
    WHERE payment_date BETWEEN '2025-12-01' AND '2025-12-31'
      AND LOWER(company_name) = 'piscess'
)
SELECT 
    '카페24 원본 데이터' AS source,
    c.total_orders AS orders,
    c.total_shipping_fee AS shipping_fee,
    c.item_product_price AS product_sales,
    c.total_coupon_discount AS coupon_discount,
    c.total_payment AS payment_total,
    NULL AS refund_total
FROM cafe24_original c
UNION ALL
SELECT 
    'daily_cafe24_sales' AS source,
    d.total_orders AS orders,
    d.total_shipping_fee AS shipping_fee,
    d.item_product_price AS product_sales,
    d.total_coupon_discount AS coupon_discount,
    d.total_payment AS payment_total,
    d.total_refund_amount AS refund_total
FROM daily_sales_summary d;

-- 2. 배송비 차이 원인 확인 (일자별)
-- 월별 요약에서 153,000 vs 기간합에서 114,000 (차이: 39,000)
SELECT 
    DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) AS payment_date_kst,
    COUNT(DISTINCT order_id) AS order_count,
    SUM(shipping_fee) AS shipping_fee,
    STRING_AGG(DISTINCT order_id, ', ' LIMIT 5) AS sample_order_ids
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders`
WHERE mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) BETWEEN '2025-12-01' AND '2025-12-31'
GROUP BY payment_date_kst
ORDER BY payment_date_kst;

-- 3. 카페24에서 데이터가 수정되었는지 확인 (업데이트 날짜 확인)
SELECT 
    DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) AS payment_date_kst,
    order_id,
    shipping_fee,
    payment_amount,
    -- updated_at이나 insert_timestamp 같은 필드가 있다면 확인
    TIMESTAMP(payment_date) AS payment_timestamp
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders`
WHERE mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) BETWEEN '2025-12-01' AND '2025-12-31'
ORDER BY payment_date_kst, order_id
LIMIT 50;

-- 4. 혹시 다른 월의 데이터가 포함되었는지 확인 (시간대 경계)
-- 11월 마지막 주문이 12월로 잘못 집계되었는지
SELECT 
    DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) AS payment_date_kst,
    TIMESTAMP(payment_date) AS payment_date_utc,
    order_id,
    shipping_fee,
    payment_amount
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders`
WHERE mall_id = 'piscess1'
  AND (
    (DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) = '2025-12-01'
     AND TIME(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) < '09:00:00')
    OR
    (DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) = '2025-11-30'
     AND TIME(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) >= '15:00:00')
  )
ORDER BY payment_date_utc;

-- 5. 카페24 API에서 배송비가 큰 주문 확인
-- (배송비 차이 원인 파악)
SELECT 
    order_id,
    payment_date,
    DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) AS payment_date_kst,
    shipping_fee,
    payment_amount,
    canceled,
    paid,
    order_price_amount
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders`
WHERE mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) BETWEEN '2025-12-01' AND '2025-12-31'
  -- 최근 수정된 것으로 의심되는 주문 (예: shipping_fee가 비정상적으로 큰 값)
ORDER BY shipping_fee DESC
LIMIT 20;

