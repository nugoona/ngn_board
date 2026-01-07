-- ✅ 12/5 중복 환불 삭제
-- 주의: 삭제 전에 check_1205_duplicate.sql로 확인하세요!

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
          AND DATE(DATETIME(TIMESTAMP(refund_date), 'Asia/Seoul')) = '2025-12-05'
    )
    WHERE rank_num > 1
);

