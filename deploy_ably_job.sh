#!/bin/bash

set -euo pipefail

# ====================================================
# [설정] 에이블리 베스트 수집기 자동 배포 스크립트
# ====================================================

# 작업 디렉토리 이동
cd ~/ngn_board

# 프로젝트 및 리소스 설정
PROJECT="winged-precept-443218-v8"
REGION_AR="asia-northeast1"
REGION_RUN="asia-northeast3" # 서울 리전
REPO="ngn-dashboard"

# 1. 자동 생성된 이름들
JOB="ably-best-collector-job"               # Cloud Run Job 이름
TOPIC_NAME="ably-best-trigger-topic"        # Pub/Sub 토픽 이름
SUBSCRIPTION_NAME="ably-best-job-sub"       # Pub/Sub 구독 이름
SCHEDULER_NAME="ably-best-weekly-scheduler" # 스케줄러 이름

# 서비스 계정 (기존 것 활용)
SA="439320386143-compute@developer.gserviceaccount.com"

# 이미지 태그 생성
IMAGE="${REGION_AR}-docker.pkg.dev/${PROJECT}/${REPO}/${JOB}:auto-$(date +%Y%m%d-%H%M%S)"

echo "🔨 1단계: Docker 이미지 빌드 중... (Ably Crawler)"

# Dockerfile 임시 복사 (에이블리용 Dockerfile 사용)
# 주의: 이전에 만든 docker/Dockerfile-ably-best 파일이 존재해야 합니다.
if [ -f "docker/Dockerfile-ably-best" ]; then
    cp docker/Dockerfile-ably-best ./Dockerfile
else
    echo "❌ 에러: docker/Dockerfile-ably-best 파일을 찾을 수 없습니다."
    exit 1
fi

# 빌드 + 푸시 (Cloud Build)
gcloud builds submit --tag "$IMAGE" .

# 임시 Dockerfile 제거
rm ./Dockerfile

echo ""
echo "🚀 2단계: Cloud Run Job 배포 중..."

# 크롬 브라우저 구동을 위해 메모리 2Gi, CPU 2로 상향 조정함
if gcloud run jobs describe "$JOB" --region="$REGION_RUN" --project="$PROJECT" &>/dev/null; then
  echo "Job이 이미 존재합니다. 업데이트 중..."
  gcloud run jobs update "$JOB" \
    --image="$IMAGE" \
    --region="$REGION_RUN" \
    --service-account="$SA" \
    --memory=2Gi \
    --cpu=2 \
    --max-retries=1 \
    --task-timeout=600s \
    --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT},BQ_DATASET=ngn_dataset" \
    --project="$PROJECT"
else
  echo "새 Job 생성 중..."
  gcloud run jobs create "$JOB" \
    --image="$IMAGE" \
    --region="$REGION_RUN" \
    --service-account="$SA" \
    --memory=2Gi \
    --cpu=2 \
    --max-retries=1 \
    --task-timeout=600s \
    --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT},BQ_DATASET=ngn_dataset" \
    --project="$PROJECT"
fi

echo ""
echo "📢 3단계: Pub/Sub 토픽 생성 중..."
gcloud pubsub topics create "$TOPIC_NAME" --project="$PROJECT" 2>/dev/null || echo "토픽이 이미 존재합니다."

echo ""
echo "📬 4단계: Pub/Sub 구독 생성 중..."
JOB_RUN_ENDPOINT="https://${REGION_RUN}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT}/jobs/${JOB}:run"

gcloud pubsub subscriptions create "$SUBSCRIPTION_NAME" \
  --topic="$TOPIC_NAME" \
  --ack-deadline=20 \
  --push-endpoint="$JOB_RUN_ENDPOINT" \
  --push-auth-service-account="$SA" \
  --project="$PROJECT" 2>/dev/null || echo "구독이 이미 존재합니다."

echo ""
echo "⏰ 5단계: Cloud Scheduler 작업 생성 중..."
# 스케줄: 매주 월요일 오전 7시 (CRON: 0 7 * * 1)
CRON_SCHEDULE="0 7 * * 1"

if gcloud scheduler jobs describe "$SCHEDULER_NAME" --location="$REGION_RUN" --project="$PROJECT" &>/dev/null; then
  echo "스케줄러가 이미 존재합니다. 업데이트 중..."
  gcloud scheduler jobs update pubsub "$SCHEDULER_NAME" \
    --location="$REGION_RUN" \
    --schedule="$CRON_SCHEDULE" \
    --topic="$TOPIC_NAME" \
    --message-body='{"trigger":"weekly"}' \
    --time-zone="Asia/Seoul" \
    --project="$PROJECT"
else
  echo "스케줄러 생성 중: 매주 월요일 오전 7시"
  gcloud scheduler jobs create pubsub "$SCHEDULER_NAME" \
    --location="$REGION_RUN" \
    --schedule="$CRON_SCHEDULE" \
    --topic="$TOPIC_NAME" \
    --message-body='{"trigger":"weekly"}' \
    --time-zone="Asia/Seoul" \
    --project="$PROJECT"
fi

echo ""
echo "✅ 배포 및 스케줄링 완료!"
echo ""
echo "📋 리소스 정보:"
echo "  - Job: ${JOB} (Memory: 2Gi, CPU: 2)"
echo "  - Scheduler: ${SCHEDULER_NAME} (매주 월요일 07:00 KST)"
echo ""
echo "📝 즉시 테스트 실행 명령어:"
echo "  gcloud run jobs execute ${JOB} --region=${REGION_RUN} --project=${PROJECT}"
