#!/bin/bash
# ============================================
# 데모 계정 스냅샷 로컬 테스트 (Cloud Run Job 방식)
# ============================================

# 현재 디렉토리 확인
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 환경 변수 파일은 Python Job 파일 내부에서 자동으로 로드됩니다
# (~/ngn_board/config/ngn.env)

echo "=========================================="
echo "데모 계정 스냅샷 로컬 테스트 (Job 방식)"
echo "=========================================="

# 환경 변수 기본값 설정 (env 파일에 없을 경우)
export GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT:-winged-precept-443218-v8}"
export GCS_BUCKET="${GCS_BUCKET:-winged-precept-443218-v8.appspot.com}"
export COMPANY_NAMES="${COMPANY_NAMES:-piscess,demo}"

echo "환경 변수:"
echo "  GOOGLE_CLOUD_PROJECT: $GOOGLE_CLOUD_PROJECT"
echo "  GCS_BUCKET: $GCS_BUCKET"
echo "  COMPANY_NAMES: $COMPANY_NAMES"
echo ""

# ============================================
# 1. 월간 스냅샷 Job 실행
# ============================================
echo "📊 [1/3] 월간 스냅샷 Job 실행 중..."
echo "----------------------------------------"
python3 tools/ai_report_test/jobs/monthly_snapshot_job.py

if [ $? -eq 0 ]; then
    echo "✅ 월간 스냅샷 Job 완료!"
else
    echo "❌ 월간 스냅샷 Job 실패"
    exit 1
fi

# ============================================
# 2. 29CM 트렌드 스냅샷 Job 실행
# ============================================
echo ""
echo "📊 [2/3] 29CM 트렌드 스냅샷 Job 실행 중..."
echo "----------------------------------------"
python3 tools/ai_report_test/jobs/trend_29cm_snapshot_job.py

if [ $? -eq 0 ]; then
    echo "✅ 29CM 트렌드 스냅샷 Job 완료!"
else
    echo "❌ 29CM 트렌드 스냅샷 Job 실패"
    exit 1
fi

# ============================================
# 3. 에이블리 트렌드 스냅샷 Job 실행
# ============================================
echo ""
echo "📊 [3/3] 에이블리 트렌드 스냅샷 Job 실행 중..."
echo "----------------------------------------"
python3 tools/ai_report_test/jobs/trend_ably_snapshot_job.py

if [ $? -eq 0 ]; then
    echo "✅ 에이블리 트렌드 스냅샷 Job 완료!"
else
    echo "❌ 에이블리 트렌드 스냅샷 Job 실패"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ 모든 Job 실행 완료!"
echo "=========================================="
