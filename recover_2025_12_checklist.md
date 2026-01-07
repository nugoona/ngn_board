# 2025-12 환불 데이터 복구 체크리스트

## 전체 순서

### 0단계: 현재 상태 확인
```
→ check_2025_12_refunds_status.sql 실행
```

확인 사항:
- `cafe24_refunds_table`에 2025-12 환불 데이터가 있는지
- `daily_cafe24_sales`에 환불 데이터가 반영되었는지
- 두 테이블 간 차이가 있는지

---

### 1단계: 기존 데이터 삭제 (필수)

#### 1-1: 삭제할 데이터 확인
```
→ delete_2025_12_data.sql의 Step 0 실행
```

확인 사항:
- `daily_cafe24_sales`의 2025-12 데이터 행 수
- `cafe24_refunds_table`의 2025-12 데이터 (선택사항)

#### 1-2: daily_cafe24_sales 삭제 (필수)
```
→ delete_2025_12_data.sql의 Step 1 실행
```
**중요**: 잘못된 환불 집계 데이터를 제거하기 위해 필수입니다.

#### 1-3: cafe24_refunds_table 삭제 (선택사항)
```
→ delete_2025_12_data.sql의 Step 2 실행 (주석 해제)
```
**참고**: MERGE로 중복 방지되므로 삭제 없이 재수집해도 됩니다.
하지만 완전히 새로 수집하고 싶다면 삭제하세요.

#### 1-4: 삭제 확인
```
→ delete_2025_12_data.sql의 Step 4 실행
```
결과가 0이어야 정상입니다.

---

### 2단계: 환불 데이터 수집

```
→ python recover_2025_12_refunds.py
```

작업 내용:
- Cafe24 API에서 2025-12-01 ~ 2025-12-31 환불 데이터 수집
- `cafe24_refunds_table`에 저장
- 중복 방지: `order_id` + `order_item_code` + `refund_code` 조합으로 MERGE

---

### 3단계: daily_cafe24_sales에 환불 데이터 반영

```
→ python recover_2025_12_data.py
```

작업 내용:
- 2025-12-01 ~ 2025-12-31 일자별로 `daily_cafe24_sales` 재수집
- 환불 데이터를 원래 주문의 `payment_date` 기준으로 집계
- 중복 방지: `payment_date` + `company_name` 조합으로 MERGE

**수정 사항**:
- ✅ JOIN 조건 버그 수정됨 (`r.payment_date` 사용)
- ✅ 환불을 원래 주문 결제일 기준으로 집계

---

### 4단계: 최종 확인

```
→ check_2025_12_refunds_status.sql 실행
```

확인 사항:
- `daily_cafe24_sales`에 환불 데이터가 정상적으로 반영되었는지
- `total_refund_amount`가 올바르게 계산되었는지

---

### 5단계: 대시보드 캐시 무효화 (필요시)

```
POST /dashboard/cache/invalidate
Body: {"pattern": "cafe24_sales"}
```

또는 브라우저에서 새로고침 (Ctrl+F5)

---

## 주의사항

1. **삭제는 필수**: 잘못된 데이터를 삭제하지 않고 재수집하면 MERGE로 업데이트는 되지만, 확실하게 하려면 삭제 후 재수집하는 것이 안전합니다.

2. **순서 중요**: 
   - 반드시 삭제 → 환불 수집 → daily_cafe24_sales 수집 순서로 진행
   - 순서를 바꾸면 데이터 불일치 발생 가능

3. **중복 방지**:
   - `recover_2025_12_refunds.py`: `order_id` + `order_item_code` + `refund_code` 조합
   - `recover_2025_12_data.py`: `payment_date` + `company_name` 조합

4. **재실행 안전**: 두 스크립트 모두 MERGE를 사용하므로 안전하게 재실행 가능합니다.

