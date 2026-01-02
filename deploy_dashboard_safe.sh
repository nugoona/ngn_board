#!/bin/bash

set -euo pipefail
cd ~/ngn_board

# 1️⃣ 반드시 최신 코드
echo "📥 최신 코드 가져오는 중..."
git pull origin main

PROJECT="winged-precept-443218-v8"
REGION_AR="asia-northeast1"
REGION_RUN="asia-northeast1"
REPO="ngn-dashboard"
SERVICE="ngn-wep"
SA="439320386143-compute@developer.gserviceaccount.com"

IMAGE="${REGION_AR}-docker.pkg.dev/${PROJECT}/${REPO}/ngn-dashboard:deploy-$(date +%Y%m%d-%H%M%S)"

echo "🔨 이미지 태그: $IMAGE"

# 2️⃣ env 로드
if [ -f config/ngn.env ]; then
  echo "📝 환경 변수 로드 중..."
  set -a
  source config/ngn.env
  set +a
else
  echo "⚠️  config/ngn.env 파일이 없습니다. 환경 변수 없이 진행합니다."
fi

# 3️⃣ Dockerfile 복사
echo "📋 Dockerfile 복사 중..."
cp docker/Dockerfile-dashboard ./Dockerfile

# 4️⃣ 빌드 (단계별로 진행, 오류 발생 시 중단)
echo "🔨 Docker 이미지 빌드 중... (이 작업은 몇 분 걸릴 수 있습니다)"
if ! gcloud builds submit --tag "$IMAGE" .; then
  echo "❌ 빌드 실패!"
  rm -f ./Dockerfile
  exit 1
fi

# 3️⃣에서 복사한 Dockerfile 정리
echo "🧹 임시 파일 정리 중..."
rm ./Dockerfile

# 5️⃣ 배포
echo "🚀 Cloud Run 서비스 배포 중..."
gcloud run deploy "$SERVICE" \
  --image="$IMAGE" \
  --region="$REGION_RUN" \
  --platform=managed \
  --allow-unauthenticated \
  --service-account="$SA" \
  --memory=1Gi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=3 \
  --cpu-boost \
  --execution-environment=gen2 \
  --update-env-vars="META_SYSTEM_TOKEN=${META_SYSTEM_TOKEN:-},META_SYSTEM_USER_TOKEN=${META_SYSTEM_USER_TOKEN:-},CRAWL_FUNCTION_URL=https://asia-northeast3-winged-precept-443218-v8.cloudfunctions.net/crawl_catalog"

echo ""
echo "✅ 배포 완료!"
echo "📝 배포된 이미지: $IMAGE"
echo ""
echo "💡 배포 확인:"
echo "   gcloud run services describe $SERVICE --region=$REGION_RUN --project=$PROJECT"

