-- ✅ recover_2025_12_items.py 수정 로직 검증 (product_no = 1005만)
-- 실제 스크립트와 동일한 로직으로 테스트

WITH valid_mall_ids AS (
  SELECT DISTINCT mall_id
  FROM `winged-precept-443218-v8.ngn_dataset.mall_mapping`
  WHERE LOWER(company_name) != 'demo'
),
FilteredOrders AS (
  SELECT DISTINCT
    o.order_id,
    DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) AS payment_date,
    m.company_name,
    m.main_url,
    CAST(o.mall_id AS STRING) AS mall_id
  FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders` AS o
  JOIN `winged-precept-443218-v8.ngn_dataset.mall_mapping` AS m
    ON o.mall_id = m.mall_id
  WHERE o.mall_id IN (SELECT mall_id FROM valid_mall_ids)
    AND DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) >= '2025-12-01'
    AND DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) <= '2025-12-03'
    AND m.company_name IS NOT NULL
),
-- ✅ 핵심 수정: order_item_code별로 먼저 중복 제거, 그 다음 order_id + product_no별로 수량 합산
OrderItemsDeduped AS (
  SELECT 
    order_id,
    CAST(mall_id AS STRING) AS mall_id,
    CAST(product_no AS INT64) AS product_no,
    SUM(item_qty) AS quantity,
    MAX(product_name) AS product_name,
    MAX(product_price) AS product_price
  FROM (
    -- 1단계: order_item_code별 유니크 행 추출 (같은 order_item_code 중복 제거)
    SELECT 
      order_id, 
      CAST(mall_id AS STRING) AS mall_id,
      CAST(product_no AS INT64) AS product_no, 
      order_item_code,
      MAX(product_name) AS product_name,
      MAX(CAST(quantity AS INT64)) AS item_qty,
      MAX(CAST(product_price AS FLOAT64)) AS product_price
    FROM `winged-precept-443218-v8.ngn_dataset.cafe24_order_items_table`
    WHERE CAST(product_no AS INT64) = 1005
    GROUP BY order_id, mall_id, product_no, order_item_code
  )
  -- 2단계: order_id + product_no별로 수량 합산 (같은 상품 여러 개 주문한 경우 정상 합산)
  GROUP BY order_id, mall_id, product_no
),
CanceledOrders AS (
  -- 취소 여부도 order_item_code 단위로 유니크하게 확인
  SELECT DISTINCT
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
  oid.product_no,
  REGEXP_REPLACE(oid.product_name, r'^\[[^\]]+\]\s*', '') AS product_name,
  oid.quantity AS total_quantity,
  COALESCE(c.canceled, 0) AS canceled,
  oid.product_price,
  oid.quantity * oid.product_price AS item_product_sales,
  -- 검증용: 최종 결과에서 order_id + product_no 기준으로 중복이 있는지 체크
  COUNT(*) OVER(PARTITION BY o.order_id, oid.product_no) AS check_row_count
FROM FilteredOrders AS o
JOIN OrderItemsDeduped AS oid 
  ON o.order_id = oid.order_id AND o.mall_id = oid.mall_id
LEFT JOIN CanceledOrders AS c 
  ON o.order_id = c.order_id 
  AND o.mall_id = c.mall_id 
  AND oid.product_no = c.product_no
ORDER BY o.payment_date, o.order_id;
