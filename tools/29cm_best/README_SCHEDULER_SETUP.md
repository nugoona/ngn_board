# 29CM BEST Job 스케줄러 설정 가이드

## 개요
`ngn-29cm-best-job`이 매주 월요일 오전 8시에 자동 실행되도록 Cloud Scheduler를 설정합니다.

## 전제 조건
- Cloud Run Job (`ngn-29cm-best-job`)이 이미 배포되어 있어야 합니다
- 프로젝트: `winged-precept-443218-v8`
- 리전: `asia-northeast3`

## 빠른 시작

### 1. 스케줄러 생성 (권장)
Cloud Shell에서 다음 명령어를 실행하세요:

```bash
cd ~/ngn_dashboard
bash tools/29cm_best/create_scheduler.sh
```

이 스크립트는 다음을 자동으로 처리합니다:
1. Cloud Run Job 존재 확인
2. Pub/Sub 토픽 생성 (없는 경우)
3. Pub/Sub 구독 생성 (없는 경우)
4. Cloud Scheduler 생성 (매주 월요일 오전 8시)

### 2. 수동으로 생성 (참고용)

#### Pub/Sub 토픽 생성
```bash
gcloud pubsub topics create 29cm-best-weekly-trigger \
  --project=winged-precept-443218-v8
```

#### Pub/Sub 구독 생성
```bash
gcloud pubsub subscriptions create 29cm-best-weekly-sub \
  --topic=29cm-best-weekly-trigger \
  --ack-deadline=20 \
  --push-endpoint="https://asia-northeast3-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/winged-precept-443218-v8/jobs/ngn-29cm-best-job:run" \
  --push-auth-service-account=439320386143-compute@developer.gserviceaccount.com \
  --project=winged-precept-443218-v8
```

#### Cloud Scheduler 생성
```bash
gcloud scheduler jobs create pubsub 29cm-best-weekly-scheduler \
  --location=asia-northeast3 \
  --schedule="0 8 * * 1" \
  --topic=29cm-best-weekly-trigger \
  --message-body='{"trigger":"weekly"}' \
  --time-zone="Asia/Seoul" \
  --project=winged-precept-443218-v8
```

## 스케줄 설정

- **Cron 표현식**: `0 8 * * 1` (매주 월요일 오전 8시)
- **타임존**: `Asia/Seoul`
- **형식**: 분 시 일 월 요일
  - `0`: 0분
  - `8`: 8시
  - `*`: 모든 일
  - `*`: 모든 월
  - `1`: 월요일 (0=일요일, 1=월요일, ...)

## 확인 방법

### 스케줄러 상태 확인
```bash
gcloud scheduler jobs describe 29cm-best-weekly-scheduler \
  --location=asia-northeast3 \
  --project=winged-precept-443218-v8
```

### 다음 실행 시간 확인
```bash
gcloud scheduler jobs describe 29cm-best-weekly-scheduler \
  --location=asia-northeast3 \
  --project=winged-precept-443218-v8 \
  --format="value(scheduleTime)"
```

### 전체 상태 확인 스크립트 실행
```bash
bash tools/29cm_best/check_scheduler.sh
```

## 데이터 수집 확인

스크립트는 다음 BigQuery 테이블로 데이터를 수집합니다:
- **테이블**: `winged-precept-443218-v8.ngn_dataset.platform_29cm_best`

### 테이블 데이터 확인
```sql
SELECT 
  run_id,
  period_type,
  COUNT(*) as row_count,
  MIN(collected_at) as first_collected,
  MAX(collected_at) as last_collected
FROM `winged-precept-443218-v8.ngn_dataset.platform_29cm_best`
GROUP BY run_id, period_type
ORDER BY last_collected DESC
LIMIT 10;
```

### 최근 수집 데이터 확인
```sql
SELECT *
FROM `winged-precept-443218-v8.ngn_dataset.platform_29cm_best`
ORDER BY collected_at DESC
LIMIT 100;
```

## 문제 해결

### 스케줄러가 생성되지 않는 경우
1. Cloud Run Job이 존재하는지 확인:
   ```bash
   gcloud run jobs describe ngn-29cm-best-job \
     --region=asia-northeast3 \
     --project=winged-precept-443218-v8
   ```

2. Job이 없으면 먼저 배포:
   ```bash
   cd ~/ngn_board
   bash tools/29cm_best/deploy_29cm_jobs.sh
   ```

### 스케줄러가 실행되지 않는 경우
1. 스케줄러 상태 확인 (ENABLED여야 함):
   ```bash
   gcloud scheduler jobs describe 29cm-best-weekly-scheduler \
     --location=asia-northeast3 \
     --project=winged-precept-443218-v8 \
     --format="value(state)"
   ```

2. 비활성화되어 있으면 활성화:
   ```bash
   gcloud scheduler jobs resume 29cm-best-weekly-scheduler \
     --location=asia-northeast3 \
     --project=winged-precept-443218-v8
   ```

### 수동 실행 테스트
스케줄러를 통하지 않고 Job을 직접 실행하여 테스트:
```bash
gcloud run jobs execute ngn-29cm-best-job \
  --region=asia-northeast3 \
  --project=winged-precept-443218-v8
```

## 관련 파일
- `create_scheduler.sh`: 스케줄러 생성 스크립트
- `check_scheduler.sh`: 스케줄러 상태 확인 스크립트
- `deploy_29cm_jobs.sh`: 전체 Job 배포 스크립트 (Job + 스케줄러)
- `test_29cm_best_local.py`: 실제 데이터 수집 스크립트

