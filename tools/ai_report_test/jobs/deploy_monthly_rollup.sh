#!/bin/bash

# 월간 집계 Cloud Run Job 배포 및 스케줄러 설정 스크립트

PROJECT_ID="winged-precept-443218-v8"
JOB_NAME="monthly-rollup-job"
TOPIC_NAME="monthly-rollup-trigger"
SUBSCRIPTION_NAME="monthly-rollup-sub"
REGION="asia-northeast3"
IMAGE_NAME="gcr.io/${PROJECT_ID}/monthly-rollup"
SERVICE_ACCOUNT="439320386143-compute@developer.gserviceaccount.com"

echo "🔨 1단계: Docker 이미지 빌드 중..."
cd ../../..  # 프로젝트 루트로 이동
gcloud builds submit --tag ${IMAGE_NAME} --project ${PROJECT_ID} --file docker/Dockerfile-monthly-rollup

echo ""
echo "🚀 2단계: Cloud Run Job 배포 중..."
gcloud run jobs create ${JOB_NAME} \
  --image=${IMAGE_NAME} \
  --region=${REGION} \
  --project=${PROJECT_ID} \
  --service-account=${SERVICE_ACCOUNT} \
  --memory=1Gi \
  --cpu=1 \
  --max-retries=3 \
  --task-timeout=1800s \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT_ID},BQ_DATASET=ngn_dataset" \
  --project=${PROJECT_ID}

echo ""
echo "📢 3단계: Pub/Sub 토픽 생성 중..."
gcloud pubsub topics create ${TOPIC_NAME} --project=${PROJECT_ID} || echo "토픽이 이미 존재합니다."

echo ""
echo "📬 4단계: Pub/Sub 구독 생성 중..."
JOB_RUN_ENDPOINT="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${JOB_NAME}:run"
gcloud pubsub subscriptions create ${SUBSCRIPTION_NAME} \
  --topic=${TOPIC_NAME} \
  --ack-deadline=20 \
  --push-endpoint=${JOB_RUN_ENDPOINT} \
  --push-auth-service-account=${SERVICE_ACCOUNT} \
  --project=${PROJECT_ID} || echo "구독이 이미 존재합니다."

echo ""
echo "⏰ 5단계: Cloud Scheduler 작업 생성 중..."
gcloud scheduler jobs create pubsub monthly-rollup-scheduler \
  --location=${REGION} \
  --schedule="0 3 1 * *" \
  --topic=${TOPIC_NAME} \
  --message-body='{"trigger":"monthly"}' \
  --project=${PROJECT_ID} || echo "스케줄러가 이미 존재합니다. 업데이트하려면 'gcloud scheduler jobs update'를 사용하세요."

echo ""
echo "✅ 모든 설정 완료!"
echo ""
echo "📋 생성된 리소스:"
echo "  - Cloud Run Job: ${JOB_NAME}"
echo "  - Pub/Sub Topic: ${TOPIC_NAME}"
echo "  - Pub/Sub Subscription: ${SUBSCRIPTION_NAME}"
echo "  - Cloud Scheduler: monthly-rollup-scheduler (매월 1일 새벽 3시 실행)"
echo ""
echo "📝 수동 실행:"
echo "  gcloud run jobs execute ${JOB_NAME} --region=${REGION} --project=${PROJECT_ID}"

