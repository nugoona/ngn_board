-- ✅ 환불 금액 비교: refund_date 기준 vs payment_date 기준
WITH refund_date_based AS (
    -- refund_date 기준 12월 환불 (중복 제거)
    SELECT
        DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) AS refund_date_kst,
        r.refund_code,
        MAX(r.total_refund_amount) AS total_refund_amount
    FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
    WHERE r.mall_id = 'piscess1'
      AND DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) >= '2025-12-01'
      AND DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) <= '2025-12-31'
    GROUP BY refund_date_kst, r.refund_code
),
payment_date_based AS (
    -- payment_date 기준 12월 환불 (중복 제거)
    SELECT
        DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) AS payment_date_kst,
        r.refund_code,
        MAX(r.total_refund_amount) AS total_refund_amount
    FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
    JOIN `winged-precept-443218-v8.ngn_dataset.cafe24_orders` o
        ON r.order_id = o.order_id AND r.mall_id = o.mall_id
    WHERE r.mall_id = 'piscess1'
      AND DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) >= '2025-12-01'
      AND DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) <= '2025-12-31'
    GROUP BY payment_date_kst, r.refund_code
),
daily_sales_value AS (
    -- daily_cafe24_sales에 저장된 값
    SELECT 
        payment_date,
        SUM(total_refund_amount) AS total_refund_amount
    FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
    WHERE payment_date >= '2025-12-01'
      AND payment_date <= '2025-12-31'
      AND LOWER(company_name) = 'piscess'
    GROUP BY payment_date
)
SELECT 
    'refund_date 기준 12월' AS criteria,
    SUM(total_refund_amount) AS total_refund_amount,
    COUNT(DISTINCT refund_code) AS unique_refund_codes
FROM refund_date_based

UNION ALL

SELECT 
    'payment_date 기준 12월' AS criteria,
    SUM(total_refund_amount) AS total_refund_amount,
    COUNT(DISTINCT refund_code) AS unique_refund_codes
FROM payment_date_based

UNION ALL

SELECT 
    'daily_cafe24_sales 저장값' AS criteria,
    SUM(total_refund_amount) AS total_refund_amount,
    NULL AS unique_refund_codes
FROM daily_sales_value;

