#!/bin/bash
set -euo pipefail
cd ~/ngn_board

PROJECT="winged-precept-443218-v8"
REGION_AR="asia-northeast1"
REGION_RUN="asia-northeast3"
REPO="ngn-dashboard"
SA="439320386143-compute@developer.gserviceaccount.com"

# ============================================
# ngn-performance-summary-today
# ============================================
JOB="ngn-performance-summary-today"
IMAGE="${REGION_AR}-docker.pkg.dev/${PROJECT}/${REPO}/${JOB}:manual-$(date +%Y%m%d-%H%M%S)"

echo "🚀 Building image for ${JOB}..."

# 1) Dockerfile 임시 복사
cp docker/Dockerfile-performance_summary-today ./Dockerfile

# 2) 빌드 + 푸시 (Cloud Build)
gcloud builds submit --tag "$IMAGE" .

# 3) 임시 Dockerfile 제거
rm ./Dockerfile

# 4) Job 업데이트
echo "📦 Updating Cloud Run Job ${JOB}..."
gcloud run jobs update "$JOB" \
  --image="$IMAGE" \
  --region="$REGION_RUN" \
  --service-account="$SA" \
  --memory=512Mi \
  --cpu=1 \
  --max-retries=3 \
  --task-timeout=600s

echo "✅ Deployment completed for ${JOB}!"

# ============================================
# ngn-performance-summary-yesterday
# ============================================
JOB="ngn-performance-summary-yesterday"
IMAGE="${REGION_AR}-docker.pkg.dev/${PROJECT}/${REPO}/${JOB}:manual-$(date +%Y%m%d-%H%M%S)"

echo "🚀 Building image for ${JOB}..."

# 1) Dockerfile 임시 복사
cp docker/Dockerfile-performance_summary-yesterday ./Dockerfile

# 2) 빌드 + 푸시 (Cloud Build)
gcloud builds submit --tag "$IMAGE" .

# 3) 임시 Dockerfile 제거
rm ./Dockerfile

# 4) Job 업데이트
echo "📦 Updating Cloud Run Job ${JOB}..."
gcloud run jobs update "$JOB" \
  --image="$IMAGE" \
  --region="$REGION_RUN" \
  --service-account="$SA" \
  --memory=512Mi \
  --cpu=1 \
  --max-retries=3 \
  --task-timeout=600s

echo "✅ Deployment completed for ${JOB}!"

echo "🎉 All performance summary jobs deployed successfully!"

