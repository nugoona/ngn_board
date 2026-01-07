-- ✅ daily_cafe24_sales 테이블의 2025년 11월 일자별 데이터 확인

-- 1. 2025년 11월 일자별 데이터 확인 (누락된 날짜 찾기)
SELECT 
    payment_date,
    company_name,
    total_orders,
    item_product_price,
    total_shipping_fee,
    total_coupon_discount,
    total_payment,
    total_refund_amount,
    net_sales,
    updated_at
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE payment_date >= '2025-11-01'
  AND payment_date <= '2025-11-30'
ORDER BY payment_date, company_name;

-- 2. 일자별 합계 확인 (모든 업체)
SELECT 
    payment_date,
    COUNT(DISTINCT company_name) AS company_count,
    SUM(total_orders) AS total_orders,
    SUM(item_product_price) AS total_product_sales,
    SUM(total_shipping_fee) AS total_shipping_fee,
    SUM(total_coupon_discount) AS total_coupon_discount,
    SUM(total_payment) AS total_payment,
    SUM(total_refund_amount) AS total_refund_amount,
    SUM(net_sales) AS net_sales
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE payment_date >= '2025-11-01'
  AND payment_date <= '2025-11-30'
GROUP BY payment_date
ORDER BY payment_date;

-- 3. 누락된 날짜 찾기 (2025년 11월 모든 날짜 중 데이터가 없는 날짜)
WITH all_dates AS (
  SELECT DATE('2025-11-01') AS date
  UNION ALL SELECT DATE('2025-11-02')
  UNION ALL SELECT DATE('2025-11-03')
  UNION ALL SELECT DATE('2025-11-04')
  UNION ALL SELECT DATE('2025-11-05')
  UNION ALL SELECT DATE('2025-11-06')
  UNION ALL SELECT DATE('2025-11-07')
  UNION ALL SELECT DATE('2025-11-08')
  UNION ALL SELECT DATE('2025-11-09')
  UNION ALL SELECT DATE('2025-11-10')
  UNION ALL SELECT DATE('2025-11-11')
  UNION ALL SELECT DATE('2025-11-12')
  UNION ALL SELECT DATE('2025-11-13')
  UNION ALL SELECT DATE('2025-11-14')
  UNION ALL SELECT DATE('2025-11-15')
  UNION ALL SELECT DATE('2025-11-16')
  UNION ALL SELECT DATE('2025-11-17')
  UNION ALL SELECT DATE('2025-11-18')
  UNION ALL SELECT DATE('2025-11-19')
  UNION ALL SELECT DATE('2025-11-20')
  UNION ALL SELECT DATE('2025-11-21')
  UNION ALL SELECT DATE('2025-11-22')
  UNION ALL SELECT DATE('2025-11-23')
  UNION ALL SELECT DATE('2025-11-24')
  UNION ALL SELECT DATE('2025-11-25')
  UNION ALL SELECT DATE('2025-11-26')
  UNION ALL SELECT DATE('2025-11-27')
  UNION ALL SELECT DATE('2025-11-28')
  UNION ALL SELECT DATE('2025-11-29')
  UNION ALL SELECT DATE('2025-11-30')
),
existing_dates AS (
  SELECT DISTINCT payment_date
  FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
  WHERE payment_date >= '2025-11-01'
    AND payment_date <= '2025-11-30'
)
SELECT 
    ad.date AS missing_date
FROM all_dates ad
LEFT JOIN existing_dates ed ON ad.date = ed.payment_date
WHERE ed.payment_date IS NULL
ORDER BY ad.date;

-- 4. 업체별 누락된 날짜 확인 (특정 업체에 데이터가 없는 날짜)
WITH all_dates AS (
  SELECT DATE('2025-11-01') AS date
  UNION ALL SELECT DATE('2025-11-02')
  UNION ALL SELECT DATE('2025-11-03')
  UNION ALL SELECT DATE('2025-11-04')
  UNION ALL SELECT DATE('2025-11-05')
  UNION ALL SELECT DATE('2025-11-06')
  UNION ALL SELECT DATE('2025-11-07')
  UNION ALL SELECT DATE('2025-11-08')
  UNION ALL SELECT DATE('2025-11-09')
  UNION ALL SELECT DATE('2025-11-10')
  UNION ALL SELECT DATE('2025-11-11')
  UNION ALL SELECT DATE('2025-11-12')
  UNION ALL SELECT DATE('2025-11-13')
  UNION ALL SELECT DATE('2025-11-14')
  UNION ALL SELECT DATE('2025-11-15')
  UNION ALL SELECT DATE('2025-11-16')
  UNION ALL SELECT DATE('2025-11-17')
  UNION ALL SELECT DATE('2025-11-18')
  UNION ALL SELECT DATE('2025-11-19')
  UNION ALL SELECT DATE('2025-11-20')
  UNION ALL SELECT DATE('2025-11-21')
  UNION ALL SELECT DATE('2025-11-22')
  UNION ALL SELECT DATE('2025-11-23')
  UNION ALL SELECT DATE('2025-11-24')
  UNION ALL SELECT DATE('2025-11-25')
  UNION ALL SELECT DATE('2025-11-26')
  UNION ALL SELECT DATE('2025-11-27')
  UNION ALL SELECT DATE('2025-11-28')
  UNION ALL SELECT DATE('2025-11-29')
  UNION ALL SELECT DATE('2025-11-30')
),
all_companies AS (
  SELECT DISTINCT company_name
  FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
  WHERE payment_date >= '2025-10-01'  -- 10월 데이터 기준으로 업체 목록 가져오기
),
existing_data AS (
  SELECT DISTINCT payment_date, company_name
  FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
  WHERE payment_date >= '2025-11-01'
    AND payment_date <= '2025-11-30'
)
SELECT 
    ad.date AS missing_date,
    ac.company_name,
    CASE WHEN ed.payment_date IS NULL THEN '누락' ELSE '존재' END AS status
FROM all_dates ad
CROSS JOIN all_companies ac
LEFT JOIN existing_data ed 
  ON ad.date = ed.payment_date 
  AND ac.company_name = ed.company_name
WHERE ed.payment_date IS NULL  -- 누락된 데이터만 표시
ORDER BY ad.date, ac.company_name;

-- 5. 원본 주문 데이터 확인 (2025년 11월 주문이 실제로 있는지 확인)
SELECT 
    DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) AS payment_date_kst,
    mall_id,
    COUNT(DISTINCT order_id) AS order_count,
    SUM(
        CASE 
            WHEN order_price_amount = 0 THEN payment_amount + naverpay_point
            ELSE order_price_amount
        END
    ) AS total_product_sales,
    SUM(shipping_fee) AS total_shipping_fee,
    SUM(coupon_discount_price) AS total_coupon_discount,
    SUM(payment_amount + points_spent_amount + naverpay_point) AS total_payment
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders`
WHERE DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) >= '2025-11-01'
  AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) <= '2025-11-30'
GROUP BY payment_date_kst, mall_id
ORDER BY payment_date_kst, mall_id;

