# 코드 검토 결과: bq_monthly_snapshot.py

## 🔴 오류 가능성 (Critical)

### 1. **딕셔너리 접근 시 KeyError 가능성**
**위치**: 여러 곳에서 `.get()` 대신 직접 접근 사용

**문제 코드**:
```python
# Line 1838-1839
net_sales_mom = delta(sales_this["net_sales"], sales_prev["net_sales"]) if (sales_this and sales_prev) else None
```

**문제점**: `sales_this`와 `sales_prev`가 None이 아니어도 `"net_sales"` 키가 없으면 KeyError 발생 가능

**해결책**: `.get()` 사용 또는 키 존재 확인
```python
net_sales_mom = delta(sales_this.get("net_sales"), sales_prev.get("net_sales")) if (sales_this and sales_prev) else None
```

**영향도**: 높음 (데이터 구조 변경 시 크래시 가능)

---

### 2. **나눗셈 제로 에러 가능성**
**위치**: Line 2005
```python
signals["mall_sales_mom_pct"] = ((net_this - net_prev) / net_prev * 100) if net_prev else None
```

**문제점**: `net_prev`가 0이면 나눗셈 제로 에러 발생 (현재는 `if net_prev`로 체크하지만, 0은 falsy이므로 None으로 처리됨 - 이건 의도된 동작일 수 있음)

**확인 필요**: `net_prev == 0`일 때 의도된 동작인지 확인

---

### 3. **리스트 인덱스 접근 시 IndexError 가능성**
**위치**: Line 1910, 1917, 1924
```python
item_month = int(item["ym"].split("-")[1])
```

**문제점**: `item["ym"]`이 "YYYY-MM" 형식이 아니면 `split("-")[1]`에서 IndexError 발생 가능

**해결책**: 형식 검증 추가
```python
ym_parts = item.get("ym", "").split("-")
if len(ym_parts) >= 2:
    item_month = int(ym_parts[1])
```

**영향도**: 중간 (데이터 품질 문제 시 발생)

---

### 4. **get_meta_ads_goals_multi()에서 period_start가 None일 때**
**위치**: Line 897-899
```python
for period_key, (period_start, _period_end) in ranges.items():
    if period_start:
        period_ym_map[period_key] = period_start[:7]  # "YYYY-MM"
```

**문제점**: `period_start`가 None이 아니지만 문자열이 아닌 경우 `[:7]` 슬라이싱에서 TypeError 발생 가능

**해결책**: 타입 체크 추가
```python
if period_start and isinstance(period_start, str):
    period_ym_map[period_key] = period_start[:7]
```

**영향도**: 낮음 (일반적으로 문자열이지만 방어적 코딩 필요)

---

## ⚠️ 잠재적 오류 (Medium)

### 5. **monthly_13m_meta에서 계산된 roas/cpc/ctr/cvr가 None일 때**
**위치**: Line 582-585
```python
"roas": (purchase_value / spend * 100) if spend > 0 else None,
"cpc": (spend / clicks) if clicks > 0 else None,
"ctr": (clicks / impressions * 100) if impressions > 0 else None,
"cvr": (purchases / clicks * 100) if clicks > 0 else None,
```

**문제점**: 계산 결과가 None이지만, 이후 `meta_ads_this.get("roas")`로 접근할 때는 안전하지만, 직접 접근 시 문제 가능

**현재 상태**: `.get()` 사용으로 안전함

---

### 6. **products_90d_map에서 키가 없을 때**
**위치**: Line 1523
```python
p30d = products_30d_map.get(p["product_no"])
```

**현재 상태**: `.get()` 사용으로 안전함 ✅

---

## 💡 효율성 개선 제안

### 1. **daily_sales 쿼리 최적화 (3번 → 1번)**
**위치**: Line 486-488
```python
daily_this = get_sales_daily(this_start, this_end)
daily_prev = get_sales_daily(prev_start, prev_end)
daily_yoy = get_sales_daily(yoy_start, yoy_end)
```

**개선안**: 3개월 전체를 한 번에 조회 후 Python에서 분해 (meta_ads_goals_multi와 동일한 패턴)

**예상 효과**: 쿼리 3회 → 1회 (약 67% 감소)

