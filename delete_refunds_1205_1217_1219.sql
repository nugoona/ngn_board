-- ✅ 12/5, 12/17, 12/19 환불 데이터 모두 삭제
-- ⚠️ 주의: 삭제 전에 확인하세요!

DELETE FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table`
WHERE mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(refund_date), 'Asia/Seoul')) IN ('2025-12-05', '2025-12-17', '2025-12-19');

