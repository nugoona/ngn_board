-- ============================================
-- demo 계정의 performance_summary_ngn 테이블에
-- cart_users와 signup_count 가짜 데이터 생성
-- 2024-12-01 ~ 2026-12-31
-- ============================================

-- ============================================
-- 1. 기존 레코드가 있는 경우: cart_users, signup_count만 UPDATE
--    cart_users가 daily_cafe24_sales의 total_orders보다 크거나 같도록 보장
--    기존 total_purchases가 새로운 cart_users보다 크면 조정
-- ============================================
MERGE `winged-precept-443218-v8.ngn_dataset.performance_summary_ngn` T
USING (
  WITH date_series AS (
    SELECT date_val
    FROM UNNEST(GENERATE_DATE_ARRAY('2024-12-01', '2026-12-31')) AS date_val
  ),
  -- daily_cafe24_sales에서 실제 주문수 조회
  daily_orders AS (
    SELECT
      payment_date AS date,
      COALESCE(SUM(total_orders), 0) AS total_orders
    FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
    WHERE company_name = 'demo'
      AND payment_date >= '2024-12-01'
      AND payment_date <= '2026-12-31'
    GROUP BY payment_date
  ),
  fake_data AS (
    SELECT
      ds.date_val AS date,
      'demo' AS company_name,
      -- 기본 cart_users: 50~500 사이 랜덤 값 (일별 약간의 변동 포함)
      CAST(
        50 + MOD(ABS(FARM_FINGERPRINT(CAST(ds.date_val AS STRING))), 451) + 
        CAST((MOD(ABS(FARM_FINGERPRINT(CAST(ds.date_val AS STRING) || 'cart')), 50) - 25) AS INT64)
      AS INT64) AS base_cart_users,
      -- signup_count: 5~50 사이 랜덤 값 (일별 약간의 변동 포함)
      CAST(
        5 + MOD(ABS(FARM_FINGERPRINT(CAST(ds.date_val AS STRING))), 46) + 
        CAST((MOD(ABS(FARM_FINGERPRINT(CAST(ds.date_val AS STRING) || 'signup')), 20) - 10) AS INT64)
      AS INT64) AS signup_count,
      COALESCE(o.total_orders, 0) AS total_orders
    FROM date_series ds
    LEFT JOIN daily_orders o ON ds.date_val = o.date
  )
  SELECT
    date,
    company_name,
    -- cart_users는 total_orders보다 크거나 같도록 보장 (최소 1.2배, 최대 10배)
    GREATEST(
      base_cart_users,
      CAST(total_orders * 1.2 AS INT64),
      CAST(total_orders + 10 AS INT64)  -- 최소한 주문수보다 10개는 더 많게
    ) AS cart_users,
    signup_count,
    total_orders
  FROM fake_data
) S
ON T.company_name = S.company_name 
  AND DATE(T.date) = S.date
WHEN MATCHED THEN UPDATE SET
  cart_users = S.cart_users,
  signup_count = S.signup_count,
  -- 기존 total_purchases가 새로운 cart_users보다 크면 cart_users의 30%로 제한
  total_purchases = LEAST(COALESCE(T.total_purchases, 0), CAST(S.cart_users * 0.3 AS INT64))
WHEN NOT MATCHED THEN INSERT (
  date, company_name, ad_media, ad_spend, total_clicks, total_purchases,
  total_purchase_value, roas_percentage, avg_cpc, click_through_rate,
  conversion_rate, site_revenue, total_visitors, product_views,
  views_per_visit, ad_spend_ratio, avg_order_value, cart_users,
  signup_count, updated_at
) VALUES (
  S.date, 
  S.company_name, 
  'meta',  -- 기본값
  0.0,     -- ad_spend
  0,       -- total_clicks
  CAST(S.cart_users * 0.15 AS INT64),  -- total_purchases: cart_users의 15% (전환율 15%)
  0.0,     -- total_purchase_value
  0.0,     -- roas_percentage
  0.0,     -- avg_cpc
  0.0,     -- click_through_rate
  0.0,     -- conversion_rate
  0.0,     -- site_revenue
  0,       -- total_visitors
  0,       -- product_views
  0.0,     -- views_per_visit
  0.0,     -- ad_spend_ratio
  0.0,     -- avg_order_value
  S.cart_users,
  S.signup_count,
  FORMAT_TIMESTAMP('%Y-%m-%d-%H-%M', CURRENT_TIMESTAMP(), 'Asia/Seoul')  -- updated_at
);

