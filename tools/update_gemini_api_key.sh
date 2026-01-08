#!/bin/bash

set -euo pipefail

# =============================================================================
# Gemini API 키 업데이트 스크립트
# Cloud Run Job들의 환경변수만 업데이트합니다 (재빌드/재배포 없이)
#
# 사용법:
#   1. .env 파일 사용: ./tools/update_gemini_api_key.sh
#   2. 직접 입력:      GEMINI_API_KEY=AIzaSy... ./tools/update_gemini_api_key.sh
#   3. 대화형 입력:    ./tools/update_gemini_api_key.sh (키가 없으면 프롬프트)
# =============================================================================

# Cloud Shell 환경: ~/ngn_board로 이동
cd ~/ngn_board || {
  echo "❌ [ERROR] ~/ngn_board 디렉토리를 찾을 수 없습니다."
  exit 1
}

PROJECT="winged-precept-443218-v8"
REGION="asia-northeast3"

# =============================================================================
# GEMINI_API_KEY 로드 (우선순위: 환경변수 > .env 파일 > 대화형 입력)
# =============================================================================

# 1. 환경변수에서 확인
if [ -n "${GEMINI_API_KEY:-}" ]; then
  echo "✅ 환경변수에서 GEMINI_API_KEY 로드됨"

# 2. .env 파일에서 로드
elif [ -f .env ]; then
  GEMINI_API_KEY=$(grep -v '^#' .env | grep "^GEMINI_API_KEY=" | cut -d'=' -f2- | tr -d '"' | tr -d "'" | xargs) || true
  if [ -n "${GEMINI_API_KEY:-}" ]; then
    echo "✅ .env 파일에서 GEMINI_API_KEY 로드됨"
  fi
fi

# 3. 키가 없으면 대화형으로 입력 받기
if [ -z "${GEMINI_API_KEY:-}" ]; then
  echo ""
  echo "🔑 GEMINI_API_KEY를 입력하세요 (Google AI Studio에서 발급):"
  echo "   https://aistudio.google.com/app/apikey"
  echo ""
  read -r -p "API Key: " GEMINI_API_KEY

  if [ -z "${GEMINI_API_KEY:-}" ]; then
    echo "❌ [ERROR] API 키가 입력되지 않았습니다."
    exit 1
  fi
fi

# =============================================================================
# API 키 유효성 기본 검사
# =============================================================================

# AIza로 시작하는지 확인 (Google API 키 형식)
if [[ ! "$GEMINI_API_KEY" =~ ^AIza ]]; then
  echo "⚠️  [WARN] API 키가 'AIza'로 시작하지 않습니다. 올바른 Gemini API 키인지 확인하세요."
fi

# 키 길이 확인 (일반적으로 39자)
KEY_LENGTH=${#GEMINI_API_KEY}
if [ "$KEY_LENGTH" -lt 30 ]; then
  echo "❌ [ERROR] API 키가 너무 짧습니다 (${KEY_LENGTH}자). 올바른 키를 입력하세요."
  exit 1
fi

# API 키 미리보기 (보안을 위해 일부만 표시)
MASKED_KEY="${GEMINI_API_KEY:0:8}...${GEMINI_API_KEY: -4}"
echo ""
echo "🔑 사용할 API 키: $MASKED_KEY (총 ${KEY_LENGTH}자)"
echo ""

# =============================================================================
# Cloud Run Jobs 업데이트
# =============================================================================

# 업데이트할 Job 목록 (Gemini API를 사용하는 Job들)
JOBS=(
  "monthly-ai-analysis-job"
  "monthly-snapshot-job"
  "ngn-29cm-best-job"
  "ably-best-collector-job"
)

echo "🔄 Cloud Run Jobs 환경변수 업데이트 중..."
echo "   프로젝트: $PROJECT"
echo "   리전: $REGION"
echo ""

SUCCESS_COUNT=0
SKIP_COUNT=0
FAIL_COUNT=0

for JOB in "${JOBS[@]}"; do
  printf "  %-30s : " "$JOB"

  # Job이 존재하는지 확인
  if gcloud run jobs describe "$JOB" --region="$REGION" --project="$PROJECT" &>/dev/null; then
    # 환경변수 업데이트 (--update-env-vars는 해당 키만 업데이트, 다른 환경변수는 유지)
    if gcloud run jobs update "$JOB" \
      --region="$REGION" \
      --project="$PROJECT" \
      --update-env-vars="GEMINI_API_KEY=${GEMINI_API_KEY}" \
      --quiet 2>/dev/null; then
      echo "✅ 완료"
      ((SUCCESS_COUNT++))
    else
      echo "❌ 실패"
      ((FAIL_COUNT++))
    fi
  else
    echo "⏭️  Job 없음 (스킵)"
    ((SKIP_COUNT++))
  fi
done

# =============================================================================
# 결과 요약
# =============================================================================

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 결과 요약"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ 성공: ${SUCCESS_COUNT}개"
echo "  ⏭️  스킵: ${SKIP_COUNT}개"
echo "  ❌ 실패: ${FAIL_COUNT}개"
echo ""

if [ "$SUCCESS_COUNT" -gt 0 ]; then
  echo "✅ GEMINI_API_KEY가 업데이트되었습니다."
  echo ""
  echo "📝 확인 방법:"
  echo "   gcloud run jobs describe monthly-ai-analysis-job \\"
  echo "     --region=$REGION --project=$PROJECT \\"
  echo "     --format='value(spec.template.spec.containers[0].env)' | tr ',' '\\n' | grep GEMINI"
  echo ""
  echo "🚀 Job 실행 테스트:"
  echo "   gcloud run jobs execute monthly-ai-analysis-job --region=$REGION --project=$PROJECT"
fi

if [ "$FAIL_COUNT" -gt 0 ]; then
  echo ""
  echo "⚠️  일부 Job 업데이트에 실패했습니다. 권한을 확인하세요:"
  echo "   gcloud auth list"
fi
