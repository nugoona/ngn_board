#!/bin/bash
set -euo pipefail

PROJECT="winged-precept-443218-v8"
REGION_RUN="asia-northeast3"
JOB="query-sales-prev-month-job"
SA="439320386143-compute@developer.gserviceaccount.com"
TOPIC_NAME="sales-prev-month-trigger"
SUBSCRIPTION_NAME="sales-prev-month-sub"
SCHEDULER_NAME="sales-prev-month-scheduler"

echo "============================================"
echo "📢 1단계: Pub/Sub 토픽 생성 중..."
gcloud pubsub topics create "$TOPIC_NAME" --project="$PROJECT" 2>/dev/null || echo "토픽이 이미 존재합니다."

echo "📬 2단계: Pub/Sub 구독 생성 중..."
JOB_RUN_ENDPOINT="https://${REGION_RUN}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT}/jobs/${JOB}:run"

gcloud pubsub subscriptions create "$SUBSCRIPTION_NAME" \
  --topic="$TOPIC_NAME" \
  --push-endpoint="$JOB_RUN_ENDPOINT" \
  --push-auth-service-account="$SA" \
  --project="$PROJECT" 2>/dev/null || echo "구독이 이미 존재합니다."

echo "⏰ 3단계: Cloud Scheduler 작업 생성 중..."
# 매월 5일 오전 5시 실행 (한국시간)
if gcloud scheduler jobs describe "$SCHEDULER_NAME" --location="$REGION_RUN" --project="$PROJECT" &>/dev/null; then
  echo "스케줄러 업데이트 중..."
  gcloud scheduler jobs update pubsub "$SCHEDULER_NAME" \
    --location="$REGION_RUN" --schedule="0 5 5 * *" --topic="$TOPIC_NAME" \
    --message-body='{"trigger":"monthly"}' --time-zone="Asia/Seoul" --project="$PROJECT"
else
  echo "새 스케줄러 생성 중..."
  gcloud scheduler jobs create pubsub "$SCHEDULER_NAME" \
    --location="$REGION_RUN" --schedule="0 5 5 * *" --topic="$TOPIC_NAME" \
    --message-body='{"trigger":"monthly"}' --time-zone="Asia/Seoul" --project="$PROJECT"
fi

echo "============================================"
echo "✅ 설정 완료: $SCHEDULER_NAME"
