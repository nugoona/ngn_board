-- ✅ 중복 제거 후 정상 환불 금액 확인 (12/5, 12/17, 12/19)
WITH refund_data AS (
    SELECT 
        DATE(DATETIME(TIMESTAMP(refund_date), 'Asia/Seoul')) AS refund_date_kst,
        order_id,
        order_item_code,
        refund_code,
        total_refund_amount,
        -- 중복 제거 전 합계
        SUM(total_refund_amount) OVER (PARTITION BY DATE(DATETIME(TIMESTAMP(refund_date), 'Asia/Seoul'))) AS total_amount_before,
        -- 각 조합별 최신 금액
        FIRST_VALUE(total_refund_amount) OVER (
            PARTITION BY order_id, order_item_code, refund_code
            ORDER BY refund_date DESC
        ) AS distinct_refund_amount
    FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table`
    WHERE mall_id = 'piscess1'
      AND DATE(DATETIME(TIMESTAMP(refund_date), 'Asia/Seoul')) IN ('2025-12-05', '2025-12-17', '2025-12-19')
)
SELECT 
    refund_date_kst,
    -- 중복 제거 전
    COUNT(*) AS total_records_before,
    MAX(total_amount_before) AS total_amount_before,
    -- 중복 제거 후
    COUNT(DISTINCT CONCAT(order_id, '_', order_item_code, '_', refund_code)) AS unique_records_after,
    SUM(distinct_refund_amount) AS total_amount_after,
    -- 차이 (과집계 금액)
    MAX(total_amount_before) - SUM(distinct_refund_amount) AS over_counted_amount
FROM refund_data
GROUP BY refund_date_kst
ORDER BY refund_date_kst;

