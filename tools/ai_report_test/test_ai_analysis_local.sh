#!/bin/bash
# 로컬에서 AI 분석 테스트 스크립트
# 사용법: ./test_ai_analysis_local.sh [company_name] [year] [month]

set -e

# 기본값 설정
COMPANY_NAME=${1:-piscess}
YEAR=${2:-2025}
MONTH=${3:-11}

# GCS 버킷
GCS_BUCKET="winged-precept-443218-v8.appspot.com"
SNAPSHOT_PATH="gs://${GCS_BUCKET}/ai-reports/monthly/${COMPANY_NAME}/${YEAR}-${MONTH:02d}/snapshot.json.gz"

# 로컬 임시 디렉토리
TEMP_DIR="./temp_test"
LOCAL_SNAPSHOT="${TEMP_DIR}/snapshot_${COMPANY_NAME}_${YEAR}-${MONTH:02d}.json.gz"
LOCAL_OUTPUT="${TEMP_DIR}/snapshot_${COMPANY_NAME}_${YEAR}-${MONTH:02d}_with_analysis.json"

echo "=========================================="
echo "🧪 로컬 AI 분석 테스트"
echo "=========================================="
echo "회사: ${COMPANY_NAME}"
echo "기간: ${YEAR}년 ${MONTH}월"
echo "스냅샷 경로: ${SNAPSHOT_PATH}"
echo "=========================================="
echo ""

# 임시 디렉토리 생성
mkdir -p "${TEMP_DIR}"

# GCS에서 스냅샷 다운로드
echo "📥 GCS에서 스냅샷 다운로드 중..."
if command -v gsutil &> /dev/null; then
    gsutil cp "${SNAPSHOT_PATH}" "${LOCAL_SNAPSHOT}"
    echo "✅ 다운로드 완료: ${LOCAL_SNAPSHOT}"
else
    echo "⚠️ gsutil이 설치되지 않았습니다. Python으로 다운로드 시도..."
    python3 -c "
from google.cloud import storage
import gzip
import json
import sys

bucket_name = '${GCS_BUCKET}'
blob_path = 'ai-reports/monthly/${COMPANY_NAME}/${YEAR}-${MONTH:02d}/snapshot.json.gz'
local_path = '${LOCAL_SNAPSHOT}'

client = storage.Client()
bucket = client.bucket(bucket_name)
blob = bucket.blob(blob_path)

if not blob.exists():
    print(f'❌ 파일이 존재하지 않습니다: gs://{bucket_name}/{blob_path}')
    sys.exit(1)

print(f'📥 다운로드 중: gs://{bucket_name}/{blob_path}')
blob.download_to_filename(local_path)
print(f'✅ 다운로드 완료: {local_path}')
"
fi

# 압축 해제 (필요한 경우)
if [[ "${LOCAL_SNAPSHOT}" == *.gz ]]; then
    echo "📦 압축 해제 중..."
    LOCAL_UNCOMPRESSED="${LOCAL_SNAPSHOT%.gz}"
    gunzip -c "${LOCAL_SNAPSHOT}" > "${LOCAL_UNCOMPRESSED}"
    LOCAL_SNAPSHOT="${LOCAL_UNCOMPRESSED}"
    echo "✅ 압축 해제 완료: ${LOCAL_SNAPSHOT}"
fi

# AI 분석 실행
echo ""
echo "🤖 AI 분석 실행 중..."
echo "=========================================="

python3 tools/ai_report_test/ai_analyst.py \
    "${LOCAL_SNAPSHOT}" \
    "${LOCAL_OUTPUT}" \
    tools/ai_report_test/system_prompt_v44.txt

echo ""
echo "=========================================="
echo "✅ 테스트 완료!"
echo "=========================================="
echo "입력 파일: ${LOCAL_SNAPSHOT}"
echo "출력 파일: ${LOCAL_OUTPUT}"
echo ""
echo "결과 확인:"
echo "  cat ${LOCAL_OUTPUT} | jq '.signals'"
echo ""

