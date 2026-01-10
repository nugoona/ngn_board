-- ============================================
-- fill_demo_cart_signup_data.sql 쿼리 실행 전
-- 예상 스캔량 및 비용 확인
-- ============================================

-- 1. daily_cafe24_sales 테이블 크기 확인 (demo 계정, 2024-12-01 ~ 2026-12-31)
SELECT 
  'daily_cafe24_sales' AS table_name,
  COUNT(*) AS row_count,
  SUM(total_orders) AS total_orders_sum,
  -- 대략적인 데이터 크기 추정 (행 수 × 평균 행 크기)
  -- 각 행이 약 500 bytes라고 가정 (보수적 추정)
  COUNT(*) * 500 / 1024.0 / 1024.0 AS estimated_size_mb
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE company_name = 'demo'
  AND payment_date >= '2024-12-01'
  AND payment_date <= '2026-12-31';

-- 2. performance_summary_ngn 테이블 크기 확인 (demo 계정, 2024-12-01 ~ 2026-12-31)
SELECT 
  'performance_summary_ngn' AS table_name,
  COUNT(*) AS row_count,
  -- 각 행이 약 1000 bytes라고 가정 (더 많은 컬럼)
  COUNT(*) * 1000 / 1024.0 / 1024.0 AS estimated_size_mb
FROM `winged-precept-443218-v8.ngn_dataset.performance_summary_ngn`
WHERE company_name = 'demo'
  AND DATE(date) >= '2024-12-01'
  AND DATE(date) <= '2026-12-31';

-- 3. 실제 테이블 크기 확인 (BigQuery 메타데이터)
SELECT
  table_id,
  row_count,
  size_bytes / 1024.0 / 1024.0 AS size_mb,
  size_bytes / 1024.0 / 1024.0 / 1024.0 AS size_gb
FROM `winged-precept-443218-v8.ngn_dataset.__TABLES__`
WHERE table_id IN ('daily_cafe24_sales', 'performance_summary_ngn')
ORDER BY size_bytes DESC;

-- 4. 예상 비용 계산
-- BigQuery 비용: 월 1TB 무료, 이후 $5/TB (약 6,700원/TB)
-- 위 쿼리 결과를 바탕으로:
-- 예상 스캔량: daily_cafe24_sales + performance_summary_ngn
-- 일반적으로 수십 MB ~ 수백 MB 정도
-- 비용: 0원 (무료 할당량 1TB 내)

-- ============================================
-- 실제 실행 후 비용 확인
-- ============================================
-- 쿼리 실행 후, 다음 쿼리로 실제 스캔량 확인:
-- 
-- SELECT 
--   job_id,
--   creation_time,
--   total_bytes_processed / 1024.0 / 1024.0 AS scanned_mb,
--   total_bytes_processed / 1024.0 / 1024.0 / 1024.0 AS scanned_gb,
--   CASE 
--     WHEN total_bytes_processed / 1024.0 / 1024.0 / 1024.0 < 1.0 THEN 0
--     ELSE (total_bytes_processed / 1024.0 / 1024.0 / 1024.0 - 1.0) * 5.0
--   END AS cost_usd,
--   SUBSTR(query, 1, 200) AS query_preview
-- FROM `region-asia-northeast1.INFORMATION_SCHEMA.JOBS_BY_PROJECT`
-- WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 10 MINUTE)
--   AND user_email = SESSION_USER()
-- ORDER BY creation_time DESC
-- LIMIT 10;
