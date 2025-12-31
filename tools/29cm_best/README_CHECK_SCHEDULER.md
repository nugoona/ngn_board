# 29CM BEST Job 스케줄러 확인 가이드

## 개요
`ngn-29cm-best-job`이 자동 실행되지 않는 문제를 진단하기 위한 스크립트입니다.

## 사용 방법

### 1. 전체 상태 확인 (권장)
Cloud Shell에서 다음 명령어를 실행하세요:

```bash
cd ~/ngn_dashboard
bash tools/29cm_best/check_scheduler.sh
```

이 스크립트는 다음을 확인합니다:
- Cloud Run Job 존재 여부
- Cloud Scheduler 상태 (활성화/비활성화)
- 스케줄 설정 (주간: 매주 월요일 새벽 3시)
- Pub/Sub 토픽 및 구독 상태
- 최근 실행 이력

### 2. 빠른 확인 (개별 명령어)

#### 스케줄러 목록 확인
```bash
gcloud scheduler jobs list \
  --location=asia-northeast3 \
  --project=winged-precept-443218-v8 \
  --filter="name:29cm-best"
```

#### 주간 스케줄러 상세 정보 확인
```bash
gcloud scheduler jobs describe 29cm-best-weekly-scheduler \
  --location=asia-northeast3 \
  --project=winged-precept-443218-v8
```

#### 스케줄러 상태만 확인
```bash
gcloud scheduler jobs describe 29cm-best-weekly-scheduler \
  --location=asia-northeast3 \
  --project=winged-precept-443218-v8 \
  --format="value(state)"
```

#### Cloud Run Job 존재 확인
```bash
gcloud run jobs describe ngn-29cm-best-job \
  --region=asia-northeast3 \
  --project=winged-precept-443218-v8
```

#### 최근 실행 이력 확인
```bash
gcloud run jobs executions list \
  --job=ngn-29cm-best-job \
  --region=asia-northeast3 \
  --project=winged-precept-443218-v8 \
  --limit=10
```

## 문제 해결

### 스케줄러가 비활성화(PAUSED/DISABLED)되어 있는 경우
다음 명령어로 활성화하세요:

```bash
gcloud scheduler jobs resume 29cm-best-weekly-scheduler \
  --location=asia-northeast3 \
  --project=winged-precept-443218-v8
```

### 스케줄러가 존재하지 않는 경우
배포 스크립트를 실행하여 스케줄러를 생성하세요:

```bash
cd ~/ngn_board  # 또는 프로젝트 루트 디렉토리
bash tools/29cm_best/deploy_29cm_jobs.sh
```

### 스케줄 설정 확인
- **주간 스케줄**: 매주 월요일 새벽 3시 (`0 3 * * 1`)
- **타임존**: `Asia/Seoul`
- **프로젝트**: `winged-precept-443218-v8`
- **리전**: `asia-northeast3`

## 참고 정보

- 주간 Job 이름: `ngn-29cm-best-job`
- 주간 스케줄러 이름: `29cm-best-weekly-scheduler`
- 주간 Pub/Sub 토픽: `29cm-best-weekly-trigger`
- 월간 Job 이름: `ngn-29cm-best-monthly-job`
- 월간 스케줄러 이름: `29cm-best-monthly-scheduler`
- 월간 Pub/Sub 토픽: `29cm-best-monthly-trigger`

