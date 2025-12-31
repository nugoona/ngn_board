#!/bin/bash

# 29CM BEST Job 스케줄러 생성 스크립트
# 매주 월요일 오전 8시에 실행되도록 스케줄러를 생성합니다.

set -euo pipefail

PROJECT="winged-precept-443218-v8"
REGION_RUN="asia-northeast3"
JOB_WEEKLY="ngn-29cm-best-job"
SCHEDULER_WEEKLY="29cm-best-weekly-scheduler"
TOPIC_WEEKLY="29cm-best-weekly-trigger"
SUBSCRIPTION_WEEKLY="29cm-best-weekly-sub"
SA="439320386143-compute@developer.gserviceaccount.com"

echo "=========================================="
echo "29CM BEST 주간 스케줄러 생성"
echo "=========================================="
echo ""

# 1. Cloud Run Job 존재 확인
echo "📦 1. Cloud Run Job 확인 중..."
if ! gcloud run jobs describe "$JOB_WEEKLY" --region="$REGION_RUN" --project="$PROJECT" &>/dev/null; then
  echo "❌ Cloud Run Job이 존재하지 않습니다: $JOB_WEEKLY"
  echo "   → 먼저 deploy_29cm_jobs.sh 스크립트를 실행하여 Job을 배포해야 합니다."
  exit 1
fi
echo "✅ Cloud Run Job 존재 확인: $JOB_WEEKLY"
echo ""

# 2. Pub/Sub 토픽 생성/확인
echo "📢 2. Pub/Sub 토픽 확인/생성 중..."
if ! gcloud pubsub topics describe "$TOPIC_WEEKLY" --project="$PROJECT" &>/dev/null; then
  echo "토픽이 존재하지 않아 생성 중..."
  gcloud pubsub topics create "$TOPIC_WEEKLY" --project="$PROJECT"
  echo "✅ 토픽 생성 완료: $TOPIC_WEEKLY"
else
  echo "✅ 토픽 이미 존재: $TOPIC_WEEKLY"
fi
echo ""

# 3. Pub/Sub 구독 생성/확인
echo "📬 3. Pub/Sub 구독 확인/생성 중..."
JOB_RUN_ENDPOINT="https://${REGION_RUN}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT}/jobs/${JOB_WEEKLY}:run"

if ! gcloud pubsub subscriptions describe "$SUBSCRIPTION_WEEKLY" --project="$PROJECT" &>/dev/null; then
  echo "구독이 존재하지 않아 생성 중..."
  gcloud pubsub subscriptions create "$SUBSCRIPTION_WEEKLY" \
    --topic="$TOPIC_WEEKLY" \
    --ack-deadline=20 \
    --push-endpoint="$JOB_RUN_ENDPOINT" \
    --push-auth-service-account="$SA" \
    --project="$PROJECT"
  echo "✅ 구독 생성 완료: $SUBSCRIPTION_WEEKLY"
else
  echo "✅ 구독 이미 존재: $SUBSCRIPTION_WEEKLY"
fi
echo ""

# 4. Cloud Scheduler 생성
echo "⏰ 4. Cloud Scheduler 생성 중..."
echo "스케줄: 매주 월요일 오전 8시 (Asia/Seoul)"
echo ""

if gcloud scheduler jobs describe "$SCHEDULER_WEEKLY" --location="$REGION_RUN" --project="$PROJECT" &>/dev/null; then
  echo "기존 스케줄러를 업데이트 중..."
  gcloud scheduler jobs update pubsub "$SCHEDULER_WEEKLY" \
    --location="$REGION_RUN" \
    --schedule="0 8 * * 1" \
    --topic="$TOPIC_WEEKLY" \
    --message-body='{"trigger":"weekly"}' \
    --time-zone="Asia/Seoul" \
    --project="$PROJECT"
  echo "✅ 스케줄러 업데이트 완료"
else
  echo "새 스케줄러 생성 중..."
  gcloud scheduler jobs create pubsub "$SCHEDULER_WEEKLY" \
    --location="$REGION_RUN" \
    --schedule="0 8 * * 1" \
    --topic="$TOPIC_WEEKLY" \
    --message-body='{"trigger":"weekly"}' \
    --time-zone="Asia/Seoul" \
    --project="$PROJECT"
  echo "✅ 스케줄러 생성 완료"
fi
echo ""

# 5. 생성된 스케줄러 정보 확인
echo "=========================================="
echo "생성된 스케줄러 정보"
echo "=========================================="
gcloud scheduler jobs describe "$SCHEDULER_WEEKLY" \
  --location="$REGION_RUN" \
  --project="$PROJECT" \
  --format="yaml(name,schedule,timeZone,state,pubsubTarget.topicName)"

echo ""
echo "✅ 스케줄러 설정 완료!"
echo ""
echo "다음 실행 예정 시간을 확인하려면:"
echo "  gcloud scheduler jobs describe $SCHEDULER_WEEKLY --location=$REGION_RUN --project=$PROJECT --format='value(scheduleTime)'"
echo ""

