# 월간 스냅샷 BigQuery 비용 분석

## 쿼리 목록 (최적화 후)

### 1. 월간 집계 테이블 쿼리 (최적화됨 - 비용 낮음)
- `mall_sales_monthly`: 13개월 데이터 조회 (1회)
- `meta_ads_monthly`: 13개월 데이터 조회 (1회)
- `ga4_traffic_monthly`: 13개월 데이터 조회 (1회)

**예상 스캔량:**
- 각 테이블당 약 13개월 × 회사당 1행 = 매우 작음
- 예상: 각 테이블당 **0.001~0.01 TB** (13개월 집계 데이터)

### 2. Daily Raw 테이블 쿼리 (여전히 필요)
- `daily_cafe24_sales`: 일자별 데이터 (this/prev/yoy = 3회)
- `meta_ads_account_summary`: YoY 존재 확인 (1회)
- `ga4_traffic_ngn`: 
  - YoY 존재 확인 (1회)
  - top_sources (this/prev/yoy = 3회)
  - totals (add_to_cart_users, sign_up_users) (this/prev = 2회)
- `performance_summary_ngn`: totals (add_to_cart_users, sign_up_users) (this/prev = 2회)

**예상 스캔량:**
- 각 쿼리당 1개월 데이터 스캔
- 예상: 각 쿼리당 **0.01~0.1 TB** (1개월 raw 데이터)

### 3. Meta Ads Goals 쿼리 (SKIP_META_ADS_GOALS=0일 때)
- `meta_ads_ad_summary`: 
  - this/prev/yoy goals (3회)
  - benchmarks (최근 6개월, 6회)

**예상 스캔량:**
- 각 쿼리당 1개월 데이터 스캔
- 예상: 각 쿼리당 **0.01~0.1 TB**

### 4. Products 쿼리
- `daily_cafe24_items`: 
  - 30d/90d rolling (2회)
  - 각 쿼리는 최대 30일 또는 90일 데이터 스캔

**예상 스캔량:**
- 30d: **0.01~0.1 TB**
- 90d: **0.03~0.3 TB**

### 5. ViewItem 쿼리
- `ga4_viewitem_monthly_raw`: 13개월 데이터 조회 (1회)

**예상 스캔량:**
- 13개월 집계 데이터: **0.001~0.01 TB**

### 6. 기타 쿼리
- `has_rows` 체크 쿼리들 (LIMIT 1 사용, 매우 작음)
- `report_monthly_snapshot` upsert (1회, 매우 작음)

## 총 예상 비용 (최적화 후)

### 시나리오 1: SKIP_META_ADS_GOALS=1 (Meta Ads Goals 스킵)
- 월간 집계 테이블: 3개 × 0.005 TB = **0.015 TB**
- Daily raw 테이블: 
  - daily_cafe24_sales: 3회 × 0.05 TB = **0.15 TB**
  - ga4_traffic_ngn: 6회 × 0.05 TB = **0.3 TB**
  - performance_summary_ngn: 2회 × 0.05 TB = **0.1 TB**
- Products: 2회 × 0.1 TB = **0.2 TB**
- ViewItem: 1회 × 0.005 TB = **0.005 TB**
- 기타: **0.01 TB**

**총계: 약 0.78 TB = 약 $3.90**

### 시나리오 2: SKIP_META_ADS_GOALS=0 (Meta Ads Goals 포함)
- 위 비용 + Meta Ads Goals: 9회 × 0.05 TB = **0.45 TB**

**총계: 약 1.23 TB = 약 $6.15**

## 최적화 전후 비교

### 최적화 전 (추정)
- this/prev/yoy 비교를 raw 테이블에서 3회씩 조회
- 예상: **약 2.0~3.0 TB = $10~15**

### 최적화 후
- this/prev/yoy 비교를 집계 테이블에서 조회
- 예상: **약 0.78~1.23 TB = $3.90~6.15**

### 비용 절감
- **약 60~70% 절감** (SKIP_META_ADS_GOALS=1일 때)
- **약 50~60% 절감** (SKIP_META_ADS_GOALS=0일 때)

## 추가 최적화 가능 영역

1. **Daily 쿼리 최적화**: daily_cafe24_sales, ga4_traffic_ngn 등을 일자별 집계 테이블로 대체
2. **Meta Ads Goals 최적화**: meta_ads_ad_summary를 월간 집계 테이블로 대체
3. **Products 최적화**: daily_cafe24_items를 월간 집계 테이블로 대체

## 참고사항

- 실제 비용은 데이터 양에 따라 달라질 수 있음
- 파티셔닝/클러스터링이 적용되어 있으면 스캔량이 더 줄어들 수 있음
- BigQuery는 첫 10GB/월 무료이므로 실제 비용은 더 낮을 수 있음


