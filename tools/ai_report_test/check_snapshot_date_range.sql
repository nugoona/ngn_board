-- 스냅샷 데이터의 실제 날짜 범위 확인 쿼리
-- piscess 2025년 12월 데이터 확인

-- 1. daily_cafe24_sales 테이블에서 12월 데이터 확인
SELECT 
    MIN(payment_date) AS min_date,
    MAX(payment_date) AS max_date,
    COUNT(DISTINCT payment_date) AS date_count,
    COUNT(*) AS total_rows
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE company_name = 'piscess'
  AND payment_date >= '2025-12-01'
  AND payment_date <= '2025-12-31'
ORDER BY payment_date DESC
LIMIT 10;

-- 2. 일별 매출 데이터의 마지막 날짜 확인
SELECT 
    payment_date,
    SUM(net_sales) AS net_sales,
    SUM(total_orders) AS total_orders
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE company_name = 'piscess'
  AND payment_date >= '2025-12-01'
  AND payment_date <= '2025-12-31'
GROUP BY payment_date
ORDER BY payment_date DESC
LIMIT 10;

-- 3. mall_sales_monthly 테이블에서 12월 집계 확인
SELECT 
    month_date,
    net_sales,
    total_orders,
    total_first_order,
    total_canceled
FROM `winged-precept-443218-v8.ngn_dataset.mall_sales_monthly`
WHERE company_name = 'piscess'
  AND month_date = '2025-12-01'
ORDER BY month_date DESC;

-- 4. GCS 스냅샷 파일의 생성 시간 확인 (스냅샷이 언제 생성되었는지)
-- 이 쿼리는 실행할 수 없으므로, GCS 콘솔에서 확인하거나 gsutil로 확인:
-- gsutil ls -l gs://winged-precept-443218-v8.appspot.com/ai-reports/monthly/piscess/2025-12/snapshot.json.gz





