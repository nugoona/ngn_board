-- ============================================
-- monthly_rollup_job.py 원인 분석 쿼리
-- piscess 2025년 12월 데이터 불일치 진단
-- ============================================

-- 1. mall_sales_monthly 테이블: piscess 12월 데이터 확인
--    (월간 집계 테이블 - monthly_rollup_job.py에서 업데이트)
SELECT 
    company_name,
    month_date,
    net_sales,
    total_orders,
    total_first_order,
    total_canceled,
    updated_at,
    TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), updated_at, HOUR) AS hours_since_update
FROM `winged-precept-443218-v8.ngn_dataset.mall_sales_monthly`
WHERE company_name = 'piscess'
  AND month_date >= '2025-12-01'
  AND month_date < '2026-01-01'
ORDER BY month_date DESC;

-- 2. daily_cafe24_sales 테이블: piscess 12월 데이터 범위 확인
--    (일별 raw 데이터 - 실제 데이터 소스)
SELECT 
    MIN(payment_date) AS min_date,
    MAX(payment_date) AS max_date,
    COUNT(DISTINCT payment_date) AS date_count,
    SUM(net_sales) AS total_net_sales,
    SUM(total_orders) AS total_orders,
    SUM(total_first_order) AS total_first_order,
    SUM(total_canceled) AS total_canceled
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE company_name = 'piscess'
  AND payment_date >= '2025-12-01'
  AND payment_date <= '2025-12-31';

-- 3. 일별 데이터 상세 확인 (12월 마지막 5일)
SELECT 
    payment_date,
    SUM(net_sales) AS net_sales,
    SUM(total_orders) AS total_orders,
    SUM(total_first_order) AS total_first_order,
    SUM(total_canceled) AS total_canceled
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE company_name = 'piscess'
  AND payment_date >= '2025-12-01'
  AND payment_date <= '2025-12-31'
GROUP BY payment_date
ORDER BY payment_date DESC
LIMIT 5;

-- 4. mall_sales_monthly vs daily_cafe24_sales 비교
--    (월간 집계 테이블과 일별 데이터 직접 집계 비교)
WITH monthly_agg AS (
    -- mall_sales_monthly 테이블에서 가져온 데이터
    SELECT 
        company_name,
        month_date,
        net_sales AS monthly_net_sales,
        total_orders AS monthly_total_orders,
        total_first_order AS monthly_total_first_order,
        total_canceled AS monthly_total_canceled,
        updated_at AS monthly_updated_at
    FROM `winged-precept-443218-v8.ngn_dataset.mall_sales_monthly`
    WHERE company_name = 'piscess'
      AND month_date = '2025-12-01'
),
daily_agg AS (
    -- daily_cafe24_sales에서 직접 집계한 데이터
    SELECT 
        company_name,
        DATE_TRUNC(payment_date, MONTH) AS month_date,
        CAST(SUM(net_sales) AS NUMERIC) AS daily_net_sales,
        SUM(total_orders) AS daily_total_orders,
        SUM(total_first_order) AS daily_total_first_order,
        SUM(total_canceled) AS daily_total_canceled
    FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
    WHERE company_name = 'piscess'
      AND payment_date >= '2025-12-01'
      AND payment_date <= '2025-12-31'
    GROUP BY company_name, month_date
)
SELECT 
    COALESCE(m.company_name, d.company_name) AS company_name,
    COALESCE(m.month_date, d.month_date) AS month_date,
    -- 월간 집계 테이블 데이터
    m.monthly_net_sales,
    m.monthly_total_orders,
    m.monthly_total_first_order,
    m.monthly_total_canceled,
    m.monthly_updated_at,
    -- 일별 데이터 직접 집계
    d.daily_net_sales,
    d.daily_total_orders,
    d.daily_total_first_order,
    d.daily_total_canceled,
    -- 차이 계산
    COALESCE(d.daily_net_sales, 0) - COALESCE(m.monthly_net_sales, 0) AS net_sales_diff,
    COALESCE(d.daily_total_orders, 0) - COALESCE(m.monthly_total_orders, 0) AS total_orders_diff,
    -- 데이터 존재 여부
    CASE WHEN m.monthly_net_sales IS NOT NULL THEN 'YES' ELSE 'NO' END AS monthly_table_exists,
    CASE WHEN d.daily_net_sales IS NOT NULL THEN 'YES' ELSE 'NO' END AS daily_data_exists
