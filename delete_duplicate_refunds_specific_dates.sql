-- ✅ 12/5, 12/17, 12/19 중복 환불 삭제
-- ⚠️ 주의: 삭제 전에 반드시 확인하세요!

-- 먼저 삭제할 중복 데이터 확인
SELECT 
    r.refund_date,
    r.order_id,
    r.order_item_code,
    r.refund_code,
    r.total_refund_amount,
    rn.rank_num
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
JOIN (
    SELECT 
        mall_id,
        order_id,
        order_item_code,
        refund_code,
        refund_date,
        ROW_NUMBER() OVER (
            PARTITION BY mall_id, order_id, order_item_code, refund_code
            ORDER BY refund_date DESC
        ) AS rank_num
    FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table`
    WHERE mall_id = 'piscess1'
      AND DATE(DATETIME(TIMESTAMP(refund_date), 'Asia/Seoul')) IN ('2025-12-05', '2025-12-17', '2025-12-19')
) rn
ON r.mall_id = rn.mall_id
   AND r.order_id = rn.order_id
   AND r.order_item_code = rn.order_item_code
   AND r.refund_code = rn.refund_code
   AND r.refund_date = rn.refund_date
WHERE r.mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) IN ('2025-12-05', '2025-12-17', '2025-12-19')
  AND rn.rank_num > 1  -- 중복된 것 (가장 최신 제외)
ORDER BY r.refund_date, r.refund_code, r.order_item_code;

-- 실제 삭제 실행 (위 확인 후 실행)
/*
DELETE FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table`
WHERE STRUCT(mall_id, order_id, order_item_code, refund_code, refund_date) IN (
    SELECT STRUCT(mall_id, order_id, order_item_code, refund_code, refund_date)
    FROM (
        SELECT 
            mall_id,
            order_id,
            order_item_code,
            refund_code,
            refund_date,
            ROW_NUMBER() OVER (
                PARTITION BY mall_id, order_id, order_item_code, refund_code
                ORDER BY refund_date DESC
            ) AS rank_num
        FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table`
        WHERE mall_id = 'piscess1'
          AND DATE(DATETIME(TIMESTAMP(refund_date), 'Asia/Seoul')) IN ('2025-12-05', '2025-12-17', '2025-12-19')
    )
    WHERE rank_num > 1
);
*/

