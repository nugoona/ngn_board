-- ============================================
-- sheets_event_data 테이블 존재 확인
-- ============================================

-- 1. 테이블 존재 여부 확인
SELECT 
  table_name,
  table_type,
  creation_time,
  last_modified_time,
  row_count,
  num_bytes,
  num_long_term_bytes
FROM `winged-precept-443218-v8.ngn_dataset.INFORMATION_SCHEMA.TABLES`
WHERE table_name = 'sheets_event_data';

-- 2. 테이블 스키마 확인
SELECT 
  column_name,
  data_type,
  is_nullable,
  column_default
FROM `winged-precept-443218-v8.ngn_dataset.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = 'sheets_event_data'
ORDER BY ordinal_position;

-- 3. 데이터 확인 (있다면)
SELECT * 
FROM `winged-precept-443218-v8.ngn_dataset.sheets_event_data`
LIMIT 10;

