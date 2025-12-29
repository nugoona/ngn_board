#!/bin/bash

# BigQuery 데이터 정리 Cloud Run Job 배포 및 Pub/Sub 설정 스크립트

PROJECT_ID="winged-precept-443218-v8"
JOB_NAME="bigquery-data-cleanup-job"
TOPIC_NAME="bigquery-data-cleanup"
SUBSCRIPTION_NAME="bigquery-data-cleanup-sub"
REGION="asia-northeast3"
IMAGE_NAME="gcr.io/${PROJECT_ID}/bigquery-data-cleanup"
SERVICE_ACCOUNT="439320386143-compute@developer.gserviceaccount.com"

echo "🔨 1단계: Docker 이미지 빌드 중..."
gcloud builds submit --tag ${IMAGE_NAME} --project ${PROJECT_ID}

echo ""
echo "🚀 2단계: Cloud Run Job 배포 중..."
gcloud run jobs create ${JOB_NAME} \
  --image=${IMAGE_NAME} \
  --region=${REGION} \
  --project=${PROJECT_ID} \
  --service-account=${SERVICE_ACCOUNT} \
  --memory=512Mi \
  --cpu=1 \
  --max-retries=3 \
  --task-timeout=600s \
  --set-env-vars="PROJECT_ID=${PROJECT_ID},DATASET_ID=ngn_dataset,MONTHS_TO_KEEP=13" \
  --set-secrets="GOOGLE_APPLICATION_CREDENTIALS=/app/service-account.json:latest"

echo ""
echo "📢 3단계: Pub/Sub 토픽 생성 중..."
gcloud pubsub topics create ${TOPIC_NAME} --project=${PROJECT_ID}

echo ""
echo "📬 4단계: Pub/Sub 구독 생성 중..."
JOB_RUN_ENDPOINT="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${JOB_NAME}:run"
gcloud pubsub subscriptions create ${SUBSCRIPTION_NAME} \
  --topic=${TOPIC_NAME} \
  --ack-deadline=20 \
  --push-endpoint=${JOB_RUN_ENDPOINT} \
  --push-auth-service-account=${SERVICE_ACCOUNT} \
  --project=${PROJECT_ID}

echo ""
echo "⏰ 5단계: Cloud Scheduler 작업 생성 중..."
gcloud scheduler jobs create pubsub bigquery-cleanup-monthly \
  --location=${REGION} \
  --schedule="0 2 1 * *" \
  --topic=${TOPIC_NAME} \
  --message-body='{"trigger":"monthly"}' \
  --project=${PROJECT_ID}

echo ""
echo "✅ 모든 설정 완료!"
echo ""
echo "📋 생성된 리소스:"
echo "  - Cloud Run Job: ${JOB_NAME}"
echo "  - Pub/Sub Topic: ${TOPIC_NAME}"
echo "  - Pub/Sub Subscription: ${SUBSCRIPTION_NAME}"
echo "  - Cloud Scheduler: bigquery-cleanup-monthly (매월 1일 새벽 2시 실행)"






