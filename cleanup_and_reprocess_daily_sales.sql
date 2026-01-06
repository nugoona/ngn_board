-- ============================================
-- daily_cafe24_sales 테이블 정리 및 재처리 가이드
-- ============================================

-- ============================================
-- Step 1: 비정상적인 환불 금액이 있는 데이터 확인
-- ============================================
-- 환불 금액이 50만원 이상인 경우 확인 (임계값은 조정 가능)

SELECT 
    payment_date,
    company_name,
    total_payment,
    total_refund_amount,
    net_sales,
    total_orders,
    updated_at
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE total_refund_amount > 500000  -- 50만원 이상
ORDER BY payment_date DESC, total_refund_amount DESC;

-- 전체 통계
SELECT 
    COUNT(*) AS error_record_count,
    MIN(total_refund_amount) AS min_refund,
    MAX(total_refund_amount) AS max_refund,
    AVG(total_refund_amount) AS avg_refund
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE total_refund_amount > 500000;

-- ============================================
-- Step 2: 특정 날짜 범위 삭제 (예: 최근 며칠)
-- ============================================
-- 예: 2025-12-10 이후의 데이터를 재처리하고 싶은 경우

-- Step 2-1: 삭제할 데이터 확인
SELECT 
    DATE(payment_date) AS payment_date,
    company_name,
    COUNT(*) AS record_count,
    SUM(total_refund_amount) AS total_refund_sum,
    AVG(total_refund_amount) AS avg_refund
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE DATE(payment_date) >= '2025-12-10'
GROUP BY payment_date, company_name
ORDER BY payment_date DESC, total_refund_sum DESC;

-- Step 2-2: 실제 삭제 (확인 후 실행)
-- DELETE FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
-- WHERE DATE(payment_date) >= '2025-12-10';

-- ============================================
-- Step 3: 특정 업체의 특정 날짜 삭제
-- ============================================

-- Step 3-1: piscess의 2025-12-23 데이터 삭제 확인
SELECT 
    payment_date,
    company_name,
    total_payment,
    total_refund_amount,
    net_sales
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE DATE(payment_date) = '2025-12-23'
  AND LOWER(company_name) = 'piscess';

-- Step 3-2: 실제 삭제
-- DELETE FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
-- WHERE DATE(payment_date) = '2025-12-23'
--   AND LOWER(company_name) = 'piscess';

-- ============================================
-- Step 4: 비정상적인 환불 금액만 선택적으로 삭제
-- ============================================
-- 환불 금액이 비정상적으로 큰 경우만 삭제

-- Step 4-1: 삭제할 데이터 확인
SELECT 
    payment_date,
    company_name,
    total_payment,
    total_refund_amount,
    net_sales,
    total_orders
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE total_refund_amount > 500000  -- 50만원 이상
ORDER BY total_refund_amount DESC;

-- Step 4-2: 실제 삭제 (확인 후 실행)
-- DELETE FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
-- WHERE total_refund_amount > 500000;














