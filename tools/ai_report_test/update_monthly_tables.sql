-- ============================================
-- 월간 집계 테이블 스키마 업데이트
-- ============================================
-- 1단계 최적화를 위해 필요한 컬럼 추가
-- ============================================

-- 1. ga4_traffic_monthly에 add_to_cart_users, sign_up_users 컬럼 추가
ALTER TABLE `winged-precept-443218-v8.ngn_dataset.ga4_traffic_monthly`
ADD COLUMN IF NOT EXISTS add_to_cart_users INT64,
ADD COLUMN IF NOT EXISTS sign_up_users INT64;

-- 컬럼 추가 확인
SELECT 
  column_name, 
  data_type, 
  is_nullable
FROM `winged-precept-443218-v8.ngn_dataset.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = 'ga4_traffic_monthly'
  AND column_name IN ('add_to_cart_users', 'sign_up_users')
ORDER BY ordinal_position;

