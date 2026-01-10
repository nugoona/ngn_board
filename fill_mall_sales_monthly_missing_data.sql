-- ============================================
-- mall_sales_monthly 누락 데이터 채우기
-- ============================================
-- 1. piscess: 2024-12-01 ~ 2024-12-31 데이터 채우기
-- 2. demo: 2024-12-01 ~ 2025-04-30 데이터 채우기
-- MERGE 사용하여 중복 방지
-- ============================================

-- ============================================
-- 1. piscess의 2024-12 데이터 채우기 (2024-12-01 ~ 2024-12-31)
-- ============================================
MERGE `winged-precept-443218-v8.ngn_dataset.mall_sales_monthly` T
USING (
  SELECT
    company_name,
    DATE_TRUNC(payment_date, MONTH) AS month_date,
    CAST(SUM(net_sales) AS NUMERIC) AS net_sales,
    SUM(total_orders) AS total_orders,
    SUM(total_first_order) AS total_first_order,
    SUM(total_canceled) AS total_canceled,
    CURRENT_TIMESTAMP() AS updated_at
  FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
  WHERE company_name = 'piscess'
    AND payment_date >= '2024-12-01'
    AND payment_date < '2025-01-01'
  GROUP BY company_name, month_date
) S
ON T.company_name = S.company_name AND T.month_date = S.month_date
WHEN MATCHED THEN UPDATE SET
  net_sales=S.net_sales,
  total_orders=S.total_orders,
  total_first_order=S.total_first_order,
  total_canceled=S.total_canceled,
  updated_at=S.updated_at
WHEN NOT MATCHED THEN INSERT (
  company_name, month_date, net_sales, total_orders, total_first_order, total_canceled, updated_at
) VALUES (
  S.company_name, S.month_date, S.net_sales, S.total_orders, S.total_first_order, S.total_canceled, S.updated_at
);

-- ============================================
-- 2. demo의 2024-12-01 ~ 2025-04-30 데이터 채우기
-- ============================================
MERGE `winged-precept-443218-v8.ngn_dataset.mall_sales_monthly` T
USING (
  SELECT
    company_name,
    DATE_TRUNC(payment_date, MONTH) AS month_date,
    CAST(SUM(net_sales) AS NUMERIC) AS net_sales,
    SUM(total_orders) AS total_orders,
    SUM(total_first_order) AS total_first_order,
    SUM(total_canceled) AS total_canceled,
    CURRENT_TIMESTAMP() AS updated_at
  FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
  WHERE company_name = 'demo'
    AND payment_date >= '2024-12-01'
    AND payment_date < '2025-05-01'
  GROUP BY company_name, month_date
) S
ON T.company_name = S.company_name AND T.month_date = S.month_date
WHEN MATCHED THEN UPDATE SET
  net_sales=S.net_sales,
  total_orders=S.total_orders,
  total_first_order=S.total_first_order,
  total_canceled=S.total_canceled,
  updated_at=S.updated_at
WHEN NOT MATCHED THEN INSERT (
  company_name, month_date, net_sales, total_orders, total_first_order, total_canceled, updated_at
) VALUES (
  S.company_name, S.month_date, S.net_sales, S.total_orders, S.total_first_order, S.total_canceled, S.updated_at
);

-- ============================================
-- 3. 확인 쿼리: 채워진 데이터 확인
-- ============================================
SELECT 
  company_name,
  month_date,
  net_sales,
  total_orders,
  total_first_order,
  total_canceled,
  updated_at
FROM `winged-precept-443218-v8.ngn_dataset.mall_sales_monthly`
WHERE company_name IN ('piscess', 'demo')
  AND (
    (company_name = 'piscess' AND month_date >= '2024-12-01' AND month_date < '2025-01-01')
    OR (company_name = 'demo' AND month_date >= '2024-12-01' AND month_date < '2025-05-01')
  )
ORDER BY company_name, month_date;
