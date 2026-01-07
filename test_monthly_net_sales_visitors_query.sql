-- ✅ monthly_net_sales_visitors 쿼리 테스트 (수정된 버전)
-- piscess 단일 회사 기준

WITH
  monthly_sales AS (
    SELECT
      company_name,
      FORMAT_DATE('%Y-%m', payment_date) AS month,
      SUM(net_sales) AS net_sales
    FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
    WHERE payment_date BETWEEN DATE_SUB(DATE_TRUNC(CURRENT_DATE(), MONTH), INTERVAL 13 MONTH)
                         AND CURRENT_DATE()
      AND LOWER(company_name) = 'piscess'
      AND company_name IS NOT NULL
    GROUP BY company_name, month
    HAVING SUM(net_sales) > 0
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
ORDER BY s.month ASC;

-- ✅ HAVING 조건 없이 확인 (모든 월 표시)
WITH
  monthly_sales_all AS (
    SELECT
      company_name,
      FORMAT_DATE('%Y-%m', payment_date) AS month,
      SUM(net_sales) AS net_sales,
      COUNT(*) AS day_count
    FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
    WHERE payment_date BETWEEN DATE_SUB(DATE_TRUNC(CURRENT_DATE(), MONTH), INTERVAL 13 MONTH)
                         AND CURRENT_DATE()
      AND LOWER(company_name) = 'piscess'
      AND company_name IS NOT NULL
    GROUP BY company_name, month
  )
SELECT
  company_name,
  month AS date,
  net_sales,
  day_count,
  CASE WHEN net_sales > 0 THEN '포함됨' ELSE '제외됨 (HAVING 조건)' END AS status
FROM monthly_sales_all
ORDER BY month ASC;

