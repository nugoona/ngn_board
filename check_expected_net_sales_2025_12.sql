-- ✅ 2025년 12월 piscess 기대 net_sales 확인 쿼리

-- 1. 원본 데이터(cafe24_orders)에서 직접 계산한 total_payment
SELECT
  'cafe24_orders 원본' AS source,
  COUNT(DISTINCT order_id) AS total_orders,
  SUM(CASE WHEN order_price_amount = 0 THEN payment_amount + naverpay_point ELSE order_price_amount END) AS item_product_price,
  SUM(shipping_fee) AS total_shipping_fee,
  SUM(coupon_discount_price) AS total_coupon_discount,
  SUM(payment_amount + points_spent_amount + naverpay_point) AS total_payment
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders`
WHERE mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) >= '2025-12-01'
  AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) <= '2025-12-31';

-- 2. 원본 환불 데이터(cafe24_refunds_table)에서 직접 계산한 total_refund_amount (refund_date 기준)
WITH refund_deduped AS (
  SELECT
    r.refund_date,
    r.order_id,
    r.refund_code,
    MAX(r.total_refund_amount) AS total_refund_amount
  FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
  WHERE r.mall_id = 'piscess1'
    AND DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) >= '2025-12-01'
    AND DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) <= '2025-12-31'
  GROUP BY r.refund_date, r.order_id, r.refund_code
)
SELECT
  'cafe24_refunds 원본 (refund_date 기준)' AS source,
  SUM(total_refund_amount) AS total_refund_amount,
  COUNT(DISTINCT refund_code) AS distinct_refund_codes
FROM refund_deduped;

-- 3. 원본 데이터 기반 net_sales 계산 (환불은 refund_date 기준)
WITH orders_total AS (
  SELECT
    SUM(payment_amount + points_spent_amount + naverpay_point) AS total_payment
  FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders`
  WHERE mall_id = 'piscess1'
    AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) >= '2025-12-01'
    AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) <= '2025-12-31'
),
refunds_total AS (
  SELECT
    SUM(refund_by_code.total_refund_amount) AS total_refund_amount
  FROM (
    SELECT
      r.refund_code,
      MAX(r.total_refund_amount) AS total_refund_amount
    FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
    WHERE r.mall_id = 'piscess1'
      AND DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) >= '2025-12-01'
      AND DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) <= '2025-12-31'
    GROUP BY r.refund_code
  ) refund_by_code
)
SELECT
  '원본 데이터 기반 계산' AS source,
  ot.total_payment,
  rt.total_refund_amount,
  (ot.total_payment - rt.total_refund_amount) AS calculated_net_sales,
  (ot.total_payment - rt.total_refund_amount - 10548411) AS difference_from_expected
FROM orders_total ot, refunds_total rt;

-- 4. daily_cafe24_sales와 비교
SELECT
  'daily_cafe24_sales 테이블' AS source,
  SUM(total_payment) AS total_payment,
  SUM(total_refund_amount) AS total_refund_amount,
  SUM(net_sales) AS net_sales,
  SUM(total_payment - total_refund_amount) AS calculated_net_sales,
  COUNT(*) AS row_count
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE payment_date >= '2025-12-01'
  AND payment_date <= '2025-12-31'
  AND LOWER(company_name) = 'piscess';

-- 5. 일자별로 비교하여 차이가 나는 날짜 찾기
WITH daily_orders AS (
  SELECT
    DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) AS payment_date,
    SUM(payment_amount + points_spent_amount + naverpay_point) AS total_payment
  FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders`
  WHERE mall_id = 'piscess1'
    AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) >= '2025-12-01'
    AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) <= '2025-12-31'
  GROUP BY payment_date
),
daily_refunds AS (
  SELECT
    DATE(DATETIME(TIMESTAMP(refund_date), 'Asia/Seoul')) AS refund_date,
    SUM(refund_by_code.total_refund_amount) AS total_refund_amount
  FROM (
    SELECT
      DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) AS refund_date,
      r.refund_code,
      MAX(r.total_refund_amount) AS total_refund_amount
    FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
    WHERE r.mall_id = 'piscess1'
      AND DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) >= '2025-12-01'
      AND DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) <= '2025-12-31'
    GROUP BY refund_date, r.refund_code
  ) refund_by_code
  GROUP BY refund_date
),
daily_sales_table AS (
  SELECT
    payment_date,
    total_payment AS table_total_payment,
    total_refund_amount AS table_total_refund_amount,
    net_sales AS table_net_sales
  FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
  WHERE payment_date >= '2025-12-01'
    AND payment_date <= '2025-12-31'
    AND LOWER(company_name) = 'piscess'
)
SELECT
  COALESCE(ds.payment_date, do.payment_date, dr.refund_date) AS date,
  COALESCE(do.total_payment, 0) AS source_total_payment,
  COALESCE(dr.total_refund_amount, 0) AS source_total_refund_amount,
  (COALESCE(do.total_payment, 0) - COALESCE(dr.total_refund_amount, 0)) AS source_net_sales,
  ds.table_total_payment,
  ds.table_total_refund_amount,
  ds.table_net_sales,
  (COALESCE(do.total_payment, 0) - ds.table_total_payment) AS payment_diff,
  (COALESCE(dr.total_refund_amount, 0) - ds.table_total_refund_amount) AS refund_diff,
  ((COALESCE(do.total_payment, 0) - COALESCE(dr.total_refund_amount, 0)) - ds.table_net_sales) AS net_sales_diff
FROM daily_sales_table ds
FULL OUTER JOIN daily_orders do ON ds.payment_date = do.payment_date
FULL OUTER JOIN daily_refunds dr ON ds.payment_date = dr.refund_date
WHERE ABS(COALESCE(do.total_payment, 0) - COALESCE(ds.table_total_payment, 0)) > 0.01
   OR ABS(COALESCE(dr.total_refund_amount, 0) - COALESCE(ds.table_total_refund_amount, 0)) > 0.01
ORDER BY date;

