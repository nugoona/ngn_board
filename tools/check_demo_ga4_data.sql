-- 데모 계정 GA4 소스별 유입수 데이터 확인 쿼리
-- 날짜 범위: 2026-01-06 (오늘)

SELECT
  company_name,
  first_user_source,
  event_date,
  total_users,
  bounce_rate
FROM `winged-precept-443218-v8.ngn_dataset.ga4_traffic_ngn`
WHERE
  event_date = '2026-01-06'
  AND LOWER(company_name) = 'demo'
  AND first_user_source IS NOT NULL
  AND first_user_source != ''
  AND first_user_source != '(not set)'
  AND first_user_source != 'not set'
  AND first_user_source NOT IN ('(data not available)', 'data not available')
  AND total_users > 0
ORDER BY total_users DESC
LIMIT 100;

-- 집계된 소스별 유입수 확인
SELECT
  company_name,
  CASE
    WHEN LOWER(first_user_source) LIKE '%instagram%' 
         OR LOWER(first_user_source) LIKE '%insta%'
         OR LOWER(first_user_source) IN ('ig', 'linktr.ee', 'lookbook', 'igshopping') THEN 'instagram'
    WHEN LOWER(first_user_source) LIKE '%naver%' THEN 'naver.com'
    WHEN LOWER(first_user_source) LIKE '%meta_ad%' THEN 'meta_ad'
    WHEN LOWER(first_user_source) LIKE '%facebook%'
         OR LOWER(first_user_source) = 'fb' THEN 'facebook'
    WHEN LOWER(first_user_source) LIKE '%youtube%' THEN 'youtube.com'
    WHEN LOWER(first_user_source) LIKE '%tiktok%' 
         OR LOWER(first_user_source) LIKE '%tt.%' THEN 'tiktok'
    WHEN LOWER(first_user_source) IN ('(direct)', 'direct')
         OR LOWER(first_user_source) LIKE '%piscess%'
         OR LOWER(first_user_source) = '파이시스' THEN '(direct)'
    WHEN LOWER(first_user_source) LIKE '%google%' THEN 'google'
    WHEN LOWER(first_user_source) = 'daum' THEN 'daum'
    WHEN LOWER(first_user_source) LIKE '%cafe24%' THEN 'cafe24.com'
    WHEN LOWER(first_user_source) = '인트로 mdgt' THEN 'from madgoat'
    WHEN LOWER(first_user_source) IN ('(data not available)', 'data not available') THEN NULL
    ELSE LOWER(first_user_source)
  END AS source,
  SUM(total_users) AS total_users,
  SAFE_DIVIDE(
    SUM(IFNULL(bounce_rate, 0) * total_users),
    SUM(total_users)
  ) AS bounce_rate
FROM `winged-precept-443218-v8.ngn_dataset.ga4_traffic_ngn`
WHERE
  event_date = '2026-01-06'
  AND LOWER(company_name) = 'demo'
  AND first_user_source IS NOT NULL
  AND first_user_source != ''
  AND first_user_source != '(not set)'
  AND first_user_source != 'not set'
  AND first_user_source NOT IN ('(data not available)', 'data not available')
  AND total_users > 0
GROUP BY company_name, source
HAVING total_users > 0
ORDER BY total_users DESC;

