#!/bin/bash
########################################
# 기존 Job/Scheduler 정리 스크립트
# 통합 파이프라인으로 대체된 Job들 삭제
########################################
set -euo pipefail

PROJECT="winged-precept-443218-v8"
REGION="asia-northeast3"

echo "========================================"
echo "🧹 기존 Job/Scheduler 정리"
echo "========================================"
echo ""
echo "⚠️  다음 Job/Scheduler들이 삭제됩니다:"
echo ""

# ─────────────────────────────────────────────────────────────
# 삭제 대상 목록
# ─────────────────────────────────────────────────────────────

# Meta 관련 (통합됨)
SCHEDULERS_TO_DELETE=(
    "ngn-meta-ads-job"
    "ngn-meta-query-job"
    "ngn-meta-ads-job-yesterday"
    "ngn-meta-query-job-yesterday"
    # Cafe24 관련 (통합됨)
    "ngn-orders-job"
    "query-sales-today-job"
    "query-items-today-job"
    "ngn-orders-job-yesterday"
    "query-sales-yesterday-job"
    "query-items-yesterday-job"
    # GA4 관련 (통합됨)
    "ngn-ga4-traffic-job"
    "ngn-ga4-view-job"
    "ngn-ga4-traffic-job-yesterday"
    "ngn-ga4-view-job-yesterday"
    # Performance Summary (Daily Batch에 통합됨)
    "ngn-performance-summary-today"
    "ngn-performance-summary-yesterday"
    # Product 관련 (Cafe24에 통합됨)
    "ngn-product-job"
    "ngn-product-job-yesterday"
)

JOBS_TO_DELETE=(
    "ngn-meta-ads-job"
    "ngn-meta-query-job"
    "ngn-meta-ads-job-yesterday"
    "ngn-meta-query-job-yesterday"
    "ngn-orders-job"
    "query-sales-today-job"
    "query-items-today-job"
    "ngn-orders-job-yesterday"
    "query-sales-yesterday-job"
    "query-items-yesterday-job"
    "ngn-ga4-traffic-job"
    "ngn-ga4-view-job"
    "ngn-ga4-traffic-job-yesterday"
    "ngn-ga4-view-job-yesterday"
    "ngn-performance-summary-today"
    "ngn-performance-summary-yesterday"
    "ngn-product-job"
    "ngn-product-job-yesterday"
)

echo "Schedulers:"
for s in "${SCHEDULERS_TO_DELETE[@]}"; do
    echo "  - $s"
done

echo ""
echo "Jobs:"
for j in "${JOBS_TO_DELETE[@]}"; do
    echo "  - $j"
done

echo ""
read -p "정말 삭제하시겠습니까? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ 취소되었습니다."
    exit 0
fi

echo ""
echo "────────────────────────────────────────"
echo "Scheduler 삭제 중..."
echo "────────────────────────────────────────"

for s in "${SCHEDULERS_TO_DELETE[@]}"; do
    echo "삭제: $s"
    gcloud scheduler jobs delete "$s" \
        --location="$REGION" \
        --project="$PROJECT" \
        --quiet 2>/dev/null || echo "  (없거나 이미 삭제됨)"
done

echo ""
echo "────────────────────────────────────────"
echo "Job 삭제 중..."
echo "────────────────────────────────────────"

for j in "${JOBS_TO_DELETE[@]}"; do
    echo "삭제: $j"
    gcloud run jobs delete "$j" \
        --region="$REGION" \
        --project="$PROJECT" \
        --quiet 2>/dev/null || echo "  (없거나 이미 삭제됨)"
done

echo ""
echo "========================================"
echo "🎉 정리 완료!"
echo "========================================"
echo ""
echo "남은 Job 목록:"
gcloud run jobs list --region="$REGION" --project="$PROJECT" --format="table(name)" 2>/dev/null
