#!/bin/bash
set -euo pipefail
cd ~/ngn_board

JOB="ngn-refund-job"
REGION_RUN="asia-northeast3"
REGION_AR="asia-northeast1"
REPO="ngn-dashboard"
PROJECT="winged-precept-443218-v8"
SA="439320386143-compute@developer.gserviceaccount.com"
DOCKERFILE="docker/Dockerfile-refund"

IMAGE="${REGION_AR}-docker.pkg.dev/${PROJECT}/${REPO}/${JOB}:manual-$(date +%Y%m%d-%H%M%S)"

echo "🚀 Building image for ${JOB}..."
gcloud builds submit --tag "$IMAGE" --dockerfile="$DOCKERFILE" .

echo "📦 Updating Cloud Run Job..."
gcloud run jobs update "$JOB" \
  --image "$IMAGE" \
  --region="$REGION_RUN" \
  --service-account="$SA" \
  --memory=512Mi \
  --cpu=1 \
  --max-retries=3 \
  --task-timeout=600s

echo "✅ Deployment completed for ${JOB}!"
echo "💡 To execute: gcloud run jobs execute $JOB --region=$REGION_RUN"


