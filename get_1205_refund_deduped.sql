-- ✅ 12/5 환불 데이터 (refund_code별 중복 제거 후 합산)
WITH refund_deduped AS (
    -- refund_code별로 먼저 집계 (같은 refund_code는 한 번만)
    SELECT
        r.refund_date,
        r.order_id,
        r.refund_code,
        MAX(r.total_refund_amount) AS total_refund_amount,  -- refund_code별 하나의 금액만
        MAX(r.actual_refund_amount) AS actual_refund_amount,
        MAX(r.used_points) AS used_points,
        MAX(r.used_credits) AS used_credits,
        MAX(r.quantity) AS quantity,
        STRING_AGG(DISTINCT r.order_item_code, ', ') AS order_item_codes  -- 여러 order_item_code 목록
    FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
    WHERE r.mall_id = 'piscess1'
      AND DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) = '2025-12-05'
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

-- ✅ 상세 데이터도 보기 (refund_code별로 정리된 것)
SELECT 
    r.refund_date,
    r.order_id,
    r.refund_code,
    MAX(r.total_refund_amount) AS total_refund_amount,
    MAX(r.actual_refund_amount) AS actual_refund_amount,
    MAX(r.used_points) AS used_points,
    MAX(r.used_credits) AS used_credits,
    STRING_AGG(DISTINCT r.order_item_code, ', ') AS order_item_codes
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
WHERE r.mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) = '2025-12-05'
GROUP BY r.refund_date, r.order_id, r.refund_code
ORDER BY r.order_id, r.refund_code;

