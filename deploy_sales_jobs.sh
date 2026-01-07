#!/bin/bash

# Codespaces 경로로 수정
cd /workspaces/ngn_dashboard

# gcloud 경로 활성화
source ./google-cloud-sdk/path.bash.inc || source ~/google-cloud-sdk/path.bash.inc

PROJECT="winged-precept-443218-v8"
REGION="asia-northeast3"

echo "=========================================="
echo "🚀 [Codespaces] Sales Jobs 배포 시작"
echo "=========================================="

gcloud run jobs deploy sales-sync-job \
  --source . \
  --project "$PROJECT" \
  --region "$REGION" \
  --set-env-vars="ENV_TYPE=production" \
  --quiet

echo "=========================================="
echo "✅ 배포 완료!"
echo "=========================================="
