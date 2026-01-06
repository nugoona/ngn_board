-- ============================================
-- daily_cafe24_sales 테이블 오류 데이터 확인 및 삭제
-- ============================================
-- 환불 금액이 비정상적으로 큰 경우를 찾아서 삭제

-- ============================================
-- Step 1: 비정상적인 환불 금액 확인
-- ============================================
-- 환불 금액이 100만원 이상인 경우를 확인 (임계값은 조정 가능)

SELECT 
    payment_date,
    company_name,
    total_payment,
    total_refund_amount,
    net_sales,
    total_orders,
    updated_at
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE total_refund_amount > 1000000  -- 100만원 이상
ORDER BY total_refund_amount DESC;

-- 또는 특정 날짜 범위만 확인
SELECT 
    payment_date,
    company_name,
    total_payment,
    total_refund_amount,
    net_sales,
    total_orders,
    updated_at
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE DATE(payment_date) >= '2025-12-10'
  AND total_refund_amount > 500000  -- 50만원 이상
ORDER BY payment_date DESC, total_refund_amount DESC;

-- ============================================
-- Step 2: 특정 날짜 범위 삭제 (필요시)
-- ============================================
-- 예: 2025-12-10 이후의 데이터를 모두 재처리하고 싶은 경우

-- Step 2-1: 삭제할 데이터 확인
SELECT 
    DATE(payment_date) AS payment_date,
    company_name,
    COUNT(*) AS record_count,
    SUM(total_refund_amount) AS total_refund_sum
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE DATE(payment_date) >= '2025-12-10'
GROUP BY payment_date, company_name
ORDER BY payment_date DESC;

-- Step 2-2: 실제 삭제 (확인 후 실행)
-- DELETE FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
-- WHERE DATE(payment_date) >= '2025-12-10';

-- ============================================
-- Step 3: 특정 업체의 특정 날짜 삭제
-- ============================================
-- 예: piscess의 2025-12-23 데이터만 삭제

-- Step 3-1: 삭제할 데이터 확인
SELECT 
    payment_date,
    company_name,
    total_payment,
    total_refund_amount,
    net_sales
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE DATE(payment_date) = '2025-12-23'
  AND LOWER(company_name) = 'piscess';

-- Step 3-2: 실제 삭제 (확인 후 실행)
-- DELETE FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
-- WHERE DATE(payment_date) = '2025-12-23'
--   AND LOWER(company_name) = 'piscess';













