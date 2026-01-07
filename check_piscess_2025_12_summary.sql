-- piscess December 2025 summary: total sales, canceled orders, net sales

-- 1. Aggregate from daily_cafe24_items (current collected data)
SELECT 
    'daily_cafe24_items' AS source,
    SUM(total_quantity) AS total_quantity,
    SUM(total_canceled) AS total_canceled,
    SUM(item_quantity) AS net_quantity,
    SUM(product_price * total_quantity) AS total_sales_amount,
    SUM(product_price * total_canceled) AS canceled_amount,
    SUM(item_product_sales) AS net_sales_amount,
    COUNT(DISTINCT product_no) AS product_count,
    COUNT(*) AS row_count
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_items`
WHERE company_name = 'piscess'
  AND payment_date >= '2025-12-01'
  AND payment_date <= '2025-12-31';

-- 2. Aggregate from source data (cafe24_order_items_table) - verify canceled orders
--    Use same conditions as FilteredOrders
WITH FilteredOrders AS (
  SELECT DISTINCT
    o.order_id,
    DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) AS payment_date,
    CAST(o.mall_id AS STRING) AS mall_id
  FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders` AS o
  JOIN `winged-precept-443218-v8.ngn_dataset.mall_mapping` AS m
    ON o.mall_id = m.mall_id
  WHERE o.mall_id = 'piscess1'
    AND DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) >= '2025-12-01'
    AND DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) <= '2025-12-31'
    AND m.company_name IS NOT NULL
),
OrderItemsDeduped AS (
  -- Deduplicate by order_item_code using ROW_NUMBER
  SELECT * EXCEPT(row_num)
  FROM (
    SELECT 
      oi.order_id,
      CAST(oi.mall_id AS STRING) AS mall_id,
      CAST(oi.product_no AS INT64) AS product_no,
      CAST(oi.quantity AS INT64) AS quantity,
      CAST(oi.product_price AS FLOAT64) AS product_price,
      oi.status_code,
      ROW_NUMBER() OVER(
        PARTITION BY CAST(oi.mall_id AS STRING), oi.order_item_code 
        ORDER BY oi.ordered_date DESC
      ) AS row_num
    FROM `winged-precept-443218-v8.ngn_dataset.cafe24_order_items_table` AS oi
    INNER JOIN FilteredOrders AS fo
      ON oi.order_id = fo.order_id 
      AND CAST(oi.mall_id AS STRING) = fo.mall_id
  )
  WHERE row_num = 1
)
SELECT 
    'source_data' AS source,
    SUM(quantity) AS total_quantity,
    SUM(CASE WHEN status_code IN ('C1', 'C2', 'C3') THEN quantity ELSE 0 END) AS total_canceled,
    SUM(CASE WHEN status_code NOT IN ('C1', 'C2', 'C3') THEN quantity ELSE 0 END) AS net_quantity,
    SUM(product_price * quantity) AS total_sales_amount,
    SUM(CASE WHEN status_code IN ('C1', 'C2', 'C3') THEN product_price * quantity ELSE 0 END) AS canceled_amount,
    SUM(CASE WHEN status_code NOT IN ('C1', 'C2', 'C3') THEN product_price * quantity ELSE 0 END) AS net_sales_amount,
    COUNT(DISTINCT product_no) AS product_count,
    COUNT(*) AS row_count,
    COUNT(DISTINCT order_id) AS order_count
FROM OrderItemsDeduped;

-- 3. Detail of canceled orders
WITH FilteredOrders AS (
  SELECT DISTINCT
    o.order_id,
    DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) AS payment_date,
    CAST(o.mall_id AS STRING) AS mall_id
  FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders` AS o
  JOIN `winged-precept-443218-v8.ngn_dataset.mall_mapping` AS m
    ON o.mall_id = m.mall_id
  WHERE o.mall_id = 'piscess1'
    AND DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) >= '2025-12-01'
    AND DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) <= '2025-12-31'
    AND m.company_name IS NOT NULL
),
OrderItemsDeduped AS (
  SELECT * EXCEPT(row_num)
  FROM (
    SELECT 
      oi.order_id,
      CAST(oi.mall_id AS STRING) AS mall_id,
      CAST(oi.product_no AS INT64) AS product_no,
      CAST(oi.quantity AS INT64) AS quantity,
      oi.status_code,
      oi.product_name,
      ROW_NUMBER() OVER(
        PARTITION BY CAST(oi.mall_id AS STRING), oi.order_item_code 
        ORDER BY oi.ordered_date DESC
      ) AS row_num
    FROM `winged-precept-443218-v8.ngn_dataset.cafe24_order_items_table` AS oi
    INNER JOIN FilteredOrders AS fo
      ON oi.order_id = fo.order_id 
      AND CAST(oi.mall_id AS STRING) = fo.mall_id
  )
  WHERE row_num = 1
)
SELECT 
    order_id,
    product_no,
    product_name,
    quantity,
    status_code,
    CASE 
        WHEN status_code IN ('C1', 'C2', 'C3') THEN 'canceled'
        ELSE 'normal'
    END AS status
FROM OrderItemsDeduped
WHERE status_code IN ('C1', 'C2', 'C3')
ORDER BY order_id, product_no;
