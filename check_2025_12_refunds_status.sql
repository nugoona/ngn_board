-- ✅ 1단계: cafe24_refunds_table에 2025-12 환불 데이터가 있는지 확인
SELECT 
    DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) AS refund_date_kst,
    r.mall_id,
    COUNT(*) AS refund_count,
    SUM(r.total_refund_amount) AS total_refund_sum
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
WHERE DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) >= '2025-12-01'
  AND DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) <= '2025-12-31'
GROUP BY refund_date_kst, r.mall_id
ORDER BY refund_date_kst, r.mall_id;

-- ✅ 2단계: daily_cafe24_sales에 2025-12 환불 데이터가 반영되었는지 확인
SELECT 
    payment_date,
    company_name,
    SUM(total_refund_amount) AS total_refund_amount,
    COUNT(*) AS row_count
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE payment_date >= '2025-12-01'
  AND payment_date <= '2025-12-31'
GROUP BY payment_date, company_name
ORDER BY payment_date, company_name;

-- ✅ 3단계: 환불 데이터와 daily_cafe24_sales 비교
-- (원래 주문의 payment_date 기준으로 환불 집계)
WITH refund_by_payment_date AS (
    SELECT
        DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) AS payment_date,
        r.mall_id,
        SUM(r.total_refund_amount) AS refund_amount
    FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
    JOIN `winged-precept-443218-v8.ngn_dataset.cafe24_orders` o
        ON r.order_id = o.order_id AND r.mall_id = o.mall_id
    WHERE DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) >= '2025-12-01'
      AND DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) <= '2025-12-31'
    GROUP BY payment_date, r.mall_id
)
SELECT 
    rpd.payment_date,
    c.company_name,
    rpd.refund_amount AS expected_refund,
    COALESCE(ds.total_refund_amount, 0) AS daily_sales_refund,
    (rpd.refund_amount - COALESCE(ds.total_refund_amount, 0)) AS difference
FROM refund_by_payment_date rpd
JOIN `winged-precept-443218-v8.ngn_dataset.company_info` c
    ON rpd.mall_id = c.mall_id
LEFT JOIN (
    SELECT payment_date, company_name, SUM(total_refund_amount) AS total_refund_amount
    FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
    WHERE payment_date >= '2025-12-01'
      AND payment_date <= '2025-12-31'
    GROUP BY payment_date, company_name
) ds ON rpd.payment_date = ds.payment_date AND c.company_name = ds.company_name
ORDER BY rpd.payment_date, c.company_name;

