#!/bin/bash
set -euo pipefail

# 2-1. 변수 설정
TIMESTAMP=$(date +"%Y%m%d-%H%M%S")
PROJECT="winged-precept-443218-v8"
IMAGE="asia-northeast1-docker.pkg.dev/$PROJECT/ngn-dashboard/ngn-refund-job:manual-$TIMESTAMP"

# 2-2. Dockerfile을 루트로 복사
cp docker/Dockerfile-refund ./Dockerfile

# 2-3. 빌드 및 업데이트 실행
gcloud builds submit --tag="$IMAGE" --project="$PROJECT" . && \
gcloud run jobs update ngn-refund-job --image="$IMAGE" --region="asia-northeast3" --project="$PROJECT" --service-account="439320386143-compute@developer.gserviceaccount.com" --memory=512Mi --cpu=1 --max-retries=3 --task-timeout=600s

# 2-4. 임시 파일 삭제
rm ./Dockerfile
















