#!/bin/bash

set -euo pipefail

# 월간 집계 Cloud Run Job 배포 스크립트

cd ~/ngn_board

PROJECT="winged-precept-443218-v8"
REGION_AR="asia-northeast1"
REGION_RUN="asia-northeast3"
REPO="ngn-dashboard"
JOB="monthly-rollup-job"
SA="439320386143-compute@developer.gserviceaccount.com"

IMAGE="${REGION_AR}-docker.pkg.dev/${PROJECT}/${REPO}/${JOB}:manual-$(date +%Y%m%d-%H%M%S)"

echo "🔨 1단계: Docker 이미지 빌드 중..."
# Dockerfile 임시 복사
cp docker/Dockerfile-monthly-rollup ./Dockerfile

# 빌드 + 푸시 (Cloud Build)
gcloud builds submit --tag "$IMAGE" .

# 임시 Dockerfile 제거
rm ./Dockerfile

echo ""
echo "🚀 2단계: Cloud Run Job 배포 중..."
# Job이 없으면 생성, 있으면 업데이트
if gcloud run jobs describe "$JOB" --region="$REGION_RUN" --project="$PROJECT" &>/dev/null; then
  echo "Job이 이미 존재합니다. 업데이트 중..."
  gcloud run jobs update "$JOB" \
    --image="$IMAGE" \
    --region="$REGION_RUN" \
    --service-account="$SA" \
    --memory=1Gi \
    --cpu=1 \
    --max-retries=3 \
    --task-timeout=1800s \
    --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT},BQ_DATASET=ngn_dataset" \
    --project="$PROJECT"
else
  echo "새 Job 생성 중..."
  gcloud run jobs create "$JOB" \
    --image="$IMAGE" \
    --region="$REGION_RUN" \
    --service-account="$SA" \
    --memory=1Gi \
    --cpu=1 \
    --max-retries=3 \
    --task-timeout=1800s \
    --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT},BQ_DATASET=ngn_dataset" \
    --project="$PROJECT"
fi

echo ""
echo "📢 3단계: Pub/Sub 토픽 생성 중..."
TOPIC_NAME="monthly-rollup-trigger"
gcloud pubsub topics create "$TOPIC_NAME" --project="$PROJECT" 2>/dev/null || echo "토픽이 이미 존재합니다."

echo ""
echo "📬 4단계: Pub/Sub 구독 생성 중..."
SUBSCRIPTION_NAME="monthly-rollup-sub"
JOB_RUN_ENDPOINT="https://${REGION_RUN}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT}/jobs/${JOB}:run"
gcloud pubsub subscriptions create "$SUBSCRIPTION_NAME" \
  --topic="$TOPIC_NAME" \
  --ack-deadline=20 \
  --push-endpoint="$JOB_RUN_ENDPOINT" \
  --push-auth-service-account="$SA" \
  --project="$PROJECT" 2>/dev/null || echo "구독이 이미 존재합니다."

echo ""
echo "⏰ 5단계: Cloud Scheduler 작업 생성 중..."
if gcloud scheduler jobs describe monthly-rollup-scheduler --location="$REGION_RUN" --project="$PROJECT" &>/dev/null; then
  echo "스케줄러가 이미 존재합니다. 업데이트 중..."
  gcloud scheduler jobs update pubsub monthly-rollup-scheduler \
    --location="$REGION_RUN" \
    --schedule="0 4 1 * *" \
    --topic="$TOPIC_NAME" \
    --message-body='{"trigger":"monthly"}' \
    --time-zone="Asia/Seoul" \
    --project="$PROJECT"
else
  gcloud scheduler jobs create pubsub monthly-rollup-scheduler \
    --location="$REGION_RUN" \
    --schedule="0 4 1 * *" \
    --topic="$TOPIC_NAME" \
    --message-body='{"trigger":"monthly"}' \
    --time-zone="Asia/Seoul" \
    --project="$PROJECT"
fi

echo ""
echo "✅ 모든 설정 완료!"
echo ""
echo "📋 생성된 리소스:"
echo "  - Cloud Run Job: ${JOB_NAME}"
echo "  - Pub/Sub Topic: ${TOPIC_NAME}"
echo "  - Pub/Sub Subscription: ${SUBSCRIPTION_NAME}"
echo "  - Cloud Scheduler: monthly-rollup-scheduler (매월 1일 새벽 4시 한국시간 실행)"
echo ""
echo "📝 수동 실행:"
echo "  gcloud run jobs execute ${JOB_NAME} --region=${REGION} --project=${PROJECT_ID}"

