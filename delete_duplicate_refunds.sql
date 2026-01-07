-- ✅ 5단계: 중복 환불 삭제 쿼리
-- ⚠️ 주의: 2단계 쿼리로 중복을 확인한 후 실행하세요!
-- ⚠️ 삭제 전에 반드시 백업하거나 확인하세요!

-- 삭제할 중복 데이터 확인 (실행 후 확인)
SELECT 
    COUNT(*) AS rows_to_delete
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r1
WHERE r1.mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(r1.refund_date), 'Asia/Seoul')) >= '2025-12-01'
  AND DATE(DATETIME(TIMESTAMP(r1.refund_date), 'Asia/Seoul')) <= '2025-12-31'
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
              ) AS rn
          FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table`
          WHERE mall_id = 'piscess1'
            AND DATE(DATETIME(TIMESTAMP(refund_date), 'Asia/Seoul')) >= '2025-12-01'
            AND DATE(DATETIME(TIMESTAMP(refund_date), 'Asia/Seoul')) <= '2025-12-31'
      ) r2
      WHERE r1.mall_id = r2.mall_id
        AND r1.order_id = r2.order_id
        AND r1.order_item_code = r2.order_item_code
        AND r1.refund_code = r2.refund_code
        AND r1.refund_date = r2.refund_date
        AND r2.rn > 1
  );

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
            ) AS rn
        FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table`
        WHERE mall_id = 'piscess1'
          AND DATE(DATETIME(TIMESTAMP(refund_date), 'Asia/Seoul')) >= '2025-12-01'
          AND DATE(DATETIME(TIMESTAMP(refund_date), 'Asia/Seoul')) <= '2025-12-31'
    )
    WHERE rn > 1
);
*/

