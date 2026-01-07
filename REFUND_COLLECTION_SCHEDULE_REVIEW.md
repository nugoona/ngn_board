# 환불 수집 코드 및 스케줄 검토 결과

## 현재 상태

### 1. 환불 수집 코드 (`cafe24_refund_data_handler.py`)

#### ✅ 수정 완료 사항

1. **중복 방지 로직 강화**
   - `PARTITION BY`에 `order_item_code` 추가
   - MERGE 조건에 `order_item_code` 추가
   - 같은 `refund_code`에 여러 `order_item_code`가 있어도 각각 별도로 저장

2. **수집 기간**
   - **변경 전**: 오늘 포함 지난 7일 수집 (`timedelta(days=6)`)
   - **변경 후**: **오늘 + 어제만** 수집 (`timedelta(days=1)`)
   - **이유**: 실시간 매출 정확도 확보를 위해 최근 데이터만 집중 수집

3. **중복 제거 로직**
   - `ROW_NUMBER()`로 `refund_code`, `mall_id`, `order_id`, `order_item_code`별로 중복 제거
   - MERGE 조건: `mall_id`, `order_id`, `order_item_code`, `refund_code`

#### ⚠️ 수정 전 문제점

- **이전**: `PARTITION BY`에 `order_item_code` 없음 → 같은 `refund_code`에 여러 `order_item_code`가 있으면 마지막 것만 저장
- **이전**: MERGE 조건에 `order_item_code` 없음 → 같은 `refund_code`의 다른 `order_item_code`가 덮어씌워질 수 있음

## 실행 주기 검토

### 현재 상태

**Cloud Run Job 스케줄러 설정**: ❌ 확인되지 않음

- `deploy_refund_job.sh`에는 스케줄러 설정이 없음
- Cloud Scheduler 또는 다른 트리거 설정 여부 확인 필요

### 실행 주기 결정

#### ✅ 최종 결정: **매시간 실행**

**이유:**
- **실시간 매출 정확도**: 오늘 매출이 카페24와 정확히 일치해야 함
- **환불 즉시 반영**: 환불 발생 시 즉시 대시보드에 반영되어야 함
- **수집 기간 최소화**: 오늘 + 어제만 수집하므로 쿼리 비용 최소화

**수집 기간 변경:**
- **이전**: 오늘 포함 지난 7일 수집
- **현재**: 오늘 + 어제만 수집 (2일)
- **효과**: 수집 기간이 짧아져 쿼리 비용 및 실행 시간 감소

### 스케줄러 설정 방법

Cloud Scheduler를 사용하여 **매시간 실행** 설정:

```bash
# Pub/Sub 토픽 생성
gcloud pubsub topics create refund-collection-trigger \
  --project=winged-precept-443218-v8

# Pub/Sub 구독 생성
gcloud pubsub subscriptions create refund-collection-sub \
  --topic=refund-collection-trigger \
  --ack-deadline=20 \
  --push-endpoint="https://asia-northeast3-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/winged-precept-443218-v8/jobs/ngn-refund-job:run" \
  --push-auth-service-account=439320386143-compute@developer.gserviceaccount.com \
  --project=winged-precept-443218-v8

# Cloud Scheduler 생성 (매시간 실행)
gcloud scheduler jobs create pubsub refund-collection-scheduler \
  --location=asia-northeast3 \
  --schedule="0 * * * *" \
  --topic=refund-collection-trigger \
  --message-body='{"trigger":"hourly"}' \
  --time-zone="Asia/Seoul" \
  --project=winged-precept-443218-v8
```

**Cron 표현식 설명:**
- `0 * * * *`: 매시간 0분에 실행 (예: 00:00, 01:00, 02:00, ...)

**비용 최적화:**
- 수집 기간을 오늘 + 어제만으로 제한하여 쿼리 비용 최소화
- 매시간 실행하더라도 수집 데이터량이 적어 비용 부담 낮음

## 결론

### ✅ 코드 수정 완료
- `order_item_code`를 MERGE 조건 및 PARTITION BY에 추가하여 중복 방지 강화

### ✅ 스케줄 최종 결정
- **매시간 실행** 유지 (실시간 매출 정확도 확보)
- **수집 기간**: 오늘 + 어제만 수집하여 비용 최적화

### 📋 다음 단계
1. Cloud Scheduler 설정 (필요시)
2. 스케줄러가 이미 있다면 실행 주기 확인 및 조정
3. 수정된 코드 재배포 (`deploy_refund_job.sh` 실행)

