-- ✅ piscess 2025-12-23 환불 원본 데이터 상세 확인

-- 1. cafe24_refunds_table 원본 데이터 확인
SELECT 
    r.order_id,
    r.mall_id,
    DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) AS refund_date,
    r.total_refund_amount,
    r.refund_code,
    r.refund_status,
    c.company_name,
    COUNT(*) OVER (PARTITION BY r.order_id, r.mall_id) AS duplicate_count
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
JOIN `winged-precept-443218-v8.ngn_dataset.company_info` c
    ON r.mall_id = c.mall_id
WHERE DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) = '2025-12-23'
  AND LOWER(c.company_name) = 'piscess'
ORDER BY r.order_id;

-- 2. order_id별 총합 확인
SELECT 
    r.order_id,
    COUNT(*) AS record_count,
    SUM(r.total_refund_amount) AS total_refund_per_order,
    STRING_AGG(CAST(r.total_refund_amount AS STRING), ', ') AS refund_amounts_list
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
JOIN `winged-precept-443218-v8.ngn_dataset.company_info` c
    ON r.mall_id = c.mall_id
WHERE DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) = '2025-12-23'
  AND LOWER(c.company_name) = 'piscess'
GROUP BY r.order_id
ORDER BY record_count DESC;

-- 3. 전체 환불 금액 합계 (수정된 코드 로직대로)
SELECT 
    '수정된 코드 결과' AS check_type,
    SUM(refund_agg.total_refund_amount) AS total_refund_amount,
    COUNT(DISTINCT refund_agg.order_id) AS refund_order_count
FROM (
    SELECT
        r.order_id,
        SUM(r.total_refund_amount) AS total_refund_amount
    FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
    JOIN `winged-precept-443218-v8.ngn_dataset.company_info` c
        ON r.mall_id = c.mall_id
    WHERE DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) = '2025-12-23'
      AND LOWER(c.company_name) = 'piscess'
    GROUP BY r.order_id
) refund_agg;









