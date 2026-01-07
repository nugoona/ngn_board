# daily_cafe24_sales_handler.py 관련 Cloud Run Jobs 재배포 가이드

## 관련 파일 및 잡 정보

### 관련 Python 파일
- `ngn_wep/cafe24_api/daily_cafe24_sales_handler.py` (환불 집계 로직 수정 완료)

### Cloud Run Jobs (3개)
1. **query-sales-today-job**
   - Dockerfile: `docker/Dockerfile-sales-today`
   - 실행: `python daily_cafe24_sales_handler.py today`

2. **query-sales-yesterday-job**
   - Dockerfile: `docker/Dockerfile-sales-yesterday`
   - 실행: `python daily_cafe24_sales_handler.py yesterday`

3. **query-sales-prev-month-job** ⭐ NEW
   - Dockerfile: `docker/Dockerfile-sales-prev-month`
   - 실행: `python daily_cafe24_sales_prev_month.py`
   - 목적: 매월 5일경 지난달 데이터 재수집 (정확도 향상)
   - 배포: `deploy_sales_prev_month_job_windows.bat` 또는 `deploy_sales_prev_month_job.sh`

## 배포 명령어 (Windows PowerShell/CMD)

### 1. query-sales-today-job 배포

```powershell
$TIMESTAMP = Get-Date -Format "yyyyMMdd-HHmmss"
$JOB = "query-sales-today-job"
$IMAGE = "asia-northeast1-docker.pkg.dev/winged-precept-443218-v8/ngn-dashboard/$JOB`:manual-$TIMESTAMP"

# 이미지 빌드
gcloud builds submit --tag $IMAGE --dockerfile="docker/Dockerfile-sales-today" .

# Job 업데이트
gcloud run jobs update $JOB `
  --image $IMAGE `
  --region="asia-northeast3" `
  --service-account="439320386143-compute@developer.gserviceaccount.com" `
  --memory=512Mi `
  --cpu=1 `
  --max-retries=3 `
  --task-timeout=600s
```

### 2. query-sales-yesterday-job 배포

```powershell
$TIMESTAMP = Get-Date -Format "yyyyMMdd-HHmmss"
$JOB = "query-sales-yesterday-job"
$IMAGE = "asia-northeast1-docker.pkg.dev/winged-precept-443218-v8/ngn-dashboard/$JOB`:manual-$TIMESTAMP"

# 이미지 빌드
gcloud builds submit --tag $IMAGE --dockerfile="docker/Dockerfile-sales-yesterday" .

# Job 업데이트
gcloud run jobs update $JOB `
  --image $IMAGE `
  --region="asia-northeast3" `
  --service-account="439320386143-compute@developer.gserviceaccount.com" `
  --memory=512Mi `
  --cpu=1 `
  --max-retries=3 `
  --task-timeout=600s
```

## 주요 변경 사항

환불 집계 로직이 **payment_date 기준**에서 **refund_date 기준**으로 변경되었습니다:

- 변경 전: 원래 주문 결제일 기준으로 환불 집계
- 변경 후: 환불 발생일 기준으로 환불 집계

이 변경으로 인해 대시보드의 환불 합계가 정확하게 표시됩니다 (예: 2025-12월 환불 1,681,674원).

## query-sales-prev-month-job 설정

### 목적
매월 지난달 데이터를 재수집하여 정확도를 향상시킵니다.

### 장점
1. **카페24 데이터 변경 반영**: 월말 정산 후 카페24에서 과거 데이터를 수정하는 경우 자동 반영
2. **배송비/환불 정산 반영**: 월말 정산 후 최종 확정된 데이터로 재집계
3. **정확도 향상**: 월별 매출 리포트의 신뢰도 향상

### 실행 스케줄
- **매월 5일 오전 3시 (한국시간)**
- 월말 정산 후 데이터가 안정화되는 시점 고려

### 스케줄러 설정
```bash
bash setup_sales_prev_month_scheduler.sh
```

또는 수동 설정:
```bash
# Pub/Sub 토픽 생성
gcloud pubsub topics create sales-prev-month-trigger \
  --project=winged-precept-443218-v8

# Pub/Sub 구독 생성
gcloud pubsub subscriptions create sales-prev-month-sub \
  --topic=sales-prev-month-trigger \
  --ack-deadline=20 \
  --push-endpoint="https://asia-northeast3-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/winged-precept-443218-v8/jobs/query-sales-prev-month-job:run" \
  --push-auth-service-account=439320386143-compute@developer.gserviceaccount.com \
  --project=winged-precept-443218-v8

# Cloud Scheduler 생성 (매월 5일 오전 3시)
gcloud scheduler jobs create pubsub sales-prev-month-scheduler \
  --location=asia-northeast3 \
  --schedule="0 3 5 * *" \
  --topic=sales-prev-month-trigger \
  --message-body='{"trigger":"monthly"}' \
  --time-zone="Asia/Seoul" \
  --project=winged-precept-443218-v8
```

**Cron 표현식 설명:**
- `0 3 5 * *`: 매월 5일 3시 0분에 실행
- 형식: 분 시 일 월 요일

### 수동 실행
```bash
gcloud run jobs execute query-sales-prev-month-job --region=asia-northeast3
```

