-- ✅ cafe24_order_items_table에서 중복 확인

-- 1. 같은 (order_id, product_no) 조합이 여러 번 나타나는지 확인
SELECT 
  order_id,
  CAST(product_no AS INT64) AS product_no,
  product_name,
  COUNT(*) AS duplicate_count,
  SUM(quantity) AS sum_quantity,
  MIN(quantity) AS min_quantity,
  MAX(quantity) AS max_quantity,
  COUNT(DISTINCT product_price) AS distinct_price_count,
  STRING_AGG(DISTINCT CAST(quantity AS STRING), ', ') AS quantities
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_order_items_table`
WHERE mall_id = 'piscess1'
  AND order_id IN (
    SELECT DISTINCT order_id
    FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders`
    WHERE mall_id = 'piscess1'
      AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) >= '2025-12-01'
      AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) <= '2025-12-31'
  )
GROUP BY order_id, product_no, product_name
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC, order_id, product_no
LIMIT 50;

-- 2. 특정 상품 (예: product_no = 1005)의 상세 확인
SELECT 
  oi.order_id,
  oi.order_item_code,
  CAST(oi.product_no AS INT64) AS product_no,
  oi.product_name,
  oi.quantity,
  oi.product_price,
  oi.status_code,
  oi.ordered_date,
  DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) AS payment_date
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_order_items_table` oi
JOIN `winged-precept-443218-v8.ngn_dataset.cafe24_orders` o
  ON oi.order_id = o.order_id AND oi.mall_id = o.mall_id
WHERE oi.mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) >= '2025-12-01'
  AND DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) <= '2025-12-31'
  AND CAST(oi.product_no AS INT64) = 1005
ORDER BY oi.order_id, oi.order_item_code, oi.ordered_date;

-- 3. OrderDetails CTE 시뮬레이션 (중복 발생 확인)
WITH FilteredOrders AS (
  SELECT
    o.order_id,
    DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) AS payment_date,
    m.company_name,
    m.main_url,
    CAST(o.mall_id AS STRING) AS mall_id,
    COALESCE(o.first_order, FALSE) AS first_order
  FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders` AS o
  JOIN `winged-precept-443218-v8.ngn_dataset.mall_mapping` AS m
    ON o.mall_id = m.mall_id
  WHERE o.mall_id = 'piscess1'
    AND DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) >= '2025-12-01'
    AND DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) <= '2025-12-03'
    AND m.company_name IS NOT NULL 
),
CanceledOrders AS (
  SELECT
    order_id,
    CAST(mall_id AS STRING) AS mall_id,
    CAST(product_no AS INT64) AS product_no,
    1 AS canceled
  FROM `winged-precept-443218-v8.ngn_dataset.cafe24_order_items_table`
  WHERE status_code IN ('C1', 'C2', 'C3')
)
SELECT
  o.payment_date,
  o.order_id,
  CAST(oi.product_no AS INT64) AS product_no,
  COUNT(*) AS row_count_before_groupby,
  SUM(oi.quantity) AS sum_quantity_before_groupby,
  COUNT(DISTINCT oi.order_item_code) AS distinct_order_item_count
FROM FilteredOrders AS o
JOIN `winged-precept-443218-v8.ngn_dataset.cafe24_order_items_table` AS oi
  ON o.order_id = oi.order_id AND CAST(o.mall_id AS STRING) = CAST(oi.mall_id AS STRING)
WHERE CAST(oi.product_no AS INT64) = 1005
GROUP BY o.payment_date, o.order_id, product_no
HAVING COUNT(*) > 1  -- GROUP BY 전에 중복이 있는 경우만
ORDER BY payment_date, order_id;

