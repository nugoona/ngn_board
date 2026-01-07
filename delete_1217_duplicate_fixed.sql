-- ✅ 12/17 중복 환불 삭제 (수정 버전)
-- 주의: 삭제 전에 check_1217_duplicate.sql로 확인하세요!

DELETE FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r1
WHERE r1.mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(r1.refund_date), 'Asia/Seoul')) = '2025-12-17'
  AND EXISTS (
    SELECT 1
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
          AND DATE(DATETIME(TIMESTAMP(refund_date), 'Asia/Seoul')) = '2025-12-17'
    ) r2
    WHERE r1.mall_id = r2.mall_id
      AND r1.order_id = r2.order_id
      AND r1.order_item_code = r2.order_item_code
      AND r1.refund_code = r2.refund_code
      AND r1.refund_date = r2.refund_date
      AND r2.rank_num > 1
  );

