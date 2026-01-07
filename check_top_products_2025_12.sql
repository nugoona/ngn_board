-- ✅ piscess 2025년 12월 가장 많이 팔린 상품 및 판매수 확인

-- 1. 상품별 총 판매량 순위 (daily_cafe24_items 기준)
SELECT 
  product_no,
  product_name,
  SUM(item_quantity) AS total_item_quantity,
  SUM(total_quantity) AS total_quantity,
  SUM(total_canceled) AS total_canceled,
  SUM(item_product_sales) AS total_item_product_sales,
  MAX(product_price) AS product_price,
  COUNT(DISTINCT order_id) AS distinct_order_count,
  COUNT(*) AS row_count
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_items`
WHERE payment_date >= '2025-12-01'
  AND payment_date <= '2025-12-31'
  AND LOWER(company_name) = 'piscess'
GROUP BY product_no, product_name
ORDER BY total_item_quantity DESC
LIMIT 20;

-- 2. 원본 데이터와 비교 (cafe24_order_items_table 기준, 중복 제거)
WITH DedupedItems AS (
  -- 1. 12월 한 달간 아이템 코드별 중복을 먼저 제거
  SELECT * EXCEPT(row_num)
  FROM (
    SELECT *,
      ROW_NUMBER() OVER(
        PARTITION BY mall_id, order_item_code 
        ORDER BY ordered_date DESC
      ) as row_num
    FROM `winged-precept-443218-v8.ngn_dataset.cafe24_order_items_table`
    WHERE mall_id = 'piscess1'
      AND DATE(ordered_date, 'Asia/Seoul') BETWEEN '2025-12-01' AND '2025-12-31'
  )
  WHERE row_num = 1
)
-- 2. 12월 순수 판매량 집계
SELECT 
    CAST(product_no AS INT64) AS product_no,
    MAX(product_name) AS product_name,
    SUM(CAST(quantity AS INT64)) AS original_total_quantity,
    COUNT(DISTINCT order_id) AS original_distinct_order_count,
    MAX(CAST(product_price AS FLOAT64)) AS product_price,
    ROUND(SUM(CAST(product_price AS FLOAT64) * CAST(quantity AS INT64))) AS original_total_sales
FROM DedupedItems
WHERE status_code NOT IN ('C1', 'C2', 'C3')  -- 취소 주문 제외
GROUP BY product_no
ORDER BY original_total_quantity DESC
LIMIT 20;

-- 3. 중복 확인용: 같은 order_id + product_no 조합이 여러 행인지 확인
SELECT 
  payment_date,
  order_id,
  product_no,
  COUNT(*) AS duplicate_count,
  SUM(item_quantity) AS sum_item_quantity
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_items`
WHERE payment_date >= '2025-12-01'
  AND payment_date <= '2025-12-31'
  AND LOWER(company_name) = 'piscess'
GROUP BY payment_date, order_id, product_no
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC, payment_date, order_id, product_no
LIMIT 50;

