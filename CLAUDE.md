# CLAUDE.md - NGN Dashboard Project Guide

## Project Overview

NGN Dashboard는 이커머스 브랜드를 위한 **통합 데이터 분석 플랫폼**입니다. Cafe24 자사몰, Meta Ads, GA4, 외부 마켓플레이스(29CM, Ably) 데이터를 수집하여 BigQuery에 통합하고, Flask 기반 웹 대시보드로 시각화합니다.

### Tech Stack
- **Backend**: Python 3.11, Flask 3.0.3, Gunicorn
- **Database**: Google BigQuery (ngn_dataset)
- **Storage**: Google Cloud Storage (GCS)
- **Deployment**: Cloud Run (서비스), Cloud Run Jobs (배치 작업)
- **Scheduling**: Cloud Scheduler + Pub/Sub
- **AI**: Google Gemini API (월간 분석 리포트)
- **Caching**: Redis (선택적)

### GCP Project Info
```
Project ID: winged-precept-443218-v8
Dataset: ngn_dataset
Region: asia-northeast3 (Jobs), asia-northeast1 (Services)
Service Account: 439320386143-compute@developer.gserviceaccount.com
```

---

## Directory Structure

```
ngn_dashboard/
├── ngn_wep/                          # 메인 애플리케이션
│   ├── dashboard/                    # Flask 웹 대시보드
│   │   ├── app.py                    # Flask 진입점 (포트 8080)
│   │   ├── handlers/                 # API 라우트 핸들러
│   │   │   ├── auth_handler.py       # 로그인/인증 (/auth/*)
│   │   │   ├── data_handler.py       # 데이터 API (/dashboard/*)
│   │   │   ├── accounts_handler.py   # 계정 관리 (/accounts/*)
│   │   │   └── mobile_handler.py     # 모바일 전용 (/m/*)
│   │   ├── services/                 # 비즈니스 로직
│   │   │   ├── performance_summary_new.py  # 통합 성과 요약
│   │   │   ├── cafe24_service.py           # Cafe24 매출 조회
│   │   │   ├── meta_ads_service.py         # Meta 광고 성과
│   │   │   ├── ga4_source_summary.py       # GA4 트래픽 분석
│   │   │   ├── trend_29cm_service.py       # 29CM 트렌드
│   │   │   └── trend_ably_service.py       # Ably 트렌드
│   │   ├── utils/                    # 유틸리티
│   │   │   ├── cache_utils.py        # Redis 캐싱
│   │   │   └── query_utils.py        # BigQuery 헬퍼
│   │   ├── templates/                # HTML 템플릿
│   │   └── static/                   # CSS/JS/이미지
│   │
│   ├── cafe24_api/                   # Cafe24 데이터 수집
│   │   ├── orders_handler.py         # 주문 수집
│   │   ├── daily_cafe24_sales_handler.py  # 일일 판매 집계
│   │   ├── cafe24_refund_data_handler.py  # 환불 데이터
│   │   └── token_refresh.py          # 토큰 갱신
│   │
│   ├── GA4_API/                      # Google Analytics 4
│   │   ├── ga4_traffic_today.py      # 트래픽 수집
│   │   ├── ga4_viewitem_today.py     # 상품 조회 이벤트
│   │   └── sheet_update_custom.py    # 구글 시트 연동
│   │
│   └── meta_api/                     # Meta Ads
│       └── meta_ads_handler.py       # 광고 성과 수집
│
├── tools/                            # 백엔드 작업
│   ├── ai_report_test/               # AI 분석 리포트
│   │   ├── ai_analyst.py             # Gemini AI 분석
│   │   ├── bq_monthly_snapshot.py    # 월간 스냅샷
│   │   └── jobs/                     # Cloud Run Jobs
│   │       ├── monthly_snapshot_job.py
│   │       ├── monthly_ai_analysis_job.py
│   │       └── monthly_rollup_job.py
│   ├── trend_29cm_snapshot.py        # 29CM 크롤링
│   ├── trend_ably_snapshot.py        # Ably 크롤링
│   └── config/
│       └── company_mapping.py        # 브랜드명 매핑
│
├── docker/                           # Dockerfile 모음 (38개)
│   ├── Dockerfile-dashboard          # 메인 대시보드
│   ├── Dockerfile-sales-today        # 당일 판매
│   ├── Dockerfile-sales-yesterday    # 전일 판매
│   └── ...
│
├── bigquery_data_cleanup/            # BigQuery 정리 작업
├── cloud_function_crawl/             # Cloud Function (카탈로그 크롤링)
├── jobs/                             # Job 설정 파일
│
├── cloudbuild.yaml                   # Cloud Build 파이프라인
├── requirements.txt                  # Python 의존성
└── BIGQUERY_TABLES_SCHEMA.md         # 테이블 스키마 문서
```

