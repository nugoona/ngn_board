-- ============================================
-- 스냅샷 JSON 구조 확인
-- ============================================
-- 실제 JSON 구조를 확인하여 올바른 경로 찾기
-- ============================================

SELECT 
  company_name,
  month,
  updated_at,
  -- JSON 전체 구조 확인
  TO_JSON_STRING(snapshot_json) AS full_json,
  -- period 확인
  JSON_EXTRACT(snapshot_json, '$.period') AS period_json,
  -- data.mall_sales 확인
  JSON_EXTRACT(snapshot_json, '$.data.mall_sales') AS mall_sales_json,
  -- data.meta_ads 확인
  JSON_EXTRACT(snapshot_json, '$.data.meta_ads') AS meta_ads_json,
  -- data.ga4_traffic 확인
  JSON_EXTRACT(snapshot_json, '$.data.ga4_traffic') AS ga4_traffic_json,
  -- comparisons 확인
  JSON_EXTRACT(snapshot_json, '$.data.comparisons') AS comparisons_json
FROM `winged-precept-443218-v8.ngn_dataset.report_monthly_snapshot`
WHERE company_name = 'piscess' 
  AND month = DATE('2025-12-01')
ORDER BY updated_at DESC
LIMIT 1;

