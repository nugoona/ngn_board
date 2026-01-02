#!/bin/bash

set -euo pipefail

# 월간 AI 분석 Cloud Run Job 배포 스크립트 (수정 버전)

cd ~/ngn_board || {
  echo "❌ [ERROR] ~/ngn_board 디렉토리로 이동할 수 없습니다."
  echo "   현재 디렉토리: $(pwd)"
  exit 1
}

# .env 파일에서 GEMINI_API_KEY 로드 (안전한 방식)
if [ -f .env ]; then
  # .env 파일에서 GEMINI_API_KEY만 추출 (주석 제외, = 기준으로 분리)
  GEMINI_API_KEY=$(grep -v '^#' .env | grep "^GEMINI_API_KEY=" | cut -d'=' -f2- | tr -d '"' | tr -d "'" | xargs)
  export GEMINI_API_KEY
fi

# GEMINI_API_KEY 확인
if [ -z "${GEMINI_API_KEY:-}" ]; then
  echo "❌ [ERROR] GEMINI_API_KEY가 설정되지 않았습니다."
  echo "   .env 파일에 GEMINI_API_KEY=your-key 형식으로 추가해주세요."
  exit 1
fi

echo "✅ GEMINI_API_KEY 로드 완료 (길이: ${#GEMINI_API_KEY}자)"

PROJECT="winged-precept-443218-v8"
REGION_AR="asia-northeast1"
REGION_RUN="asia-northeast3"
REPO="ngn-dashboard"
JOB="monthly-ai-analysis-job"
SA="439320386143-compute@developer.gserviceaccount.com"

IMAGE="${REGION_AR}-docker.pkg.dev/${PROJECT}/${REPO}/${JOB}:manual-$(date +%Y%m%d-%H%M%S)"

echo "🔨 1단계: Docker 이미지 빌드 중..."
# Dockerfile 임시 복사
if [ ! -f "docker/Dockerfile-monthly-ai-analysis" ]; then
  echo "❌ [ERROR] docker/Dockerfile-monthly-ai-analysis 파일을 찾을 수 없습니다."
  exit 1
fi

cp docker/Dockerfile-monthly-ai-analysis ./Dockerfile

# 빌드 + 푸시 (Cloud Build)
if ! gcloud builds submit --tag "$IMAGE" .; then
  echo "❌ [ERROR] Docker 이미지 빌드 실패"
  rm -f ./Dockerfile
  exit 1
fi

# 임시 Dockerfile 제거
rm ./Dockerfile

echo ""
echo "🚀 2단계: Cloud Run Job 배포 중..."
# Job이 없으면 생성, 있으면 업데이트
if gcloud run jobs describe "$JOB" --region="$REGION_RUN" --project="$PROJECT" &>/dev/null; then
  echo "Job이 이미 존재합니다. 업데이트 중..."
  # 환경 변수를 따옴표로 감싸서 특수문자 문제 방지
  gcloud run jobs update "$JOB" \
    --image="$IMAGE" \
    --region="$REGION_RUN" \
    --service-account="$SA" \
    --memory=4Gi \
    --cpu=2 \
    --max-retries=3 \
    --task-timeout=3600s \
    --update-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT},GCS_BUCKET=winged-precept-443218-v8.appspot.com,COMPANY_NAMES=piscess,GEMINI_API_KEY=${GEMINI_API_KEY}" \
    --project="$PROJECT"
else
  echo "새 Job 생성 중..."
  gcloud run jobs create "$JOB" \
    --image="$IMAGE" \
    --region="$REGION_RUN" \
    --service-account="$SA" \
    --memory=4Gi \
    --cpu=2 \
    --max-retries=3 \
    --task-timeout=3600s \
    --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT},GCS_BUCKET=winged-precept-443218-v8.appspot.com,COMPANY_NAMES=piscess,GEMINI_API_KEY=${GEMINI_API_KEY}" \
    --project="$PROJECT"
fi

echo ""
echo "✅ 배포 완료!"

