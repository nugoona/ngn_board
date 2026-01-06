# 29CM 경쟁사 비교 페이지 기획안

## 📋 목차
1. [개요](#개요)
2. [데이터 수집 전략](#데이터-수집-전략)
3. [BigQuery 테이블 설계](#bigquery-테이블-설계)
4. [효율적인 매칭 전략](#효율적인-매칭-전략)
5. [수집 주기 및 스케줄링](#수집-주기-및-스케줄링)
6. [구현 계획](#구현-계획)

---

## 개요

### 목적
29CM에서 자사몰과 경쟁사들의 추천순 TOP 20 상품을 비교 분석할 수 있는 페이지 제공

### 주요 기능
- 자사몰 + 경쟁사별 탭으로 상품 비교
- 각 상품의 29CM 베스트 순위 매칭 표시
- 상품별 리뷰 조회 (최대 10개)
- 5개씩 2줄로 총 10개 표시, 좌우 버튼으로 페이지네이션

### 페이지 구조
- **위치**: `/trend/29cm` 페이지의 Compare 버튼 클릭 시 사이드바로 표시
- **제목**: "29CM 경쟁사 추천순 TOP 20"
- **탭 구성**: 자사몰 (첫 번째) + 경쟁사명들 (검색어)

---

## 데이터 수집 전략

### 1. 검색 결과 수집
- **API**: `https://display-bff-api.29cm.co.kr/api/v1/listing/items`
- **방법**: 각 경쟁사명을 검색어로 사용하여 TOP 20 상품 수집
- **저장**: BigQuery 테이블 `platform_29cm_search_results`에 저장

### 2. 리뷰 수집
- **API**: `https://review-api.29cm.co.kr/api/v4/reviews`
- **방법**: 각 상품의 `item_id`로 리뷰 조회 (최대 10개)
- **저장**: 검색 결과와 함께 JSON 형태로 저장

### 3. 베스트 목록 매칭
- **소스**: 기존 `platform_29cm_best` 테이블 (14개 탭, 1~100위)
- **매칭 키**: `item_id` (검색 결과) == `product_id` (베스트 목록의 `REGEXP_EXTRACT(item_url, r'catalog/([0-9]+)')`)
- **시점**: 베스트 목록 수집과 동일한 `run_id` 사용

---

## BigQuery 테이블 설계

### 1. `platform_29cm_search_results` (검색 결과 테이블)

```sql
CREATE TABLE `winged-precept-443218-v8.ngn_dataset.platform_29cm_search_results` (
  -- 기본 정보 (고유 키 구성 요소)
  search_keyword STRING,              -- 검색어 (경쟁사명)
  company_name STRING,                -- 자사몰 company_name (어떤 자사몰의 경쟁사인지)
  run_id STRING,                      -- 베스트 목록과 동일한 run_id
  item_id INT64,                      -- 상품 ID (고유 키의 일부)
  
  -- 상품 정보
  rank INT64,                         -- 검색 결과 순위 (1-20)
  brand_name STRING,                  -- 브랜드명
  product_name STRING,                -- 상품명
  price INT64,                         -- 가격
  discount_rate INT64,                 -- 할인율
  like_count INT64,                   -- 좋아요 수
  review_count INT64,                 -- 리뷰 수
  review_score FLOAT64,               -- 리뷰 평점
  thumbnail_url STRING,               -- 썸네일 URL
  item_url STRING,                    -- 상품 URL
  
  -- 베스트 목록 매칭 정보
  best_rank INT64,                    -- 29CM 베스트 순위 (매칭된 경우)
  best_category STRING,               -- 베스트 카테고리 (매칭된 경우)
  
  -- 메타 정보
  search_date DATE,                   -- 검색 날짜 (파티션 키)
  created_at TIMESTAMP,               -- 수집 시간
  updated_at TIMESTAMP,               -- 업데이트 시간
  reviews JSON                        -- 리뷰 데이터 (JSON 배열)
)
PARTITION BY search_date
CLUSTER BY company_name, search_keyword, run_id, item_id;

-- 고유 제약 조건 (중복 방지)
-- (company_name, search_keyword, run_id, item_id) 조합이 고유해야 함
```

**중복 방지 전략**:
- **고유 키**: `(company_name, search_keyword, run_id, item_id)` 조합
- **덮어쓰기 방법**: MERGE 문 사용하여 기존 데이터 업데이트 또는 새 데이터 삽입
- **수집 시**: 같은 `run_id`, `company_name`, `search_keyword` 조합의 기존 데이터를 모두 삭제 후 새 데이터 삽입 (더 안전)

### 2. `company_competitor_keywords` (경쟁사 검색어 관리 테이블)

```sql
CREATE TABLE `winged-precept-443218-v8.ngn_dataset.company_competitor_keywords` (
  company_name STRING,                -- 자사몰 company_name
  competitor_keyword STRING,          -- 경쟁사 검색어
  display_name STRING,                -- 탭에 표시될 이름 (한글명 등)
  is_active BOOLEAN,                  -- 활성화 여부
  sort_order INT64,                   -- 정렬 순서
  created_at TIMESTAMP,               -- 생성 시간
  updated_at TIMESTAMP                -- 수정 시간
)
CLUSTER BY company_name;
```

**초기 데이터 (파이시스 기준)**:
```sql
INSERT INTO `winged-precept-443218-v8.ngn_dataset.company_competitor_keywords`
  (company_name, competitor_keyword, display_name, is_active, sort_order)
VALUES
  ('piscess', '데이즈데이즈', '데이즈데이즈', TRUE, 1),
  ('piscess', '코랄리크', '코랄리크', TRUE, 2),
  ('piscess', '라메레이', '라메레이', TRUE, 3),
  ('piscess', '마딘', '마딘', TRUE, 4),
  ('piscess', '플로움', '플로움', TRUE, 5),
  ('piscess', '엔조블루스', '엔조블루스', TRUE, 6),
  ('piscess', '페스토', '페스토', TRUE, 7),
  ('piscess', '노컨텐츠', '노컨텐츠', TRUE, 8),
  ('piscess', '오버듀플레어', '오버듀플레어', TRUE, 9),
  ('piscess', '문달', '문달', TRUE, 10),
  ('piscess', '글로니', '글로니', TRUE, 11);
```

---

## 효율적인 매칭 전략

### 문제 분석
- **베스트 목록**: 14개 탭 × 100위 = 1,400개 상품
- **검색 결과**: 11개 경쟁사 × 20개 = 220개 상품
- **매칭 작업**: 220개 검색 결과를 1,400개 베스트 목록과 비교

### 최적화 방안 ✅

**방법 1: 베스트 목록을 딕셔너리로 로드 후 매칭 (권장)**
```python
# 1. 베스트 목록을 한 번에 로드 (1,400개)
best_dict = {}  # {item_id: {rank, category, ...}}
for row in best_list:
    item_id = extract_item_id(row['item_url'])
    best_dict[item_id] = {
        'rank': row['rank'],
        'category': row['best_page_name'],
        ...
    }

# 2. 검색 결과와 매칭 (220번 반복, O(1) 조회)
for search_result in search_results:
    item_id = search_result['item_id']
    if item_id in best_dict:
        search_result['best_rank'] = best_dict[item_id]['rank']
        search_result['best_category'] = best_dict[item_id]['category']
```

**시간 복잡도**: O(1,400) + O(220) = O(1,620) ✅

**방법 2: BigQuery JOIN 사용 (비추천)**
```sql
-- 검색 결과 220개 × 베스트 목록 1,400개 = 최대 308,000개 비교
SELECT ...
FROM search_results s
LEFT JOIN best_list b ON s.item_id = b.product_id
```
**시간 복잡도**: O(220 × 1,400) = O(308,000) ❌

### 결론
**방법 1 (딕셔너리 매칭)을 사용**하여 메모리에서 빠르게 매칭하는 것이 가장 효율적입니다.

---

## 수집 주기 및 스케줄링

### 수집 주기
- **매주 화요일 오후 9시 (KST)**
- **매주 금요일 오후 9시 (KST)**

### 베스트 목록과 동기화
- **동일한 `run_id` 사용**: 베스트 목록 수집과 동일한 시점의 `run_id` 사용
- **수집 순서**:
  1. 베스트 목록 수집 완료 확인 (`platform_29cm_best` 테이블에서 최신 `run_id` 조회)
  2. 해당 `run_id`로 검색 결과 수집
  3. 베스트 목록과 매칭
  4. BigQuery 저장 + GCS 스냅샷 생성

### Cloud Scheduler 설정
```bash
# 화요일 오후 9시 (KST = UTC+9, UTC 기준 12:00)
0 12 * * 2

# 금요일 오후 9시 (KST = UTC+9, UTC 기준 12:00)
0 12 * * 5
```

---

## 구현 계획

### 1. 백엔드 서비스 (`ngn_wep/dashboard/services/compare_29cm_service.py`)

주요 함수:
- `get_competitor_keywords(company_name: str) -> List[str]`: 경쟁사 검색어 조회
- `search_29cm_products(keyword: str) -> List[Dict]`: 29CM 검색 API 호출
- `fetch_product_reviews(item_id: int) -> List[Dict]`: 리뷰 수집
- `load_best_ranking_dict(run_id: str) -> Dict[int, Dict]`: 베스트 목록을 딕셔너리로 로드
- `match_with_best_ranking(search_results: List[Dict], best_dict: Dict) -> List[Dict]`: 매칭
- `delete_existing_search_results(company_name: str, search_keyword: str, run_id: str) -> bool`: 기존 데이터 삭제
- `save_search_results_to_bq(company_name: str, run_id: str, results: Dict[str, List[Dict]]) -> bool`: BigQuery 저장 (덮어쓰기)

### 2. 스냅샷 생성 Job (`tools/compare_29cm_snapshot.py`)

- 베스트 목록 수집 Job과 동일한 시점에 실행
- 모든 자사몰의 경쟁사 검색 결과 수집
- GCS 스냅샷 생성: `ai-reports/compare/29cm/{YYYY-MM-DD}/search_results.json.gz`

### 3. API 엔드포인트 (`ngn_wep/dashboard/handlers/data_handler.py`)

```python
@data_blueprint.route("/compare/29cm/search", methods=["POST"])
def get_compare_search_results():
    """경쟁사 검색 결과 조회"""
    # company_name, run_id 받아서 검색 결과 반환

@data_blueprint.route("/compare/29cm/reviews", methods=["GET"])
def get_product_reviews():
    """상품 리뷰 조회"""
    # item_id 받아서 리뷰 반환
```

### 4. 프론트엔드

파일:
- `ngn_wep/dashboard/templates/components/compare_sidebar.html`: 사이드바 HTML
- `ngn_wep/dashboard/static/js/compare_page.js`: JavaScript 로직
- `ngn_wep/dashboard/static/css/compare.css`: 스타일

기능:
- 탭 전환 시 해당 검색어 데이터 로드
- 상품 카드 10개씩 표시 (5개 × 2줄)
- 좌우 화살표로 페이지네이션
- 리뷰 모달 표시

---

## 중복 방지 및 덮어쓰기 전략

### 저장 로직
1. **기존 데이터 삭제**: 같은 `run_id`, `company_name`, `search_keyword` 조합의 모든 데이터 삭제
2. **새 데이터 삽입**: 수집한 모든 상품 정보(리뷰 포함) 삽입

### BigQuery MERGE 문 예시
```sql
-- 방법 1: DELETE 후 INSERT (권장, 더 안전)
DELETE FROM `platform_29cm_search_results`
WHERE company_name = @company_name
  AND search_keyword = @search_keyword
  AND run_id = @run_id;

INSERT INTO `platform_29cm_search_results` (...)
VALUES (...);

-- 방법 2: MERGE 문 사용
MERGE `platform_29cm_search_results` AS target
USING (SELECT ... FROM temp_table) AS source
ON target.company_name = source.company_name
   AND target.search_keyword = source.search_keyword
   AND target.run_id = source.run_id
   AND target.item_id = source.item_id
WHEN MATCHED THEN
  UPDATE SET
    rank = source.rank,
    brand_name = source.brand_name,
    product_name = source.product_name,
    price = source.price,
    reviews = source.reviews,
    updated_at = CURRENT_TIMESTAMP()
WHEN NOT MATCHED THEN
  INSERT (...)
  VALUES (...);
```

**권장 방법**: DELETE 후 INSERT (방법 1)
- 더 간단하고 명확함
- 트랜잭션 없이도 안전 (같은 run_id는 한 번만 수집)
- 삭제된 데이터는 스냅샷에서 복구 가능

## 비용 최적화

### BigQuery 비용
- **검색 결과 저장**: 주 2회 × 11개 경쟁사 × 20개 = 440개/주
- **기존 데이터 삭제**: 주 2회 × 11개 경쟁사 = 22회 DELETE 쿼리/주
- **베스트 목록 조회**: 주 2회 × 1,400개 = 2,800개/주
- **매칭**: 메모리에서 처리 (BigQuery 비용 없음)

### API 호출 비용
- **검색 API**: 주 2회 × 11개 경쟁사 = 22회/주
- **리뷰 API**: 주 2회 × 11개 경쟁사 × 20개 상품 = 440회/주

### GCS 스토리지
- **스냅샷 크기**: 약 500KB ~ 1MB/주
- **보관 기간**: 3개월 (자동 삭제)

---

## 다음 단계

1. ✅ BigQuery 테이블 생성 스크립트 작성
2. ✅ `compare_29cm_service.py` 구현
3. ✅ 스냅샷 생성 Job 구현
4. ✅ API 엔드포인트 추가
5. ✅ 프론트엔드 구현
6. ✅ Cloud Scheduler 설정

