-- 2025년 8월 파이시스 기본 데이터 존재 여부 확인 (daily_cafe24_sales, ga4_traffic_ngn, ga4_viewitem_ngn)
-- performance_summary_ngn 생성에 필요한 기본 데이터가 있는지 확인

WITH base_data AS (
  -- daily_cafe24_sales에서 파이시스 데이터
  SELECT DISTINCT 
    DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) AS date,
    'daily_cafe24_sales' AS source_table
  FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
  WHERE LOWER(company_name) = 'piscess'
    AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) >= DATE('2025-08-02')
    AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) <= DATE('2025-08-09')
  
  UNION DISTINCT
  
  -- ga4_traffic_ngn에서 파이시스 데이터
  SELECT DISTINCT 
    DATE(DATETIME(TIMESTAMP(event_date), 'Asia/Seoul')) AS date,
    'ga4_traffic_ngn' AS source_table
  FROM `winged-precept-443218-v8.ngn_dataset.ga4_traffic_ngn`
  WHERE LOWER(company_name) = 'piscess'
    AND DATE(DATETIME(TIMESTAMP(event_date), 'Asia/Seoul')) >= DATE('2025-08-02')
    AND DATE(DATETIME(TIMESTAMP(event_date), 'Asia/Seoul')) <= DATE('2025-08-09')
  
  UNION DISTINCT
  
  -- ga4_viewitem_ngn에서 파이시스 데이터
  SELECT DISTINCT 
    DATE(DATETIME(TIMESTAMP(event_date), 'Asia/Seoul')) AS date,
    'ga4_viewitem_ngn' AS source_table
  FROM `winged-precept-443218-v8.ngn_dataset.ga4_viewitem_ngn`
  WHERE LOWER(company_name) = 'piscess'
    AND DATE(DATETIME(TIMESTAMP(event_date), 'Asia/Seoul')) >= DATE('2025-08-02')
    AND DATE(DATETIME(TIMESTAMP(event_date), 'Asia/Seoul')) <= DATE('2025-08-09')
)
SELECT
  date,
  COUNT(DISTINCT source_table) AS source_count,
  STRING_AGG(DISTINCT source_table, ', ' ORDER BY source_table) AS source_tables
FROM base_data
GROUP BY date
ORDER BY date;

