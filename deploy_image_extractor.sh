#!/bin/bash
########################################
# Image Extractor API Cloud Run 배포 스크립트
# - Artifact Registry: asia-northeast1 (도쿄)
# - Cloud Run: asia-northeast3 (서울) - 해외 IP 차단 우회
########################################
set -euo pipefail

# 1. 작업 디렉토리 설정
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

# 2. 프로젝트 설정
PROJECT="winged-precept-443218-v8"
AR_REGION="asia-northeast1"     # Artifact Registry 리전 (기존)
DEPLOY_REGION="asia-northeast3" # Cloud Run 배포 리전 (서울)
REPO="ngn-dashboard"
SERVICE="image-extractor-api"
SA="439320386143-compute@developer.gserviceaccount.com"

# 3. 이미지 태그 생성 (AR 리전 사용)
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
IMAGE="${AR_REGION}-docker.pkg.dev/${PROJECT}/${REPO}/${SERVICE}:deploy-${TIMESTAMP}"

echo "================================================"
echo "  Image Extractor API 배포"
echo "================================================"
echo "🔨 이미지 경로: $IMAGE"
echo "🏗️  빌드 리전: $AR_REGION (Artifact Registry)"
echo "🚀 배포 리전: $DEPLOY_REGION (Cloud Run)"
echo "------------------------------------------------"

# 4. Dockerfile 준비
echo "📋 Dockerfile 복사 중..."
cp docker/Dockerfile-image-extractor ./Dockerfile

# 5. cloudbuild.yaml 임시 이름 변경 (--tag 옵션과 충돌 방지)
if [ -f cloudbuild.yaml ]; then
  mv cloudbuild.yaml cloudbuild.yaml.bak
  RESTORE_CLOUDBUILD=true
else
  RESTORE_CLOUDBUILD=false
fi

# 6. 빌드 및 푸시 (AR 리전에서)
echo "🔨 Docker 이미지 빌드 중... (약 10분 소요)"
if ! gcloud builds submit \
  --tag "$IMAGE" \
  --project="$PROJECT" \
  --region="$AR_REGION" \
  --timeout=1800s \
  --machine-type=e2-highcpu-8 \
  .; then
  echo "❌ 빌드 실패!"
  rm -f ./Dockerfile
  [ "$RESTORE_CLOUDBUILD" = true ] && mv cloudbuild.yaml.bak cloudbuild.yaml
  exit 1
fi

# 7. 임시 파일 정리
echo "🧹 임시 파일 정리 중..."
rm -f ./Dockerfile
[ "$RESTORE_CLOUDBUILD" = true ] && mv cloudbuild.yaml.bak cloudbuild.yaml

# 8. Cloud Run 배포 (서울 리전에)
echo "🚀 Cloud Run 서비스 배포 중... (서울 리전)"
gcloud run deploy "$SERVICE" \
  --image="$IMAGE" \
  --region="$DEPLOY_REGION" \
  --project="$PROJECT" \
  --platform=managed \
  --allow-unauthenticated \
  --service-account="$SA" \
  --memory=2Gi \
  --cpu=1 \
  --timeout=300 \
  --concurrency=10 \
  --min-instances=0 \
  --max-instances=3 \
  --cpu-boost \
  --execution-environment=gen2 \
  --set-env-vars="PYTHONUNBUFFERED=1,GOOGLE_CLOUD_PROJECT=${PROJECT}" \
  --quiet

# 9. 새 서비스 URL 가져오기
NEW_URL=$(gcloud run services describe $SERVICE --platform managed --region $DEPLOY_REGION --project $PROJECT --format 'value(status.url)')

echo ""
echo "================================================"
echo "✅ 배포 완료!"
echo "📝 배포된 이미지: $IMAGE"
echo "🔗 서비스 URL: $NEW_URL"
echo ""
echo "⚠️  중요: 프론트엔드 API URL 업데이트 필요!"
echo "   IMAGE_EXTRACTOR_API = '$NEW_URL'"
echo ""
echo "테스트 명령어:"
echo "curl -X POST $NEW_URL/extract -H 'Content-Type: application/json' -d '{\"url\": \"https://example.com/product/123\", \"account_id\": \"1289149138367044\"}'"
echo "================================================"
