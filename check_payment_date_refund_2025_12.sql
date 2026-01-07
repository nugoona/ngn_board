-- ✅ payment_date 기준 2025-12 환불 금액 (refund_code별 중복 제거)
WITH refund_by_code AS (
    -- refund_code별로 먼저 집계 (같은 refund_code는 한 번만)
    SELECT
        r.mall_id,
        c.company_name,
        DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) AS payment_date,
        r.refund_code,
        MAX(r.total_refund_amount) AS total_refund_amount
    FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
    JOIN `winged-precept-443218-v8.ngn_dataset.cafe24_orders` o
        ON r.order_id = o.order_id AND r.mall_id = o.mall_id
    JOIN `winged-precept-443218-v8.ngn_dataset.company_info` c
        ON r.mall_id = c.mall_id
    WHERE DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) >= '2025-12-01'
      AND DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) <= '2025-12-31'
      AND r.mall_id = 'piscess1'
    GROUP BY r.mall_id, c.company_name, payment_date, r.refund_code
)
SELECT 
    company_name,
    COUNT(DISTINCT refund_code) AS unique_refund_codes,
    SUM(total_refund_amount) AS total_refund_amount
FROM refund_by_code
GROUP BY company_name;

-- ✅ daily_cafe24_sales에 저장된 값 확인
SELECT 
    company_name,
    SUM(total_refund_amount) AS total_refund_amount,
    COUNT(*) AS row_count
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE payment_date >= '2025-12-01'
  AND payment_date <= '2025-12-31'
  AND LOWER(company_name) = 'piscess'
GROUP BY company_name;

