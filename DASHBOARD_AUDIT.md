# NGN Dashboard - Full-Stack Architecture Audit

> **목적**: 대시보드 프로젝트의 전체 성능 최적화를 위한 아키텍처 분석 문서  
> **생성일**: 2025-01-29  
> **프로젝트**: NGN Dashboard (`ngn_dashboard`)

---

## 1. 기술 스택 요약 (Tech Stack)

### Frontend
- **Framework**: 순수 JavaScript (jQuery 기반) + Jinja2 템플릿
- **라이브러리**:
  - jQuery 3.6.0
  - Chart.js (차트 렌더링)
  - ApexCharts 3.45.1
  - ECharts 5.5.0
  - SweetAlert2 11 (알림)
- **렌더링 방식**: **CSR (Client-Side Rendering)** - Flask가 HTML 템플릿을 서빙하고, JavaScript가 AJAX로 데이터를 비동기 로드
- **모바일 지원**: 별도 모바일 템플릿 (`templates/mobile/dashboard.html`)

### Backend/API
- **Framework**: **Flask 3.0.3** (Python)
- **아키텍처**: Blueprint 기반 모듈화
  - `handlers/` - API 엔드포인트 (Blueprint)
  - `services/` - 비즈니스 로직
  - `utils/` - 유틸리티 함수
- **세션 관리**: Flask Session (8시간 만료)
- **인증**: 세션 기반 (`user_id`, `company_names`)

### Database & Cloud
- **BigQuery**: 주요 데이터 웨어하우스
  - 프로젝트: `winged-precept-443218-v8`
  - 데이터셋: `ngn_dataset`
  - 클라이언트: `google-cloud-bigquery==3.10.0`
- **Google Cloud Storage (GCS)**: 
  - 월간 리포트 스냅샷 저장 (`ai-reports/monthly/{company}/{year}-{month}/snapshot.json.gz`)
  - Gzip 압축 지원
- **인증**: ADC (Application Default Credentials) - Cloud Run 환경
- **기타**:
  - MySQL (mysql-connector-python==9.1.0) - 사용 여부 확인 필요
  - Google Sheets API (플랫폼 매출 데이터 수집)

### Hosting
- **GCP Cloud Run**: Flask 앱 배포
- **Gunicorn**: WSGI 서버 (프로덕션)
- **Cloud Build**: CI/CD (`cloudbuild.yaml`)
- **Cloud Scheduler**: 주기적 워밍업 (`/health` 엔드포인트)

---

## 2. 프로젝트 구조 (File Structure)

```
ngn_dashboard/
├── ngn_wep/
│   ├── dashboard/                    # 메인 대시보드 앱
│   │   ├── app.py                    # ⭐ Flask 앱 진입점
│   │   ├── handlers/                 # API 엔드포인트 (Blueprint)
│   │   │   ├── data_handler.py       # ⭐ 메인 데이터 API (/dashboard/*)
│   │   │   ├── auth_handler.py       # 인증
│   │   │   ├── accounts_handler.py   # 계정 관리
│   │   │   └── mobile_handler.py     # 모바일 전용
│   │   ├── services/                 # 비즈니스 로직
│   │   │   ├── performance_summary_new.py    # ⭐ 성과 요약
│   │   │   ├── cafe24_service.py             # 카페24 매출
│   │   │   ├── meta_ads_service.py           # Meta 광고
│   │   │   ├── ga4_source_summary.py         # GA4 유입
│   │   │   ├── viewitem_summary.py           # 상품 조회
│   │   │   └── ... (24개 서비스 파일)
│   │   ├── templates/                # Jinja2 템플릿
│   │   │   ├── index.html            # ⭐ 메인 대시보드 페이지
│   │   │   ├── ads_page.html         # 광고 성과 페이지
│   │   │   └── components/           # 재사용 컴포넌트
│   │   │       ├── performance_summary_table.html
│   │   │       ├── cafe24_sales_table.html
│   │   │       └── ...
│   │   ├── static/
│   │   │   ├── js/
│   │   │   │   ├── dashboard.js      # ⭐ 메인 대시보드 로직
│   │   │   │   ├── fetch_data.js     # API 호출 유틸
│   │   │   │   ├── filters.js         # 필터 관리
│   │   │   │   ├── monthly_report.js # 월간 리포트
│   │   │   │   └── ... (39개 JS 파일)
│   │   │   ├── css/
│   │   │   │   ├── styles.css        # 메인 스타일
│   │   │   │   └── monthly_report.css
│   │   │   └── img/
│   │   └── utils/
│   │       ├── query_utils.py        # BigQuery 유틸
│   │       ├── cache_utils.py         # ⭐ 캐시 관리
│   │       └── date_utils.py
│   ├── GA4_API/                      # GA4 데이터 수집
│   ├── meta_api/                      # Meta Ads API
│   └── cafe24_api/                    # Cafe24 API
├── tools/
│   └── ai_report_test/                # 월간 리포트 생성 도구
│       ├── bq_monthly_snapshot.py     # 스냅샷 생성
│       └── generate_monthly_report_from_snapshot.py
└── docker/                            # Docker 설정
```

