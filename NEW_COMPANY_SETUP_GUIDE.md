# 새 업체 추가 가이드

새로운 업체가 추가되었을 때 메타 광고 계정과 GA4 계정을 추가하는 방법입니다.

---

## 📋 필요한 정보

새 업체 추가 시 다음 정보가 필요합니다:

- `company_name`: 회사명 (소문자)
- `meta_acc`: 메타 계정명
- `main_url`: 메인 URL
- `ga4_property_id`: GA4 Property ID (5자리 이상 숫자)
- `meta_business_id`: 메타 비즈니스 ID
- `instagram_id`: Instagram 계정 ID
- `instagram_acc_name`: Instagram 계정명
- `meta_acc_id`: 메타 광고 계정 ID
- `meta_acc_name`: 메타 광고 계정명
- `user_email`: 사용자 이메일 (예: oscar@nugoona.co.kr)

---

## 1️⃣ BigQuery에 데이터 추가

### 1-1. `company_info` 테이블에 업체 정보 추가

```sql
INSERT INTO `winged-precept-443218-v8.ngn_dataset.company_info` 
  (company_name, meta_acc, main_url, ga4_property_id, meta_business_id, instagram_id, instagram_acc_name)
VALUES
  ('업체명', '메타계정명', '메인URL', GA4_PROPERTY_ID, '메타비즈니스ID', '인스타그램ID', '인스타그램계정명');
```

**예시:**
```sql
INSERT INTO `winged-precept-443218-v8.ngn_dataset.company_info` 
  (company_name, meta_acc, main_url, ga4_property_id, meta_business_id, instagram_id, instagram_acc_name)
VALUES
  ('nugoona', 'NGN_MKT', 'nugoona.co.kr', 505684714, '287563004172481', '17841478374157414', 'ngn_mkt');
```

### 1-2. `metaAds_acc` 테이블에 메타 광고 계정 추가

```sql
INSERT INTO `winged-precept-443218-v8.ngn_dataset.metaAds_acc` 
  (company_name, meta_acc_id, meta_acc_name)
VALUES
  ('업체명', '메타광고계정ID', '메타광고계정명');
```

**예시:**
```sql
INSERT INTO `winged-precept-443218-v8.ngn_dataset.metaAds_acc` 
  (company_name, meta_acc_id, meta_acc_name)
VALUES
  ('nugoona', '3105780736382214', 'NGN');
```

### 1-3. `user_company_map` 테이블에 사용자-회사 매핑 추가

```sql
INSERT INTO `winged-precept-443218-v8.ngn_dataset.user_company_map` 
  (user_email, company_name)
VALUES
  ('사용자이메일', '업체명');
```

**예시:**
```sql
INSERT INTO `winged-precept-443218-v8.ngn_dataset.user_company_map` 
  (user_email, company_name)
VALUES
  ('oscar@nugoona.co.kr', 'nugoona');
```

---

## 2️⃣ Google Analytics 권한 부여

**⚠️ 중요:** GA4 Property에 데이터 수집을 위해 **두 개의 서비스 계정**에 모두 권한을 부여해야 합니다.

### 2-1. 서비스 계정 확인

필요한 서비스 계정:
1. `winged-precept-443218-v8@appspot.gserviceaccount.com` (service-account.json 파일의 계정)
2. `439320386143-compute@developer.gserviceaccount.com` (Cloud Run Job 실행 계정)

### 2-2. Google Analytics에서 권한 부여

1. **Google Analytics 접속**
   - https://analytics.google.com 접속

2. **Property 선택**
   - 새로 추가한 GA4 Property ID 선택

3. **권한 설정**
   - 왼쪽 하단 **Admin** (관리) 클릭
   - **Property Access Management** (속성 액세스 관리) 클릭
   - **+** 버튼 클릭 → **Add users** (사용자 추가)

4. **두 계정 모두 추가**
   - 첫 번째 계정 추가:
     - 이메일: `winged-precept-443218-v8@appspot.gserviceaccount.com`
     - 역할: **Viewer** (또는 **Analyst**)
     - **Add** 클릭
   
   - 두 번째 계정 추가:
     - 이메일: `439320386143-compute@developer.gserviceaccount.com`
     - 역할: **Viewer** (또는 **Analyst**)
     - **Add** 클릭

