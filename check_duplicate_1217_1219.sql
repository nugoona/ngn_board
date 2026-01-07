-- ✅ 12/17, 12/19 중복 환불 상세 확인
SELECT 
    DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) AS refund_date_kst,
    r.order_id,
    r.order_item_code,
    r.refund_code,
    r.total_refund_amount,
    r.actual_refund_amount,
    r.used_points,
    r.quantity
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
WHERE r.mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) IN ('2025-12-17', '2025-12-19')
ORDER BY r.refund_date, r.refund_code, r.order_item_code;

-- ✅ 같은 refund_code의 금액 합계 확인
SELECT 
    DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) AS refund_date_kst,
    r.refund_code,
    COUNT(*) AS record_count,
    COUNT(DISTINCT r.order_item_code) AS unique_items,
    SUM(r.total_refund_amount) AS sum_amount,
    -- 첫 번째 레코드의 금액 (실제 환불 금액일 수 있음)
    MAX(r.total_refund_amount) AS max_amount,
    MIN(r.total_refund_amount) AS min_amount
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
WHERE r.mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) IN ('2025-12-17', '2025-12-19')
GROUP BY refund_date_kst, r.refund_code
HAVING COUNT(*) > 1  -- 중복된 refund_code만
ORDER BY refund_date_kst, r.refund_code;

