#!/bin/bash

# 29CM BEST Job 스케줄러 상태 확인 스크립트
# Cloud Shell에서 실행하여 스케줄러 상태를 확인합니다.

set -euo pipefail

PROJECT="winged-precept-443218-v8"
REGION_RUN="asia-northeast3"
JOB_WEEKLY="ngn-29cm-best-job"
JOB_MONTHLY="ngn-29cm-best-monthly-job"
SCHEDULER_WEEKLY="29cm-best-weekly-scheduler"
SCHEDULER_MONTHLY="29cm-best-monthly-scheduler"

echo "=========================================="
echo "29CM BEST Job 스케줄러 상태 확인"
echo "=========================================="
echo ""

# 1. Cloud Run Job 상태 확인
echo "📦 1. Cloud Run Job 상태 확인"
echo "----------------------------------------"
if gcloud run jobs describe "$JOB_WEEKLY" --region="$REGION_RUN" --project="$PROJECT" &>/dev/null; then
  echo "✅ 주간 Job 존재: $JOB_WEEKLY"
  gcloud run jobs describe "$JOB_WEEKLY" --region="$REGION_RUN" --project="$PROJECT" --format="table(name,generation,activeDeadlineSeconds,created)" 2>/dev/null || true
else
  echo "❌ 주간 Job 없음: $JOB_WEEKLY"
fi

echo ""
if gcloud run jobs describe "$JOB_MONTHLY" --region="$REGION_RUN" --project="$PROJECT" &>/dev/null; then
  echo "✅ 월간 Job 존재: $JOB_MONTHLY"
  gcloud run jobs describe "$JOB_MONTHLY" --region="$REGION_RUN" --project="$PROJECT" --format="table(name,generation,activeDeadlineSeconds,created)" 2>/dev/null || true
else
  echo "❌ 월간 Job 없음: $JOB_MONTHLY"
fi

echo ""
echo "=========================================="
echo ""

# 2. Cloud Scheduler 상태 확인
echo "⏰ 2. Cloud Scheduler 상태 확인"
echo "----------------------------------------"

# 주간 스케줄러 확인
echo ""
echo "📅 주간 스케줄러: $SCHEDULER_WEEKLY"
if gcloud scheduler jobs describe "$SCHEDULER_WEEKLY" --location="$REGION_RUN" --project="$PROJECT" &>/dev/null; then
  echo "✅ 스케줄러 존재"
  echo ""
  echo "상세 정보:"
  gcloud scheduler jobs describe "$SCHEDULER_WEEKLY" \
    --location="$REGION_RUN" \
    --project="$PROJECT" \
    --format="yaml(schedule,timeZone,state,pubsubTarget.topicName,pubsubTarget.data,lastAttemptTime,nextRunTime)" 2>/dev/null || true
  
  echo ""
  echo "상태 요약:"
  STATE=$(gcloud scheduler jobs describe "$SCHEDULER_WEEKLY" --location="$REGION_RUN" --project="$PROJECT" --format="value(state)" 2>/dev/null || echo "UNKNOWN")
  if [ "$STATE" = "ENABLED" ]; then
    echo "  ✅ 상태: 활성화됨 (ENABLED)"
  elif [ "$STATE" = "PAUSED" ] || [ "$STATE" = "DISABLED" ]; then
    echo "  ⚠️  상태: 비활성화됨 ($STATE) - 자동 실행 안됨!"
  else
    echo "  ❓ 상태: $STATE"
  fi
  
  NEXT_RUN=$(gcloud scheduler jobs describe "$SCHEDULER_WEEKLY" --location="$REGION_RUN" --project="$PROJECT" --format="value(scheduleTime)" 2>/dev/null || echo "알 수 없음")
  echo "  📅 다음 실행 시간: $NEXT_RUN"
  
else
  echo "❌ 스케줄러가 존재하지 않습니다!"
  echo "   → deploy_29cm_jobs.sh 스크립트를 실행하여 스케줄러를 생성해야 합니다."
fi

