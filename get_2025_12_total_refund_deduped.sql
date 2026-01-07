-- ✅ 2025-12 전체 환불 합산값 (refund_code별 중복 제거)
WITH refund_deduped AS (
    -- refund_code별로 먼저 집계 (같은 refund_code는 한 번만)
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
    COUNT(DISTINCT refund_code) AS total_unique_refund_codes,
    COUNT(*) AS total_refund_records,
    SUM(total_refund_amount) AS total_refund_amount,
    SUM(actual_refund_amount) AS actual_refund_amount,
    SUM(used_points) AS used_points,
    SUM(used_credits) AS used_credits
FROM refund_deduped;

