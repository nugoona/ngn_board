#!/bin/bash
# 모든 수정된 Job 재배포 스크립트
set -euo pipefail
cd ~/ngn_board

REGION_RUN="asia-northeast3"
REGION_AR="asia-northeast1"
REPO="ngn-dashboard"
PROJECT="winged-precept-443218-v8"
SA="439320386143-compute@developer.gserviceaccount.com"

# ============================================
# 1. ngn-refund-job (cafe24_refund_data_handler.py 수정)
# ============================================
echo "📦 Deploying ngn-refund-job..."
JOB="ngn-refund-job"
DOCKERFILE="docker/Dockerfile-refund"
IMAGE="${REGION_AR}-docker.pkg.dev/${PROJECT}/${REPO}/${JOB}:manual-$(date +%Y%m%d-%H%M%S)"

gcloud builds submit --tag "$IMAGE" --dockerfile="$DOCKERFILE" .

gcloud run jobs update "$JOB" \
  --image "$IMAGE" \
  --region="$REGION_RUN" \
  --service-account="$SA" \
  --memory=512Mi \
  --cpu=1 \
  --max-retries=3 \
  --task-timeout=600s

echo "✅ ngn-refund-job deployed!"

# ============================================
# 2. query-sales-today-job (daily_cafe24_sales_handler.py 수정)
# ============================================
echo "📦 Deploying query-sales-today-job..."
JOB="query-sales-today-job"
DOCKERFILE="docker/Dockerfile-sales-today"
IMAGE="${REGION_AR}-docker.pkg.dev/${PROJECT}/${REPO}/${JOB}:manual-$(date +%Y%m%d-%H%M%S)"

gcloud builds submit --tag "$IMAGE" --dockerfile="$DOCKERFILE" .

gcloud run jobs update "$JOB" \
  --image "$IMAGE" \
  --region="$REGION_RUN" \
  --service-account="$SA" \
  --memory=512Mi \
  --cpu=1 \
  --max-retries=3 \
  --task-timeout=600s

echo "✅ query-sales-today-job deployed!"

# ============================================
# 3. query-sales-yesterday-job (daily_cafe24_sales_handler.py 수정)
# ============================================
echo "📦 Deploying query-sales-yesterday-job..."
JOB="query-sales-yesterday-job"
DOCKERFILE="docker/Dockerfile-sales-yesterday"
IMAGE="${REGION_AR}-docker.pkg.dev/${PROJECT}/${REPO}/${JOB}:manual-$(date +%Y%m%d-%H%M%S)"

gcloud builds submit --tag "$IMAGE" --dockerfile="$DOCKERFILE" .

gcloud run jobs update "$JOB" \
  --image "$IMAGE" \
  --region="$REGION_RUN" \
  --service-account="$SA" \
  --memory=512Mi \
  --cpu=1 \
  --max-retries=3 \
  --task-timeout=600s

echo "✅ query-sales-yesterday-job deployed!"

echo "🎉 All jobs deployed successfully!"