### 핵심 진입점 파일

1. **Backend**: `ngn_wep/dashboard/app.py`
   - Flask 앱 초기화
   - Blueprint 등록
   - 라우트 정의 (`/`, `/ads`, `/health`)

2. **Frontend**: `ngn_wep/dashboard/templates/index.html`
   - 메인 대시보드 페이지
   - 컴포넌트 include
   - JavaScript 파일 로드

3. **API Handler**: `ngn_wep/dashboard/handlers/data_handler.py`
   - `/dashboard/get_data` - 통합 데이터 API
   - `/dashboard/monthly_report` - 월간 리포트 API

---

## 3. 데이터 흐름 분석 (Data Flow)

### Dashboard Main Page (`/dashboard` 또는 `/`)

#### 컴포넌트 구성
1. **필터 영역** (`components/filters.html`)
   - 업체 선택 (`#accountFilter`)
   - 기간 선택 (`#periodFilter`)
   - 수동 날짜 입력 (`#startDate`, `#endDate`)

2. **성과 요약** (`components/performance_summary_table.html`)
   - 매출, 주문, 방문자, 장바구니, 회원가입 등 통합 지표

3. **카페24 매출** (`components/cafe24_sales_table.html`)
   - 일별/월별 매출 데이터

4. **GA4 소스별 유입수** (`components/ga4_source_summary_table.html`)
   - 트래픽 소스별 유입 통계

5. **상품 매출 비중** (`components/product_sales_ratio.html`)
   - 상품별 매출 비중 차트

6. **플랫폼 매출 요약** (`components/platform_sales_summary_table.html`)
   - 플랫폼별 매출 통계

7. **월간 AI 리포트** (모달)
   - GCS에서 스냅샷 JSON 로드

#### 데이터 로딩 방식

**CSR (Client-Side Rendering)** 방식:
1. Flask가 HTML 템플릿을 서빙 (빈 테이블 구조만 포함)
2. JavaScript (`dashboard.js`)가 페이지 로드 시 `updateAllData()` 호출
3. 각 위젯별로 독립적인 AJAX 요청 (`fetch_data.js`)
4. 응답 받은 후 DOM 조작으로 테이블/차트 렌더링

**주요 API 호출 함수 위치**:

```javascript
// ngn_wep/dashboard/static/js/dashboard.js
window.updateAllData = async function() {
  // 1. 성과 요약
  fetchPerformanceSummaryData();
  
  // 2. 카페24 매출
  fetchCafe24SalesData(salesRequest);
  
  // 3. GA4 소스별 유입
  fetchGa4SourceSummaryData();
  
  // 4. 상품 매출 비중
  fetchProductSalesRatioData();
  
  // 5. 플랫폼 매출
  fetchPlatformSalesSummary();
  
  // 6. 월간 차트
  fetchMonthlyNetSalesVisitors();
}
```

**백엔드 API 엔드포인트**:

```python
# ngn_wep/dashboard/handlers/data_handler.py
@data_blueprint.route("/get_data", methods=["POST"])
def get_dashboard_data_route():
    # ThreadPoolExecutor로 병렬 처리
    with ThreadPoolExecutor(max_workers=10) as executor:
        # 각 서비스 함수를 병렬 실행
        fetch_tasks.append(executor.submit(fetch_performance_summary))
        fetch_tasks.append(executor.submit(fetch_cafe24_sales))
        # ...
```

### Slow Points (병목 의심 지점)

#### 1. **BigQuery 쿼리 병목**
- **위치**: `ngn_wep/dashboard/services/*.py`
- **문제점**:
  - 각 위젯마다 독립적인 BigQuery 쿼리 실행
  - `performance_summary_new.py` - 복잡한 JOIN 쿼리
  - `ga4_source_summary.py` - GA4 데이터 집계
  - `cafe24_service.py` - 일별/월별 매출 집계
- **최적화 여지**:
  - 쿼리 결과 캐싱 (`cache_utils.py` 사용 중)
  - 인덱스 최적화 확인 필요
  - 쿼리 병렬화 (이미 `ThreadPoolExecutor` 사용 중)

