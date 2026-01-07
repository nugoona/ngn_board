-- Check if daily_cafe24_items has canceled data for December 2025

-- 1. Check if total_canceled column has any non-zero values
SELECT 
    product_no,
    product_name,
    SUM(total_quantity) AS total_quantity,
    SUM(total_canceled) AS total_canceled,
    SUM(item_quantity) AS item_quantity,
    COUNT(*) AS row_count
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_items`
WHERE company_name = 'piscess'
  AND payment_date >= '2025-12-01'
  AND payment_date <= '2025-12-31'
GROUP BY product_no, product_name
HAVING SUM(total_canceled) > 0
ORDER BY SUM(total_canceled) DESC
LIMIT 20;

-- 2. Overall summary
SELECT 
    'summary' AS type,
    SUM(total_quantity) AS total_quantity,
    SUM(total_canceled) AS total_canceled,
    SUM(item_quantity) AS item_quantity,
    COUNT(DISTINCT product_no) AS product_count
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_items`
WHERE company_name = 'piscess'
  AND payment_date >= '2025-12-01'
  AND payment_date <= '2025-12-31';

-- 3. Sample rows with canceled data
SELECT 
    payment_date,
    order_id,
    product_no,
    product_name,
    total_quantity,
    total_canceled,
    item_quantity,
    item_product_sales
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_items`
WHERE company_name = 'piscess'
  AND payment_date >= '2025-12-01'
  AND payment_date <= '2025-12-31'
  AND total_canceled > 0
ORDER BY total_canceled DESC, payment_date
LIMIT 20;

