-- ✅ 삭제 후 확인: 삭제가 제대로 되었는지 확인
SELECT 
    DATE(DATETIME(TIMESTAMP(refund_date), 'Asia/Seoul')) AS refund_date_kst,
    COUNT(*) AS remaining_records
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table`
WHERE mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(refund_date), 'Asia/Seoul')) IN ('2025-12-05', '2025-12-17', '2025-12-19')
GROUP BY refund_date_kst
ORDER BY refund_date_kst;
-- 결과가 없어야 정상입니다 (각 날짜별로 0건)

