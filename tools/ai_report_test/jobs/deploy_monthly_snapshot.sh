#!/bin/bash

set -euo pipefail

# 월간 스냅샷 생성 및 AI 분석 Cloud Run Job 배포 스크립트

cd ~/ngn_board || {
  echo "❌ [ERROR] ~/ngn_board 디렉토리로 이동할 수 없습니다."
  echo "   현재 디렉토리: $(pwd)"
  exit 1
}

# config/ngn.env 또는 .env 파일에서 GEMINI_API_KEY 로드
if [ -f config/ngn.env ]; then
  GEMINI_API_KEY=$(grep -v '^#' config/ngn.env | grep "^GEMINI_API_KEY=" | cut -d'=' -f2- | tr -d '"' | tr -d "'" | xargs)
  export GEMINI_API_KEY
  echo "✅ config/ngn.env에서 GEMINI_API_KEY 로드"
elif [ -f .env ]; then
  GEMINI_API_KEY=$(grep -v '^#' .env | grep "^GEMINI_API_KEY=" | cut -d'=' -f2- | tr -d '"' | tr -d "'" | xargs)
  export GEMINI_API_KEY
  echo "✅ .env에서 GEMINI_API_KEY 로드"
fi

# GEMINI_API_KEY 확인
if [ -z "${GEMINI_API_KEY:-}" ]; then
  echo "❌ [ERROR] GEMINI_API_KEY가 설정되지 않았습니다."
  echo "   .env 파일에 GEMINI_API_KEY=your-key 형식으로 추가해주세요."
  exit 1
fi

echo "✅ GEMINI_API_KEY 로드 완료 (길이: ${#GEMINI_API_KEY}자)"

PROJECT="winged-precept-443218-v8"
REGION_AR="asia-northeast1"
REGION_RUN="asia-northeast3"
REPO="ngn-dashboard"
JOB="monthly-snapshot-job"
SA="439320386143-compute@developer.gserviceaccount.com"

IMAGE="${REGION_AR}-docker.pkg.dev/${PROJECT}/${REPO}/${JOB}:manual-$(date +%Y%m%d-%H%M%S)"

echo "🔨 1단계: Docker 이미지 빌드 중..."
# Dockerfile 임시 복사
cp docker/Dockerfile-monthly-snapshot ./Dockerfile

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
    --memory=2Gi \
    --cpu=2 \
    --max-retries=3 \
    --task-timeout=3600s \
    --update-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT}" \
    --update-env-vars="BQ_DATASET=ngn_dataset" \
    --update-env-vars="GCS_BUCKET=winged-precept-443218-v8.appspot.com" \
    --update-env-vars="COMPANY_NAMES=piscess,demo" \
    --update-env-vars="GEMINI_API_KEY=${GEMINI_API_KEY}" \
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
    --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT},BQ_DATASET=ngn_dataset,GCS_BUCKET=winged-precept-443218-v8.appspot.com,COMPANY_NAMES=piscess,demo,GEMINI_API_KEY=${GEMINI_API_KEY}" \
    --project="$PROJECT"
fi

echo ""
echo "📢 3단계: Pub/Sub 토픽 생성 중..."
TOPIC_NAME="monthly-snapshot-trigger"
gcloud pubsub topics create "$TOPIC_NAME" --project="$PROJECT" 2>/dev/null || echo "토픽이 이미 존재합니다."

echo ""
echo "📬 4단계: Pub/Sub 구독 생성 중..."
SUBSCRIPTION_NAME="monthly-snapshot-sub"
JOB_RUN_ENDPOINT="https://${REGION_RUN}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT}/jobs/${JOB}:run"
gcloud pubsub subscriptions create "$SUBSCRIPTION_NAME" \
  --topic="$TOPIC_NAME" \
  --ack-deadline=20 \
  --push-endpoint="$JOB_RUN_ENDPOINT" \
  --push-auth-service-account="$SA" \
  --project="$PROJECT" 2>/dev/null || echo "구독이 이미 존재합니다."

echo ""
echo "⏰ 5단계: Cloud Scheduler 작업 생성 중..."
# 한국시간 오전 6시 = UTC 21시 (전날)
if gcloud scheduler jobs describe monthly-snapshot-scheduler --location="$REGION_RUN" --project="$PROJECT" &>/dev/null; then
  echo "스케줄러가 이미 존재합니다. 업데이트 중..."
  gcloud scheduler jobs update pubsub monthly-snapshot-scheduler \
    --location="$REGION_RUN" \
    --schedule="0 21 1 * *" \
    --topic="$TOPIC_NAME" \
    --message-body='{"trigger":"monthly"}' \
    --time-zone="Asia/Seoul" \
    --project="$PROJECT"
else
  gcloud scheduler jobs create pubsub monthly-snapshot-scheduler \
    --location="$REGION_RUN" \
    --schedule="0 6 1 * *" \
    --topic="$TOPIC_NAME" \
    --message-body='{"trigger":"monthly"}' \
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
echo "  - Cloud Scheduler: monthly-snapshot-scheduler (매월 1일 오전 6시 한국시간 실행)"
echo ""
echo "📝 수동 실행:"
echo "  gcloud run jobs execute ${JOB} --region=${REGION_RUN} --project=${PROJECT}"
echo ""
echo "✅ GEMINI_API_KEY가 .env 파일에서 자동으로 로드되었습니다."

