#!/bin/bash

# Ably 트렌드 스냅샷 생성 스크립트
# Cloud Shell에서 실행

set -euo pipefail

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

# Python 스크립트 실행
echo "🚀 Ably 트렌드 스냅샷 생성 시작..."
echo ""

python3 tools/trend_ably_snapshot.py

echo ""
echo "✅ Ably 트렌드 스냅샷 생성 완료!"

