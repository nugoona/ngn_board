# 월간 리포트 NEW 배지 구현 (비용 최적화 버전)

## 비용 분석

### ❌ BigQuery 사용 시
- **쿼리 비용**: 월 100회 조회 기준 약 $0.01 (매우 저렴하지만 불필요)
- **저장 비용**: 테이블 크기 작음 (거의 무료)
- **문제점**: 단순한 키-값 저장에 BigQuery는 과도함

### ✅ 최적화된 방법 (권장)

## 방법 1: localStorage + GCS 메타데이터만 확인 (가장 저렴)

### 비용: 거의 0원
- localStorage: 클라이언트 측 저장 (비용 없음)
- GCS 메타데이터 조회: `blob.updated` 확인만 (파일 다운로드 안 함, 비용 거의 없음)

### 구현
1. **localStorage 키에 user_id 포함**
   ```javascript
   const key = `monthlyReportLastViewed_${currentUserId}_${companyName}`;
   ```

2. **서버 API 1개만 추가** (GCS 메타데이터만 확인)
   - `POST /dashboard/monthly_report/check_new`
   - GCS `blob.updated` 시간만 반환 (파일 다운로드 안 함)
   - BigQuery 사용 안 함

3. **클라이언트에서 비교**
   - localStorage의 마지막 본 시간 vs 서버에서 받은 파일 수정 시간

### 장점
- ✅ 비용 거의 없음
- ✅ 구현 간단
- ✅ 빠른 응답

### 단점
- ❌ 브라우저별로만 저장 (다른 브라우저/기기에서는 안 됨)
- ❌ 브라우저 캐시 삭제 시 초기화

---

## 방법 2: Redis 사용 (이미 인프라 있음)

### 비용: Redis 인프라 비용만 (이미 사용 중)
- Redis는 이미 사용 중이므로 추가 비용 없음
- BigQuery보다 훨씬 저렴하고 빠름

### 구현
1. **Redis 키 구조**
   ```
   monthly_report_viewed:{user_id}:{company_name}:{year}:{month}
   ```

2. **서버 API 2개**
   - `POST /dashboard/monthly_report/check_new`: Redis에서 조회
   - `POST /dashboard/monthly_report/mark_viewed`: Redis에 저장 (TTL 90일)

3. **GCS 메타데이터 확인**
   - `blob.updated` 시간만 확인 (파일 다운로드 안 함)

### 장점
- ✅ 비용 거의 없음 (이미 사용 중)
- ✅ 모든 브라우저/기기에서 동일하게 작동
- ✅ 빠른 응답 (Redis는 메모리 기반)
- ✅ TTL 자동 관리

### 단점
- ❌ Redis 인프라 필요 (이미 있음)

---

## 방법 3: 하이브리드 (localStorage + Redis 폴백)

### 구현
1. **우선 localStorage 사용** (비용 0)
2. **Redis는 백업/동기화용** (선택사항)
3. **서버 API는 GCS 메타데이터만 확인**

### 장점
- ✅ 비용 최소화
- ✅ 오프라인에서도 작동 (localStorage)
- ✅ 필요시 서버 동기화 가능

---

## 권장 방법: 방법 1 (localStorage + GCS 메타데이터)

### 이유
1. **비용 거의 0원**: GCS 메타데이터 조회는 무료에 가까움
2. **구현 간단**: 서버 API 1개만 추가
3. **빠른 응답**: 파일 다운로드 없이 메타데이터만 확인

### 구현 코드 예시

#### 서버 API (최소한)
```python
@data_blueprint.route("/monthly_report/check_new", methods=["POST"])
def check_new_monthly_report():
    """GCS 파일 수정 시간만 확인 (파일 다운로드 안 함)"""
    data = request.get_json()
    company_name = data.get("company_name")
    year = int(data.get("year"))
    month = int(data.get("month"))
    
    # GCS 메타데이터만 확인 (비용 거의 없음)
    blob_path = f"ai-reports/monthly/{company_name}/{year}-{month:02d}/snapshot.json.gz"
    blob = bucket.blob(blob_path)
    
    if not blob.exists():
        return jsonify({"status": "error", "message": "파일 없음"}), 404
    
    # 파일 다운로드 안 함! 메타데이터만 확인
    return jsonify({
        "status": "success",
        "snapshot_updated": blob.updated.isoformat()  # 수정 시간만 반환
    }), 200
```

#### 클라이언트
```javascript
// localStorage 키에 user_id 포함
const storageKey = `monthlyReportLastViewed_${currentUserId}_${companyName}_${year}_${month}`;
const lastViewed = localStorage.getItem(storageKey);

// 서버에서 파일 수정 시간만 가져오기
const response = await fetch('/dashboard/monthly_report/check_new', {
    method: 'POST',
    body: JSON.stringify({ company_name: companyName, year, month })
});
const { snapshot_updated } = await response.json();

// 비교
if (!lastViewed || new Date(snapshot_updated) > new Date(lastViewed)) {
    showMonthlyReportNewBadge();
}
```

---

## 비용 비교

| 방법 | 월 예상 비용 | 구현 복잡도 |
|------|------------|------------|
| BigQuery | ~$0.01 | 중간 |
| localStorage + GCS 메타 | ~$0 | 낮음 |
| Redis | $0 (이미 사용 중) | 낮음 |
| 하이브리드 | ~$0 | 중간 |

**결론: localStorage + GCS 메타데이터 방법이 가장 저렴하고 간단합니다!**

