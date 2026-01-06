-- ==================================================
-- 29CM 경쟁사 비교 페이지용 BigQuery 테이블 생성
-- ==================================================

-- 1. 검색 결과 테이블
-- ==================================================
CREATE TABLE IF NOT EXISTS `winged-precept-443218-v8.ngn_dataset.platform_29cm_search_results` (
  -- 기본 정보 (고유 키 구성 요소)
  search_keyword STRING NOT NULL,              -- 검색어 (경쟁사명)
  company_name STRING NOT NULL,                -- 자사몰 company_name
  run_id STRING NOT NULL,                      -- 베스트 목록과 동일한 run_id
  item_id INT64 NOT NULL,                      -- 상품 ID (고유 키의 일부)
  
  -- 상품 정보
  rank INT64,                                  -- 검색 결과 순위 (1-20)
  brand_name STRING,                          -- 브랜드명
  product_name STRING,                         -- 상품명
  price INT64,                                 -- 가격
  discount_rate INT64,                         -- 할인율
  like_count INT64,                           -- 좋아요 수
  review_count INT64,                          -- 리뷰 수
  review_score FLOAT64,                        -- 리뷰 평점
  thumbnail_url STRING,                        -- 썸네일 URL
  item_url STRING,                             -- 상품 URL
  
  -- 베스트 목록 매칭 정보
  best_rank INT64,                             -- 29CM 베스트 순위 (매칭된 경우)
  best_category STRING,                        -- 베스트 카테고리 (매칭된 경우)
  
  -- 메타 정보
  search_date DATE NOT NULL,                   -- 검색 날짜 (파티션 키)
  created_at TIMESTAMP NOT NULL,               -- 수집 시간
  updated_at TIMESTAMP,                        -- 업데이트 시간
  reviews JSON                                 -- 리뷰 데이터 (JSON 배열)
)
PARTITION BY search_date
CLUSTER BY company_name, search_keyword, run_id, item_id
OPTIONS(
  description="29CM 경쟁사 검색 결과 저장 테이블. 검색어별 TOP 20 상품 정보와 리뷰를 저장합니다."
);

-- 2. 경쟁사 검색어 관리 테이블
-- ==================================================
CREATE TABLE IF NOT EXISTS `winged-precept-443218-v8.ngn_dataset.company_competitor_keywords` (
  company_name STRING NOT NULL,                -- 자사몰 company_name
  competitor_keyword STRING NOT NULL,          -- 경쟁사 검색어
  display_name STRING,                         -- 탭에 표시될 이름 (한글명 등)
  is_active BOOLEAN NOT NULL,                  -- 활성화 여부
  sort_order INT64 NOT NULL,                   -- 정렬 순서
  created_at TIMESTAMP NOT NULL,               -- 생성 시간
  updated_at TIMESTAMP                         -- 수정 시간
)
CLUSTER BY company_name
OPTIONS(
  description="자사몰별 경쟁사 검색어 관리 테이블. 각 자사몰의 경쟁사 검색어 목록을 저장합니다."
);

-- 3. 초기 데이터 삽입 (파이시스 기준)
-- ==================================================
INSERT INTO `winged-precept-443218-v8.ngn_dataset.company_competitor_keywords`
  (company_name, competitor_keyword, display_name, is_active, sort_order, created_at)
VALUES
  ('piscess', '데이즈데이즈', '데이즈데이즈', TRUE, 1, CURRENT_TIMESTAMP()),
  ('piscess', '코랄리크', '코랄리크', TRUE, 2, CURRENT_TIMESTAMP()),
  ('piscess', '라메레이', '라메레이', TRUE, 3, CURRENT_TIMESTAMP()),
  ('piscess', '마딘', '마딘', TRUE, 4, CURRENT_TIMESTAMP()),
  ('piscess', '플로움', '플로움', TRUE, 5, CURRENT_TIMESTAMP()),
  ('piscess', '엔조블루스', '엔조블루스', TRUE, 6, CURRENT_TIMESTAMP()),
  ('piscess', '페스토', '페스토', TRUE, 7, CURRENT_TIMESTAMP()),
  ('piscess', '노컨텐츠', '노컨텐츠', TRUE, 8, CURRENT_TIMESTAMP()),
  ('piscess', '오버듀플레어', '오버듀플레어', TRUE, 9, CURRENT_TIMESTAMP()),
  ('piscess', '문달', '문달', TRUE, 10, CURRENT_TIMESTAMP()),
  ('piscess', '글로니', '글로니', TRUE, 11, CURRENT_TIMESTAMP())
ON CONFLICT DO NOTHING;  -- BigQuery는 ON CONFLICT를 지원하지 않으므로, 중복 체크는 애플리케이션에서 처리

-- 참고: BigQuery는 ON CONFLICT를 지원하지 않으므로,
-- 중복 삽입을 방지하려면 아래 쿼리로 먼저 확인하거나
-- 애플리케이션에서 중복 체크를 수행해야 합니다.

-- 중복 체크 쿼리 (실행 전 확인용)
-- SELECT company_name, competitor_keyword, COUNT(*) as cnt
-- FROM `winged-precept-443218-v8.ngn_dataset.company_competitor_keywords`
-- GROUP BY company_name, competitor_keyword
-- HAVING cnt > 1;

