# 29CM Best BigQuery 비용 분석 및 최적화 방안

## 🔴 주요 비용 발생 원인

### 1. 중복 체크 쿼리 - 전체 테이블 스캔 문제 ⚠️ **가장 큰 문제**

**현재 코드 (124-141줄):**
```python
def bq_run_already_loaded(bq: bigquery.Client, run_id: str, period_type: str) -> bool:
    sql = f"""
    SELECT COUNT(1) AS cnt
    FROM `{bq_table_fqn()}`
    WHERE run_id = @run_id
      AND period_type = @period_type
    """
```

**문제점:**
- `run_id`와 `period_type` 컬럼에 클러스터링/인덱스가 없으면 **전체 테이블을 스캔**
- 월간 스냅샷이 누적되면 테이블 크기가 증가 → 스캔 비용 기하급수적 증가
- 이 쿼리가 **2번 실행**됨 (279줄: 크롤링 전, 400줄: 크롤링 후)
- BigQuery 스캔 비용: **$5 per TB** → 테이블이 100GB면 스캔당 $0.50

**예상 비용:**
- 테이블 크기: 50GB (월간 스냅샷 누적)
- 중복 체크 쿼리 2회: 50GB × 2 = 100GB 스캔
- 비용: 100GB × ($5 / 1024GB) = **$0.49 per 실행**

### 2. 스트리밍 INSERT 비용

**현재 코드 (144-148줄):**
```python
def bq_insert_rows(bq: bigquery.Client, rows: list[dict]):
    table_ref = bq.dataset(DATASET_ID).table(TABLE_ID)
    errors = bq.insert_rows_json(table_ref, rows)
```

**문제점:**
- 스트리밍 insert 비용: **$0.01 per GB**
- 일반적으로 무료 할당량 ($200/month, 1GB/day) 내에서 처리 가능
- 하지만 데이터가 많으면 비용 발생 가능

---

## ✅ 최적화 방안

### 방안 1: 테이블 클러스터링 추가 (권장) ⭐

**가장 효과적인 방법:**
```sql
-- 기존 테이블을 클러스터링 테이블로 재생성
CREATE OR REPLACE TABLE `winged-precept-443218-v8.ngn_dataset.platform_29cm_best`
CLUSTER BY run_id, period_type
AS
SELECT * FROM `winged-precept-443218-v8.ngn_dataset.platform_29cm_best`
```

**효과:**
- `run_id`와 `period_type`으로 클러스터링하면 중복 체크 쿼리가 매우 작은 범위만 스캔
- 스캔 비용 **90% 이상 감소**
- 쿼리 성능도 크게 향상

### 방안 2: 중복 체크 쿼리 최적화

**LIMIT 1 사용 (COUNT보다 효율적):**
```python
def bq_run_already_loaded(bq: bigquery.Client, run_id: str, period_type: str) -> bool:
    sql = f"""
    SELECT 1
    FROM `{bq_table_fqn()}`
    WHERE run_id = @run_id
      AND period_type = @period_type
    LIMIT 1
    """
    job = bq.query(
        sql,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("run_id", "STRING", run_id),
                bigquery.ScalarQueryParameter("period_type", "STRING", period_type)
            ]
        ),
    )
    rows = list(job.result())
    return len(rows) > 0
```

**효과:**
- COUNT는 모든 매칭 행을 확인하지만, LIMIT 1은 첫 번째 행만 찾으면 중단
- 클러스터링과 함께 사용하면 더욱 효율적

### 방안 3: 중복 체크를 1회만 실행

**현재는 2회 실행 (279줄, 400줄):**
- 크롤링 전에 1회 체크하여 불필요한 크롤링 방지 (유지)
- 크롤링 후 재확인은 제거하거나, 메모리 변수로 저장

**개선안:**
```python
# 크롤링 전 체크 결과를 변수에 저장
already_loaded = bq_run_already_loaded(bq, run_id, period_type)
if already_loaded:
    print(f"⏭️ 이미 적재된 run_id라서 스킵: {run_id}")
    return

# ... 크롤링 및 저장 ...

# 크롤링 후 재확인 제거 (동시 실행 확률이 매우 낮으므로)
# 또는 메모리 변수 활용
bq_insert_rows(bq, results)
```

### 방안 4: 파티셔닝 추가 (선택사항)

**날짜 기준 파티셔닝:**
- `collected_at` 또는 `run_id`의 날짜 부분으로 파티셔닝
- 오래된 데이터 쿼리 시 비용 절감

---

## 📊 예상 비용 절감 효과

### 현재 상태 (클러스터링 없음):
- 테이블 크기: 50GB
- 중복 체크 2회: 100GB 스캔
- **비용: $0.49 per 실행**

### 최적화 후 (클러스터링 + LIMIT 1):
- 클러스터링으로 스캔 범위 감소: 50GB → 0.1GB (500배 감소)
- 중복 체크 2회: 0.2GB 스캔
- **비용: $0.001 per 실행 (500배 감소)**

### 연간 절감액 (월 1회 실행 기준):
- 현재: $0.49 × 12 = $5.88/year
- 최적화 후: $0.001 × 12 = $0.012/year
- **절감: $5.87/year (99.8% 절감)**

---

## 🚀 권장 조치 사항

1. **즉시 적용**: 중복 체크 쿼리를 LIMIT 1로 변경
2. **중요**: 테이블에 클러스터링 추가 (run_id, period_type)
3. **선택**: 크롤링 후 중복 체크 제거 (동시 실행 확률이 낮으면)

