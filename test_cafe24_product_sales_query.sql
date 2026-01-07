-- Test the exact query used by cafe24_service.py for product sales

-- This simulates the query with piscess data for December 2025
SELECT
    CONCAT('2025-12-01', ' ~ ', '2025-12-31') AS report_date,
    i.company_name,
    i.product_name,
    MAX(i.product_price) AS product_price,
    SUM(i.total_quantity) AS total_quantity,
    SUM(i.total_canceled) AS total_canceled,
    SUM(i.item_quantity) AS item_quantity,
    SUM(i.item_product_sales) AS item_product_sales,
    SUM(i.total_first_order) AS total_first_order,
    CAST(i.product_no AS STRING) AS product_no
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_items` AS i
LEFT JOIN `winged-precept-443218-v8.ngn_dataset.company_info` AS info
    ON i.mall_id = info.mall_id
LEFT JOIN `winged-precept-443218-v8.ngn_dataset.cafe24_products_table` AS prod
    ON i.mall_id = prod.mall_id AND CAST(i.product_no AS STRING) = prod.product_no
WHERE DATE(DATETIME(TIMESTAMP(i.payment_date), 'Asia/Seoul')) BETWEEN '2025-12-01' AND '2025-12-31'
  AND LOWER(i.company_name) = 'piscess'
  AND (i.item_product_sales > 0 OR i.total_canceled > 0)
GROUP BY i.company_name, i.product_name, i.product_no
ORDER BY SUM(i.item_quantity) DESC, i.company_name, i.product_name
LIMIT 20;

