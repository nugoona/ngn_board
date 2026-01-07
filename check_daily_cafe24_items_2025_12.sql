-- ✅ daily_cafe24_items 테이블의 2025년 12월 데이터 확인

-- 1. 2025년 12월 데이터 존재 여부 확인
SELECT 
    DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) AS payment_date_kst,
    company_name,
    COUNT(DISTINCT order_id) AS order_count,
    COUNT(DISTINCT product_no) AS product_count,
    SUM(item_quantity) AS total_item_quantity,
    SUM(item_product_sales) AS total_item_product_sales
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_items`
WHERE DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) >= '2025-12-01'
  AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) <= '2025-12-31'
GROUP BY payment_date_kst, company_name
ORDER BY payment_date_kst, company_name;

-- 2. 전체 기간 데이터 확인 (최근 3개월)
SELECT 
    DATE_TRUNC(DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')), MONTH) AS month,
    company_name,
    COUNT(DISTINCT order_id) AS order_count,
    COUNT(DISTINCT product_no) AS product_count,
    SUM(item_quantity) AS total_item_quantity,
    SUM(item_product_sales) AS total_item_product_sales
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_items`
WHERE DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) >= '2025-10-01'
GROUP BY month, company_name
ORDER BY month DESC, company_name;

-- 3. cafe24_orders에서 2025년 12월 주문이 있는지 확인 (daily_cafe24_items 비교용)
SELECT 
    DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) AS payment_date_kst,
    mall_id,
    COUNT(DISTINCT order_id) AS order_count
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders`
WHERE DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) >= '2025-12-01'
  AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) <= '2025-12-31'
  AND mall_id = 'piscess1'
GROUP BY payment_date_kst, mall_id
ORDER BY payment_date_kst;

