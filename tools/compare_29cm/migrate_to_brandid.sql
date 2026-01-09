-- ==================================================
-- 29CM 경쟁사 비교: keyword → brandId 마이그레이션
-- 실행 순서: 1) 새 테이블 생성 → 2) 데이터 삽입 → 3) 기존 테이블 삭제
-- ==================================================

-- 1. 새 테이블 생성: company_competitor_brands
-- ==================================================
CREATE TABLE IF NOT EXISTS `winged-precept-443218-v8.ngn_dataset.company_competitor_brands` (
  company_name STRING NOT NULL,        -- 자사몰 company_name (예: piscess)
  brand_id INT64 NOT NULL,             -- 29CM 브랜드 ID
  brand_name STRING,                   -- 브랜드명 (API에서 자동 수집)
  display_name STRING,                 -- 탭에 표시될 이름
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  sort_order INT64 NOT NULL,           -- 정렬 순서
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP
)
CLUSTER BY company_name
OPTIONS(
  description="29CM 브랜드 ID 기반 경쟁사 관리 테이블. 각 자사몰의 경쟁 브랜드 ID 목록을 저장합니다."
);


-- 2. 파이시스(piscess) 경쟁사 브랜드 데이터 삽입
-- brand_name은 API 호출 시 자동으로 업데이트됨
-- ==================================================
INSERT INTO `winged-precept-443218-v8.ngn_dataset.company_competitor_brands`
  (company_name, brand_id, brand_name, display_name, is_active, sort_order, created_at)
VALUES
  ('piscess', 1138, NULL, NULL, TRUE, 1, CURRENT_TIMESTAMP()),
  ('piscess', 9443, NULL, NULL, TRUE, 2, CURRENT_TIMESTAMP()),
  ('piscess', 43189, NULL, NULL, TRUE, 3, CURRENT_TIMESTAMP()),
  ('piscess', 10473, NULL, NULL, TRUE, 4, CURRENT_TIMESTAMP()),
  ('piscess', 1549, NULL, NULL, TRUE, 5, CURRENT_TIMESTAMP()),
  ('piscess', 16507, NULL, NULL, TRUE, 6, CURRENT_TIMESTAMP()),
  ('piscess', 11649, NULL, NULL, TRUE, 7, CURRENT_TIMESTAMP()),
  ('piscess', 4348, NULL, NULL, TRUE, 8, CURRENT_TIMESTAMP()),
  ('piscess', 4349, NULL, NULL, TRUE, 9, CURRENT_TIMESTAMP()),
  ('piscess', 16723, NULL, NULL, TRUE, 10, CURRENT_TIMESTAMP());


-- 3. 기존 테이블 삭제 (데이터 확인 후 실행)
-- ==================================================
-- 주의: 아래 명령은 확인 후 수동 실행하세요
-- DROP TABLE IF EXISTS `winged-precept-443218-v8.ngn_dataset.company_competitor_keywords`;


-- 4. 데이터 확인 쿼리
-- ==================================================
-- SELECT * FROM `winged-precept-443218-v8.ngn_dataset.company_competitor_brands`
-- WHERE company_name = 'piscess'
-- ORDER BY sort_order;


-- 5. brand_name 업데이트 쿼리 (API 수집 후 실행용)
-- ==================================================
-- UPDATE `winged-precept-443218-v8.ngn_dataset.company_competitor_brands`
-- SET brand_name = @brand_name, display_name = @brand_name, updated_at = CURRENT_TIMESTAMP()
-- WHERE company_name = @company_name AND brand_id = @brand_id;
