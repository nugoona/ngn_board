# query-sales-prev-month-job 개요

## 목적

매월 지난달 `daily_cafe24_sales` 데이터를 삭제 후 재수집하여 정확도를 향상시킵니다.

## 배경

### 문제점
1. **카페24 데이터 변경**: 월말 정산 후 카페24에서 과거 데이터를 수정하는 경우가 있음
2. **배송비/환불 정산**: 월말 정산 후 배송비나 환불 금액이 최종 확정됨
3. **데이터 불일치**: 월별 리포트와 실제 카페24 데이터 간 차이 발생 가능

### 해결책
- 매월 5일경 지난달 전체 데이터를 삭제하고 최신 카페24 원본 데이터로 재수집
- 월말 정산 후 안정화된 데이터로 재집계하여 정확도 향상

## 실행 주기

- **스케줄**: 매월 5일 오전 3시 (한국시간)
- **Cron 표현식**: `0 3 5 * *`
- **이유**: 월말 정산 후 데이터가 안정화되는 시점 고려

## 파일 구조

### Python 스크립트
- `ngn_wep/cafe24_api/daily_cafe24_sales_prev_month.py`
  - 지난달 기간 자동 계산
  - 데이터 삭제 후 재수집
  - 진행 상황 로그 출력

### Dockerfile
- `docker/Dockerfile-sales-prev-month`
  - Python 3.11 slim 기반
  - 필요한 의존성 설치

### 배포 스크립트
- `deploy_sales_prev_month_job_windows.bat` (Windows)
- `deploy_sales_prev_month_job.sh` (Linux/Mac)

### 스케줄러 설정
- `setup_sales_prev_month_scheduler.sh`
  - Pub/Sub 토픽 생성
  - Pub/Sub 구독 생성
  - Cloud Scheduler 생성

## 배포 방법

### 1. Cloud Run Job 배포

#### Linux/Mac
```bash
# 2-1. 변수 설정
TIMESTAMP=$(date +"%Y%m%d-%H%M%S")
PROJECT="winged-precept-443218-v8"
IMAGE="asia-northeast1-docker.pkg.dev/$PROJECT/ngn-dashboard/query-sales-prev-month-job:manual-$TIMESTAMP"

# 2-2. Dockerfile을 루트로 복사
cp docker/Dockerfile-sales-prev-month ./Dockerfile

# 2-3. 빌드 및 업데이트 실행
gcloud builds submit --tag="$IMAGE" --project="$PROJECT" . && \
gcloud run jobs update query-sales-prev-month-job --image="$IMAGE" --region="asia-northeast3" --project="$PROJECT" --service-account="439320386143-compute@developer.gserviceaccount.com" --memory=1Gi --cpu=1 --max-retries=2 --task-timeout=3600s

# 2-4. 임시 파일 삭제
rm ./Dockerfile
```

또는 스크립트 파일 사용:
```bash
bash deploy_sales_prev_month_job.sh
```

#### Windows
```batch
deploy_sales_prev_month_job_windows.bat
```

### 2. 스케줄러 설정

```bash
bash setup_sales_prev_month_scheduler.sh
```

## 수동 실행

```bash
gcloud run jobs execute query-sales-prev-month-job --region=asia-northeast3
```

## 처리 프로세스

1. **지난달 기간 계산**: 현재 날짜 기준으로 지난달 1일 ~ 마지막일 계산
2. **기존 데이터 삭제**: 지난달 전체 `daily_cafe24_sales` 데이터 삭제
3. **재수집**: 일별로 순차 처리
   - 각 날짜별로 `cafe24_orders`와 `cafe24_refunds_table`에서 데이터 집계
   - `daily_cafe24_sales` 테이블에 MERGE

## 예상 실행 시간

- **데이터량에 따라 다름**: 약 30분 ~ 1시간
- **설정**: `task-timeout=3600s` (1시간)

## 리소스 설정

- **Memory**: 1Gi (월 전체 데이터 처리)
- **CPU**: 1 vCPU
- **Max Retries**: 2회
- **Task Timeout**: 3600s (1시간)

## 주의사항

1. **데이터 삭제**: 지난달 전체 데이터를 삭제하므로 실행 시 주의
2. **실행 시간**: 월 전체 데이터를 처리하므로 시간이 소요됨
3. **비용**: BigQuery 쿼리 비용 발생 (월 1TB 무료 할당량 내에서 처리 가능)

## 비용 추정

- **BigQuery 스캔**: 월 1TB 무료 할당량 내 (추정 100-200MB)
- **Cloud Run**: 실행 시간 × 리소스 사용량 (약 $0.10-0.20)

## 장점

1. ✅ **정확도 향상**: 월말 정산 후 최종 확정 데이터 반영
2. ✅ **자동화**: 매월 자동 실행으로 수동 작업 불필요
3. ✅ **일관성**: 월별 리포트 데이터 일관성 유지

## 참고

- 관련 파일: `DEPLOY_SALES_JOBS_INFO.md`
- 쿼리 로직: `daily_cafe24_sales_handler.py`와 동일

