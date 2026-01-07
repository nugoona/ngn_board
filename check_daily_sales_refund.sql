-- ✅ 2026-01 기간 daily_cafe24_sales 테이블의 환불 데이터 확인
SELECT 
    payment_date,
    company_name,
    total_orders,
    total_payment,
    total_refund_amount,
    net_sales
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE payment_date BETWEEN '2026-01-01' AND '2026-01-07'
  AND LOWER(company_name) = 'piscess'
ORDER BY payment_date;

-- ✅ 전체 기간 합계로 확인
SELECT 
    SUM(total_refund_amount) AS total_refund_sum,
    COUNT(*) AS row_count,
    COUNT(CASE WHEN total_refund_amount > 0 THEN 1 END) AS non_zero_refund_count
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE payment_date BETWEEN '2026-01-01' AND '2026-01-07'
  AND LOWER(company_name) = 'piscess';

