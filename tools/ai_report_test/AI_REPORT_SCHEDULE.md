# AI 리포트 관련 작업 스케줄 정리

## 📅 월간 스냅샷 관련 작업 스케줄

### 1. **monthly-rollup-job** (월간 집계 테이블 생성)
- **Cloud Run Job**: `monthly-rollup-job`
- **스케줄**: 매월 1일 새벽 3시 (`0 3 1 * *`)
- **시간대**: UTC (Asia/Seoul 기준 새벽 3시)
- **역할**: `mall_sales_monthly`, `meta_ads_monthly`, `ga4_traffic_monthly` 테이블 생성
- **배포 스크립트**: `tools/ai_report_test/jobs/deploy_monthly_rollup.sh`
- **Dockerfile**: `docker/Dockerfile-monthly-rollup`

### 2. **sheet-event-collector-job** (Event 시트 수집)
- **Cloud Run Job**: `sheet-event-collector-job`
- **스케줄**: 매월 1일 새벽 4시 20분 (`20 4 1 * *`)
- **시간대**: Asia/Seoul
- **역할**: Google Sheets event 시트 데이터를 BigQuery에 수집
- **배포 스크립트**: `tools/ai_report_test/jobs/deploy_sheet_event_collector.sh`
- **Dockerfile**: `docker/Dockerfile-sheet-event-collector`

### 3. **bq_monthly_snapshot.py** (월간 스냅샷 생성)
- **현재 상태**: ❌ **자동 실행 스케줄 없음** (수동 실행만 가능)
- **역할**: 월간 스냅샷 생성 및 GCS 버킷 저장
- **파일**: `tools/ai_report_test/bq_monthly_snapshot.py`
- **실행 방법**: 수동 실행
  ```bash
  python3 bq_monthly_snapshot.py <company_name> <year> <month> --save-to-gcs
  ```

## 📊 실행 순서 (권장)

월간 스냅샷 생성 전에 필요한 데이터가 준비되어야 하므로, 다음 순서로 실행됩니다:

1. **새벽 2시**: BigQuery 데이터 정리 (선택사항)
2. **새벽 3시**: 월간 집계 테이블 생성 (`monthly-rollup-job`)
3. **새벽 4시 20분**: Event 시트 수집 (`sheet-event-collector-job`)
4. **새벽 5시 이후**: 월간 스냅샷 생성 (현재 수동 실행)

## ⚠️ 주의사항

- **월간 스냅샷은 자동 실행 스케줄이 없습니다.**
- 월간 스냅샷을 자동화하려면 별도의 Cloud Run Job과 Scheduler를 생성해야 합니다.
- 월간 스냅샷은 `monthly-rollup-job`과 `sheet-event-collector-job`이 완료된 후 실행해야 합니다.

## 🔗 관련 파일

- `tools/ai_report_test/bq_monthly_snapshot.py` - 스냅샷 생성 스크립트
- `tools/ai_report_test/jobs/monthly_rollup_job.py` - 월간 집계 작업
- `tools/ai_report_test/jobs/sheet_event_collector.py` - Event 시트 수집
- `tools/ai_report_test/generate_monthly_report_from_snapshot.py` - 스냅샷 기반 리포트 생성

## 📝 추가 작업 필요

월간 스냅샷 자동화를 위해서는:
1. `Dockerfile-monthly-snapshot` 생성
2. `deploy_monthly_snapshot.sh` 배포 스크립트 생성
3. Cloud Scheduler 설정 (매월 1일 새벽 5시 권장)

