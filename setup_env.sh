#!/bin/bash

echo "🚀 ngn_board 프로젝트: Cloud Shell 환경 동기화 시작..."

# 1. 구글 클라우드 프로젝트 고정
export PROJECT_ID="winged-precept-443218-v8"
gcloud config set project $PROJECT_ID --quiet

# 2. 서비스 계정 파일 복구 (Secret -> JSON 파일)
mkdir -p config
if [ -z "$GCP_SERVICE_ACCOUNT_JSON" ]; then
    echo "⚠️ 경고: GCP_SERVICE_ACCOUNT_JSON 변수가 비어있습니다."
else
    echo "$GCP_SERVICE_ACCOUNT_JSON" > config/service-account.json
    export GOOGLE_APPLICATION_CREDENTIALS=$(pwd)/config/service-account.json
    
    # 🌟 핵심: gcloud CLI가 이 파일을 사용하도록 강제 활성화
    gcloud auth activate-service-account --key-file=$GOOGLE_APPLICATION_CREDENTIALS --quiet
    echo "✅ GCP 인증 및 서비스 계정 활성화 완료"
fi

# 3. 기타 환경변수 로드
export META_SYSTEM_TOKEN=$META_SYSTEM_TOKEN
export META_SYSTEM_USER_TOKEN=$META_SYSTEM_USER_TOKEN
export SLACK_WEBHOOK_URL=$SLACK_WEBHOOK_URL
export GEMINI_API_KEY=$GEMINI_API_KEY
export META_APP_ID=$META_APP_ID
export META_APP_SECRET=$META_APP_SECRET
export CRAWL_FUNCTION_URL=$CRAWL_FUNCTION_URL

echo "------------------------------------------------"
echo "✅ 모든 세팅이 완료되었습니다. 이제 gcloud 명령어를 바로 사용하세요!"
echo "------------------------------------------------"