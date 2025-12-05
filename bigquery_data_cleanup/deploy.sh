#!/bin/bash

# BigQuery 데이터 정리 Cloud Run 배포 스크립트

PROJECT_ID="winged-precept-443218-v8"
SERVICE_NAME="bigquery-data-cleanup"
REGION="asia-northeast3"  # 서울 리전 (필요시 변경)
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "🔨 Docker 이미지 빌드 중..."
gcloud builds submit --tag ${IMAGE_NAME} --project ${PROJECT_ID}

echo "🚀 Cloud Run 서비스 배포 중..."
gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE_NAME} \
  --platform managed \
  --region ${REGION} \
  --project ${PROJECT_ID} \
  --allow-unauthenticated \
  --memory 512Mi \
  --timeout 540s \
  --max-instances 1 \
  --set-env-vars PROJECT_ID=${PROJECT_ID},DATASET_ID=ngn_dataset,MONTHS_TO_KEEP=13

echo "✅ 배포 완료!"
echo ""
echo "📋 다음 단계: Cloud Scheduler 설정"
echo "아래 명령어로 스케줄러를 생성하세요:"
echo ""
echo "gcloud scheduler jobs create http bigquery-cleanup-monthly \\"
echo "  --location=${REGION} \\"
echo "  --schedule='0 2 1 * *' \\"
echo "  --uri=\$(gcloud run services describe ${SERVICE_NAME} --region=${REGION} --format='value(status.url)') \\"
echo "  --http-method=POST \\"
echo "  --project=${PROJECT_ID}"
