#!/bin/bash

# piscess 12월 데이터 테스트 스크립트

COMPANY="piscess"
YEAR=2025
MONTH=12

echo "=========================================="
echo "piscess ${YEAR}년 ${MONTH}월 데이터 테스트"
echo "=========================================="
echo ""

# 1. 스냅샷 생성
echo "📸 [1/2] 스냅샷 생성 중..."
echo "----------------------------------------"
python3 tools/ai_report_test/bq_monthly_snapshot.py ${COMPANY} ${YEAR} ${MONTH} --save-to-gcs

if [ $? -ne 0 ]; then
    echo "❌ 스냅샷 생성 실패"
    exit 1
fi

echo ""
echo "✅ 스냅샷 생성 완료"
echo ""

# 2. AI 분석 실행
echo "🤖 [2/2] AI 분석 실행 중..."
echo "----------------------------------------"

# GCS 경로
SNAPSHOT_PATH="gs://winged-precept-443218-v8.appspot.com/ai-reports/monthly/${COMPANY}/${YEAR}-${MONTH:02d}/snapshot.json.gz"

# 또는 로컬 파일이 있다면
# SNAPSHOT_PATH="tools/ai_report_test/snapshots/${COMPANY}_${YEAR}_${MONTH}.json"

python3 tools/ai_report_test/ai_analyst.py "${SNAPSHOT_PATH}"

if [ $? -ne 0 ]; then
    echo "❌ AI 분석 실패"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ 테스트 완료!"
echo "=========================================="
echo ""
echo "결과 확인:"
echo "  gsutil cat ${SNAPSHOT_PATH} | gunzip | jq '.signals'"
echo ""










