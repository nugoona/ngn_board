-- ============================================
-- demo 계정의 daily_cafe24_items 테이블에서
-- 상품명을 실제 상품명으로 랜덤하게 업데이트
-- 2024-12-01 ~ 2026-12-31
-- ============================================

MERGE `winged-precept-443218-v8.ngn_dataset.daily_cafe24_items` T
USING (
  WITH actual_product_names AS (
    SELECT DISTINCT
      product_name,
      ROW_NUMBER() OVER (ORDER BY product_name) - 1 AS name_index
    FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_items`
    WHERE LOWER(company_name) != 'demo'
      AND product_name IS NOT NULL
      AND product_name != ''
      AND product_name NOT LIKE '데모%'
      AND product_name NOT LIKE 'DEMO%'
      AND product_name NOT LIKE '%TEST%'
      AND product_name NOT LIKE '%test%'
    LIMIT 500
  ),
  product_count AS (
    SELECT COUNT(*) AS cnt FROM actual_product_names
  ),
  target_data AS (
    SELECT
      payment_date,
      company_name,
      order_id,
      product_no,
      -- 날짜와 product_no 기반 일관된 랜덤 선택 (같은 날짜+product_no면 항상 같은 상품명)
      MOD(
        ABS(FARM_FINGERPRINT(CAST(payment_date AS STRING) || '_' || CAST(product_no AS STRING))),
        (SELECT cnt FROM product_count)
      ) AS name_index
    FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_items`
    WHERE LOWER(company_name) = 'demo'
      AND payment_date >= '2024-12-01'
      AND payment_date <= '2026-12-31'
      AND (product_name LIKE '데모%' OR product_name LIKE 'DEMO%' OR product_name = '데모 상품 1' OR product_name = '데모 상품 2')
  )
  SELECT
    td.payment_date,
    td.company_name,
    td.order_id,
    td.product_no,
    apn.product_name AS new_product_name
  FROM target_data td
  JOIN actual_product_names apn ON td.name_index = apn.name_index
) S
ON T.payment_date = S.payment_date
  AND T.company_name = S.company_name
  AND T.order_id = S.order_id
  AND T.product_no = S.product_no
WHEN MATCHED THEN UPDATE SET
  product_name = S.new_product_name;

-- ============================================
-- 확인 쿼리: 업데이트된 상품명 확인
-- ============================================
-- 일별 상품명 다양성 확인
SELECT 
  payment_date,
  COUNT(DISTINCT product_name) AS distinct_product_names,
  COUNT(*) AS total_records,
  ARRAY_AGG(DISTINCT product_name LIMIT 10) AS sample_product_names
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_items`
WHERE LOWER(company_name) = 'demo'
  AND payment_date >= '2024-12-01'
  AND payment_date <= '2026-12-31'
GROUP BY payment_date
ORDER BY payment_date DESC
LIMIT 10;

-- 상품명별 집계 (매출 순)
SELECT 
  product_name,
  COUNT(*) AS record_count,
  COUNT(DISTINCT payment_date) AS distinct_dates,
  COUNT(DISTINCT product_no) AS distinct_product_nos,
  SUM(item_product_sales) AS total_sales,
  SUM(item_quantity) AS total_quantity
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_items`
WHERE LOWER(company_name) = 'demo'
  AND payment_date >= '2024-12-01'
  AND payment_date <= '2026-12-31'
GROUP BY product_name
ORDER BY total_sales DESC
LIMIT 20;
