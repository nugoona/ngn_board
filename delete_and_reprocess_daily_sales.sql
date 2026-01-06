-- ============================================
-- daily_cafe24_sales 오류 데이터 삭제 및 재처리 가이드
-- ============================================

-- ============================================
-- Step 1: 삭제할 레코드 확인 (전체)
-- ============================================
-- 비정상 환불 금액 (50만원 이상) 전체 확인

SELECT 
    payment_date,
    company_name,
    total_payment,
    total_refund_amount,
    net_sales,
    total_orders,
    updated_at
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE total_refund_amount > 500000
ORDER BY payment_date DESC, total_refund_amount DESC;

-- ============================================
-- Step 2: 삭제할 날짜별 통계
-- ============================================

SELECT 
    DATE(payment_date) AS payment_date,
    COUNT(*) AS error_record_count,
    SUM(total_refund_amount) AS total_refund_sum
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE total_refund_amount > 500000
GROUP BY payment_date
ORDER BY payment_date DESC;

-- ============================================
-- Step 3: 실제 삭제 실행
-- ============================================
-- ⚠️ 주의: 이 쿼리는 실제로 데이터를 삭제합니다!
-- Step 1과 Step 2로 확인한 후 실행하세요

DELETE FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE total_refund_amount > 500000;

-- ============================================
-- Step 4: 삭제 후 확인
-- ============================================

-- 50만원 이상 환불 금액이 남아있는지 확인 (결과가 없어야 함)
SELECT 
    COUNT(*) AS remaining_error_records
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE total_refund_amount > 500000;














