-- BigQuery performance_summary_ngn 테이블에 장바구니 사용자 수와 회원가입 수 컬럼 추가
-- 실행 방법: BigQuery 콘솔에서 이 SQL을 실행하세요.

ALTER TABLE `winged-precept-443218-v8.ngn_dataset.performance_summary_ngn`
ADD COLUMN IF NOT EXISTS cart_users INTEGER,
ADD COLUMN IF NOT EXISTS signup_count INTEGER;

-- 컬럼이 정상적으로 추가되었는지 확인
SELECT 
  column_name, 
  data_type, 
  is_nullable
FROM `winged-precept-443218-v8.ngn_dataset.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = 'performance_summary_ngn'
  AND column_name IN ('cart_users', 'signup_count')
ORDER BY ordinal_position;


