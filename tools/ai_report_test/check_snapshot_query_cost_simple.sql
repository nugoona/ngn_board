-- ============================================
-- 스냅샷 생성 시 쿼리 비용 확인 (간단 버전)
-- ============================================
-- 시간 범위를 늘려서 확인
-- ============================================

-- 최근 24시간 동안의 모든 쿼리 요약
SELECT 
  COUNT(*) AS total_queries,
  SUM(total_bytes_processed) / 1024.0 / 1024.0 / 1024.0 / 1024.0 AS total_tb,
  SUM(total_bytes_processed / 1024.0 / 1024.0 / 1024.0 / 1024.0) * 5.0 AS total_estimated_cost_usd,
  AVG(total_bytes_processed) / 1024.0 / 1024.0 / 1024.0 / 1024.0 AS avg_tb_per_query,
  MIN(creation_time) AS earliest_query,
  MAX(creation_time) AS latest_query
FROM `region-asia-northeast1.INFORMATION_SCHEMA.JOBS_BY_PROJECT`
WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
  AND state = 'DONE'
  AND job_type = 'QUERY'
  AND total_bytes_processed > 0;

-- 스냅샷 관련 쿼리만 필터링 (최근 24시간)
SELECT 
  CASE 
    WHEN query LIKE '%mall_sales_monthly%' THEN 'mall_sales_monthly (집계)'
    WHEN query LIKE '%meta_ads_monthly%' THEN 'meta_ads_monthly (집계)'
    WHEN query LIKE '%ga4_traffic_monthly%' THEN 'ga4_traffic_monthly (집계)'
    WHEN query LIKE '%daily_cafe24_sales%' THEN 'daily_cafe24_sales (raw)'
    WHEN query LIKE '%meta_ads_account_summary%' THEN 'meta_ads_account_summary (raw)'
    WHEN query LIKE '%ga4_traffic_ngn%' THEN 'ga4_traffic_ngn (raw)'
    WHEN query LIKE '%performance_summary_ngn%' THEN 'performance_summary_ngn (raw)'
    WHEN query LIKE '%report_monthly_snapshot%' THEN 'report_monthly_snapshot'
    ELSE 'other'
  END AS table_type,
  COUNT(*) AS query_count,
  SUM(total_bytes_processed) / 1024.0 / 1024.0 / 1024.0 / 1024.0 AS total_tb,
  SUM(total_bytes_processed / 1024.0 / 1024.0 / 1024.0 / 1024.0) * 5.0 AS total_estimated_cost_usd,
  AVG(total_bytes_processed) / 1024.0 / 1024.0 / 1024.0 / 1024.0 AS avg_tb_per_query
FROM `region-asia-northeast1.INFORMATION_SCHEMA.JOBS_BY_PROJECT`
WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
  AND state = 'DONE'
  AND job_type = 'QUERY'
  AND total_bytes_processed > 0
  AND (
    query LIKE '%mall_sales_monthly%'
    OR query LIKE '%meta_ads_monthly%'
    OR query LIKE '%ga4_traffic_monthly%'
    OR query LIKE '%daily_cafe24_sales%'
    OR query LIKE '%meta_ads_account_summary%'
    OR query LIKE '%ga4_traffic_ngn%'
    OR query LIKE '%performance_summary_ngn%'
    OR query LIKE '%report_monthly_snapshot%'
  )
GROUP BY table_type
ORDER BY total_estimated_cost_usd DESC;

-- 최근 쿼리 목록 (시간순)
SELECT 
  creation_time,
  total_bytes_processed / 1024.0 / 1024.0 / 1024.0 / 1024.0 AS total_tb,
  (total_bytes_processed / 1024.0 / 1024.0 / 1024.0 / 1024.0) * 5.0 AS estimated_cost_usd,
  SUBSTR(query, 1, 150) AS query_preview
FROM `region-asia-northeast1.INFORMATION_SCHEMA.JOBS_BY_PROJECT`
WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
  AND state = 'DONE'
  AND job_type = 'QUERY'
  AND total_bytes_processed > 0
ORDER BY creation_time DESC
LIMIT 20;


