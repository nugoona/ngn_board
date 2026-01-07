-- ✅ 환불 데이터 변화 확인

-- 1. refund_date 원본 값과 KST 변환 확인
SELECT 
    refund_date,
    TYPEOF(refund_date) AS refund_date_type,
    TIMESTAMP(refund_date) AS refund_date_utc,
    DATETIME(TIMESTAMP(refund_date), 'Asia/Seoul') AS refund_date_kst_datetime,
    DATE(DATETIME(TIMESTAMP(refund_date), 'Asia/Seoul')) AS refund_date_kst_date,
    refund_code,
    total_refund_amount
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table`
WHERE mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(refund_date), 'Asia/Seoul')) BETWEEN '2025-12-01' AND '2025-12-31'
ORDER BY refund_date
LIMIT 20;

-- 2. refund_date KST 기준 일자별 환불 합계 (refund_code별 중복 제거)
WITH refund_by_code AS (
    SELECT
        DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) AS refund_date_kst,
        r.refund_code,
        MAX(r.total_refund_amount) AS total_refund_amount
    FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
    WHERE r.mall_id = 'piscess1'
      AND DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) BETWEEN '2025-12-01' AND '2025-12-31'
    GROUP BY refund_date_kst, r.refund_code
)
SELECT 
    refund_date_kst,
    COUNT(DISTINCT refund_code) AS unique_refund_codes,
    SUM(total_refund_amount) AS total_refund_amount
FROM refund_by_code
GROUP BY refund_date_kst
ORDER BY refund_date_kst;

-- 3. daily_cafe24_sales에 저장된 환불 데이터 확인
SELECT 
    payment_date,
    company_name,
    total_refund_amount
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE payment_date BETWEEN '2025-12-01' AND '2025-12-31'
  AND LOWER(company_name) = 'piscess'
ORDER BY payment_date;

-- 4. 환불 데이터 합계 비교 (원본 vs daily_cafe24_sales)
WITH refund_source AS (
    SELECT
        DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) AS refund_date_kst,
        r.refund_code,
        MAX(r.total_refund_amount) AS total_refund_amount
    FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
    WHERE r.mall_id = 'piscess1'
      AND DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) BETWEEN '2025-12-01' AND '2025-12-31'
    GROUP BY refund_date_kst, r.refund_code
),
refund_source_total AS (
    SELECT SUM(total_refund_amount) AS total_refund
    FROM refund_source
),
sales_refund_total AS (
    SELECT SUM(total_refund_amount) AS total_refund
    FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
    WHERE payment_date BETWEEN '2025-12-01' AND '2025-12-31'
      AND LOWER(company_name) = 'piscess'
)
SELECT 
    '원본 환불 합계 (refund_code 중복 제거)' AS source,
    r.total_refund AS amount
FROM refund_source_total r
UNION ALL
SELECT 
    'daily_cafe24_sales 환불 합계' AS source,
    s.total_refund AS amount
FROM sales_refund_total s;

-- 5. 일자별 환불 비교 (어느 날짜가 차이가 나는지)
WITH refund_source_daily AS (
    SELECT
        DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) AS refund_date_kst,
        r.refund_code,
        MAX(r.total_refund_amount) AS total_refund_amount
    FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
    WHERE r.mall_id = 'piscess1'
      AND DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) BETWEEN '2025-12-01' AND '2025-12-31'
    GROUP BY refund_date_kst, r.refund_code
),
refund_source_summary AS (
    SELECT 
        refund_date_kst AS refund_date,
        SUM(total_refund_amount) AS total_refund_amount
    FROM refund_source_daily
    GROUP BY refund_date_kst
),
sales_refund_summary AS (
    SELECT 
        payment_date AS refund_date,
        SUM(total_refund_amount) AS total_refund_amount
    FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
    WHERE payment_date BETWEEN '2025-12-01' AND '2025-12-31'
      AND LOWER(company_name) = 'piscess'
    GROUP BY payment_date
)
SELECT 
    COALESCE(r.refund_date, s.refund_date) AS date,
    COALESCE(r.total_refund_amount, 0) AS refund_in_source,
    COALESCE(s.total_refund_amount, 0) AS refund_in_sales,
    COALESCE(r.total_refund_amount, 0) - COALESCE(s.total_refund_amount, 0) AS refund_diff
FROM refund_source_summary r
FULL OUTER JOIN sales_refund_summary s ON r.refund_date = s.refund_date
WHERE COALESCE(r.total_refund_amount, 0) != COALESCE(s.total_refund_amount, 0)
ORDER BY date;

