-- ============================================
-- 데모 계정 2025년 daily_cafe24_items 데이터 보충
-- daily_cafe24_sales 데이터를 기반으로 상품별 데이터 생성
-- ============================================

-- daily_cafe24_sales에서 매출이 있는 날짜에 대해 가짜 상품 데이터 생성
INSERT INTO `winged-precept-443218-v8.ngn_dataset.daily_cafe24_items`
(
  payment_date,
  mall_id,
  company_name,
  order_id,
  product_no,
  product_name,
  product_price,
  total_quantity,
  total_canceled,
  item_quantity,
  item_product_sales,
  total_first_order,
  product_url,
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
  -- daily_cafe24_sales에서 매출이 있는 날짜만 가져오기 (2025년 5월~12월)
  sales_dates AS (
    SELECT DISTINCT
      ds.payment_date,
      dm.mall_id,
      ds.company_name,
      ds.net_sales,
      ds.total_orders
    FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales` ds
    CROSS JOIN demo_mall dm
    WHERE LOWER(ds.company_name) = 'demo'
      AND EXTRACT(YEAR FROM ds.payment_date) = 2025
      AND EXTRACT(MONTH FROM ds.payment_date) BETWEEN 5 AND 12
      AND ds.net_sales > 0
  ),
  -- 각 날짜별로 가짜 상품 데이터 생성
  -- daily_cafe24_sales의 total_orders와 net_sales를 기반으로 주문별 상품 데이터 생성
  order_products AS (
    SELECT
      sd.payment_date,
      sd.mall_id,
      sd.company_name,
      order_index,
      -- 가짜 order_id 생성
      CONCAT('DEMO_', FORMAT_DATE('%Y%m%d', sd.payment_date), '_', LPAD(CAST(order_index AS STRING), 4, '0')) AS order_id,
      -- 각 주문당 1-3개의 상품 생성
      product_index,
      -- 가짜 product_no (1000 + 날짜 인덱스 + 주문 인덱스 * 10 + 상품 인덱스)
      CAST(
        1000 + EXTRACT(DAY FROM sd.payment_date) * 100 + order_index * 10 + product_index 
        AS INT64
      ) AS product_no,
      -- 가짜 product_name
      CONCAT('데모 상품 ', product_index) AS product_name,
      -- 상품 가격 (일일 매출을 주문 수로 나눈 후 상품 수로 분배, 약간의 변동성 추가)
      CAST(
        (sd.net_sales / NULLIF(sd.total_orders, 0) / 2.0) * 
        (0.9 + (product_index * 0.1) + MOD(order_index, 10) * 0.01)
        AS FLOAT64
      ) AS product_price,
      -- 수량 (1-2개)
      CAST(1 + MOD(product_index, 2) AS INT64) AS total_quantity,
      0 AS total_canceled,  -- 취소 없음
      CAST(1 + MOD(product_index, 2) AS INT64) AS item_quantity,
      -- 상품 판매 금액 = 가격 * 수량
      CAST(
        (sd.net_sales / NULLIF(sd.total_orders, 0) / 2.0) * 
        (0.9 + (product_index * 0.1) + MOD(order_index, 10) * 0.01) *
        (1 + MOD(product_index, 2))
        AS FLOAT64
      ) AS item_product_sales,
      -- 첫 주문 (첫 번째 주문의 첫 번째 상품만)
      CASE WHEN order_index = 1 AND product_index = 1 THEN 1 ELSE 0 END AS total_first_order,
      -- 가짜 product_url
      CONCAT(
        'https://demo-mall.com/product/',
        CAST(1000 + EXTRACT(DAY FROM sd.payment_date) * 100 + order_index * 10 + product_index AS STRING)
      ) AS product_url
    FROM sales_dates sd
    -- 주문 인덱스 생성 (1부터 total_orders까지)
    CROSS JOIN UNNEST(GENERATE_ARRAY(1, CAST(sd.total_orders AS INT64))) AS order_index
    -- 각 주문당 1-2개의 상품 생성
    CROSS JOIN UNNEST([1, 2]) AS product_index
    WHERE sd.total_orders > 0
  )
SELECT
  op.payment_date,
  op.mall_id,
  op.company_name,
  op.order_id,
  op.product_no,
  op.product_name,
  op.product_price,
  op.total_quantity,
  op.total_canceled,
  op.item_quantity,
  op.item_product_sales,
  op.total_first_order,
  op.product_url,
  CURRENT_TIMESTAMP() AS updated_at
FROM order_products op
WHERE NOT EXISTS (
  -- 이미 존재하는 데이터는 건너뛰기
  SELECT 1
  FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_items` existing
  WHERE existing.payment_date = op.payment_date
    AND LOWER(existing.company_name) = 'demo'
    AND existing.product_no = op.product_no
    AND existing.order_id = op.order_id
)
ORDER BY op.payment_date, op.product_no;

-- 확인 쿼리
SELECT 
  payment_date,
  company_name,
  COUNT(DISTINCT product_no) AS distinct_products,
  COUNT(*) AS total_records,
  SUM(item_quantity) AS total_quantity,
  SUM(item_product_sales) AS total_sales
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_items`
WHERE LOWER(company_name) = 'demo'
  AND EXTRACT(YEAR FROM payment_date) = 2025
GROUP BY payment_date, company_name
ORDER BY payment_date
LIMIT 10;
