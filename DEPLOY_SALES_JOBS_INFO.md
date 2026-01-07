# daily_cafe24_sales_handler.py 관련 Cloud Run Jobs 재배포 가이드

## 관련 파일 및 잡 정보

### 관련 Python 파일
- `ngn_wep/cafe24_api/daily_cafe24_sales_handler.py` (환불 집계 로직 수정 완료)

### Cloud Run Jobs (2개)
1. **query-sales-today-job**
   - Dockerfile: `docker/Dockerfile-sales-today`
   - 실행: `python daily_cafe24_sales_handler.py today`

2. **query-sales-yesterday-job**
   - Dockerfile: `docker/Dockerfile-sales-yesterday`
   - 실행: `python daily_cafe24_sales_handler.py yesterday`

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

