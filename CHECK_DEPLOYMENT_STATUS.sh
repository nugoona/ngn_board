#!/bin/bash

# 배포 상태 확인 스크립트

PROJECT="winged-precept-443218-v8"
REGION_RUN="asia-northeast1"
SERVICE="ngn-wep"
REPO="ngn-dashboard"

echo "=========================================="
echo "1. 현재 배포된 Cloud Run 서비스 정보"
echo "=========================================="
gcloud run services describe "$SERVICE" \
  --region="$REGION_RUN" \
  --project="$PROJECT" \
  --format="table(
    metadata.name,
    status.latestReadyRevisionName,
    spec.template.spec.containers[0].image,
    status.url
  )"

echo ""
echo "=========================================="
echo "2. 현재 사용 중인 이미지 상세 정보"
echo "=========================================="
CURRENT_IMAGE=$(gcloud run services describe "$SERVICE" \
  --region="$REGION_RUN" \
  --project="$PROJECT" \
  --format="value(spec.template.spec.containers[0].image)")

echo "현재 이미지: $CURRENT_IMAGE"

echo ""
echo "=========================================="
echo "3. 이미지 빌드 히스토리 (최근 5개)"
echo "=========================================="
gcloud container images list-tags \
  "${REGION_RUN}-docker.pkg.dev/${PROJECT}/${REPO}/ngn-dashboard" \
  --limit=5 \
  --sort-by=~TIMESTAMP \
  --format="table(
    TAGS,
    TIMESTAMP,
    DIGEST
  )"

echo ""
echo "=========================================="
echo "4. 최근 빌드 로그 (최근 3개)"
echo "=========================================="
gcloud builds list \
  --project="$PROJECT" \
  --limit=3 \
  --format="table(
    id,
    status,
    createTime,
    source.repoSource.branchName,
    images[0]
  )"

echo ""
echo "=========================================="
echo "5. 최근 Cloud Run 리비전 (최근 3개)"
echo "=========================================="
gcloud run revisions list \
  --service="$SERVICE" \
  --region="$REGION_RUN" \
  --project="$PROJECT" \
  --limit=3 \
  --format="table(
    metadata.name,
    status.conditions[0].status,
    spec.containers[0].image,
    metadata.creationTimestamp
  )"

echo ""
echo "=========================================="
echo "6. 현재 실행 중인 리비전의 환경 변수"
echo "=========================================="
gcloud run services describe "$SERVICE" \
  --region="$REGION_RUN" \
  --project="$PROJECT" \
  --format="value(spec.template.spec.containers[0].env)" | head -20

echo ""
echo "=========================================="
echo "7. 최근 Cloud Run 로그 (오류만)"
echo "=========================================="
gcloud run services logs read "$SERVICE" \
  --region="$REGION_RUN" \
  --project="$PROJECT" \
  --limit=20 \
  --format="value(textPayload)" | grep -i "error\|exception\|traceback" | head -10

echo ""
echo "=========================================="
echo "8. 이미지에 포함된 파일 확인 (data_handler.py)"
echo "=========================================="
echo "⚠️  이 명령어는 이미지를 다운로드해야 하므로 시간이 걸릴 수 있습니다."
echo "실행하려면 아래 명령어를 사용하세요:"
echo ""
echo "docker pull $CURRENT_IMAGE"
echo "docker run --rm $CURRENT_IMAGE cat /app/ngn_wep/dashboard/handlers/data_handler.py | grep -A 5 'gzip.GzipFile\|gzip.decompress'"

echo ""
echo "=========================================="
echo "9. 강제로 새 리비전 배포 (트래픽 없이)"
echo "=========================================="
echo "현재 이미지로 새 리비전을 강제 생성하려면:"
echo ""
echo "gcloud run services update $SERVICE \\"
echo "  --region=$REGION_RUN \\"
echo "  --project=$PROJECT \\"
echo "  --no-traffic"

