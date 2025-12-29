#!/bin/bash

set -euo pipefail

# 29CM BEST 주간/월간 Job 배포 스크립트

cd ~/ngn_board

PROJECT="winged-precept-443218-v8"
REGION_AR="asia-northeast1"
REGION_RUN="asia-northeast3"
REPO="ngn-dashboard"
JOB_WEEKLY="ngn-29cm-best-job"
JOB_MONTHLY="ngn-29cm-best-monthly-job"
SA="439320386143-compute@developer.gserviceaccount.com"

# =========================
# 1) 주간 Job 배포
# =========================
echo "🔨 1단계: 주간 Job Docker 이미지 빌드 중..."
IMAGE_WEEKLY="${REGION_AR}-docker.pkg.dev/${PROJECT}/${REPO}/${JOB_WEEKLY}:manual-$(date +%Y%m%d-%H%M%S)"

# Dockerfile 임시 복사
cp docker/Dockerfile-29cm-best ./Dockerfile

# 빌드 + 푸시
gcloud builds submit --tag "$IMAGE_WEEKLY" .

# 임시 Dockerfile 제거
rm ./Dockerfile

echo ""
echo "🚀 2단계: 주간 Job 배포 중..."
# 기존 Job 삭제 후 재생성
if gcloud run jobs describe "$JOB_WEEKLY" --region="$REGION_RUN" --project="$PROJECT" &>/dev/null; then
  echo "기존 주간 Job 삭제 중..."
  gcloud run jobs delete "$JOB_WEEKLY" --region="$REGION_RUN" --project="$PROJECT" --quiet
fi

echo "새 주간 Job 생성 중..."
gcloud run jobs create "$JOB_WEEKLY" \
  --image="$IMAGE_WEEKLY" \
  --region="$REGION_RUN" \
  --service-account="$SA" \
  --memory=512Mi \
  --cpu=1 \
  --max-retries=3 \
  --task-timeout=600s \
  --set-env-vars="PERIOD_TYPE=WEEKLY" \
  --project="$PROJECT"

# =========================
# 2) 월간 Job 배포
# =========================
echo ""
echo "🔨 3단계: 월간 Job Docker 이미지 빌드 중..."
IMAGE_MONTHLY="${REGION_AR}-docker.pkg.dev/${PROJECT}/${REPO}/${JOB_MONTHLY}:manual-$(date +%Y%m%d-%H%M%S)"

# Dockerfile 임시 복사
cp docker/Dockerfile-29cm-best ./Dockerfile

# 빌드 + 푸시
gcloud builds submit --tag "$IMAGE_MONTHLY" .

# 임시 Dockerfile 제거
rm ./Dockerfile

echo ""
echo "🚀 4단계: 월간 Job 배포 중..."
# 기존 Job이 있으면 삭제 후 재생성
if gcloud run jobs describe "$JOB_MONTHLY" --region="$REGION_RUN" --project="$PROJECT" &>/dev/null; then
  echo "기존 월간 Job 삭제 중..."
  gcloud run jobs delete "$JOB_MONTHLY" --region="$REGION_RUN" --project="$PROJECT" --quiet
fi

echo "새 월간 Job 생성 중..."
gcloud run jobs create "$JOB_MONTHLY" \
  --image="$IMAGE_MONTHLY" \
  --region="$REGION_RUN" \
  --service-account="$SA" \
  --memory=512Mi \
  --cpu=1 \
  --max-retries=3 \
  --task-timeout=600s \
  --set-env-vars="PERIOD_TYPE=MONTHLY" \
  --project="$PROJECT"

# =========================
# 3) Pub/Sub 토픽 및 구독 생성
# =========================
echo ""
echo "📢 5단계: Pub/Sub 토픽 생성 중..."

# 주간용 토픽
TOPIC_WEEKLY="29cm-best-weekly-trigger"
gcloud pubsub topics create "$TOPIC_WEEKLY" --project="$PROJECT" 2>/dev/null || echo "주간 토픽이 이미 존재합니다."

# 월간용 토픽
TOPIC_MONTHLY="29cm-best-monthly-trigger"
gcloud pubsub topics create "$TOPIC_MONTHLY" --project="$PROJECT" 2>/dev/null || echo "월간 토픽이 이미 존재합니다."

echo ""
echo "📬 6단계: Pub/Sub 구독 생성 중..."

# 주간용 구독
SUBSCRIPTION_WEEKLY="29cm-best-weekly-sub"
JOB_RUN_ENDPOINT_WEEKLY="https://${REGION_RUN}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT}/jobs/${JOB_WEEKLY}:run"
gcloud pubsub subscriptions create "$SUBSCRIPTION_WEEKLY" \
  --topic="$TOPIC_WEEKLY" \
  --ack-deadline=20 \
  --push-endpoint="$JOB_RUN_ENDPOINT_WEEKLY" \
  --push-auth-service-account="$SA" \
  --project="$PROJECT" 2>/dev/null || echo "주간 구독이 이미 존재합니다."

# 월간용 구독
SUBSCRIPTION_MONTHLY="29cm-best-monthly-sub"
JOB_RUN_ENDPOINT_MONTHLY="https://${REGION_RUN}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT}/jobs/${JOB_MONTHLY}:run"
gcloud pubsub subscriptions create "$SUBSCRIPTION_MONTHLY" \
  --topic="$TOPIC_MONTHLY" \
  --ack-deadline=20 \
  --push-endpoint="$JOB_RUN_ENDPOINT_MONTHLY" \
  --push-auth-service-account="$SA" \
  --project="$PROJECT" 2>/dev/null || echo "월간 구독이 이미 존재합니다."

