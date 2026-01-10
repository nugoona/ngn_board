# 데모 계정 스냅샷 로컬 테스트 (Cloud Run Job 방식)

## 개별 실행

### 1. 월간 스냅샷 Job
```bash
python3 tools/ai_report_test/jobs/monthly_snapshot_job.py
```

이 Job은:
- 환경 변수 `COMPANY_NAMES`에서 업체 목록을 가져옴 (기본값: `piscess,demo`)
- 전월 데이터로 스냅샷 생성
- 각 업체별로 스냅샷 생성 및 AI 분석 추가

---

### 2. 29CM 트렌드 스냅샷 Job
```bash
python3 tools/ai_report_test/jobs/trend_29cm_snapshot_job.py
```

이 Job은:
- `get_all_companies_from_bq()`로 모든 업체 목록 조회 (demo 포함)
- 최신 주차 데이터로 스냅샷 생성
- 각 업체별로 스냅샷 생성 및 AI 분석 추가

---

### 3. 에이블리 트렌드 스냅샷 Job
```bash
python3 tools/ai_report_test/jobs/trend_ably_snapshot_job.py
```

이 Job은:
- `get_all_companies_from_bq()`로 모든 업체 목록 조회 (demo 포함)
- 최신 주차 데이터로 스냅샷 생성
- 각 업체별로 스냅샷 생성 및 AI 분석 추가

---

## 한 번에 실행

```bash
chmod +x run_demo_snapshots_job_local.sh
./run_demo_snapshots_job_local.sh
```

---

## 환경 변수 설정 (선택사항)

```bash
# 월간 스냅샷 Job에서 사용
export COMPANY_NAMES="piscess,demo"
export GOOGLE_CLOUD_PROJECT="winged-precept-443218-v8"
export GCS_BUCKET="winged-precept-443218-v8.appspot.com"
export GEMINI_API_KEY="your-api-key"  # AI 분석용
```

---

## 주의사항

1. **월간 스냅샷 Job**: 전월 데이터를 사용하므로, 오늘이 1월 1일이면 2024년 12월 리포트를 생성합니다.
2. **트렌드 스냅샷 Job**: 최신 주차 데이터를 자동으로 찾아서 사용합니다.
3. 모든 Job은 업체별로 스냅샷을 생성하므로, demo 계정도 포함되어 처리됩니다.
