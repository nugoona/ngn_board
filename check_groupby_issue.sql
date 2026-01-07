-- Check if product_name variations cause GROUP BY issues

-- 1. Check product_name variations for same product_no
SELECT 
    product_no,
    product_name,
    COUNT(*) AS row_count,
    SUM(total_quantity) AS sum_total_quantity,
    SUM(total_canceled) AS sum_total_canceled,
    SUM(item_quantity) AS sum_item_quantity
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_items`
WHERE company_name = 'piscess'
  AND payment_date >= '2025-12-01'
  AND payment_date <= '2025-12-31'
  AND product_no IN (950, 1005)
GROUP BY product_no, product_name
ORDER BY product_no, product_name;

-- 2. Compare: GROUP BY product_no only vs GROUP BY product_no + product_name
-- GROUP BY product_no only
SELECT 
    product_no,
    'GROUP BY product_no only' AS group_method,
    COUNT(DISTINCT product_name) AS distinct_product_names,
    SUM(total_quantity) AS total_quantity,
    SUM(total_canceled) AS total_canceled,
    SUM(item_quantity) AS item_quantity
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_items`
WHERE company_name = 'piscess'
  AND payment_date >= '2025-12-01'
  AND payment_date <= '2025-12-31'
  AND product_no IN (950, 1005)
GROUP BY product_no;

-- GROUP BY product_no + product_name (current service query method)
SELECT 
    product_no,
    product_name,
    'GROUP BY product_no + product_name' AS group_method,
    SUM(total_quantity) AS total_quantity,
    SUM(total_canceled) AS total_canceled,
    SUM(item_quantity) AS item_quantity
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_items`
WHERE company_name = 'piscess'
  AND payment_date >= '2025-12-01'
  AND payment_date <= '2025-12-31'
  AND product_no IN (950, 1005)
GROUP BY product_no, product_name
ORDER BY product_no, total_canceled DESC;

-- 3. Check if service query GROUP BY is correct
SELECT
    i.company_name,
    i.product_name,
    CAST(i.product_no AS INT64) AS product_no,
    MAX(i.product_price) AS product_price,
    SUM(i.total_quantity) AS total_quantity,
    SUM(i.total_canceled) AS total_canceled,
    SUM(i.item_quantity) AS item_quantity,
    SUM(i.item_product_sales) AS item_product_sales
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_items` AS i
WHERE DATE(DATETIME(TIMESTAMP(i.payment_date), 'Asia/Seoul')) BETWEEN '2025-12-01' AND '2025-12-31'
  AND LOWER(i.company_name) = 'piscess'
  AND i.item_product_sales > 0
  AND i.product_no IN (950, 1005)
GROUP BY i.company_name, i.product_name, i.product_no
HAVING SUM(i.total_quantity) > 0
ORDER BY i.product_no, SUM(i.total_canceled) DESC;

