-- ✅ 삭제 전 확인: 12/5, 12/17, 12/19 환불 데이터 확인
SELECT 
    DATE(DATETIME(TIMESTAMP(refund_date), 'Asia/Seoul')) AS refund_date_kst,
    COUNT(*) AS total_records,
    COUNT(DISTINCT order_id) AS unique_orders,
    SUM(total_refund_amount) AS total_refund_amount
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table`
WHERE mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(refund_date), 'Asia/Seoul')) IN ('2025-12-05', '2025-12-17', '2025-12-19')
GROUP BY refund_date_kst
ORDER BY refund_date_kst;

