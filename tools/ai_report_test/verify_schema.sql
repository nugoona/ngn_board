-- ============================================
-- ga4_traffic_monthly 테이블 스키마 확인
-- ============================================
-- add_to_cart_users, sign_up_users 컬럼이 있는지 확인
-- ============================================

SELECT 
  column_name,
  data_type,
  is_nullable
FROM `winged-precept-443218-v8.ngn_dataset.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = 'ga4_traffic_monthly'
ORDER BY ordinal_position;

