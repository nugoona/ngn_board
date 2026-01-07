-- ✅ 2025-12-30 누락된 주문 확인

-- 1. 2025-12-30의 원본 주문 데이터 상세 확인
SELECT 
    order_id,
    payment_date,
    TIMESTAMP(payment_date) AS payment_date_utc,
    DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul') AS payment_date_kst_datetime,
    DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) AS payment_date_kst_date,
    DATE(TIMESTAMP(payment_date), 'Asia/Seoul') AS payment_date_kst_date_direct,
    payment_amount,
    points_spent_amount,
    naverpay_point,
    payment_amount + points_spent_amount + naverpay_point AS total_payment
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders`
WHERE mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) = '2025-12-30'
ORDER BY payment_date;

-- 2. daily_cafe24_sales에 2025-12-30 데이터가 있는지 확인
SELECT 
    payment_date,
    company_name,
    total_orders,
    total_payment
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE payment_date = '2025-12-30'
  AND LOWER(company_name) = 'piscess';

-- 3. 현재 쿼리 로직으로 2025-12-30 주문이 선택되는지 테스트
-- (daily_cafe24_sales_handler.py의 order_summary 로직 시뮬레이션)
SELECT 
    o.mall_id,
    o.order_id,
    DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) AS payment_date,
    o.payment_amount + o.points_spent_amount + o.naverpay_point AS total_payment
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders` AS o
WHERE DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) = '2025-12-30'
  AND o.mall_id = 'piscess1';

-- 4. 2025-12-30의 UTC 시간 범위 확인 (KST로 변환했을 때 2025-12-30이 되는 UTC 시간)
-- 2025-12-30 00:00:00 KST = 2025-12-29 15:00:00 UTC
-- 2025-12-30 23:59:59 KST = 2025-12-30 14:59:59 UTC
SELECT 
    order_id,
    payment_date,
    TIMESTAMP(payment_date) AS payment_date_utc,
    -- KST 변환
    DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul') AS payment_date_kst,
    DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) AS payment_date_kst_date,
    -- UTC 기준 날짜 (잘못된 방식)
    DATE(payment_date) AS payment_date_utc_date,
    payment_amount
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders`
WHERE mall_id = 'piscess1'
  AND payment_date >= '2025-12-29 15:00:00'
  AND payment_date < '2025-12-30 15:00:00'
ORDER BY payment_date;

