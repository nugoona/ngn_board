-- ✅ 1단계: refund_date 기준 일자별 환불 확인 (중복 의심)
SELECT 
    DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) AS refund_date_kst,
    COUNT(*) AS total_records,
    COUNT(DISTINCT r.order_id) AS unique_orders,
    COUNT(DISTINCT CONCAT(r.order_id, '_', r.order_item_code, '_', r.refund_code)) AS unique_refund_items,
    SUM(r.total_refund_amount) AS total_refund_amount,
    -- 중복 의심 지표
    COUNT(*) - COUNT(DISTINCT CONCAT(r.order_id, '_', r.order_item_code, '_', r.refund_code)) AS duplicate_count
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
WHERE r.mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) >= '2025-12-01'
  AND DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) <= '2025-12-31'
GROUP BY refund_date_kst
HAVING duplicate_count > 0  -- 중복이 있는 날짜만
ORDER BY refund_date_kst;

