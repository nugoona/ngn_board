-- ✅ daily_cafe24_sales 테이블에 2026-01-02 데이터 확인
SELECT 
    payment_date,
    company_name,
    total_orders,
    total_payment,
    total_refund_amount,
    net_sales,
    updated_at
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE payment_date = '2026-01-02'
  AND LOWER(company_name) = 'piscess';

-- ✅ 만약 total_refund_amount가 0이면, 수정된 로직으로 재수집 필요
-- recover_2026_01_data.py를 실행하거나, 수동으로 2026-01-02만 재수집

