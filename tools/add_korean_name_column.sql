-- company_info 테이블에 korean_name 컬럼 추가
-- 기존 데이터 업데이트 (예시: piscess -> 파이시스)

-- 1. 컬럼 추가
ALTER TABLE `winged-precept-443218-v8.ngn_dataset.company_info`
ADD COLUMN IF NOT EXISTS korean_name STRING;

-- 2. 기존 데이터 업데이트 (예시)
-- UPDATE `winged-precept-443218-v8.ngn_dataset.company_info`
-- SET korean_name = '파이시스'
-- WHERE LOWER(company_name) = 'piscess';

-- 3. 새로운 업체 추가 시 예시:
-- INSERT INTO `winged-precept-443218-v8.ngn_dataset.company_info`
--   (company_name, korean_name, mall_id, meta_acc, main_url, ...)
-- VALUES
--   ('new_company', '새로운회사', 'mall_id', 'meta_acc', 'main_url', ...);

