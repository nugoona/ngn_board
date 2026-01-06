-- performance_summary_ngn 테이블에서 장바구니/회원가입 데이터 확인 쿼리
-- 2025-12-26 날짜 데이터 확인

SELECT 
  date,
  company_name,
  ad_media,
  cart_users,
  signup_count,
  updated_at
FROM `winged-precept-443218-v8.ngn_dataset.performance_summary_ngn`
WHERE DATE(date) = DATE('2025-12-26')
  AND LOWER(company_name) IN ('piscess', 'nugoona', 'mdgt')
ORDER BY company_name, date;

-- 전체 날짜 범위 확인 (최근 7일)
SELECT 
  date,
  company_name,
  SUM(cart_users) AS total_cart_users,
  SUM(signup_count) AS total_signup_count
FROM `winged-precept-443218-v8.ngn_dataset.performance_summary_ngn`
WHERE DATE(date) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
  AND LOWER(company_name) IN ('piscess', 'nugoona', 'mdgt')
GROUP BY date, company_name
ORDER BY date DESC, company_name;