---

## 3️⃣ 확인 방법

### 3-1. GA4 데이터 수집 확인

1. **Cloud Run Job 로그 확인**
   - Google Cloud Console → Cloud Run → Jobs
   - `ngn-ga4-traffic-job` 또는 `ngn-ga4-view-job` 실행 로그 확인
   - 로그에서 다음 메시지 확인:
     ```
     ✅ GA4 Property IDs 로드 완료: [..., 505684714, ...]
     📡 505684714 (날짜) 트래픽 데이터 수집 중...
     ```

2. **BigQuery 데이터 확인**
   ```sql
   SELECT * 
   FROM `winged-precept-443218-v8.ngn_dataset.ga4_traffic_ngn`
   WHERE ga4_property_id = 505684714
   ORDER BY event_date DESC
   LIMIT 10;
   ```

### 3-2. Meta Ads 데이터 수집 확인

1. **BigQuery 데이터 확인**
   ```sql
   SELECT * 
   FROM `winged-precept-443218-v8.ngn_dataset.meta_ads_account_summary`
   WHERE account_id = '메타광고계정ID'
   ORDER BY date DESC
   LIMIT 10;
   ```

2. **대시보드에서 확인**
   - 대시보드 접속 후 해당 업체 선택
   - Meta Ads 섹션에서 계정이 표시되는지 확인

---

## ✅ 완료 체크리스트

- [ ] `company_info` 테이블에 업체 정보 추가 완료
- [ ] `metaAds_acc` 테이블에 메타 광고 계정 추가 완료
- [ ] `user_company_map` 테이블에 사용자-회사 매핑 추가 완료
- [ ] Google Analytics에서 `winged-precept-443218-v8@appspot.gserviceaccount.com` 권한 부여 완료
- [ ] Google Analytics에서 `439320386143-compute@developer.gserviceaccount.com` 권한 부여 완료
- [ ] GA4 데이터 수집 확인 완료
- [ ] Meta Ads 데이터 수집 확인 완료

---

## 📝 참고 사항

### 자동 처리되는 항목

- ✅ **GA4 Property ID 수집**: `company_info` 테이블에서 `ga4_property_id`가 NULL이 아니고 5자리 이상인 것들을 자동으로 가져옵니다.
- ✅ **Meta Ads 계정 수집**: `metaAds_acc` 테이블에 추가된 계정을 자동으로 가져옵니다.
- ✅ **재배포 불필요**: 코드가 동적으로 처리하므로 Cloud Run Job 재배포가 필요 없습니다.

### 주의 사항

- ⚠️ **GA4 Property ID**: 반드시 5자리 이상이어야 합니다 (10000 이상).
- ⚠️ **서비스 계정 권한**: 두 개의 서비스 계정 모두에 권한을 부여해야 합니다. 하나만 부여하면 데이터 수집이 실패할 수 있습니다.
- ⚠️ **권한 부여 후 대기**: 권한 부여 후 몇 분 정도 기다린 후 Cloud Scheduler에서 작업을 수동 실행하거나 다음 스케줄 실행 시 확인하세요.

---

## 🔧 문제 해결

### GA4 데이터가 수집되지 않는 경우

1. **권한 확인**
   - Google Analytics에서 두 서비스 계정 모두 권한이 부여되었는지 확인
   - Property ID가 정확한지 확인

2. **로그 확인**
   - Cloud Run Job 로그에서 에러 메시지 확인
   - `❌ 505684714 (날짜) 트래픽 데이터 수집 실패: ...` 메시지가 있는지 확인

3. **BigQuery 확인**
   - `company_info` 테이블에 데이터가 올바르게 추가되었는지 확인
   - `ga4_property_id`가 5자리 이상인지 확인

### Meta Ads 데이터가 수집되지 않는 경우

1. **BigQuery 확인**
   - `metaAds_acc` 테이블에 데이터가 올바르게 추가되었는지 확인
   - `meta_acc_id`가 정확한지 확인

2. **Meta API 토큰 확인**
   - Meta System User Token이 유효한지 확인
   - 해당 계정에 대한 접근 권한이 있는지 확인

---

**마지막 업데이트:** 2025-12-05



