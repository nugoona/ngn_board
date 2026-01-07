-- ✅ 2025-12 데이터 삭제 쿼리
-- ⚠️ 주의: 삭제하기 전에 반드시 확인 쿼리를 실행하세요!

-- ============================================
-- Step 0: 삭제할 데이터 확인 (실행 필수!)
-- ============================================

-- 0-1: daily_cafe24_sales의 2025-12 데이터 확인
SELECT 
    payment_date,
    company_name,
    COUNT(*) AS row_count,
    SUM(total_payment) AS total_payment_sum,
    SUM(total_refund_amount) AS total_refund_sum,
    SUM(net_sales) AS net_sales_sum
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE payment_date >= '2025-12-01'
  AND payment_date <= '2025-12-31'
GROUP BY payment_date, company_name
ORDER BY payment_date, company_name;

-- 0-2: 전체 행 수 확인
SELECT COUNT(*) AS total_rows_to_delete
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE payment_date >= '2025-12-01'
  AND payment_date <= '2025-12-31';

-- 0-3: cafe24_refunds_table의 2025-12 데이터 확인 (선택사항)
SELECT 
    DATE(DATETIME(TIMESTAMP(refund_date), 'Asia/Seoul')) AS refund_date_kst,
    mall_id,
    COUNT(*) AS refund_count,
    SUM(total_refund_amount) AS refund_amount_sum
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table`
WHERE DATE(DATETIME(TIMESTAMP(refund_date), 'Asia/Seoul')) >= '2025-12-01'
  AND DATE(DATETIME(TIMESTAMP(refund_date), 'Asia/Seoul')) <= '2025-12-31'
GROUP BY refund_date_kst, mall_id
ORDER BY refund_date_kst, mall_id;

-- ============================================
-- Step 1: daily_cafe24_sales의 2025-12 데이터 삭제
-- ============================================
-- ⚠️ 위의 확인 쿼리 실행 후, 삭제할 데이터가 맞는지 확인한 후 실행하세요!

DELETE FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE payment_date >= '2025-12-01'
  AND payment_date <= '2025-12-31';

-- ============================================
-- Step 2: cafe24_refunds_table의 2025-12 환불 데이터 삭제 (선택사항)
-- ============================================
-- ⚠️ 주의: 
-- - 이 테이블은 MERGE로 중복 방지되므로 삭제 없이 재수집해도 됩니다.
-- - 하지만 완전히 새로 수집하고 싶다면 삭제하세요.
-- - 위의 0-3 확인 쿼리 실행 후 결정하세요.

/*
DELETE FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table`
WHERE DATE(DATETIME(TIMESTAMP(refund_date), 'Asia/Seoul')) >= '2025-12-01'
  AND DATE(DATETIME(TIMESTAMP(refund_date), 'Asia/Seoul')) <= '2025-12-31';
*/

-- ============================================
-- Step 3: performance_summary_ngn의 2025-12 데이터 삭제 (필요시)
-- ============================================
-- ⚠️ 주의: 이 테이블도 재수집 스크립트가 있다면 삭제 후 재수집이 필요할 수 있습니다.

/*
-- 3-1: 확인
SELECT 
    report_date,
    company_name,
    COUNT(*) AS row_count
FROM `winged-precept-443218-v8.ngn_dataset.performance_summary_ngn`
WHERE report_date >= '2025-12-01'
  AND report_date <= '2025-12-31'
GROUP BY report_date, company_name
ORDER BY report_date, company_name;

-- 3-2: 삭제 (확인 후 실행)
DELETE FROM `winged-precept-443218-v8.ngn_dataset.performance_summary_ngn`
WHERE report_date >= '2025-12-01'
  AND report_date <= '2025-12-31';
*/

-- ============================================
-- Step 4: 삭제 후 확인
-- ============================================
-- 삭제가 제대로 되었는지 확인

SELECT COUNT(*) AS remaining_rows
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE payment_date >= '2025-12-01'
  AND payment_date <= '2025-12-31';
-- 결과가 0이어야 정상입니다.