FROM monthly_agg m
FULL OUTER JOIN daily_agg d
    ON m.company_name = d.company_name
    AND m.month_date = d.month_date;

-- 5. 12월 29-31일 데이터만 집계 (누락된 날짜 확인)
SELECT 
    payment_date,
    SUM(net_sales) AS net_sales,
    SUM(total_orders) AS total_orders,
    SUM(total_first_order) AS total_first_order,
    SUM(total_canceled) AS total_canceled
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE company_name = 'piscess'
  AND payment_date >= '2025-12-29'
  AND payment_date <= '2025-12-31'
GROUP BY payment_date
ORDER BY payment_date;

-- 6. monthly_rollup_job 실행 시점 추정
--    (updated_at 기준으로 마지막 업데이트 시간 확인)
SELECT 
    company_name,
    month_date,
    updated_at,
    FORMAT_TIMESTAMP('%Y-%m-%d %H:%M:%S', updated_at) AS updated_at_formatted,
    TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), updated_at, DAY) AS days_since_update
FROM `winged-precept-443218-v8.ngn_dataset.mall_sales_monthly`
WHERE company_name = 'piscess'
  AND month_date >= '2025-11-01'
  AND month_date < '2026-01-01'
ORDER BY month_date DESC, updated_at DESC;

-- 7. prev_month_range 로직 시뮬레이션
--    (12월 28일에 실행했다면 어떤 월을 집계하는지 확인)
--    monthly_rollup_job.py의 prev_month_range 함수 로직:
--    - 12월 28일 실행 시: 11월 데이터 집계 (2025-11-01 ~ 2025-11-30)
--    - 1월 1일 실행 시: 12월 데이터 집계 (2025-12-01 ~ 2025-12-31)
SELECT 
    '2025-12-28' AS execution_date,
    '2025-11-01' AS expected_start_date,
    '2025-11-30' AS expected_end_date,
    '2025-11' AS expected_ym,
    '11월 데이터만 집계됨 (12월은 다음 달에 집계)' AS explanation
UNION ALL
SELECT 
    '2026-01-01' AS execution_date,
    '2025-12-01' AS expected_start_date,
    '2025-12-31' AS expected_end_date,
    '2025-12' AS expected_ym,
    '12월 데이터 집계됨' AS explanation;

-- 8. 결론: 데이터 불일치 원인 확인
--    (mall_sales_monthly에 12월 데이터가 없거나 불완전한 경우)
SELECT 
    CASE 
        WHEN EXISTS (
            SELECT 1 
            FROM `winged-precept-443218-v8.ngn_dataset.mall_sales_monthly`
            WHERE company_name = 'piscess'
              AND month_date = '2025-12-01'
        ) THEN '✅ mall_sales_monthly에 12월 데이터 존재'
        ELSE '❌ mall_sales_monthly에 12월 데이터 없음'
    END AS monthly_table_status,
    CASE 
        WHEN EXISTS (
            SELECT 1 
            FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
            WHERE company_name = 'piscess'
              AND payment_date = '2025-12-31'
        ) THEN '✅ daily_cafe24_sales에 12월 31일 데이터 존재'
        ELSE '❌ daily_cafe24_sales에 12월 31일 데이터 없음'
    END AS daily_table_status,
    '원인: monthly_rollup_job은 전월 데이터만 집계하므로, 12월 28일 실행 시 11월만 집계됨. 12월 데이터는 1월 1일 이후에 집계됨.' AS root_cause;





