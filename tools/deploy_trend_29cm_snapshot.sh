#!/bin/bash

set -euo pipefail

# 29CM 트렌드 스냅샷 생성 Cloud Run Job 재배포 스크립트 (스케줄러 제외)

cd ~/ngn_board || {
  echo "❌ [ERROR] ~/ngn_board 디렉토리로 이동할 수 없습니다."
  echo "   현재 디렉토리: $(pwd)"
  exit 1
}

PROJECT="winged-precept-443218-v8"
REGION_AR="asia-northeast1"
REGION_RUN="asia-northeast3"
REPO="ngn-dashboard"
JOB="trend-29cm-snapshot-job"
SA="439320386143-compute@developer.gserviceaccount.com"

IMAGE="${REGION_AR}-docker.pkg.dev/${PROJECT}/${REPO}/${JOB}:manual-$(date +%Y%m%d-%H%M%S)"

echo "🔨 1단계: Docker 이미지 빌드 중..."
# Dockerfile 확인
if [ ! -f "docker/Dockerfile-trend-29cm-snapshot" ]; then
  echo "❌ [ERROR] docker/Dockerfile-trend-29cm-snapshot 파일을 찾을 수 없습니다."
  exit 1
fi

# Dockerfile 임시 복사
cp docker/Dockerfile-trend-29cm-snapshot ./Dockerfile

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
  gcloud run jobs update "$JOB" \
    --image="$IMAGE" \
    --region="$REGION_RUN" \
    --service-account="$SA" \
    --memory=2Gi \
    --cpu=2 \
    --max-retries=3 \
    --task-timeout=3600s \
    --update-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT},GCS_BUCKET=winged-precept-443218-v8.appspot.com,RUNNING_IN_CLOUD_RUN=true" \
    --project="$PROJECT"
else
  echo "새 Job 생성 중..."
  gcloud run jobs create "$JOB" \
    --image="$IMAGE" \
    --region="$REGION_RUN" \
    --service-account="$SA" \
    --memory=2Gi \
    --cpu=2 \
    --max-retries=3 \
    --task-timeout=3600s \
    --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT},GCS_BUCKET=winged-precept-443218-v8.appspot.com,RUNNING_IN_CLOUD_RUN=true" \
    --project="$PROJECT"
fi

echo ""
echo "✅ 배포 완료!"
echo ""
echo "📋 배포된 리소스:"
echo "  - Cloud Run Job: ${JOB}"
echo ""
echo "📝 수동 실행:"
echo "  gcloud run jobs execute ${JOB} --region=${REGION_RUN} --project=${PROJECT}"