---

### 2. **ga4_top_sources 쿼리 최적화 (3번 → 1번)**
**위치**: Line 1442, 1446, 1432
```python
ga4_this = {
    "totals": ga4_this_totals,
    "top_sources": get_ga4_top_sources(this_start, this_end),
}
ga4_prev = {
    "totals": ga4_prev_totals,
    "top_sources": get_ga4_top_sources(prev_start, prev_end),
}
```

**개선안**: this/prev/yoy를 한 번에 조회 후 Python에서 분해

**예상 효과**: 쿼리 3회 → 1회 (약 67% 감소)

---

### 3. **products 쿼리 최적화 (2번 → 1번)**
**위치**: Line 1472-1498
```python
for days in PRODUCT_ROLLING_WINDOWS:  # [30, 90]
    s, e = rolling_range(end_date_iso, days)
    rows = list(client.query(...))
```

**개선안**: 30일과 90일을 한 번에 조회 (90일 데이터에서 30일 필터링)

**예상 효과**: 쿼리 2회 → 1회 (약 50% 감소)

**주의**: 30일과 90일의 end_date가 다를 수 있으므로 주의 필요

---

### 4. **디버그 로그 제거 또는 조건부 출력**
**위치**: Line 232, 287
```python
print(f"[DEBUG] query_monthly_13m_generic: ...", file=sys.stderr)
```

**개선안**: 환경 변수로 제어하거나 프로덕션에서는 제거

---

### 5. **has_rows() 함수 최적화**
**위치**: Line 192-219
```python
def has_rows(client, table_fq, date_col, company_name, start_date, end_date):
    query = f"""
    SELECT COUNT(1) AS cnt
    ...
    LIMIT 1
    """
```

**개선안**: `EXISTS` 서브쿼리 사용 (더 효율적)
```sql
SELECT EXISTS(
    SELECT 1
    FROM `{table_fq}`
    WHERE company_name = @company_name
      AND {date_col} >= @start_date
      AND {date_col} <= @end_date
    LIMIT 1
) AS has_rows
```

**예상 효과**: COUNT보다 EXISTS가 더 빠름 (첫 번째 행만 찾으면 중단)

---

## ✅ 잘 구현된 부분

1. **None-safe 처리**: `delta()`, `note_if_base_small()` 함수에서 None 체크 잘 구현됨
2. **타입 안전성**: `delta()` 함수에서 float 캐스팅 및 try-except 처리
3. **월간 집계 우선**: YoY 데이터 존재 여부 확인 시 월간 집계 우선, raw fallback 구조
4. **쿼리 최적화**: meta_ads_benchmarks, meta_ads_goals_multi에서 배치 쿼리 사용
5. **에러 처리**: GCS 저장 시 try-except로 안전하게 처리

---

## 📊 우선순위별 개선 권장사항

### 높은 우선순위 (안정성)
1. **딕셔너리 접근 안전화**: `.get()` 사용 또는 키 존재 확인
2. **리스트 인덱스 접근 안전화**: split 결과 길이 확인

### 중간 우선순위 (효율성)
3. **daily_sales 쿼리 최적화**: 3번 → 1번
4. **ga4_top_sources 쿼리 최적화**: 3번 → 1번
5. **has_rows() 최적화**: COUNT → EXISTS

### 낮은 우선순위 (코드 품질)
6. **디버그 로그 제거 또는 조건부 출력**
7. **products 쿼리 최적화**: 2번 → 1번 (주의 필요)

---

## 🎯 종합 평가

**안정성**: ⭐⭐⭐⭐ (4/5)
- 대부분의 None 처리와 타입 안전성이 잘 구현됨
- 일부 딕셔너리 직접 접근 부분 개선 필요

**효율성**: ⭐⭐⭐⭐ (4/5)
- 주요 쿼리들이 최적화됨 (meta_ads_benchmarks, meta_ads_goals_multi)
- daily_sales, ga4_top_sources 추가 최적화 여지 있음

**유지보수성**: ⭐⭐⭐⭐⭐ (5/5)
- 코드 구조가 명확하고 주석이 잘 작성됨
- 함수 분리가 잘 되어 있음


