-- GA4 API에서 조회 가능한 날짜 범위 확인
-- 실제로는 이 쿼리로는 확인 불가하고, Python 스크립트로 테스트해야 함
-- 참고용 쿼리: performance_summary_ngn에서 cart_users나 signup_count가 0이 아닌 최근 날짜 확인

SELECT
  DATE(date) AS date,
  company_name,
  cart_users,
  signup_count,
  updated_at
FROM `winged-precept-443218-v8.ngn_dataset.performance_summary_ngn`
WHERE LOWER(company_name) = 'piscess'
  AND (cart_users > 0 OR signup_count > 0)
ORDER BY DATE(date) DESC
LIMIT 50;