# 월간 스케줄러 확인
echo ""
echo "📅 월간 스케줄러: $SCHEDULER_MONTHLY"
if gcloud scheduler jobs describe "$SCHEDULER_MONTHLY" --location="$REGION_RUN" --project="$PROJECT" &>/dev/null; then
  echo "✅ 스케줄러 존재"
  echo ""
  echo "상세 정보:"
  gcloud scheduler jobs describe "$SCHEDULER_MONTHLY" \
    --location="$REGION_RUN" \
    --project="$PROJECT" \
    --format="yaml(schedule,timeZone,state,pubsubTarget.topicName,pubsubTarget.data,lastAttemptTime,nextRunTime)" 2>/dev/null || true
  
  echo ""
  echo "상태 요약:"
  STATE=$(gcloud scheduler jobs describe "$SCHEDULER_MONTHLY" --location="$REGION_RUN" --project="$PROJECT" --format="value(state)" 2>/dev/null || echo "UNKNOWN")
  if [ "$STATE" = "ENABLED" ]; then
    echo "  ✅ 상태: 활성화됨 (ENABLED)"
  elif [ "$STATE" = "PAUSED" ] || [ "$STATE" = "DISABLED" ]; then
    echo "  ⚠️  상태: 비활성화됨 ($STATE) - 자동 실행 안됨!"
  else
    echo "  ❓ 상태: $STATE"
  fi
  
  NEXT_RUN=$(gcloud scheduler jobs describe "$SCHEDULER_MONTHLY" --location="$REGION_RUN" --project="$PROJECT" --format="value(scheduleTime)" 2>/dev/null || echo "알 수 없음")
  echo "  📅 다음 실행 시간: $NEXT_RUN"
  
else
  echo "❌ 스케줄러가 존재하지 않습니다!"
  echo "   → deploy_29cm_jobs.sh 스크립트를 실행하여 스케줄러를 생성해야 합니다."
fi

echo ""
echo "=========================================="
echo ""

# 3. Pub/Sub 토픽 및 구독 확인
echo "📢 3. Pub/Sub 토픽 및 구독 확인"
echo "----------------------------------------"
TOPIC_WEEKLY="weekly-29cm-best-trigger"
TOPIC_MONTHLY="monthly-29cm-best-trigger"

if gcloud pubsub topics describe "$TOPIC_WEEKLY" --project="$PROJECT" &>/dev/null; then
  echo "✅ 주간 토픽 존재: $TOPIC_WEEKLY"
else
  echo "❌ 주간 토픽 없음: $TOPIC_WEEKLY"
fi

if gcloud pubsub topics describe "$TOPIC_MONTHLY" --project="$PROJECT" &>/dev/null; then
  echo "✅ 월간 토픽 존재: $TOPIC_MONTHLY"
else
  echo "❌ 월간 토픽 없음: $TOPIC_MONTHLY"
fi

echo ""
echo "=========================================="
echo ""

# 4. 최근 Job 실행 이력 확인 (최근 5개)
echo "📊 4. 최근 Job 실행 이력 확인"
echo "----------------------------------------"
echo ""
echo "주간 Job 최근 실행 이력:"
gcloud run jobs executions list \
  --job="$JOB_WEEKLY" \
  --region="$REGION_RUN" \
  --project="$PROJECT" \
  --limit=5 \
  --format="table(name,createTime,completionTime,status.conditions[0].type:label=STATUS)" 2>/dev/null || echo "이력 조회 실패"

echo ""
echo "월간 Job 최근 실행 이력:"
gcloud run jobs executions list \
  --job="$JOB_MONTHLY" \
  --region="$REGION_RUN" \
  --project="$PROJECT" \
  --limit=5 \
  --format="table(name,createTime,completionTime,status.conditions[0].type:label=STATUS)" 2>/dev/null || echo "이력 조회 실패"

echo ""
echo "=========================================="
echo "✅ 확인 완료!"
echo ""
echo "💡 스케줄러가 비활성화되어 있다면 다음 명령어로 활성화할 수 있습니다:"
echo "   gcloud scheduler jobs resume $SCHEDULER_WEEKLY --location=$REGION_RUN --project=$PROJECT"
echo ""

