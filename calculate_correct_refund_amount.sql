-- ✅ 4단계: 중복 제거 후 합계 (정상 환불 금액 계산)
SELECT 
    DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) AS refund_date_kst,
    COUNT(DISTINCT CONCAT(r.order_id, '_', r.order_item_code, '_', r.refund_code)) AS unique_refund_items,
    -- 중복 제거 후 금액 집계 (각 조합별 최신 금액 사용)
    SUM(DISTINCT_REFUND_AMOUNT) AS total_refund_amount
FROM (
    SELECT 
        r.refund_date,
        r.order_id,
        r.order_item_code,
        r.refund_code,
        -- 중복 중 가장 최신 금액 사용
        FIRST_VALUE(r.total_refund_amount) OVER (
            PARTITION BY r.order_id, r.order_item_code, r.refund_code 
            ORDER BY r.refund_date DESC
        ) AS DISTINCT_REFUND_AMOUNT
    FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
    WHERE r.mall_id = 'piscess1'
      AND DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) >= '2025-12-01'
      AND DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) <= '2025-12-31'
) r
GROUP BY refund_date_kst
ORDER BY refund_date_kst;

