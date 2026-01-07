-- ✅ payment_date 시간대 이슈 확인

-- 1. cafe24_orders의 payment_date 원본 값과 타입 확인
SELECT 
    payment_date,
    TYPEOF(payment_date) AS payment_date_type,
    TIMESTAMP(payment_date) AS payment_date_as_timestamp,
    DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul') AS payment_date_kst_datetime,
    DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) AS payment_date_kst_date,
    order_id
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders`
WHERE mall_id = 'piscess1'
  AND (
    DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) = '2025-12-31'
    OR DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) = '2026-01-01'
  )
ORDER BY payment_date
LIMIT 10;

-- 2. 12월 31일 자정 근처 주문 데이터 확인 (시간대 경계)
SELECT 
    payment_date,
    TIMESTAMP(payment_date) AS payment_date_utc,
    DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul') AS payment_date_kst,
    DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) AS payment_date_kst_date,
    TIME(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) AS payment_date_kst_time,
    order_id,
    payment_amount
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders`
WHERE mall_id = 'piscess1'
  AND (
    DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) BETWEEN '2025-12-30' AND '2026-01-01'
  )
ORDER BY payment_date;

-- 3. daily_cafe24_sales의 payment_date와 원본 주문 데이터 비교
WITH orders_raw AS (
    SELECT 
        DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) AS payment_date_kst,
        COUNT(DISTINCT order_id) AS order_count,
        SUM(payment_amount + points_spent_amount + naverpay_point) AS total_payment
    FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders`
    WHERE mall_id = 'piscess1'
      AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) BETWEEN '2025-12-01' AND '2025-12-31'
    GROUP BY payment_date_kst
),
sales_agg AS (
    SELECT 
        payment_date,
        total_orders,
        total_payment
    FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
    WHERE payment_date BETWEEN '2025-12-01' AND '2025-12-31'
      AND LOWER(company_name) = 'piscess'
)
SELECT 
    COALESCE(o.payment_date_kst, s.payment_date) AS date,
    COALESCE(o.order_count, 0) AS orders_in_source,
    COALESCE(s.total_orders, 0) AS orders_in_sales,
    COALESCE(o.order_count, 0) - COALESCE(s.total_orders, 0) AS order_diff,
    COALESCE(o.total_payment, 0) AS payment_in_source,
    COALESCE(s.total_payment, 0) AS payment_in_sales,
    COALESCE(o.total_payment, 0) - COALESCE(s.total_payment, 0) AS payment_diff
FROM orders_raw o
FULL OUTER JOIN sales_agg s ON o.payment_date_kst = s.payment_date
ORDER BY date;

-- 4. payment_date가 이미 DATETIME 형식인지, TIMESTAMP 형식인지 확인
-- 만약 이미 DATETIME(KST)라면 TIMESTAMP() 변환이 잘못됨
SELECT 
    payment_date,
    CASE 
        WHEN TYPEOF(payment_date) = 'TIMESTAMP' THEN 'TIMESTAMP (UTC)'
        WHEN TYPEOF(payment_date) = 'DATETIME' THEN 'DATETIME (timezone-naive)'
        WHEN TYPEOF(payment_date) = 'STRING' THEN 'STRING'
        ELSE TYPEOF(payment_date)
    END AS date_type,
    -- 이미 KST로 저장되어 있다면 그냥 DATE()만 하면 됨
    DATE(payment_date) AS direct_date,
    -- 현재 방식 (TIMESTAMP 변환 후 KST)
    DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) AS current_way
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders`
WHERE mall_id = 'piscess1'
  AND payment_date IS NOT NULL
LIMIT 5;

