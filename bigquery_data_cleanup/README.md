# BigQuery 데이터 자동 정리 서비스

13개월 이전 데이터를 자동으로 삭제하는 Cloud Run 서비스입니다.

## 배포 전 확인 (중요!)

### 0. 테이블 구조 확인 (먼저 실행!)

실제 테이블의 날짜 컬럼과 타입을 확인합니다:

```bash
# 로컬에서 실행하거나 Cloud Shell에서 실행
cd bigquery_data_cleanup
python check_tables.py
```

이 스크립트는 모든 테이블의 날짜 컬럼을 확인하고 출력합니다.
결과를 확인한 후 `main.py`의 `TABLE_DATE_COLUMNS` 딕셔너리를 필요에 따라 수정하세요.

## 배포 방법

### 1. Cloud Shell에서 파일 업로드

```bash
# 프로젝트 디렉토리로 이동
cd ~/ngn_dashboard

# 파일 업로드 (로컬에서 실행)
# 또는 Cloud Shell에서 직접 파일 생성
```

### 2. Cloud Run 배포

```bash
cd bigquery_data_cleanup

# 배포 스크립트 실행
chmod +x deploy.sh
./deploy.sh
```

또는 수동 배포:

```bash
PROJECT_ID="winged-precept-443218-v8"
SERVICE_NAME="bigquery-data-cleanup"
REGION="asia-northeast3"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# Docker 이미지 빌드
gcloud builds submit --tag ${IMAGE_NAME} --project ${PROJECT_ID}

# Cloud Run 배포
gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE_NAME} \
  --platform managed \
  --region ${REGION} \
  --project ${PROJECT_ID} \
  --allow-unauthenticated \
  --memory 512Mi \
  --timeout 540s \
  --max-instances 1 \
  --set-env-vars PROJECT_ID=${PROJECT_ID},DATASET_ID=ngn_dataset,MONTHS_TO_KEEP=13
```

### 3. Cloud Scheduler 설정 (매월 1일 새벽 2시 실행)

```bash
REGION="asia-northeast3"
SERVICE_NAME="bigquery-data-cleanup"
PROJECT_ID="winged-precept-443218-v8"

# 서비스 URL 가져오기
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
  --region=${REGION} \
  --format='value(status.url)')

# 스케줄러 생성 (매월 1일 새벽 2시)
gcloud scheduler jobs create http bigquery-cleanup-monthly \
  --location=${REGION} \
  --schedule="0 2 1 * *" \
  --uri="${SERVICE_URL}" \
  --http-method=POST \
  --project=${PROJECT_ID}
```

## 수동 실행

```bash
# 서비스 URL 가져오기
SERVICE_URL=$(gcloud run services describe bigquery-data-cleanup \
  --region=asia-northeast3 \
  --format='value(status.url)')

# 수동 실행
curl -X POST ${SERVICE_URL}
```

## 환경 변수

- `PROJECT_ID`: GCP 프로젝트 ID (기본값: winged-precept-443218-v8)
- `DATASET_ID`: BigQuery 데이터셋 ID (기본값: ngn_dataset)
- `MONTHS_TO_KEEP`: 보관할 개월 수 (기본값: 13)

## 로그 확인

```bash
gcloud run services logs read bigquery-data-cleanup \
  --region=asia-northeast3 \
  --limit=50
```
