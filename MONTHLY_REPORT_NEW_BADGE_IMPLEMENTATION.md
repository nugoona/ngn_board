# 월간 리포트 NEW 배지 구현 가이드

## 목표
- **유저별로 독립적인 NEW 배지**: 같은 업체라도 유저마다 다른 NEW 상태
- **서버 기반 추적**: localStorage 대신 서버에서 유저별 마지막 본 시간 저장

## 필요한 작업

### 1. BigQuery 테이블 생성
유저별 리포트 본 시간을 저장할 테이블이 필요합니다.

```sql
CREATE TABLE IF NOT EXISTS `winged-precept-443218-v8.ngn_dataset.user_monthly_report_viewed` (
  user_id STRING NOT NULL,
  company_name STRING NOT NULL,
  year INT64 NOT NULL,
  month INT64 NOT NULL,
  viewed_at TIMESTAMP NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY DATE(created_at)
CLUSTER BY user_id, company_name;

-- 복합 기본 키 (중복 방지)
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_company_year_month 
ON `winged-precept-443218-v8.ngn_dataset.user_monthly_report_viewed`(user_id, company_name, year, month);
```

### 2. 서버 API 엔드포인트 추가

#### 2-1. 새로운 데이터 확인 API
**경로**: `POST /dashboard/monthly_report/check_new`

**기능**:
- GCS 버킷의 스냅샷 파일 수정 시간(`blob.updated`) 확인
- BigQuery에서 해당 유저의 마지막 본 시간 조회
- 비교하여 새로운 데이터가 있는지 반환

**요청**:
```json
{
  "company_name": "piscess",
  "year": 2025,
  "month": 1
}
```

**응답**:
```json
{
  "status": "success",
  "has_new": true,
  "snapshot_updated": "2025-01-15T10:30:00Z",
  "last_viewed": "2025-01-14T15:20:00Z"
}
```

#### 2-2. 리포트 본 시간 저장 API
**경로**: `POST /dashboard/monthly_report/mark_viewed`

**기능**:
- 유저가 리포트를 열었을 때 호출
- BigQuery에 `user_id`, `company_name`, `year`, `month`, `viewed_at` 저장
- MERGE 문 사용 (이미 있으면 업데이트, 없으면 INSERT)

**요청**:
```json
{
  "company_name": "piscess",
  "year": 2025,
  "month": 1
}
```

**응답**:
```json
{
  "status": "success",
  "message": "마지막 본 시간이 저장되었습니다"
}
```

### 3. 클라이언트 코드 수정

#### 3-1. `checkAndShowNewBadge()` 함수 수정
- localStorage 대신 서버 API 호출
- `user_id`와 `company_name`을 함께 전송

#### 3-2. `hideMonthlyReportNewBadge()` 함수 수정
- 배지 숨길 때 서버에 마지막 본 시간 저장 API 호출

#### 3-3. `openMonthlyReportModal()` 함수 수정
- 모달 열 때 `mark_viewed` API 호출

## 구현 순서

1. ✅ BigQuery 테이블 생성 (SQL 실행)
2. ✅ 서버 API 2개 추가 (`data_handler.py`)
3. ✅ 클라이언트 코드 수정 (`monthly_report.js`)
4. ✅ 테스트 (다른 유저로 로그인하여 확인)

## 참고사항

- `session.get("user_id")`로 현재 유저 ID 가져오기
- `getSelectedCompany()`로 현재 선택된 업체 가져오기
- GCS `blob.updated` 속성으로 파일 수정 시간 확인
- BigQuery MERGE 문으로 중복 방지 및 업데이트

