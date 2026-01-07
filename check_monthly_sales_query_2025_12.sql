-- ✅ 월별 차트 쿼리 디버깅: 2025년 12월 piscess 데이터 확인

-- 1. daily_cafe24_sales 테이블의 2025년 12월 원본 데이터 확인
SELECT
  payment_date,
  company_name,
  total_payment,
  total_refund_amount,
  (total_payment - total_refund_amount) AS net_sales
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE payment_date >= '2025-12-01'
  AND payment_date <= '2025-12-31'
  AND LOWER(company_name) = 'piscess'
ORDER BY payment_date;

-- 2. 월별 집계 (monthly_sales CTE와 동일한 로직)
SELECT
  company_name,
  FORMAT_DATE('%Y-%m', payment_date) AS month,
  SUM(net_sales) AS net_sales,
  SUM(total_payment) AS total_payment,
  SUM(total_refund_amount) AS total_refund_amount
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE payment_date BETWEEN DATE_SUB(DATE_TRUNC(CURRENT_DATE(), MONTH), INTERVAL 13 MONTH)
                       AND CURRENT_DATE()
  AND LOWER(company_name) = 'piscess'
  AND net_sales > 0
  AND company_name IS NOT NULL
GROUP BY company_name, month
HAVING month = '2025-12'
ORDER BY month;

-- 3. net_sales > 0 조건 없이 집계 (음수 포함)
SELECT
  company_name,
  FORMAT_DATE('%Y-%m', payment_date) AS month,
  SUM(net_sales) AS net_sales,
  SUM(total_payment) AS total_payment,
  SUM(total_refund_amount) AS total_refund_amount,
  COUNT(*) AS row_count
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE payment_date >= '2025-12-01'
  AND payment_date <= '2025-12-31'
  AND LOWER(company_name) = 'piscess'
  AND company_name IS NOT NULL
GROUP BY company_name, month
ORDER BY month;

-- 4. daily_cafe24_sales의 2025-12 전체 합계 (쿼리와 비교)
SELECT
  'daily_cafe24_sales_total' AS source,
  SUM(total_payment) AS total_payment,
  SUM(total_refund_amount) AS total_refund_amount,
  SUM(net_sales) AS net_sales,
  COUNT(*) AS row_count,
  COUNT(DISTINCT payment_date) AS distinct_dates
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE payment_date >= '2025-12-01'
  AND payment_date <= '2025-12-31'
  AND LOWER(company_name) = 'piscess';

-- 5. 월별 차트 쿼리와 동일한 로직 (완전 재현)
WITH
  monthly_sales AS (
    SELECT
      company_name,
      FORMAT_DATE('%Y-%m', payment_date) AS month,
      SUM(net_sales) AS net_sales
    FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
    WHERE payment_date BETWEEN DATE_SUB(DATE_TRUNC(CURRENT_DATE(), MONTH), INTERVAL 13 MONTH)
                         AND CURRENT_DATE()
      AND net_sales > 0
      AND company_name IS NOT NULL
    GROUP BY company_name, month
  ),
  monthly_traffic AS (
    SELECT
      company_name,
      FORMAT_DATE('%Y-%m', event_date) AS month,
      SUM(total_users) AS total_visitors
    FROM `winged-precept-443218-v8.ngn_dataset.ga4_traffic_ngn`
    WHERE event_date BETWEEN DATE_SUB(DATE_TRUNC(CURRENT_DATE(), MONTH), INTERVAL 13 MONTH)
                       AND CURRENT_DATE()
      AND total_users > 0
      AND company_name IS NOT NULL
      AND (first_user_source != '(not set)' AND first_user_source != 'not set' AND first_user_source IS NOT NULL)
    GROUP BY company_name, month
  )
SELECT
  s.company_name,
  s.month AS date,
  s.net_sales,
  COALESCE(t.total_visitors, 0) AS total_visitors
FROM monthly_sales s
LEFT JOIN monthly_traffic t
  ON s.company_name = t.company_name
  AND s.month = t.month
WHERE LOWER(s.company_name) = 'piscess'
  AND s.net_sales > 0
  AND s.month = '2025-12'
ORDER BY s.month ASC;

