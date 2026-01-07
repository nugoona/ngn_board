-- ✅ 2025년 12월 daily_cafe24_items 중복 확인 쿼리

-- 1. daily_cafe24_items 테이블에서 중복된 (order_id, product_no) 조합 확인
SELECT 
  payment_date,
  order_id,
  product_no,
  company_name,
  COUNT(*) AS duplicate_count,
  SUM(total_quantity) AS sum_total_quantity,
  SUM(item_quantity) AS sum_item_quantity,
  SUM(item_product_sales) AS sum_item_product_sales
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_items`
WHERE payment_date >= '2025-12-01'
  AND payment_date <= '2025-12-31'
  AND LOWER(company_name) = 'piscess'
GROUP BY payment_date, order_id, product_no, company_name
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC, payment_date, order_id, product_no;

-- 2. 상품별 집계 확인 (order_id 무시하고 product_no만으로 집계)
SELECT 
  payment_date,
  product_no,
  product_name,
  COUNT(DISTINCT order_id) AS distinct_order_count,
  COUNT(*) AS total_rows,
  SUM(total_quantity) AS sum_total_quantity,
  SUM(item_quantity) AS sum_item_quantity,
  SUM(item_product_sales) AS sum_item_product_sales,
  MAX(product_price) AS product_price
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_items`
WHERE payment_date >= '2025-12-01'
  AND payment_date <= '2025-12-31'
  AND LOWER(company_name) = 'piscess'
GROUP BY payment_date, product_no, product_name
ORDER BY payment_date, sum_item_quantity DESC;

-- 3. 원본 cafe24_order_items_table에서 (order_id, product_no) 조합 확인
SELECT 
  DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) AS payment_date,
  oi.order_id,
  oi.product_no,
  oi.product_name,
  COUNT(*) AS row_count,
  SUM(oi.quantity) AS total_quantity,
  MAX(oi.product_price) AS product_price
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders` o
JOIN `winged-precept-443218-v8.ngn_dataset.cafe24_order_items_table` oi
  ON o.order_id = oi.order_id AND o.mall_id = oi.mall_id
WHERE o.mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) >= '2025-12-01'
  AND DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) <= '2025-12-31'
GROUP BY payment_date, oi.order_id, oi.product_no, oi.product_name
HAVING COUNT(*) > 1  -- 중복이 있는 경우만
ORDER BY row_count DESC, payment_date, oi.order_id, oi.product_no;

-- 4. 원본에서 상품별 집계 (정상 집계값 확인용)
SELECT 
  DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) AS payment_date,
  CAST(oi.product_no AS INT64) AS product_no,
  MAX(oi.product_name) AS product_name,
  COUNT(DISTINCT oi.order_id) AS distinct_order_count,
  SUM(oi.quantity) AS total_quantity,
  MAX(oi.product_price) AS product_price,
  SUM(oi.quantity) * MAX(oi.product_price) AS expected_total_sales
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders` o
JOIN `winged-precept-443218-v8.ngn_dataset.cafe24_order_items_table` oi
  ON o.order_id = oi.order_id AND o.mall_id = oi.mall_id
WHERE o.mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) >= '2025-12-01'
  AND DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) <= '2025-12-31'
  AND oi.status_code NOT IN ('C1', 'C2', 'C3')  -- 취소된 주문 제외
GROUP BY payment_date, product_no
ORDER BY payment_date, total_quantity DESC;

-- 5. daily_cafe24_items vs 원본 비교 (상품별)
WITH original_data AS (
  SELECT 
    DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) AS payment_date,
    CAST(oi.product_no AS INT64) AS product_no,
    SUM(oi.quantity) AS original_quantity,
    MAX(oi.product_price) AS original_price,
    SUM(oi.quantity) * MAX(oi.product_price) AS original_total_sales
  FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders` o
  JOIN `winged-precept-443218-v8.ngn_dataset.cafe24_order_items_table` oi
    ON o.order_id = oi.order_id AND o.mall_id = oi.mall_id
  WHERE o.mall_id = 'piscess1'
    AND DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) >= '2025-12-01'
    AND DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) <= '2025-12-31'
    AND oi.status_code NOT IN ('C1', 'C2', 'C3')
  GROUP BY payment_date, product_no
),
aggregated_data AS (
  SELECT 
    payment_date,
    CAST(product_no AS INT64) AS product_no,
    SUM(item_quantity) AS aggregated_quantity,
    SUM(item_product_sales) AS aggregated_total_sales,
    MAX(product_price) AS aggregated_price,
    COUNT(*) AS row_count,
    COUNT(DISTINCT order_id) AS distinct_order_count
  FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_items`
  WHERE payment_date >= '2025-12-01'
    AND payment_date <= '2025-12-31'
    AND LOWER(company_name) = 'piscess'
  GROUP BY payment_date, product_no
)
SELECT 
  COALESCE(od.payment_date, ad.payment_date) AS payment_date,
  COALESCE(od.product_no, ad.product_no) AS product_no,
  od.original_quantity,
  ad.aggregated_quantity,
  (ad.aggregated_quantity - COALESCE(od.original_quantity, 0)) AS quantity_diff,
  od.original_total_sales,
  ad.aggregated_total_sales,
  (ad.aggregated_total_sales - COALESCE(od.original_total_sales, 0)) AS sales_diff,
  ad.row_count,
  ad.distinct_order_count,
  CASE 
    WHEN ad.aggregated_quantity > COALESCE(od.original_quantity, 0) * 1.1 THEN '과집계'
    WHEN ad.aggregated_quantity < COALESCE(od.original_quantity, 0) * 0.9 THEN '과소집계'
    ELSE '정상'
  END AS status
FROM original_data od
FULL OUTER JOIN aggregated_data ad
  ON od.payment_date = ad.payment_date
  AND od.product_no = ad.product_no
WHERE ad.aggregated_quantity != COALESCE(od.original_quantity, 0)
   OR od.original_quantity IS NULL
   OR ad.aggregated_quantity IS NULL
ORDER BY ABS(ad.aggregated_quantity - COALESCE(od.original_quantity, 0)) DESC;

-- 6. 특정 상품의 상세 내역 확인 (예: 가장 많이 중복된 상품)
-- 위 쿼리 5번 결과에서 가장 차이가 큰 product_no를 선택해서 실행
/*
SELECT 
  payment_date,
  order_id,
  product_no,
  product_name,
  total_quantity,
  item_quantity,
  item_product_sales,
  product_price
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_items`
WHERE payment_date >= '2025-12-01'
  AND payment_date <= '2025-12-31'
  AND LOWER(company_name) = 'piscess'
  AND product_no = '123456'  -- 위 쿼리 결과에서 확인한 product_no로 변경
ORDER BY payment_date, order_id;
*/

