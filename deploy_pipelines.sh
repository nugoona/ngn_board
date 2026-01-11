#!/bin/bash
########################################
# 통합 파이프라인 Job 배포 스크립트
# - Meta Pipeline (today)
# - Cafe24 Pipeline (today)
# - GA4 Pipeline (today)
# - Daily Batch Pipeline (yesterday)
########################################
set -euo pipefail

PROJECT="winged-precept-443218-v8"
REGION="asia-northeast3"
REPO="ngn-dashboard"
AR_REGION="asia-northeast1"
SA="439320386143-compute@developer.gserviceaccount.com"

TIMESTAMP=$(date +%Y%m%d-%H%M%S)

echo "========================================"
echo "🚀 통합 파이프라인 Job 배포 시작"
echo "========================================"

# 환경변수 로드
if [ -f config/ngn.env ]; then
    set -a
    source config/ngn.env
    set +a
    echo "✅ 환경변수 로드 완료"
fi

# ─────────────────────────────────────────────────────────────
# 1. Meta Pipeline (today)
# ─────────────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════"
echo "[1/4] Meta Pipeline 배포"
echo "════════════════════════════════════════"

JOB_NAME="ngn-meta-pipeline-job"
IMAGE="${AR_REGION}-docker.pkg.dev/${PROJECT}/${REPO}/${JOB_NAME}:${TIMESTAMP}"

cp docker/Dockerfile-meta-pipeline ./Dockerfile
gcloud builds submit --tag "$IMAGE" --project="$PROJECT" --region="$AR_REGION" .
rm -f ./Dockerfile

gcloud run jobs create "$JOB_NAME" \
    --image="$IMAGE" \
    --region="$REGION" \
    --project="$PROJECT" \
    --task-timeout=10m \
    --max-retries=3 \
    --memory=512Mi \
    --cpu=1 \
    --set-env-vars="META_SYSTEM_USER_TOKEN=${META_SYSTEM_USER_TOKEN:-}" \
    --service-account="$SA" \
    --args="today" \
    --quiet 2>/dev/null || \
gcloud run jobs update "$JOB_NAME" \
    --image="$IMAGE" \
    --region="$REGION" \
    --project="$PROJECT" \
    --task-timeout=10m \
    --max-retries=3 \
    --memory=512Mi \
    --cpu=1 \
    --set-env-vars="META_SYSTEM_USER_TOKEN=${META_SYSTEM_USER_TOKEN:-}" \
    --args="today" \
    --quiet

echo "✅ Meta Pipeline 배포 완료: $JOB_NAME"

# ─────────────────────────────────────────────────────────────
# 2. Cafe24 Pipeline (today)
# ─────────────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════"
echo "[2/4] Cafe24 Pipeline 배포"
echo "════════════════════════════════════════"

JOB_NAME="ngn-cafe24-pipeline-job"
IMAGE="${AR_REGION}-docker.pkg.dev/${PROJECT}/${REPO}/${JOB_NAME}:${TIMESTAMP}"

cp docker/Dockerfile-cafe24-pipeline ./Dockerfile
gcloud builds submit --tag "$IMAGE" --project="$PROJECT" --region="$AR_REGION" .
rm -f ./Dockerfile

gcloud run jobs create "$JOB_NAME" \
    --image="$IMAGE" \
    --region="$REGION" \
    --project="$PROJECT" \
    --task-timeout=10m \
    --max-retries=3 \
    --memory=512Mi \
    --cpu=1 \
    --service-account="$SA" \
    --args="today" \
    --quiet 2>/dev/null || \
gcloud run jobs update "$JOB_NAME" \
    --image="$IMAGE" \
    --region="$REGION" \
    --project="$PROJECT" \
    --task-timeout=10m \
    --max-retries=3 \
    --memory=512Mi \
    --cpu=1 \
    --args="today" \
    --quiet

echo "✅ Cafe24 Pipeline 배포 완료: $JOB_NAME"

# ─────────────────────────────────────────────────────────────
# 3. GA4 Pipeline (today)
# ─────────────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════"
echo "[3/4] GA4 Pipeline 배포"
echo "════════════════════════════════════════"

JOB_NAME="ngn-ga4-pipeline-job"
IMAGE="${AR_REGION}-docker.pkg.dev/${PROJECT}/${REPO}/${JOB_NAME}:${TIMESTAMP}"

cp docker/Dockerfile-ga4-pipeline ./Dockerfile
gcloud builds submit --tag "$IMAGE" --project="$PROJECT" --region="$AR_REGION" .
rm -f ./Dockerfile

gcloud run jobs create "$JOB_NAME" \
    --image="$IMAGE" \
    --region="$REGION" \
    --project="$PROJECT" \
    --task-timeout=10m \
    --max-retries=3 \
    --memory=1Gi \
    --cpu=1 \
    --service-account="$SA" \
    --args="today" \
    --quiet 2>/dev/null || \
gcloud run jobs update "$JOB_NAME" \
    --image="$IMAGE" \
    --region="$REGION" \
    --project="$PROJECT" \
    --task-timeout=10m \
    --max-retries=3 \
    --memory=1Gi \
    --cpu=1 \
    --args="today" \
    --quiet

echo "✅ GA4 Pipeline 배포 완료: $JOB_NAME"

# ─────────────────────────────────────────────────────────────
# 4. Daily Batch Pipeline (yesterday)
# ─────────────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════"
echo "[4/4] Daily Batch Pipeline 배포"
echo "════════════════════════════════════════"

JOB_NAME="ngn-daily-batch-pipeline-job"
IMAGE="${AR_REGION}-docker.pkg.dev/${PROJECT}/${REPO}/${JOB_NAME}:${TIMESTAMP}"

cp docker/Dockerfile-daily-batch-pipeline ./Dockerfile
gcloud builds submit --tag "$IMAGE" --project="$PROJECT" --region="$AR_REGION" .
rm -f ./Dockerfile

gcloud run jobs create "$JOB_NAME" \
    --image="$IMAGE" \
    --region="$REGION" \
    --project="$PROJECT" \
    --task-timeout=30m \
    --max-retries=3 \
    --memory=1Gi \
    --cpu=1 \
    --set-env-vars="META_SYSTEM_USER_TOKEN=${META_SYSTEM_USER_TOKEN:-}" \
    --service-account="$SA" \
    --quiet 2>/dev/null || \
gcloud run jobs update "$JOB_NAME" \
    --image="$IMAGE" \
    --region="$REGION" \
    --project="$PROJECT" \
    --task-timeout=30m \
    --max-retries=3 \
    --memory=1Gi \
    --cpu=1 \
    --set-env-vars="META_SYSTEM_USER_TOKEN=${META_SYSTEM_USER_TOKEN:-}" \
    --quiet

echo "✅ Daily Batch Pipeline 배포 완료: $JOB_NAME"

# ─────────────────────────────────────────────────────────────
# 완료
# ─────────────────────────────────────────────────────────────
echo ""
echo "========================================"
echo "🎉 모든 파이프라인 배포 완료!"
echo "========================================"
echo ""
echo "배포된 Job 목록:"
echo "  - ngn-meta-pipeline-job (today)"
echo "  - ngn-cafe24-pipeline-job (today)"
echo "  - ngn-ga4-pipeline-job (today)"
echo "  - ngn-daily-batch-pipeline-job (yesterday)"
echo ""
echo "다음 단계:"
echo "  1. 각 Job 테스트 실행"
echo "  2. Scheduler 생성 (create_pipeline_schedulers.sh)"
echo "  3. 기존 Job/Scheduler 삭제 (cleanup_old_jobs.sh)"
