#!/bin/bash
########################################
# ngn-wep Cloud Run 대시보드 배포 스크립트
# - Artifact Registry: asia-northeast1
# - Cloud Run: asia-northeast1
########################################
set -euo pipefail

# 1. 작업 디렉토리 설정
cd /workspaces/ngn_dashboard

# 2. 최신 코드 동기화
echo "📥 최신 코드 가져오는 중..."
git pull origin main

# 3. 프로젝트 설정
PROJECT="winged-precept-443218-v8"
REGION="asia-northeast1"
REPO="ngn-dashboard"
SERVICE="ngn-wep"
SA="439320386143-compute@developer.gserviceaccount.com"

# 4. 이미지 태그 생성
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/${REPO}/ngn-dashboard:deploy-${TIMESTAMP}"

echo "------------------------------------------------"
echo "🔨 이미지 경로: $IMAGE"
echo "🌏 빌드/배포 리전: $REGION"
echo "------------------------------------------------"

# 5. 환경 변수 로드 (선택적)
if [ -f config/ngn.env ]; then
  echo "📝 환경 변수 로드 중..."
  set -a
  source config/ngn.env
  set +a
else
  echo "⚠️  config/ngn.env 파일이 없습니다. 환경 변수 없이 진행합니다."
fi

# 6. Dockerfile 준비
echo "📋 Dockerfile 복사 중..."
cp docker/Dockerfile-dashboard ./Dockerfile

# 7. 빌드 및 푸시 (cloudbuild.yaml 무시)
echo "🔨 Docker 이미지 빌드 중... (몇 분 소요될 수 있습니다)"
if ! gcloud builds submit \
  --tag "$IMAGE" \
  --project="$PROJECT" \
  --region="$REGION" \
  --config=/dev/null \
  .; then
  echo "❌ 빌드 실패!"
  rm -f ./Dockerfile
  exit 1
fi

# 8. 임시 파일 정리
echo "🧹 임시 파일 정리 중..."
rm -f ./Dockerfile

# 9. Cloud Run 배포
echo "🚀 Cloud Run 서비스 배포 중..."
gcloud run deploy "$SERVICE" \
  --image="$IMAGE" \
  --region="$REGION" \
  --project="$PROJECT" \
  --platform=managed \
  --allow-unauthenticated \
  --service-account="$SA" \
  --memory=1Gi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=3 \
  --cpu-boost \
  --execution-environment=gen2 \
  --update-env-vars="GEMINI_API_KEY=${GEMINI_API_KEY:-},META_SYSTEM_TOKEN=${META_SYSTEM_TOKEN:-},META_SYSTEM_USER_TOKEN=${META_SYSTEM_USER_TOKEN:-},META_APP_ID=${META_APP_ID:-},META_APP_SECRET=${META_APP_SECRET:-},CRAWL_FUNCTION_URL=${CRAWL_FUNCTION_URL:-https://asia-northeast3-winged-precept-443218-v8.cloudfunctions.net/crawl_catalog},GOOGLE_CLOUD_PROJECT=${PROJECT},GCS_BUCKET=winged-precept-443218-v8.appspot.com" \
  --quiet

echo ""
echo "------------------------------------------------"
echo "✅ 배포 완료!"
echo "📝 배포된 이미지: $IMAGE"
echo "🔗 접속 URL: $(gcloud run services describe $SERVICE --platform managed --region $REGION --project $PROJECT --format 'value(status.url)')"
echo "------------------------------------------------"
