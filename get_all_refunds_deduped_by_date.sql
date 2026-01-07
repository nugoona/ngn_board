-- ✅ 모든 날짜 환불 데이터 (refund_code별 중복 제거 후 일자별 합산)
WITH refund_deduped AS (
    SELECT
        DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) AS refund_date_kst,
        r.order_id,
        r.refund_code,
        MAX(r.total_refund_amount) AS total_refund_amount,
        MAX(r.actual_refund_amount) AS actual_refund_amount,
        MAX(r.used_points) AS used_points,
        MAX(r.used_credits) AS used_credits
    FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
    WHERE r.mall_id = 'piscess1'
      AND DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) >= '2025-12-01'
      AND DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) <= '2025-12-31'
    GROUP BY refund_date_kst, r.order_id, r.refund_code
)
SELECT 
    refund_date_kst,
    COUNT(*) AS unique_refund_count,
    SUM(total_refund_amount) AS total_refund_amount,
    SUM(actual_refund_amount) AS actual_refund_amount,
    SUM(used_points) AS used_points,
    SUM(used_credits) AS used_credits
FROM refund_deduped
GROUP BY refund_date_kst
ORDER BY refund_date_kst;

