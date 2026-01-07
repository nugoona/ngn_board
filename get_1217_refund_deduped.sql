-- ✅ 12/17 환불 데이터 (refund_code별 중복 제거 후 합산)
WITH refund_deduped AS (
    SELECT
        r.refund_date,
        r.order_id,
        r.refund_code,
        MAX(r.total_refund_amount) AS total_refund_amount,
        MAX(r.actual_refund_amount) AS actual_refund_amount,
        MAX(r.used_points) AS used_points,
        MAX(r.used_credits) AS used_credits,
        MAX(r.quantity) AS quantity
    FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
    WHERE r.mall_id = 'piscess1'
      AND DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) = '2025-12-17'
    GROUP BY r.refund_date, r.order_id, r.refund_code
)
SELECT 
    refund_date,
    COUNT(*) AS unique_refund_count,
    SUM(total_refund_amount) AS total_refund_amount,
    SUM(actual_refund_amount) AS actual_refund_amount,
    SUM(used_points) AS used_points,
    SUM(used_credits) AS used_credits
FROM refund_deduped
GROUP BY refund_date;

