#!/bin/bash
set -euo pipefail
cd ~/ngn_board

PROJECT="winged-precept-443218-v8"
REGION_AR="asia-northeast1"
REGION_RUN="asia-northeast3"
REPO="ngn-dashboard"
JOB="ngn-sheet-platform"
SA="439320386143-compute@developer.gserviceaccount.com"
DOCKERFILE="docker/Dockerfile-Sheet-update"

IMAGE="${REGION_AR}-docker.pkg.dev/${PROJECT}/${REPO}/${JOB}:manual-$(date +%Y%m%d-%H%M%S)"

echo "🚀 Building image for ${JOB}..."
gcloud builds submit --tag "$IMAGE" --dockerfile="$DOCKERFILE" .

echo "📦 Updating Cloud Run Job ${JOB}..."
if gcloud run jobs describe "$JOB" --region="$REGION_RUN" --project="$PROJECT" &>/dev/null; then
  echo "Job이 이미 존재합니다. 업데이트 중..."
  gcloud run jobs update "$JOB" \
    --image="$IMAGE" \
    --region="$REGION_RUN" \
    --service-account="$SA" \
    --memory=512Mi \
    --cpu=1 \
    --max-retries=3 \
    --task-timeout=600s \
    --project="$PROJECT"
else
  echo "새 Job 생성 중..."
  gcloud run jobs create "$JOB" \
    --image="$IMAGE" \
    --region="$REGION_RUN" \
    --service-account="$SA" \
    --memory=512Mi \
    --cpu=1 \
    --max-retries=3 \
    --task-timeout=600s \
    --project="$PROJECT"
fi

echo "✅ Deployment completed for ${JOB}!"
echo ""
echo "💡 수동 실행:"
echo "  gcloud run jobs execute ${JOB} --region=${REGION_RUN} --project=${PROJECT}"

