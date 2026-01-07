-- ✅ 12/17 중복 환불 확인
SELECT 
    DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) AS refund_date_kst,
    r.order_id,
    r.order_item_code,
    r.refund_code,
    r.total_refund_amount
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
WHERE r.mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) = '2025-12-17'
ORDER BY r.refund_code, r.order_item_code;

