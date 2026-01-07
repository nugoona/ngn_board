-- ✅ 시간대 이슈 확인 쿼리

-- 1. cafe24_refunds_table의 refund_date 타입 및 원본 값 확인
SELECT 
    refund_date,
    TYPEOF(refund_date) AS refund_date_type,
    TIMESTAMP(refund_date) AS refund_date_as_timestamp,
    DATETIME(TIMESTAMP(refund_date), 'Asia/Seoul') AS refund_date_kst_datetime,
    DATE(DATETIME(TIMESTAMP(refund_date), 'Asia/Seoul')) AS refund_date_kst_date,
    total_refund_amount
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table`
WHERE mall_id = 'piscess1'
  AND (
    DATE(DATETIME(TIMESTAMP(refund_date), 'Asia/Seoul')) = '2025-12-31'
    OR DATE(DATETIME(TIMESTAMP(refund_date), 'Asia/Seoul')) = '2026-01-01'
  )
ORDER BY refund_date
LIMIT 10;

-- 2. 12월 31일 자정 근처 환불 데이터 확인 (시간대 경계 이슈)
SELECT 
    refund_date,
    TIMESTAMP(refund_date) AS refund_date_utc,
    DATETIME(TIMESTAMP(refund_date), 'Asia/Seoul') AS refund_date_kst,
    DATE(DATETIME(TIMESTAMP(refund_date), 'Asia/Seoul')) AS refund_date_kst_date,
    TIME(DATETIME(TIMESTAMP(refund_date), 'Asia/Seoul')) AS refund_date_kst_time,
    total_refund_amount
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table`
WHERE mall_id = 'piscess1'
  AND (
    DATE(DATETIME(TIMESTAMP(refund_date), 'Asia/Seoul')) BETWEEN '2025-12-30' AND '2026-01-01'
  )
ORDER BY refund_date;

-- 3. daily_cafe24_sales에 저장된 payment_date 타입 확인
SELECT 
    payment_date,
    TYPEOF(payment_date) AS payment_date_type,
    DATE(payment_date) AS payment_date_as_date,
    COUNT(*) AS row_count
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE payment_date >= '2025-12-30'
  AND payment_date <= '2026-01-01'
  AND LOWER(company_name) = 'piscess'
GROUP BY payment_date, payment_date_type
ORDER BY payment_date;

-- 4. refund_date KST 변환 전후 비교 (경계일 확인)
SELECT 
    '2025-12-31 23:00 KST' AS test_case,
    TIMESTAMP('2025-12-31 23:00:00+09:00') AS original_kst,
    DATETIME(TIMESTAMP('2025-12-31 23:00:00+09:00'), 'Asia/Seoul') AS converted_datetime,
    DATE(DATETIME(TIMESTAMP('2025-12-31 23:00:00+09:00'), 'Asia/Seoul')) AS converted_date
UNION ALL
SELECT 
    '2025-12-31 23:59 KST' AS test_case,
    TIMESTAMP('2025-12-31 23:59:59+09:00') AS original_kst,
    DATETIME(TIMESTAMP('2025-12-31 23:59:59+09:00'), 'Asia/Seoul') AS converted_datetime,
    DATE(DATETIME(TIMESTAMP('2025-12-31 23:59:59+09:00'), 'Asia/Seoul')) AS converted_date
UNION ALL
SELECT 
    '2026-01-01 00:00 KST' AS test_case,
    TIMESTAMP('2026-01-01 00:00:00+09:00') AS original_kst,
    DATETIME(TIMESTAMP('2026-01-01 00:00:00+09:00'), 'Asia/Seoul') AS converted_datetime,
    DATE(DATETIME(TIMESTAMP('2026-01-01 00:00:00+09:00'), 'Asia/Seoul')) AS converted_date
UNION ALL
SELECT 
    '2025-12-31 14:00 UTC (23:00 KST)' AS test_case,
    TIMESTAMP('2025-12-31 14:00:00Z') AS original_utc,
    DATETIME(TIMESTAMP('2025-12-31 14:00:00Z'), 'Asia/Seoul') AS converted_datetime,
    DATE(DATETIME(TIMESTAMP('2025-12-31 14:00:00Z'), 'Asia/Seoul')) AS converted_date;

