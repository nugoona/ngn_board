-- Check individual rows in daily_cafe24_items to see if total_canceled exists

-- 1. Check if there are any rows with total_canceled > 0 BEFORE GROUP BY
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
LIMIT 30;

-- 2. Check a specific product that should have canceled items (from summary query)
-- Let's check products that appear in the top list
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
  AND product_name LIKE '%Flare Panel Midi Skirt_Melange%'
ORDER BY payment_date, order_id;

-- 3. Sample all rows for a few products to see the pattern
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
  AND product_name IN (
    'Flare Panel Midi Skirt_Melange Grey',
    'Button Layered Skirt Pants_4Color'
  )
ORDER BY product_name, payment_date, order_id
LIMIT 50;

