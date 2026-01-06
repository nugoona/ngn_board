#!/bin/bash
set -euo pipefail
cd ~/ngn_board

REGION_RUN="asia-northeast3"
REGION_AR="asia-northeast1"
REPO="ngn-dashboard"
PROJECT="winged-precept-443218-v8"
SA="439320386143-compute@developer.gserviceaccount.com"

# ============================================
# query-sales-today-job
# ============================================
JOB="query-sales-today-job"
DOCKERFILE="docker/Dockerfile-sales-today"

IMAGE="${REGION_AR}-docker.pkg.dev/${PROJECT}/${REPO}/${JOB}:manual-$(date +%Y%m%d-%H%M%S)"

echo "🚀 Building image for ${JOB}..."
gcloud builds submit --tag "$IMAGE" --dockerfile="$DOCKERFILE" .

echo "📦 Updating Cloud Run Job ${JOB}..."
gcloud run jobs update "$JOB" \
  --image "$IMAGE" \
  --region="$REGION_RUN" \
  --service-account="$SA" \
  --memory=512Mi \
  --cpu=1 \
  --max-retries=3 \
  --task-timeout=600s

echo "✅ Deployment completed for ${JOB}!"

# ============================================
# query-sales-yesterday-job
# ============================================
JOB="query-sales-yesterday-job"
DOCKERFILE="docker/Dockerfile-sales-yesterday"

IMAGE="${REGION_AR}-docker.pkg.dev/${PROJECT}/${REPO}/${JOB}:manual-$(date +%Y%m%d-%H%M%S)"

echo "🚀 Building image for ${JOB}..."
gcloud builds submit --tag "$IMAGE" --dockerfile="$DOCKERFILE" .

echo "📦 Updating Cloud Run Job ${JOB}..."
gcloud run jobs update "$JOB" \
  --image "$IMAGE" \
  --region="$REGION_RUN" \
  --service-account="$SA" \
  --memory=512Mi \
  --cpu=1 \
  --max-retries=3 \
  --task-timeout=600s

echo "✅ Deployment completed for ${JOB}!"
echo "🎉 All sales jobs deployed successfully!"