---

## Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    외부 데이터 소스                          │
├─────────────────────────────────────────────────────────────┤
│  Cafe24 API  │  GA4 API  │  Meta Ads  │  29CM  │  Ably     │
└──────┬───────┴─────┬─────┴─────┬──────┴───┬────┴────┬──────┘
       │             │           │          │         │
       ▼             ▼           ▼          ▼         ▼
┌─────────────────────────────────────────────────────────────┐
│              Cloud Run Jobs (데이터 수집)                    │
│  - ngn-orders-job (주문)                                    │
│  - query-sales-today-job (매출)                             │
│  - ngn-ga4-view-job (트래픽)                                │
│  - ably-best-collector-job (트렌드)                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              BigQuery (ngn_dataset)                          │
├─────────────────────────────────────────────────────────────┤
│  원본 테이블:                집계 테이블:                    │
│  - cafe24_orders            - daily_cafe24_sales            │
│  - cafe24_order_items       - ads_performance               │
│  - ga4_traffic              - performance_summary_ngn       │
│  - meta_ads_ad_level        - trend_*_snapshot              │
└──────────────────────┬──────────────────────────────────────┘
                       │
         ┌─────────────┴─────────────┐
         │                           │
         ▼                           ▼
┌─────────────────┐         ┌─────────────────────┐
│   GCS 버킷      │         │  Flask Dashboard    │
│  (스냅샷 저장)   │         │  (Cloud Run)        │
│                 │         │                     │
│  ai-reports/    │    ◄────│  /dashboard/*       │
│  trend-snapshots│         │  /auth/*            │
└─────────────────┘         │  /m/*               │
                            └─────────────────────┘
```

---

## Key BigQuery Tables

| 테이블 | 설명 | 주요 컬럼 |
|--------|------|----------|
| `daily_cafe24_sales` | 일별 매출 집계 | payment_date, company_name, total_orders, net_sales |
| `ads_performance` | Meta 광고 성과 | date, account_name, spend, purchases, purchase_value |
| `ga4_traffic` | GA4 트래픽 | event_date, firstUserSource, activeUsers |
| `ga4_viewitem` | 상품 조회 이벤트 | event_date, item_id, item_views |
| `company_info` | 업체 정보 매핑 | company_name, mall_id, meta_acc, ga4_property_id |
| `user_accounts` | 사용자 계정 | user_id, password, status, company_names |
| `trend_29cm_snapshot` | 29CM 순위 | run_id, rank, product_name, brand_name |
| `trend_ably_snapshot` | Ably 순위 | run_id, rank, product_name, brand_name |

---

## API Endpoints

### Dashboard API (`/dashboard/*`)
```
GET /dashboard/performance-summary   # 통합 성과 요약 (매출, 광고, 방문자)
GET /dashboard/cafe24-sales          # Cafe24 매출 데이터
GET /dashboard/meta-ads              # Meta 광고 성과
GET /dashboard/ga4-source-summary    # GA4 트래픽 소스
GET /dashboard/trend/29cm/*          # 29CM 트렌드 분석
GET /dashboard/trend/ably/*          # Ably 트렌드 분석
```

### Auth API (`/auth/*`)
```
GET  /auth/login                     # 로그인 페이지
POST /auth/login                     # 사용자 인증
GET  /auth/logout                    # 로그아웃
```

---

## Cloud Run Jobs Schedule

| Job | 스케줄 | 메모리 | 설명 |
|-----|--------|--------|------|
| query-sales-today-job | 매일 | 512Mi | 당일 판매 데이터 |
| query-sales-yesterday-job | 매일 | 512Mi | 전일 판매 데이터 |
| ngn-orders-job | 매일 | 1Gi | 주문 데이터 수집 |
| ngn-ga4-view-job | 매일 | 1Gi | GA4 데이터 수집 |
| ably-best-collector-job | 매주 월 07:00 | 2Gi | Ably 베스트 크롤링 |
| ngn-29cm-best-job | 매주 월 08:00 | 2Gi | 29CM 베스트 크롤링 |
| monthly-snapshot-job | 매월 1일 06:00 | 2Gi | 월간 스냅샷 생성 |
| monthly-ai-analysis-job | 매월 1일 06:05 | 4Gi | AI 분석 리포트 |
| bigquery-data-cleanup-job | 매월 1일 02:00 | 512Mi | 13개월 이상 데이터 삭제 |

---

## Common Development Commands

### Local Development
```bash
# 가상환경 활성화 및 의존성 설치
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Flask 로컬 실행
cd ngn_wep/dashboard
python app.py  # http://localhost:8080

# 특정 핸들러 단독 실행 (데이터 수집)
python ngn_wep/cafe24_api/daily_cafe24_sales_handler.py today
python ngn_wep/GA4_API/ga4_traffic_today.py
```

### Deployment
```bash
# 메인 대시보드 배포
./deploy_dashboard_safe.sh

# 특정 Job 배포
./deploy_sales_jobs.sh
./deploy_ably_job.sh

# 배포 상태 확인
./CHECK_DEPLOYMENT_STATUS.sh

# Cloud Build 직접 실행
gcloud builds submit --config=cloudbuild.yaml
```

### BigQuery 작업
```bash
# 스키마 내보내기
python export_bq_schema.py

# 데이터 정리 (수동)
python bigquery_data_cleanup/main.py

# SQL 쿼리 실행
bq query --use_legacy_sql=false < check_*.sql
```

---

## Environment Variables

### Required (Cloud Run에서 자동 주입)
```
GOOGLE_CLOUD_PROJECT=winged-precept-443218-v8
GCS_BUCKET=winged-precept-443218-v8.appspot.com
```

### Optional (로컬 개발용 .env)
```
META_SYSTEM_USER_TOKEN=...
META_APP_ID=...
META_APP_SECRET=...
GEMINI_API_KEY=...
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_ENABLED=false
```

---

## Code Patterns

### BigQuery 파라미터화된 쿼리
```python
from google.cloud import bigquery

client = bigquery.Client()
query_params = [
    bigquery.ScalarQueryParameter("company_name", "STRING", company_name),
    bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
]
query = """
    SELECT * FROM `ngn_dataset.daily_cafe24_sales`
    WHERE company_name = @company_name
      AND payment_date >= @start_date
"""
job_config = bigquery.QueryJobConfig(query_parameters=query_params)
result = client.query(query, job_config=job_config).result()
```

### 병렬 쿼리 실행 (성능 최적화)
```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=5) as executor:
    future_cafe24 = executor.submit(get_cafe24_summary, ...)
    future_meta = executor.submit(get_meta_ads_summary, ...)
    future_ga4 = executor.submit(get_ga4_visitors, ...)

    cafe24_data = future_cafe24.result(timeout=30)
    meta_data = future_meta.result(timeout=30)
    ga4_data = future_ga4.result(timeout=30)
```

### GCS 스냅샷 저장
```python
from google.cloud import storage
import gzip
import json

storage_client = storage.Client()
bucket = storage_client.bucket("winged-precept-443218-v8.appspot.com")
blob = bucket.blob(f"ai-reports/monthly/{company}/{year}-{month}/snapshot.json.gz")

compressed = gzip.compress(json.dumps(data).encode('utf-8'))
blob.upload_from_string(compressed, content_type='application/gzip')
```

---

## Timezone Handling

모든 날짜/시간은 **KST (Asia/Seoul, UTC+9)** 기준입니다.

```python
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))
now_kst = datetime.now(KST)

# BigQuery 쿼리에서
WHERE DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) = @target_date
```

---

## Caching Strategy

| 서비스 | TTL | 캐시 키 패턴 |
|--------|-----|-------------|
| performance_summary_new | 60초 | `perf_summary:{company}:{period}` |
| cafe24_sales | 180초 | `cafe24:{company}:{period}:{page}` |
| ga4_source_summary | 600초 | `ga4_source:{company}:{period}` |
| monthly_net_sales | 3600초 | `monthly:{company}:{year}:{month}` |

---

## Authentication Flow

1. 사용자가 `/auth/login`에서 로그인
2. BigQuery `user_accounts` 테이블에서 검증
3. 세션에 `user_id`, `company_names`, `is_demo_user` 저장
4. 데이터 조회 시 `company_names`로 필터링
5. Demo 사용자는 'demo' 업체 데이터만 조회 가능

---

## Company Mapping (자사몰 브랜드)

`tools/config/company_mapping.py`:
```python
COMPANY_MAPPING = {
    "piscess": {
        "ko": "파이시스",
        "brands": ["파이시스", "PISCESS", "piscess", "Piscess"]
    }
}
```

트렌드 분석에서 자사 브랜드 식별 및 AI 리포트에서 브랜드명 변환에 사용됩니다.

---

## Error Handling

- **Tenacity**: API 호출 재시도 (3회, 5초 간격)
- **Cloud Run Jobs**: max-retries=3 설정
- **BigQuery MERGE**: 중복 방지 및 안전한 업데이트
- **Demo 계정**: 데이터 접근 제한으로 보안 유지

---

## File Naming Conventions

- **handlers/**: `*_handler.py` - API 라우트 핸들러
- **services/**: `*_service.py` - 비즈니스 로직
- **jobs/**: `*_job.py` - Cloud Run Job 진입점
- **docker/**: `Dockerfile-{기능명}` - 컨테이너 이미지
- **deploy_*.sh**: 배포 스크립트
- **check_*.sql**: 데이터 검증 쿼리
- **cleanup_*.sql**: 데이터 정리 쿼리

---

## Quick Reference

### 새 업체 추가 시
1. `company_info` 테이블에 업체 정보 추가
2. Cafe24 토큰 발급 및 `tokens.json` 업데이트
3. GA4 Property ID, Meta 광고 계정 연결
4. `user_accounts`에 사용자 계정 추가

### 새 Cloud Run Job 추가 시
1. `docker/Dockerfile-{기능명}` 생성
2. `deploy_{기능명}.sh` 배포 스크립트 작성
3. Pub/Sub 토픽 및 Cloud Scheduler 설정
4. `cloudbuild.yaml` 또는 수동 배포

### 문제 해결
- **데이터 누락**: 해당 날짜 핸들러 수동 실행
- **Job 실패**: Cloud Logging에서 로그 확인
- **성능 저하**: Redis 캐시 TTL 조정, BigQuery 쿼리 최적화

---

## Important Files for AI Assistant

코드 분석 시 우선 참조할 파일들:

1. **Flask 앱 구조**: `ngn_wep/dashboard/app.py`
2. **핵심 서비스**: `ngn_wep/dashboard/services/performance_summary_new.py`
3. **데이터 수집**: `ngn_wep/cafe24_api/daily_cafe24_sales_handler.py`
4. **배포 설정**: `cloudbuild.yaml`, `docker/Dockerfile-dashboard`
5. **테이블 스키마**: `BIGQUERY_TABLES_SCHEMA.md`
6. **브랜드 매핑**: `tools/config/company_mapping.py`
