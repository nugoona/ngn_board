# 대시보드 취소된 주문 미표시 이슈 수정 명령문

## 문제 상황
- **문제**: 대시보드 "카페24 상품 판매" 섹션에서 취소된 주문(`total_canceled`)이 표시되지 않음
- **영향 범위**: 12월뿐만 아니라 다른 달에도 동일하게 발생
- **증상**: 개별 행 데이터(`daily_cafe24_items`)에는 `total_canceled > 0` 값이 있지만, GROUP BY 후 집계에서는 0으로 표시됨

## 원인 분석
1. **WHERE 조건 문제**: `cafe24_service.py`의 `get_cafe24_product_sales` 함수에서 `WHERE i.item_product_sales > 0` 조건 때문에 취소만 있고 판매가 0인 행이 제외됨
2. **GROUP BY 문제**: `GROUP BY i.company_name, i.product_name, i.product_no`로 인해 같은 `product_no`에 대해 `product_name`이 다른 경우(예: `"[1/12 예약배송] Button..."` vs `"Button..."`) 별도로 집계되어 취소 항목이 분리됨

## 수정 내용

### 파일: `ngn_wep/dashboard/services/cafe24_service.py`

#### 1. WHERE 조건 수정
```python
# 수정 전
AND i.item_product_sales > 0

# 수정 후  
AND (i.item_product_sales > 0 OR i.total_canceled > 0)
```

#### 2. GROUP BY 변경 및 product_name 처리
```python
# 수정 전
SELECT
    i.product_name,
    ...
GROUP BY i.company_name, i.product_name, i.product_no

# 수정 후
SELECT
    -- ✅ product_name은 가장 많이 사용된 것을 선택 (정상 판매 우선)
    ARRAY_AGG(i.product_name ORDER BY i.item_product_sales DESC, i.total_quantity DESC LIMIT 1)[OFFSET(0)] AS product_name,
    ...
GROUP BY i.company_name, i.product_no
```

#### 3. ORDER BY 수정
```python
# 수정 전
ORDER BY {order_by_column} DESC, i.company_name, i.product_name

# 수정 후
ORDER BY {order_by_column} DESC, i.company_name, MAX(i.product_name)
```

#### 4. count_query도 동일하게 수정
```python
# 수정 전
AND i.item_product_sales > 0
GROUP BY i.company_name, i.product_name, i.product_no

# 수정 후
AND (i.item_product_sales > 0 OR i.total_canceled > 0)
GROUP BY i.company_name, i.product_no
HAVING SUM(i.total_quantity) > 0
```

## 확인 사항
- 개별 행 데이터 확인: `check_individual_rows_total_canceled.sql` 실행
- 집계 결과 확인: `check_groupby_issue.sql` 실행
- 서비스 쿼리 테스트: `test_service_query_total_canceled.sql` 실행

## 배포 후 확인
1. 캐시 무효화 필요 (브라우저 콘솔 또는 `clear_cache_local.py` 실행)
2. 대시보드에서 취소된 주문이 정상적으로 표시되는지 확인
3. 모든 달에서 취소된 주문이 정상 표시되는지 확인

