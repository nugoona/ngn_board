#!/bin/bash
# 모든 sales/orders 관련 Job 재배포 스크립트
# 사용법: ./deploy_all_sales_orders_jobs.sh

set -euo pipefail

PROJECT="winged-precept-443218-v8"
REGION="asia-northeast3"
SA="439320386143-compute@developer.gserviceaccount.com"

echo "============================================"
echo "🚀 Sales & Orders Jobs 일괄 배포 시작"
echo "============================================"

# ============================================
# 1. query-sales-today-job
# ============================================
echo ""
echo "[1/4] 📦 Deploying query-sales-today-job..."
JOB="query-sales-today-job"
IMAGE="asia-northeast1-docker.pkg.dev/${PROJECT}/ngn-dashboard/${JOB}:manual-$(date +%Y%m%d-%H%M%S)"

cp docker/Dockerfile-sales-today ./Dockerfile
gcloud builds submit --tag "$IMAGE" .
rm ./Dockerfile

gcloud run jobs update "$JOB" \
  --image "$IMAGE" \
  --region="$REGION" \
  --service-account="$SA" \
  --memory=512Mi \
  --cpu=1 \
  --max-retries=3 \
  --task-timeout=600s

echo "✅ query-sales-today-job 배포 완료!"

# ============================================
# 2. query-sales-yesterday-job
# ============================================
echo ""
echo "[2/4] 📦 Deploying query-sales-yesterday-job..."
JOB="query-sales-yesterday-job"
IMAGE="asia-northeast1-docker.pkg.dev/${PROJECT}/ngn-dashboard/${JOB}:manual-$(date +%Y%m%d-%H%M%S)"

cp docker/Dockerfile-sales-yesterday ./Dockerfile
gcloud builds submit --tag "$IMAGE" .
rm ./Dockerfile

gcloud run jobs update "$JOB" \
  --image "$IMAGE" \
  --region="$REGION" \
  --service-account="$SA" \
  --memory=512Mi \
  --cpu=1 \
  --max-retries=3 \
  --task-timeout=600s

echo "✅ query-sales-yesterday-job 배포 완료!"

# ============================================
# 3. query-sales-prev-month-job
# ============================================
echo ""
echo "[3/4] 📦 Deploying query-sales-prev-month-job..."
JOB="query-sales-prev-month-job"
IMAGE="asia-northeast1-docker.pkg.dev/${PROJECT}/ngn-dashboard/${JOB}:manual-$(date +%Y%m%d-%H%M%S)"

cp docker/Dockerfile-sales-prev-month ./Dockerfile
gcloud builds submit --tag "$IMAGE" .
rm ./Dockerfile

gcloud run jobs update "$JOB" \
  --image "$IMAGE" \
  --region="$REGION" \
  --service-account="$SA" \
  --memory=512Mi \
  --cpu=1 \
  --max-retries=3 \
  --task-timeout=600s

echo "✅ query-sales-prev-month-job 배포 완료!"

# ============================================
# 4. ngn-orders-job (이미 배포했으면 스킵 가능)
# ============================================
echo ""
echo "[4/4] 📦 Deploying ngn-orders-job..."
JOB="ngn-orders-job"
IMAGE="asia-northeast1-docker.pkg.dev/${PROJECT}/ngn-dashboard/${JOB}:manual-$(date +%Y%m%d-%H%M%S)"

cp docker/Dockerfile-orders ./Dockerfile
gcloud builds submit --tag "$IMAGE" .
rm ./Dockerfile

gcloud run jobs update "$JOB" \
  --image "$IMAGE" \
  --region="$REGION" \
  --service-account="$SA" \
  --memory=1Gi \
  --cpu=1 \
  --max-retries=3 \
  --task-timeout=600s

echo "✅ ngn-orders-job 배포 완료!"

# ============================================
# 완료
# ============================================
echo ""
echo "============================================"
echo "🎉 모든 Job 배포 완료!"
echo "============================================"
echo "배포된 Jobs:"
echo "  ✅ query-sales-today-job"
echo "  ✅ query-sales-yesterday-job"
echo "  ✅ query-sales-prev-month-job"
echo "  ✅ ngn-orders-job"
echo "============================================"
