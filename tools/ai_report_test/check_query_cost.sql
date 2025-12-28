-- ============================================
-- BigQuery 쿼리 비용 확인 (최근 1시간)
-- ============================================
-- BigQuery 콘솔에서 실행하거나
-- bq query --use_legacy_sql=false < check_query_cost.sql
-- ============================================

-- 최근 1시간 동안의 쿼리 히스토리 확인
SELECT 
  job_id,
  creation_time,
  user_email,
  total_bytes_processed,
  -- TB 단위로 변환
  total_bytes_processed / 1024.0 / 1024.0 / 1024.0 / 1024.0 AS total_tb,
  -- 비용 추정 (TB당 $5)
  (total_bytes_processed / 1024.0 / 1024.0 / 1024.0 / 1024.0) * 5.0 AS estimated_cost_usd,
  -- 쿼리 텍스트 (처음 200자만)
  SUBSTR(query, 1, 200) AS query_preview,
  state,
  total_slot_ms
FROM `region-asia-northeast1.INFORMATION_SCHEMA.JOBS_BY_PROJECT`
WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
  AND state = 'DONE'
  AND job_type = 'QUERY'
  AND total_bytes_processed > 0
ORDER BY creation_time DESC
LIMIT 50;

-- 요약 통계
SELECT 
  COUNT(*) AS total_queries,
  SUM(total_bytes_processed) / 1024.0 / 1024.0 / 1024.0 / 1024.0 AS total_tb,
  SUM(total_bytes_processed / 1024.0 / 1024.0 / 1024.0 / 1024.0) * 5.0 AS total_estimated_cost_usd,
  AVG(total_bytes_processed) / 1024.0 / 1024.0 / 1024.0 / 1024.0 AS avg_tb_per_query
FROM `region-asia-northeast1.INFORMATION_SCHEMA.JOBS_BY_PROJECT`
WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
  AND state = 'DONE'
  AND job_type = 'QUERY'
  AND total_bytes_processed > 0;

