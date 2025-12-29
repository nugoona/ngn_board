#!/bin/bash
set -euo pipefail
cd ~/ngn_board

PROJECT="winged-precept-443218-v8"
REGION_AR="asia-northeast1"
REGION_RUN="asia-northeast3"
REPO="ngn-dashboard"
SA="439320386143-compute@developer.gserviceaccount.com"

# ============================================
# 1. ngn-refund-job
# ============================================
echo "============================================"
echo "🚀 Deploying ngn-refund-job..."
echo "============================================"

JOB="ngn-refund-job"
IMAGE="${REGION_AR}-docker.pkg.dev/${PROJECT}/${REPO}/${JOB}:manual-$(date +%Y%m%d-%H%M%S)"

# 1) Dockerfile 임시 복사
cp docker/Dockerfile-refund ./Dockerfile

# 2) 빌드 + 푸시 (Cloud Build)
gcloud builds submit --tag "$IMAGE" .

# 3) 임시 Dockerfile 제거
rm ./Dockerfile

# 4) Job 업데이트
gcloud run jobs update "$JOB" \
  --image="$IMAGE" \
  --region="$REGION_RUN" \
  --service-account="$SA" \
  --memory=512Mi \
  --cpu=1 \
  --max-retries=3 \
  --task-timeout=600s

echo "✅ ngn-refund-job deployed successfully!"
echo ""

# ============================================
# 2. query-sales-today-job
# ============================================
echo "============================================"
echo "🚀 Deploying query-sales-today-job..."
echo "============================================"

JOB="query-sales-today-job"
IMAGE="${REGION_AR}-docker.pkg.dev/${PROJECT}/${REPO}/${JOB}:manual-$(date +%Y%m%d-%H%M%S)"

# 1) Dockerfile 임시 복사
cp docker/Dockerfile-sales-today ./Dockerfile

# 2) 빌드 + 푸시 (Cloud Build)
gcloud builds submit --tag "$IMAGE" .

# 3) 임시 Dockerfile 제거
rm ./Dockerfile

# 4) Job 업데이트
gcloud run jobs update "$JOB" \
  --image="$IMAGE" \
  --region="$REGION_RUN" \
  --service-account="$SA" \
  --memory=512Mi \
  --cpu=1 \
  --max-retries=3 \
  --task-timeout=600s

echo "✅ query-sales-today-job deployed successfully!"
echo ""

# ============================================
# 3. query-sales-yesterday-job
# ============================================
echo "============================================"
echo "🚀 Deploying query-sales-yesterday-job..."
echo "============================================"

JOB="query-sales-yesterday-job"
IMAGE="${REGION_AR}-docker.pkg.dev/${PROJECT}/${REPO}/${JOB}:manual-$(date +%Y%m%d-%H%M%S)"

# 1) Dockerfile 임시 복사
cp docker/Dockerfile-sales-yesterday ./Dockerfile

# 2) 빌드 + 푸시 (Cloud Build)
gcloud builds submit --tag "$IMAGE" .

# 3) 임시 Dockerfile 제거
rm ./Dockerfile

# 4) Job 업데이트
gcloud run jobs update "$JOB" \
  --image="$IMAGE" \
  --region="$REGION_RUN" \
  --service-account="$SA" \
  --memory=512Mi \
  --cpu=1 \
  --max-retries=3 \
  --task-timeout=600s

echo "✅ query-sales-yesterday-job deployed successfully!"
echo ""

# ============================================
# 완료
# ============================================
echo "============================================"
echo "🎉 All jobs deployed successfully!"
echo "============================================"
echo "Deployed Jobs:"
echo "  - ngn-refund-job"
echo "  - query-sales-today-job"
echo "  - query-sales-yesterday-job"


