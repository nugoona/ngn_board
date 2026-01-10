-- ============================================
-- 데모 계정 2025년 daily_cafe24_sales 데이터 보충
-- mall_sales_monthly 테이블의 월간 데이터를 일일로 분배하여 생성
-- ============================================

-- 월간 데이터를 일일로 분배하여 daily_cafe24_sales에 삽입
INSERT INTO `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
(
  payment_date,
  mall_id,
  company_name,
  total_orders,
  item_orders,
  item_product_price,
  total_shipping_fee,
  total_coupon_discount,
  total_payment,
  total_refund_amount,
  net_sales,
  total_naverpay_point,
  total_prepayment,
  total_first_order,
  total_canceled,
  total_naverpay_payment_info,
  updated_at
)
WITH
  -- company_info에서 demo의 mall_id 가져오기
  demo_mall AS (
    SELECT mall_id, company_name
    FROM `winged-precept-443218-v8.ngn_dataset.company_info`
    WHERE LOWER(company_name) = 'demo'
    LIMIT 1
  ),
  -- 월간 데이터 가져오기 (5월~12월)
  monthly_data AS (
    SELECT
      month_date,
      m.company_name,
      m.net_sales,
      m.total_orders,
      m.total_first_order,
      m.total_canceled,
      dm.mall_id,
      EXTRACT(DAY FROM DATE_SUB(DATE_ADD(m.month_date, INTERVAL 1 MONTH), INTERVAL 1 DAY)) AS days_in_month
    FROM `winged-precept-443218-v8.ngn_dataset.mall_sales_monthly` m
    CROSS JOIN demo_mall dm
    WHERE LOWER(m.company_name) = 'demo'
      AND EXTRACT(YEAR FROM m.month_date) = 2025
      AND EXTRACT(MONTH FROM m.month_date) BETWEEN 5 AND 12
  ),
  -- 각 일자별 데이터 생성 (월의 첫날부터 마지막날까지)
  daily_data AS (
    SELECT
      DATE_ADD(md.month_date, INTERVAL day_offset DAY) AS payment_date,
      md.mall_id,
      md.company_name,
      -- 일일 매출 = 월 매출 / 월 일수 (균등 분배)
      CAST(md.net_sales / md.days_in_month AS FLOAT64) AS daily_net_sales,
      -- 일일 주문 수 = 월 주문 수 / 월 일수 (반올림)
      CAST(ROUND(md.total_orders / md.days_in_month) AS INT64) AS daily_total_orders,
      -- 일일 첫 주문 수 = 월 첫 주문 수 / 월 일수 (반올림)
      CAST(ROUND(md.total_first_order / md.days_in_month) AS INT64) AS daily_total_first_order,
      -- 일일 취소 주문 수 = 월 취소 주문 수 / 월 일수 (반올림)
      CAST(ROUND(md.total_canceled / md.days_in_month) AS INT64) AS daily_total_canceled,
      -- 날짜 인덱스 (랜덤성 추가용)
      day_offset
    FROM monthly_data md
    CROSS JOIN UNNEST(GENERATE_ARRAY(0, CAST(md.days_in_month AS INT64) - 1)) AS day_offset
  )
SELECT
  dd.payment_date,
  dd.mall_id,
  dd.company_name,
  -- 기본값 설정 (가짜 데이터이므로)
  dd.daily_total_orders AS total_orders,
  0 AS item_orders,  -- 기본값 0
  -- 일일 매출보다 약간 크게 설정 (배송비/할인 고려)
  CAST(dd.daily_net_sales * 1.1 AS FLOAT64) AS item_product_price,
  -- 배송비 약 5%
  CAST(dd.daily_net_sales * 0.05 AS FLOAT64) AS total_shipping_fee,
  -- 쿠폰 할인 약 5%
  CAST(dd.daily_net_sales * 0.05 AS FLOAT64) AS total_coupon_discount,
  -- 총 결제금액 = net_sales + 배송비
  CAST(dd.daily_net_sales * 1.1 AS FLOAT64) AS total_payment,
  0.0 AS total_refund_amount,  -- 환불 0으로 설정
  dd.daily_net_sales AS net_sales,
  0.0 AS total_naverpay_point,  -- 기본값 0
  0 AS total_prepayment,  -- 기본값 0
  dd.daily_total_first_order AS total_first_order,
  dd.daily_total_canceled AS total_canceled,
  0 AS total_naverpay_payment_info,  -- 기본값 0
  CURRENT_TIMESTAMP() AS updated_at
FROM daily_data dd
WHERE NOT EXISTS (
  -- 이미 존재하는 데이터는 건너뛰기
  SELECT 1
  FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales` existing
  WHERE existing.payment_date = dd.payment_date
    AND LOWER(existing.company_name) = 'demo'
)
ORDER BY dd.payment_date;

-- 확인 쿼리
SELECT 
  payment_date,
  company_name,
  total_orders,
  net_sales,
  COUNT(*) OVER () AS total_records
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE LOWER(company_name) = 'demo'
  AND EXTRACT(YEAR FROM payment_date) = 2025
ORDER BY payment_date
LIMIT 10;
