#!/bin/bash

# 2단계만 실행: Cloud Run Job 업데이트

set -euo pipefail

# config/ngn.env 또는 .env 파일에서 GEMINI_API_KEY 로드
if [ -f config/ngn.env ]; then
  GEMINI_API_KEY=$(grep -v '^#' config/ngn.env | grep "^GEMINI_API_KEY=" | cut -d'=' -f2- | tr -d '"' | tr -d "'" | xargs)
  export GEMINI_API_KEY
  echo "✅ config/ngn.env에서 GEMINI_API_KEY 로드"
elif [ -f .env ]; then
  GEMINI_API_KEY=$(grep -v '^#' .env | grep "^GEMINI_API_KEY=" | cut -d'=' -f2- | tr -d '"' | tr -d "'" | xargs)
  export GEMINI_API_KEY
  echo "✅ .env에서 GEMINI_API_KEY 로드"
fi

# GEMINI_API_KEY 확인
if [ -z "${GEMINI_API_KEY:-}" ]; then
  echo "❌ [ERROR] GEMINI_API_KEY가 설정되지 않았습니다."
  echo "   .env 파일에 GEMINI_API_KEY=your-key 형식으로 추가해주세요."
  exit 1
fi

PROJECT="winged-precept-443218-v8"
REGION_RUN="asia-northeast3"
JOB="monthly-snapshot-job"
SA="439320386143-compute@developer.gserviceaccount.com"

# 이미지 이름을 인자로 받거나, 가장 최근 이미지 사용
if [ -z "${1:-}" ]; then
  echo "⚠️  이미지 이름을 지정하지 않았습니다. 가장 최근 이미지를 조회합니다..."
  # 가장 최근 이미지 조회 (태그가 manual-로 시작하는 것)
  IMAGE_TAG=$(gcloud container images list-tags "asia-northeast1-docker.pkg.dev/${PROJECT}/ngn-dashboard/${JOB}" \
    --filter="tags:manual-*" \
    --sort-by="~timestamp" \
    --limit=1 \
    --format="value(tags[0])" 2>/dev/null || echo "")
  
  if [ -z "$IMAGE_TAG" ]; then
    echo "❌ [ERROR] 빌드된 이미지를 찾을 수 없습니다."
    echo "   사용법: $0 <이미지-태그>"
    echo "   예: $0 manual-20260110-123701"
    exit 1
  fi
  
  IMAGE="asia-northeast1-docker.pkg.dev/${PROJECT}/ngn-dashboard/${JOB}:${IMAGE_TAG}"
  echo "✅ 최근 이미지 사용: ${IMAGE}"
else
  IMAGE="asia-northeast1-docker.pkg.dev/${PROJECT}/ngn-dashboard/${JOB}:$1"
fi

echo ""
echo "🚀 Cloud Run Job 업데이트 중..."
echo "   이미지: ${IMAGE}"
echo ""

gcloud run jobs update "$JOB" \
  --image="$IMAGE" \
  --region="$REGION_RUN" \
  --service-account="$SA" \
  --memory=2Gi \
  --cpu=2 \
  --max-retries=3 \
  --task-timeout=3600s \
  --update-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT}" \
  --update-env-vars="BQ_DATASET=ngn_dataset" \
  --update-env-vars="GCS_BUCKET=winged-precept-443218-v8.appspot.com" \
  --update-env-vars="COMPANY_NAMES=piscess,demo" \
  --update-env-vars="GEMINI_API_KEY=${GEMINI_API_KEY}" \
  --project="$PROJECT"

echo ""
echo "✅ Job 업데이트 완료!"