#### 2. **중복 API 호출 가능성**
- **위치**: `ngn_wep/dashboard/static/js/dashboard.js`
- **문제점**:
  - 필터 변경 시 `updateAllData()` 전체 재호출
  - 각 위젯이 독립적으로 로딩되어 중복 요청 가능
- **현재 대응**:
  - `requestRegistry`로 오래된 응답 무시 (`latestAjaxRequestWrapper`)
  - `isLoading` 플래그로 중복 호출 방지

#### 3. **월간 리포트 GCS 다운로드**
- **위치**: `ngn_wep/dashboard/handlers/data_handler.py:620`
- **문제점**:
  - GCS에서 전체 JSON 파일 다운로드 (Gzip 압축 해제)
  - 파일 크기가 클 수 있음 (수십 MB)
- **최적화 여지**:
  - 이미 Gzip 압축 적용됨
  - 프론트엔드에서 Lazy Loading 적용됨 (Intersection Observer)

#### 4. **useEffect/fetch 중복 호출**
- **위치**: `ngn_wep/dashboard/static/js/*.js`
- **문제점**:
  - jQuery 기반이라 `useEffect`는 없지만, `$(document).ready()`와 `$(window).on("load")` 중복 가능
  - 필터 변경 시 여러 이벤트 리스너가 동시에 트리거될 수 있음
- **현재 대응**:
  - `filters.js`에서 중앙화된 필터 변경 처리
  - `dashboard.js`에서 중복 호출 방지 로직

---

## 4. 주요 소스 코드 추출 (Key Code Snippets)

### 프론트엔드: 대시보드 메인 페이지

**파일**: `ngn_wep/dashboard/templates/index.html`

```html
<!DOCTYPE html>
<html lang="ko">
<head>
  <!-- 외부 라이브러리 -->
  <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  
  <!-- 내부 스크립트 -->
  <script src="{{ url_for('static', filename='js/dashboard.js') }}"></script>
  <script src="{{ url_for('static', filename='js/fetch_data.js') }}"></script>
</head>
<body>
  <!-- 필터 -->
  {% include 'components/filters.html' %}
  
  <!-- 성과 요약 -->
  <section class="performance-summary-full-width">
    {% include 'components/performance_summary_table.html' %}
  </section>
  
  <!-- 카페24 매출 + GA4 유입 -->
  <div class="container">
    <section class="table-wrapper">
      {% include 'components/cafe24_sales_table.html' %}
    </section>
    <section class="table-wrapper">
      {% include 'components/ga4_source_summary_table.html' %}
    </section>
  </div>
</body>
</html>
```

**파일**: `ngn_wep/dashboard/static/js/dashboard.js`

```javascript
// 페이지 로드 시 전체 데이터 업데이트
$(window).on("load", () => updateAllData());

window.updateAllData = async function() {
  const promises = [];
  
  // 성과 요약
  promises.push(fetchPerformanceSummaryData());
  
  // 카페24 매출
  if (typeof fetchCafe24SalesData === 'function') {
    promises.push(fetchCafe24SalesData(salesRequest));
  }
  
  // GA4 소스별 유입
  promises.push(fetchGa4SourceSummaryData());
  
  // 병렬 실행
  await Promise.all(promises);
};
```

### 백엔드: 대시보드 데이터 API 핸들러

**파일**: `ngn_wep/dashboard/handlers/data_handler.py`

```python
@data_blueprint.route("/get_data", methods=["POST"])
def get_dashboard_data_route():
    t0 = time.time()
    data = request.get_json()
    
    # 파라미터 추출
    company_name = data.get("company_name", "all")
    period = data.get("period", "today")
    start_date, end_date = get_start_end_dates(period, ...)
    data_type = data.get("data_type", "all")
    
    # ThreadPoolExecutor로 병렬 처리
    with ThreadPoolExecutor(max_workers=10) as executor:
        fetch_tasks = []
        
        # 성과 요약
        if data_type in ["performance_summary", "all"]:
            def fetch_performance_summary():
                return get_performance_summary_new(
                    company_name=company_name,
                    start_date=start_date,
                    end_date=end_date
                )
            fetch_tasks.append(executor.submit(fetch_performance_summary))
        
        # 카페24 매출
        if data_type in ["cafe24_sales", "all"]:
            def fetch_cafe24_sales():
                return get_cafe24_sales_data(...)
            fetch_tasks.append(executor.submit(fetch_cafe24_sales))
        
        # 결과 수집
        results = [task.result() for task in fetch_tasks]
    
    return jsonify(response_data), 200
```

