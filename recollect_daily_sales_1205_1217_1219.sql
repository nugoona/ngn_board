-- ✅ 12/5, 12/17, 12/19 daily_cafe24_sales 재수집 쿼리
-- ⚠️ refund_code별로 집계하여 중복 방지

-- 12/5 재수집
CALL `winged-precept-443218-v8.ngn_dataset.sp_recollect_daily_sales`('2025-12-05');

-- 12/17 재수집  
CALL `winged-precept-443218-v8.ngn_dataset.sp_recollect_daily_sales`('2025-12-17');

-- 12/19 재수집
CALL `winged-precept-443218-v8.ngn_dataset.sp_recollect_daily_sales`('2025-12-19');