-- ============================================
-- 2. 확인 쿼리: 생성된 데이터 확인 및 일관성 검증
-- ============================================
-- 일별 데이터 확인 (주문수와 비교)
SELECT 
  p.date,
  p.company_name,
  p.cart_users,
  p.signup_count,
  p.total_purchases,
  COALESCE(d.total_orders, 0) AS daily_total_orders,
  CASE 
    WHEN p.cart_users < COALESCE(d.total_orders, 0) THEN 'WARNING: cart_users < total_orders'
    WHEN p.total_purchases > p.cart_users THEN 'WARNING: total_purchases > cart_users'
    ELSE 'OK'
  END AS consistency_check,
  p.updated_at
FROM `winged-precept-443218-v8.ngn_dataset.performance_summary_ngn` p
LEFT JOIN (
  SELECT
    payment_date AS date,
    SUM(total_orders) AS total_orders
  FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
  WHERE company_name = 'demo'
    AND payment_date >= '2024-12-01'
    AND payment_date <= '2026-12-31'
  GROUP BY payment_date
) d ON DATE(p.date) = d.date
WHERE p.company_name = 'demo'
  AND DATE(p.date) >= '2024-12-01'
  AND DATE(p.date) <= '2026-12-31'
ORDER BY p.date DESC
LIMIT 100;

-- 일관성 문제가 있는 레코드 확인
-- 1. cart_users < total_orders (장바구니수 < 주문수)
SELECT 
  p.date,
  p.company_name,
  p.cart_users,
  COALESCE(d.total_orders, 0) AS total_orders,
  (COALESCE(d.total_orders, 0) - p.cart_users) AS difference
FROM `winged-precept-443218-v8.ngn_dataset.performance_summary_ngn` p
LEFT JOIN (
  SELECT
    payment_date AS date,
    SUM(total_orders) AS total_orders
  FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
  WHERE company_name = 'demo'
    AND payment_date >= '2024-12-01'
    AND payment_date <= '2026-12-31'
  GROUP BY payment_date
) d ON DATE(p.date) = d.date
WHERE p.company_name = 'demo'
  AND DATE(p.date) >= '2024-12-01'
  AND DATE(p.date) <= '2026-12-31'
  AND p.cart_users < COALESCE(d.total_orders, 0)
ORDER BY p.date DESC;

-- 2. total_purchases > cart_users (구매수 > 장바구니수)
SELECT 
  date,
  company_name,
  cart_users,
  total_purchases,
  (total_purchases - cart_users) AS difference
FROM `winged-precept-443218-v8.ngn_dataset.performance_summary_ngn`
WHERE company_name = 'demo'
  AND DATE(date) >= '2024-12-01'
  AND DATE(date) <= '2026-12-31'
  AND total_purchases > cart_users
ORDER BY date DESC;

-- 월별 집계 확인
SELECT 
  DATE_TRUNC(DATE(date), MONTH) AS month_date,
  SUM(cart_users) AS total_cart_users,
  SUM(signup_count) AS total_signup_count,
  AVG(cart_users) AS avg_cart_users,
  AVG(signup_count) AS avg_signup_count
FROM `winged-precept-443218-v8.ngn_dataset.performance_summary_ngn`
WHERE company_name = 'demo'
  AND DATE(date) >= '2024-12-01'
  AND DATE(date) <= '2026-12-31'
GROUP BY month_date
ORDER BY month_date DESC;
