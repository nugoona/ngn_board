#!/bin/bash
set -euo pipefail

# Codespaces 경로로 이동
cd /workspaces/ngn_dashboard

PROJECT="winged-precept-443218-v8"
REGION_RUN="asia-northeast1"
SERVICE="ngn-wep"
SA="439320386143-compute@developer.gserviceaccount.com"

echo "=========================================="
echo "🚀 [Gemini & Meta] 대시보드 최종 배포 시작"
echo "=========================================="

# 1. 환경 변수 직접 설정 (파일에서 읽지 않고 즉시 주입)
GEMINI_API_KEY="AIzaSyAajfFCfpc1NcgazcbiQxjwHXP9p4jFNQg"
META_SYSTEM_TOKEN='EAAPedvkO7m4BOzwxExPzDhPRDkh59illVkGZAApj5W2ZAjwA7SIZC8gwlNruazGHqDwGCZBIwKwnTIm5zDsHsBQpDFCi8bDAjGrlOP9fiuMn13TpSNpBlaCwktV3DFctQKnCxZCauCJGOO1CwLBwDompzxz4adA4dvvyNIRKYfNmTszZAR43r2O3uNcmpDZCJdYbgZDZD'
META_SYSTEM_USER_TOKEN='EAAPedvkO7m4BQF0hLQZAZBH4OX1LKhtSRLDJv2aXyrOnqsBZC0doGkrZAN4ZCiQ9TE3BeW1cP33lgf4Hbvw6bZCmUuWLUgh0nikz2EoatIEcKETPGr0pQIQLo5RxSOkjvBNGGI80Mb4v2wggzr39qqmRUsO0c9NZCxWi2AuSJpX0Af5foAcxjLad7YsY2lk'
META_APP_ID='1089027496144494'
META_APP_SECRET='9387d1b5b725c49b76500ffa00c69553'
CRAWL_FUNCTION_URL="https://asia-northeast3-winged-precept-443218-v8.cloudfunctions.net/crawl_catalog"

# 2. Dockerfile 복사
echo "📋 1. Dockerfile 준비 중..."
cp docker/Dockerfile-dashboard ./Dockerfile

# 3. 이미지 태그 생성 및 빌드
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
IMAGE="asia-northeast1-docker.pkg.dev/${PROJECT}/ngn-dashboard/ngn-dashboard:deploy-${TIMESTAMP}"

echo "🔨 2. 이미지 빌드 중..."
gcloud builds submit --tag "$IMAGE" --project="$PROJECT" .

# 4. Cloud Run 배포 (모든 변수 전달)
echo "🚀 3. Cloud Run 배포 중..."
gcloud run deploy "$SERVICE" \
  --image="$IMAGE" \
  --region="$REGION_RUN" \
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
  --update-env-vars="GEMINI_API_KEY=$GEMINI_API_KEY,META_SYSTEM_TOKEN=$META_SYSTEM_TOKEN,META_SYSTEM_USER_TOKEN=$META_SYSTEM_USER_TOKEN,META_APP_ID=$META_APP_ID,META_APP_SECRET=$META_APP_SECRET,CRAWL_FUNCTION_URL=$CRAWL_FUNCTION_URL"

# 5. 임시 파일 삭제
rm ./Dockerfile

echo "=========================================="
echo "✅ 배포 완료! 대시보드가 정상적으로 업데이트되었습니다."
echo "=========================================="
