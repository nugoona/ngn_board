-- ✅ 2단계: 중복된 환불 상세 확인 (refund_code, order_id, order_item_code 조합 기준)
SELECT 
    DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) AS refund_date_kst,
    r.order_id,
    r.order_item_code,
    r.refund_code,
    COUNT(*) AS duplicate_count,
    SUM(r.total_refund_amount) AS total_amount,
    MAX(r.total_refund_amount) AS max_amount,
    MIN(r.total_refund_amount) AS min_amount,
    STRING_AGG(CAST(r.total_refund_amount AS STRING), ', ') AS amounts
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
WHERE r.mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) >= '2025-12-01'
  AND DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) <= '2025-12-31'
GROUP BY refund_date_kst, r.order_id, r.order_item_code, r.refund_code
HAVING COUNT(*) > 1  -- 중복된 것만
ORDER BY refund_date_kst, duplicate_count DESC;

