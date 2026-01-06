#!/bin/bash

set -euo pipefail

# 29CM 경쟁사 비교 스냅샷 생성 Cloud Run Job 배포 스크립트
# 매일 오전 8시 (한국시간) 실행

cd ~/ngn_board || {
  echo "❌ [ERROR] ~/ngn_board 디렉토리로 이동할 수 없습니다."
  echo "   현재 디렉토리: $(pwd)"
  exit 1
}

PROJECT="winged-precept-443218-v8"
REGION_AR="asia-northeast1"
REGION_RUN="asia-northeast3"
REPO="ngn-dashboard"
JOB="compare-29cm-snapshot-job"
SA="439320386143-compute@developer.gserviceaccount.com"

IMAGE="${REGION_AR}-docker.pkg.dev/${PROJECT}/${REPO}/${JOB}:manual-$(date +%Y%m%d-%H%M%S)"

echo "🔨 1단계: Docker 이미지 빌드 중..."
# Dockerfile 확인
if [ ! -f "docker/Dockerfile-compare-29cm-snapshot" ]; then
  echo "❌ [ERROR] docker/Dockerfile-compare-29cm-snapshot 파일을 찾을 수 없습니다."
  exit 1
fi

# Dockerfile 임시 복사
cp docker/Dockerfile-compare-29cm-snapshot ./Dockerfile

# 빌드 + 푸시 (Cloud Build)
if ! gcloud builds submit --tag "$IMAGE" .; then
  echo "❌ [ERROR] Docker 이미지 빌드 실패"
  rm -f ./Dockerfile
  exit 1
fi

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
    --memory=2Gi \
    --cpu=2 \
    --max-retries=3 \
    --task-timeout=3600s \
    --update-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT},BQ_DATASET=ngn_dataset,GCS_BUCKET=winged-precept-443218-v8.appspot.com" \
    --project="$PROJECT"
else
  echo "새 Job 생성 중..."
  gcloud run jobs create "$JOB" \
    --image="$IMAGE" \
    --region="$REGION_RUN" \
    --service-account="$SA" \
    --memory=2Gi \
    --cpu=2 \
    --max-retries=3 \
    --task-timeout=3600s \
    --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT},BQ_DATASET=ngn_dataset,GCS_BUCKET=winged-precept-443218-v8.appspot.com" \
    --project="$PROJECT"
fi

echo ""
echo "📢 3단계: Pub/Sub 토픽 생성 중..."
TOPIC_NAME="compare-29cm-snapshot-trigger"
gcloud pubsub topics create "$TOPIC_NAME" --project="$PROJECT" 2>/dev/null || echo "토픽이 이미 존재합니다."

echo ""
echo "📬 4단계: Pub/Sub 구독 생성 중..."
SUBSCRIPTION_NAME="compare-29cm-snapshot-sub"
JOB_RUN_ENDPOINT="https://${REGION_RUN}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT}/jobs/${JOB}:run"
gcloud pubsub subscriptions create "$SUBSCRIPTION_NAME" \
  --topic="$TOPIC_NAME" \
  --ack-deadline=20 \
  --push-endpoint="$JOB_RUN_ENDPOINT" \
  --push-auth-service-account="$SA" \
  --project="$PROJECT" 2>/dev/null || echo "구독이 이미 존재합니다."

echo ""
echo "⏰ 5단계: Cloud Scheduler 작업 생성 중..."
# 한국시간 매일 오전 8시 = cron "0 8 * * *"
SCHEDULER_NAME="compare-29cm-snapshot-scheduler"
if gcloud scheduler jobs describe "$SCHEDULER_NAME" --location="$REGION_RUN" --project="$PROJECT" &>/dev/null; then
  echo "스케줄러가 이미 존재합니다. 업데이트 중..."
  gcloud scheduler jobs update pubsub "$SCHEDULER_NAME" \
    --location="$REGION_RUN" \
    --schedule="0 8 * * *" \
    --topic="$TOPIC_NAME" \
    --message-body='{"trigger":"daily"}' \
    --time-zone="Asia/Seoul" \
    --project="$PROJECT"
else
  gcloud scheduler jobs create pubsub "$SCHEDULER_NAME" \
    --location="$REGION_RUN" \
    --schedule="0 8 * * *" \
    --topic="$TOPIC_NAME" \
    --message-body='{"trigger":"daily"}' \
    --time-zone="Asia/Seoul" \
    --project="$PROJECT"
fi

echo ""
echo "✅ 모든 설정 완료!"
echo ""
echo "📋 생성된 리소스:"
echo "  - Cloud Run Job: ${JOB}"
echo "  - Pub/Sub Topic: ${TOPIC_NAME}"
echo "  - Pub/Sub Subscription: ${SUBSCRIPTION_NAME}"
echo "  - Cloud Scheduler: ${SCHEDULER_NAME} (매일 오전 8시 한국시간 실행)"
echo ""
echo "📝 수동 실행:"
echo "  gcloud run jobs execute ${JOB} --region=${REGION_RUN} --project=${PROJECT}"
echo ""
echo "✅ 배포 완료!"

