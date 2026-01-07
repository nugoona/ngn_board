-- ✅ 12월 매출 불일치 원인 확인 쿼리

-- 1. daily_cafe24_sales 테이블의 12월 합계 (월별 매출/유입과 동일한 로직)
SELECT
    'daily_cafe24_sales 합계' AS source,
    SUM(net_sales) AS net_sales,
    SUM(total_payment) AS total_payment,
    SUM(total_refund_amount) AS total_refund_amount,
    SUM(total_payment - total_refund_amount) AS calculated_net_sales
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE payment_date >= '2025-12-01'
  AND payment_date <= '2025-12-31'
  AND company_name = 'piscess'
  AND net_sales > 0;

-- 2. performance_summary_new와 동일한 로직 (total_payment > 0 조건 포함)
SELECT
    'performance_summary 로직' AS source,
    SUM(total_payment - total_refund_amount) AS total_revenue,
    SUM(total_orders) AS total_orders
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE payment_date >= '2025-12-01'
  AND payment_date <= '2025-12-31'
  AND company_name = 'piscess'
  AND total_payment > 0;

-- 3. cafe24_service 로직 (기간합과 동일)
SELECT
    'cafe24_service 로직' AS source,
    SUM(total_payment) AS total_payment,
    SUM(total_refund_amount) AS total_refund_amount,
    SUM(total_payment - total_refund_amount) AS net_sales
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE payment_date >= '2025-12-01'
  AND payment_date <= '2025-12-31'
  AND company_name = 'piscess';

-- 4. 일자별 상세 확인
SELECT
    payment_date,
    SUM(net_sales) AS net_sales,
    SUM(total_payment) AS total_payment,
    SUM(total_refund_amount) AS total_refund_amount,
    SUM(total_payment - total_refund_amount) AS calculated_net_sales
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE payment_date >= '2025-12-01'
  AND payment_date <= '2025-12-31'
  AND company_name = 'piscess'
GROUP BY payment_date
ORDER BY payment_date;

-- 5. net_sales와 계산값이 다른 경우 확인
SELECT
    payment_date,
    SUM(net_sales) AS stored_net_sales,
    SUM(total_payment - total_refund_amount) AS calculated_net_sales,
    SUM(total_payment - total_refund_amount) - SUM(net_sales) AS difference
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE payment_date >= '2025-12-01'
  AND payment_date <= '2025-12-31'
  AND company_name = 'piscess'
GROUP BY payment_date
HAVING SUM(net_sales) != SUM(total_payment - total_refund_amount)
ORDER BY payment_date;

