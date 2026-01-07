-- ✅ 3단계: 특정일의 모든 환불 데이터 확인 (과집계된 날짜 확인용)
-- ⚠️ 날짜를 원하는 날짜로 변경해서 실행하세요 (예: '2025-12-05')
SELECT 
    r.refund_date,
    r.order_id,
    r.order_item_code,
    r.refund_code,
    r.total_refund_amount,
    r.actual_refund_amount,
    r.used_points,
    r.used_credits,
    r.quantity
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
WHERE r.mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) = '2025-12-XX'  -- XX를 특정 날짜로 변경
ORDER BY r.order_id, r.order_item_code, r.refund_code;

