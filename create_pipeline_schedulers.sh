#!/bin/bash
########################################
# 통합 파이프라인 Scheduler 생성 스크립트
# 기존 스케줄과 동일한 빈도 유지
########################################
set -euo pipefail

PROJECT="winged-precept-443218-v8"
REGION="asia-northeast3"

echo "========================================"
echo "📅 파이프라인 Scheduler 생성"
echo "========================================"

# ─────────────────────────────────────────────────────────────
# 1. Meta Pipeline Scheduler (매시간 9분 - 기존과 동일)
# ─────────────────────────────────────────────────────────────
echo "[1/4] Meta Pipeline Scheduler 생성..."
gcloud scheduler jobs create http ngn-meta-pipeline-scheduler \
    --location="$REGION" \
    --schedule="9 * * * *" \
    --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT}/jobs/ngn-meta-pipeline-job:run" \
    --http-method=POST \
    --oauth-service-account-email="439320386143-compute@developer.gserviceaccount.com" \
    --project="$PROJECT" \
    --quiet 2>/dev/null || \
gcloud scheduler jobs update http ngn-meta-pipeline-scheduler \
    --location="$REGION" \
    --schedule="9 * * * *" \
    --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT}/jobs/ngn-meta-pipeline-job:run" \
    --http-method=POST \
    --oauth-service-account-email="439320386143-compute@developer.gserviceaccount.com" \
    --project="$PROJECT" \
    --quiet
echo "✅ ngn-meta-pipeline-scheduler (매시간 09분)"

# ─────────────────────────────────────────────────────────────
# 2. Cafe24 Pipeline Scheduler (매시간 5분 - 기존과 동일)
# ─────────────────────────────────────────────────────────────
echo "[2/4] Cafe24 Pipeline Scheduler 생성..."
gcloud scheduler jobs create http ngn-cafe24-pipeline-scheduler \
    --location="$REGION" \
    --schedule="5 * * * *" \
    --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT}/jobs/ngn-cafe24-pipeline-job:run" \
    --http-method=POST \
    --oauth-service-account-email="439320386143-compute@developer.gserviceaccount.com" \
    --project="$PROJECT" \
    --quiet 2>/dev/null || \
gcloud scheduler jobs update http ngn-cafe24-pipeline-scheduler \
    --location="$REGION" \
    --schedule="5 * * * *" \
    --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT}/jobs/ngn-cafe24-pipeline-job:run" \
    --http-method=POST \
    --oauth-service-account-email="439320386143-compute@developer.gserviceaccount.com" \
    --project="$PROJECT" \
    --quiet
echo "✅ ngn-cafe24-pipeline-scheduler (매시간 05분)"

# ─────────────────────────────────────────────────────────────
# 3. GA4 Pipeline Scheduler (매시간 9분 - 기존과 동일)
# ─────────────────────────────────────────────────────────────
echo "[3/4] GA4 Pipeline Scheduler 생성..."
gcloud scheduler jobs create http ngn-ga4-pipeline-scheduler \
    --location="$REGION" \
    --schedule="9 * * * *" \
    --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT}/jobs/ngn-ga4-pipeline-job:run" \
    --http-method=POST \
    --oauth-service-account-email="439320386143-compute@developer.gserviceaccount.com" \
    --project="$PROJECT" \
    --quiet 2>/dev/null || \
gcloud scheduler jobs update http ngn-ga4-pipeline-scheduler \
    --location="$REGION" \
    --schedule="9 * * * *" \
    --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT}/jobs/ngn-ga4-pipeline-job:run" \
    --http-method=POST \
    --oauth-service-account-email="439320386143-compute@developer.gserviceaccount.com" \
    --project="$PROJECT" \
    --quiet
echo "✅ ngn-ga4-pipeline-scheduler (매시간 09분)"

# ─────────────────────────────────────────────────────────────
# 4. Daily Batch Pipeline Scheduler (매일 03:05 - 기존과 동일)
# ─────────────────────────────────────────────────────────────
echo "[4/4] Daily Batch Pipeline Scheduler 생성..."
gcloud scheduler jobs create http ngn-daily-batch-pipeline-scheduler \
    --location="$REGION" \
    --schedule="5 3 * * *" \
    --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT}/jobs/ngn-daily-batch-pipeline-job:run" \
    --http-method=POST \
    --oauth-service-account-email="439320386143-compute@developer.gserviceaccount.com" \
    --project="$PROJECT" \
    --quiet 2>/dev/null || \
gcloud scheduler jobs update http ngn-daily-batch-pipeline-scheduler \
    --location="$REGION" \
    --schedule="5 3 * * *" \
    --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT}/jobs/ngn-daily-batch-pipeline-job:run" \
    --http-method=POST \
    --oauth-service-account-email="439320386143-compute@developer.gserviceaccount.com" \
    --project="$PROJECT" \
    --quiet
echo "✅ ngn-daily-batch-pipeline-scheduler (매일 03:05)"

echo ""
echo "========================================"
echo "🎉 모든 Scheduler 생성 완료!"
echo "========================================"
