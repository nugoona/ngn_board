#!/bin/bash

# 배포된 이미지에 실제 코드가 포함되어 있는지 확인

PROJECT="winged-precept-443218-v8"
REGION_RUN="asia-northeast1"
SERVICE="ngn-wep"
REPO="ngn-dashboard"
REGION_AR="asia-northeast1"

echo "=========================================="
echo "배포된 이미지의 코드 확인"
echo "=========================================="

# 현재 배포된 이미지 가져오기
CURRENT_IMAGE=$(gcloud run services describe "$SERVICE" \
  --region="$REGION_RUN" \
  --project="$PROJECT" \
  --format="value(spec.template.spec.containers[0].image)")

echo "현재 이미지: $CURRENT_IMAGE"
echo ""

# 이미지에서 data_handler.py 파일 확인
echo "이미지에서 data_handler.py의 gzip 관련 코드 확인 중..."
echo ""

# Cloud Build를 사용하여 이미지 내부 확인
echo "방법 1: Cloud Build로 임시 컨테이너 실행"
echo "----------------------------------------"
cat << 'EOF' > /tmp/check_code.sh
#!/bin/bash
if [ -f /app/ngn_wep/dashboard/handlers/data_handler.py ]; then
  echo "✅ 파일 존재 확인"
  echo ""
  echo "gzip.GzipFile 사용 여부:"
  grep -n "gzip.GzipFile" /app/ngn_wep/dashboard/handlers/data_handler.py | head -3
  echo ""
  echo "gzip.decompress 사용 여부:"
  grep -n "gzip.decompress" /app/ngn_wep/dashboard/handlers/data_handler.py || echo "  ✅ gzip.decompress 없음 (좋음)"
  echo ""
  echo "io 모듈 import 여부:"
  grep -n "^import io\|^import.*io" /app/ngn_wep/dashboard/handlers/data_handler.py || echo "  ❌ io 모듈 import 없음"
else
  echo "❌ 파일을 찾을 수 없습니다"
fi
EOF

echo "임시 컨테이너로 코드 확인 중..."
gcloud builds submit --config=- <<EOF
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['run', '--rm', '$CURRENT_IMAGE', 'bash', '-c', 'cat /app/ngn_wep/dashboard/handlers/data_handler.py | grep -A 3 "gzip.GzipFile\|gzip.decompress" || echo "파일 확인 실패"']
EOF

echo ""
echo "=========================================="
echo "방법 2: 로컬에서 이미지 다운로드 후 확인"
echo "=========================================="
echo "다음 명령어를 로컬에서 실행하세요:"
echo ""
echo "docker pull $CURRENT_IMAGE"
echo "docker run --rm $CURRENT_IMAGE grep -A 5 'gzip.GzipFile\|gzip.decompress' /app/ngn_wep/dashboard/handlers/data_handler.py"

