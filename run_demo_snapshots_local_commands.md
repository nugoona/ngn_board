# 데모 계정 스냅샷 로컬 실행 명령어

## 개별 실행

### 1. 월간 스냅샷 생성 (2025년 12월 예시)
```bash
python3 tools/ai_report_test/bq_monthly_snapshot.py demo 2025 12 --save-to-gcs --force
```

**다른 월 테스트:**
```bash
# 2025년 11월
python3 tools/ai_report_test/bq_monthly_snapshot.py demo 2025 11 --save-to-gcs --force

# 2025년 10월
python3 tools/ai_report_test/bq_monthly_snapshot.py demo 2025 10 --save-to-gcs --force
```

**옵션 설명:**
- `demo`: 회사명
- `2025 12`: 연도와 월
- `--save-to-gcs`: GCS에 저장
- `--force`: 기존 스냅샷이 있어도 재생성

---

### 2. 29CM 트렌드 스냅샷 생성
```bash
python3 tools/trend_29cm_snapshot.py --company-name demo
```

**특정 run_id로 테스트:**
```bash
python3 tools/trend_29cm_snapshot.py --company-name demo --run-id 2025W01_WEEKLY_20250106
```

---

### 3. 에이블리 트렌드 스냅샷 생성
```bash
python3 tools/trend_ably_snapshot.py --company-name demo
```

**특정 run_id로 테스트:**
```bash
python3 tools/trend_ably_snapshot.py --company-name demo --run-id 2025W01
```

---

## 한 번에 실행 (스크립트 사용)

```bash
# 실행 권한 부여 (최초 1회)
chmod +x run_demo_snapshots_local.sh

# 실행
./run_demo_snapshots_local.sh
```

---

## 환경 변수 설정 (필요한 경우)

```bash
export GOOGLE_CLOUD_PROJECT="winged-precept-443218-v8"
export GCS_BUCKET="winged-precept-443218-v8.appspot.com"
export GEMINI_API_KEY="your-api-key-here"  # AI 분석을 위한 경우
```