### 유틸: BigQuery 쿼리 실행

**파일**: `ngn_wep/dashboard/utils/query_utils.py`

```python
def get_date_filter(period, start_date=None, end_date=None, table_alias="", column="order_date"):
    """기간 필터 SQL 생성"""
    column_ref = f"{table_alias}.{column}" if table_alias else column
    
    if period == "today":
        return f"DATE(TIMESTAMP({column_ref})) = CURRENT_DATE()"
    elif period == "last7days":
        return f"DATE(TIMESTAMP({column_ref})) BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 6 DAY) AND CURRENT_DATE()"
    elif period == "manual":
        if start_date and end_date:
            return f"DATE(TIMESTAMP({column_ref})) BETWEEN DATE('{start_date}') AND DATE('{end_date}')"
    # ...
```

**파일**: `ngn_wep/dashboard/services/performance_summary_new.py`

```python
def get_performance_summary_new(company_name, start_date, end_date):
    """성과 요약 데이터 조회"""
    client = bigquery.Client(project=PROJECT_ID)
    
    query = f"""
    SELECT 
        ad_media,
        SUM(site_revenue) as site_revenue,
        SUM(total_orders) as total_orders,
        SUM(total_visitors) as total_visitors
    FROM `{PROJECT_ID}.{DATASET}.performance_summary`
    WHERE company_name IN ({company_filter})
      AND order_date BETWEEN @start_date AND @end_date
    GROUP BY ad_media
    ORDER BY site_revenue DESC
    """
    
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
            bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
        ]
    )
    
    results = client.query(query, job_config=job_config).result()
    return [dict(row) for row in results]
```

### 캐시 관리

**파일**: `ngn_wep/dashboard/utils/cache_utils.py`

```python
# 인메모리 캐시 (dict 기반)
_cache = {}

def get_cache_stats():
    """캐시 통계 반환"""
    return {
        "total_keys": len(_cache),
        "memory_usage": sys.getsizeof(_cache)
    }

def invalidate_cache_by_pattern(pattern):
    """패턴 기반 캐시 무효화"""
    keys_to_delete = [k for k in _cache.keys() if pattern in k]
    for key in keys_to_delete:
        del _cache[key]
    return len(keys_to_delete)
```

---

## 5. 성능 최적화 권장 사항

### 즉시 적용 가능한 최적화

1. **BigQuery 쿼리 최적화**
   - 인덱스 확인 (`company_name`, `order_date` 컬럼)
   - 파티셔닝 확인 (날짜 기반 파티션)
   - 쿼리 결과 캐싱 강화

2. **프론트엔드 로딩 최적화**
   - Lazy Loading 확대 (현재 월간 리포트만 적용)
   - 이미지 최적화 (WebP 변환)
   - JavaScript 번들링 (현재 분산된 파일들)

3. **API 응답 최적화**
   - Gzip 압축 (이미 적용됨)
   - 응답 크기 최소화 (불필요한 필드 제거)
   - 페이지네이션 개선

### 중장기 최적화

1. **아키텍처 개선**
   - React/Vue.js로 마이그레이션 (현재 jQuery 기반)
   - GraphQL 도입 (복수 API 호출 통합)
   - 서버 사이드 캐싱 (Redis)

2. **데이터 파이프라인**
   - 실시간 스트리밍 (현재 배치 처리)
   - 데이터 웨어하우스 최적화
   - ETL 프로세스 개선

3. **모니터링**
   - APM 도입 (성능 모니터링)
   - 에러 추적 강화
   - 사용자 행동 분석

---

## 6. 참고 파일 목록

### 핵심 파일
- `ngn_wep/dashboard/app.py` - Flask 앱 진입점
- `ngn_wep/dashboard/handlers/data_handler.py` - 메인 API 핸들러
- `ngn_wep/dashboard/templates/index.html` - 메인 페이지
- `ngn_wep/dashboard/static/js/dashboard.js` - 프론트엔드 로직
- `ngn_wep/dashboard/services/performance_summary_new.py` - 성과 요약 서비스

### 유틸리티
- `ngn_wep/dashboard/utils/query_utils.py` - BigQuery 유틸
- `ngn_wep/dashboard/utils/cache_utils.py` - 캐시 관리
- `ngn_wep/dashboard/utils/date_utils.py` - 날짜 처리

### 설정 파일
- `ngn_wep/dashboard/requirements.txt` - Python 의존성
- `cloudbuild.yaml` - Cloud Build 설정
- `docker/Dockerfile-*` - Docker 이미지

---

**문서 버전**: 1.0  
**최종 업데이트**: 2025-01-29











