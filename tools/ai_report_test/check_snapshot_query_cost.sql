-- ============================================
-- 스냅샷 생성 시 쿼리 비용 확인
-- ============================================
-- 최근 1시간 동안의 쿼리 중 스냅샷 관련 쿼리만 필터링
-- ============================================

-- 1. 최근 1시간 동안의 모든 쿼리 요약
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

-- 2. 스냅샷 관련 쿼리만 필터링 (mall_sales_monthly, meta_ads_monthly, ga4_traffic_monthly 등)
SELECT 
  job_id,
  creation_time,
  user_email,
  total_bytes_processed / 1024.0 / 1024.0 / 1024.0 / 1024.0 AS total_tb,
  (total_bytes_processed / 1024.0 / 1024.0 / 1024.0 / 1024.0) * 5.0 AS estimated_cost_usd,
  -- 쿼리에서 테이블명 추출
  CASE 
    WHEN query LIKE '%mall_sales_monthly%' THEN 'mall_sales_monthly'
    WHEN query LIKE '%meta_ads_monthly%' THEN 'meta_ads_monthly'
    WHEN query LIKE '%ga4_traffic_monthly%' THEN 'ga4_traffic_monthly'
    WHEN query LIKE '%daily_cafe24_sales%' THEN 'daily_cafe24_sales'
    WHEN query LIKE '%meta_ads_account_summary%' THEN 'meta_ads_account_summary'
    WHEN query LIKE '%ga4_traffic_ngn%' THEN 'ga4_traffic_ngn'
    WHEN query LIKE '%performance_summary_ngn%' THEN 'performance_summary_ngn'
    WHEN query LIKE '%report_monthly_snapshot%' THEN 'report_monthly_snapshot'
    ELSE 'other'
  END AS table_type,
  SUBSTR(query, 1, 200) AS query_preview
FROM `region-asia-northeast1.INFORMATION_SCHEMA.JOBS_BY_PROJECT`
WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
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
ORDER BY creation_time DESC;

-- 3. 테이블별 집계 비용
SELECT 
  CASE 
    WHEN query LIKE '%mall_sales_monthly%' THEN 'mall_sales_monthly'
    WHEN query LIKE '%meta_ads_monthly%' THEN 'meta_ads_monthly'
    WHEN query LIKE '%ga4_traffic_monthly%' THEN 'ga4_traffic_monthly'
    WHEN query LIKE '%daily_cafe24_sales%' THEN 'daily_cafe24_sales'
    WHEN query LIKE '%meta_ads_account_summary%' THEN 'meta_ads_account_summary'
    WHEN query LIKE '%ga4_traffic_ngn%' THEN 'ga4_traffic_ngn'
    WHEN query LIKE '%performance_summary_ngn%' THEN 'performance_summary_ngn'
    WHEN query LIKE '%report_monthly_snapshot%' THEN 'report_monthly_snapshot'
    ELSE 'other'
  END AS table_type,
  COUNT(*) AS query_count,
  SUM(total_bytes_processed) / 1024.0 / 1024.0 / 1024.0 / 1024.0 AS total_tb,
  SUM(total_bytes_processed / 1024.0 / 1024.0 / 1024.0 / 1024.0) * 5.0 AS total_estimated_cost_usd,
  AVG(total_bytes_processed) / 1024.0 / 1024.0 / 1024.0 / 1024.0 AS avg_tb_per_query
FROM `region-asia-northeast1.INFORMATION_SCHEMA.JOBS_BY_PROJECT`
WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
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

