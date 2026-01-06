# 29CM 경쟁사 비교 테이블 생성 가이드

## 테이블 생성 순서

### 1. 기본 테이블 생성
```bash
# BigQuery 콘솔에서 실행하거나
bq query --use_legacy_sql=false < tools/compare_29cm/create_tables.sql

# 또는 안전 버전 (중복 체크 포함)
bq query --use_legacy_sql=false < tools/compare_29cm/create_tables_safe.sql
```

### 2. 테이블 확인
```sql
-- 검색 결과 테이블 확인
SELECT COUNT(*) as row_count
FROM `winged-precept-443218-v8.ngn_dataset.platform_29cm_search_results`;

-- 경쟁사 검색어 테이블 확인
SELECT *
FROM `winged-precept-443218-v8.ngn_dataset.company_competitor_keywords`
WHERE company_name = 'piscess'
ORDER BY sort_order;
```

## 테이블 구조

### `platform_29cm_search_results`
- **파티션**: `search_date` (일별)
- **클러스터링**: `company_name`, `search_keyword`, `run_id`, `item_id`
- **고유 키**: `(company_name, search_keyword, run_id, item_id)` 조합

### `company_competitor_keywords`
- **클러스터링**: `company_name`
- **고유 키**: `(company_name, competitor_keyword)` 조합

## 주의사항

1. **중복 삽입 방지**: `create_tables_safe.sql`을 사용하면 기존 데이터를 확인 후 삽입합니다.
2. **덮어쓰기**: 검색 결과는 같은 `run_id`, `company_name`, `search_keyword` 조합의 기존 데이터를 삭제 후 새로 삽입합니다.
3. **리뷰 데이터**: `reviews` 컬럼은 JSON 타입으로 저장되며, 최대 10개 리뷰를 포함합니다.

