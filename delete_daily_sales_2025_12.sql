-- ✅ daily_cafe24_sales의 2025-12 데이터 삭제
-- ⚠️ 주의: 삭제 전에 확인하세요!

-- 삭제 전 확인
SELECT 
    payment_date,
    company_name,
    COUNT(*) AS row_count,
    SUM(total_refund_amount) AS total_refund_amount_sum
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE payment_date >= '2025-12-01'
  AND payment_date <= '2025-12-31'
GROUP BY payment_date, company_name
ORDER BY payment_date, company_name;

-- 실제 삭제
DELETE FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE payment_date >= '2025-12-01'
  AND payment_date <= '2025-12-31';

-- 삭제 후 확인 (결과가 없어야 정상)
SELECT COUNT(*) AS remaining_rows
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE payment_date >= '2025-12-01'
  AND payment_date <= '2025-12-31';