# =========================
# 4) Cloud Scheduler 설정
# =========================
echo ""
echo "⏰ 7단계: Cloud Scheduler 작업 설정 중..."

# 기존 스케줄러 확인 및 삭제
SCHEDULER_WEEKLY="29cm-best-weekly-scheduler"
SCHEDULER_MONTHLY="29cm-best-monthly-scheduler"

# 주간 스케줄러 삭제 (존재하는 경우)
if gcloud scheduler jobs describe "$SCHEDULER_WEEKLY" --location="$REGION_RUN" --project="$PROJECT" &>/dev/null; then
  echo "기존 주간 스케줄러 삭제 중..."
  gcloud scheduler jobs delete "$SCHEDULER_WEEKLY" --location="$REGION_RUN" --project="$PROJECT" --quiet
fi

# 월간 스케줄러 삭제 (존재하는 경우)
if gcloud scheduler jobs describe "$SCHEDULER_MONTHLY" --location="$REGION_RUN" --project="$PROJECT" &>/dev/null; then
  echo "기존 월간 스케줄러 삭제 중..."
  gcloud scheduler jobs delete "$SCHEDULER_MONTHLY" --location="$REGION_RUN" --project="$PROJECT" --quiet
fi

# 기존 29cm 관련 스케줄러 모두 확인 및 삭제 (혹시 다른 이름으로 존재하는 경우)
echo "기존 29cm 관련 스케줄러 확인 중..."
gcloud scheduler jobs list --location="$REGION_RUN" --project="$PROJECT" --format="value(name)" 2>/dev/null | grep -i "29cm" | while read -r scheduler_name; do
  scheduler_id=$(basename "$scheduler_name")
  if [ "$scheduler_id" != "$SCHEDULER_WEEKLY" ] && [ "$scheduler_id" != "$SCHEDULER_MONTHLY" ]; then
    echo "  - 삭제: $scheduler_id"
    gcloud scheduler jobs delete "$scheduler_id" --location="$REGION_RUN" --project="$PROJECT" --quiet 2>/dev/null || true
  fi
done

# 주간 스케줄러 생성 (매주 월요일 새벽 3시)
SCHEDULER_WEEKLY="29cm-best-weekly-scheduler"
echo "주간 스케줄러 생성 중: 매주 월요일 새벽 3시"
if gcloud scheduler jobs describe "$SCHEDULER_WEEKLY" --location="$REGION_RUN" --project="$PROJECT" &>/dev/null; then
  echo "주간 스케줄러 업데이트 중..."
  gcloud scheduler jobs update pubsub "$SCHEDULER_WEEKLY" \
  --location="$REGION_RUN" \
  --schedule="0 3 * * 1" \
  --topic="$TOPIC_WEEKLY" \
  --message-body='{"trigger":"weekly"}' \
  --time-zone="Asia/Seoul" \
    --project="$PROJECT"
else
  echo "주간 스케줄러 생성 중..."
  gcloud scheduler jobs create pubsub "$SCHEDULER_WEEKLY" \
  --location="$REGION_RUN" \
  --schedule="0 3 * * 1" \
  --topic="$TOPIC_WEEKLY" \
  --message-body='{"trigger":"weekly"}' \
  --time-zone="Asia/Seoul" \
  --project="$PROJECT"
fi

# 월간 스케줄러 생성 (매월 1일 새벽 3시)
SCHEDULER_MONTHLY="29cm-best-monthly-scheduler"
echo "월간 스케줄러 생성 중: 매월 1일 새벽 3시"
if gcloud scheduler jobs describe "$SCHEDULER_MONTHLY" --location="$REGION_RUN" --project="$PROJECT" &>/dev/null; then
  echo "월간 스케줄러 업데이트 중..."
  gcloud scheduler jobs update pubsub "$SCHEDULER_MONTHLY" \
  --location="$REGION_RUN" \
  --schedule="0 3 1 * *" \
  --topic="$TOPIC_MONTHLY" \
  --message-body='{"trigger":"monthly"}' \
  --time-zone="Asia/Seoul" \
    --project="$PROJECT"
else
  echo "월간 스케줄러 생성 중..."
  gcloud scheduler jobs create pubsub "$SCHEDULER_MONTHLY" \
  --location="$REGION_RUN" \
  --schedule="0 3 1 * *" \
  --topic="$TOPIC_MONTHLY" \
  --message-body='{"trigger":"monthly"}' \
  --time-zone="Asia/Seoul" \
  --project="$PROJECT"
fi

echo ""
echo "✅ 모든 설정 완료!"
echo ""
echo "📋 생성된 리소스:"
echo "  - 주간 Cloud Run Job: ${JOB_WEEKLY}"
echo "  - 월간 Cloud Run Job: ${JOB_MONTHLY}"
echo "  - 주간 Pub/Sub Topic: ${TOPIC_WEEKLY}"
echo "  - 월간 Pub/Sub Topic: ${TOPIC_MONTHLY}"
echo "  - 주간 Pub/Sub Subscription: ${SUBSCRIPTION_WEEKLY}"
echo "  - 월간 Pub/Sub Subscription: ${SUBSCRIPTION_MONTHLY}"
echo "  - 주간 Cloud Scheduler: ${SCHEDULER_WEEKLY} (매주 월요일 새벽 3시)"
echo "  - 월간 Cloud Scheduler: ${SCHEDULER_MONTHLY} (매월 1일 새벽 3시)"
echo ""
echo "📝 수동 실행:"
echo "  주간: gcloud run jobs execute ${JOB_WEEKLY} --region=${REGION_RUN} --project=${PROJECT}"
echo "  월간: gcloud run jobs execute ${JOB_MONTHLY} --region=${REGION_RUN} --project=${PROJECT}"

