#!/bin/bash

# 강제로 새 이미지 빌드 및 배포 스크립트

set -euo pipefail
cd ~/ngn_board

PROJECT="winged-precept-443218-v8"
REGION_AR="asia-northeast1"
REGION_RUN="asia-northeast1"
REPO="ngn-dashboard"
SERVICE="ngn-wep"
SA="439320386143-compute@developer.gserviceaccount.com"

# 고유한 이미지 태그 생성 (타임스탬프 + 랜덤)
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
RANDOM_SUFFIX=$(openssl rand -hex 4)
IMAGE="${REGION_AR}-docker.pkg.dev/${PROJECT}/${REPO}/ngn-dashboard:deploy-${TIMESTAMP}-${RANDOM_SUFFIX}"

echo "=========================================="
echo "강제 새 이미지 빌드 및 배포"
echo "=========================================="
echo "이미지 태그: $IMAGE"
echo ""

# 1️⃣ 최신 코드
echo "📥 1. 최신 코드 가져오는 중..."
git pull origin main

# 2️⃣ env 로드
if [ -f config/ngn.env ]; then
  echo "📝 2. 환경 변수 로드 중..."
  set -a
  source config/ngn.env
  set +a
fi

# 3️⃣ Dockerfile 복사
echo "📋 3. Dockerfile 복사 중..."
cp docker/Dockerfile-dashboard ./Dockerfile

# 4️⃣ 기존 이미지 삭제 (선택사항, 주석 해제하면 실행)
# echo "🗑️  4. 기존 이미지 태그 삭제 중..."
# gcloud container images delete "${REGION_AR}-docker.pkg.dev/${PROJECT}/${REPO}/ngn-dashboard:latest" --quiet 2>/dev/null || true

# 5️⃣ 새 이미지 빌드
echo "🔨 5. 새 이미지 빌드 중... (이 작업은 몇 분 걸릴 수 있습니다)"
echo "   빌드 ID를 기록해두세요. 나중에 로그를 확인할 수 있습니다."
BUILD_ID=$(gcloud builds submit --tag "$IMAGE" . --format="value(id)" 2>&1 | tail -1)
echo "   빌드 ID: $BUILD_ID"

# 6️⃣ 정리
echo "🧹 6. 임시 파일 정리 중..."
rm ./Dockerfile

# 7️⃣ 빌드 완료 확인
echo "⏳ 7. 빌드 완료 대기 중..."
gcloud builds wait "$BUILD_ID" --project="$PROJECT"

# 8️⃣ 배포
echo "🚀 8. Cloud Run 서비스 배포 중..."
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
echo "=========================================="
echo "✅ 배포 완료!"
echo "=========================================="
echo "배포된 이미지: $IMAGE"
echo "빌드 ID: $BUILD_ID"
echo ""
echo "빌드 로그 확인:"
echo "  gcloud builds log $BUILD_ID --project=$PROJECT"
echo ""
echo "서비스 상태 확인:"
echo "  gcloud run services describe $SERVICE --region=$REGION_RUN --project=$PROJECT"

