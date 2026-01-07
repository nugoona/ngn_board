-- ✅ 1단계: refund_date 기준 일자별 환불 확인 (중복 의심)
SELECT 
    DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) AS refund_date_kst,
    COUNT(*) AS total_records,
    COUNT(DISTINCT r.order_id) AS unique_orders,
    COUNT(DISTINCT CONCAT(r.order_id, '_', r.order_item_code, '_', r.refund_code)) AS unique_refund_items,
    SUM(r.total_refund_amount) AS total_refund_amount,
    -- 중복 의심 지표
    COUNT(*) - COUNT(DISTINCT CONCAT(r.order_id, '_', r.order_item_code, '_', r.refund_code)) AS duplicate_count
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
WHERE r.mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) >= '2025-12-01'
  AND DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) <= '2025-12-31'
GROUP BY refund_date_kst
HAVING duplicate_count > 0  -- 중복이 있는 날짜만
ORDER BY refund_date_kst;

-- ✅ 2단계: 중복된 환불 상세 확인 (refund_code, order_id, order_item_code 조합 기준)
SELECT 
    DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) AS refund_date_kst,
    r.order_id,
    r.order_item_code,
    r.refund_code,
    COUNT(*) AS duplicate_count,
    SUM(r.total_refund_amount) AS total_amount,
    MAX(r.total_refund_amount) AS max_amount,
    MIN(r.total_refund_amount) AS min_amount,
    STRING_AGG(CAST(r.total_refund_amount AS STRING), ', ') AS amounts
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
WHERE r.mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) >= '2025-12-01'
  AND DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) <= '2025-12-31'
GROUP BY refund_date_kst, r.order_id, r.order_item_code, r.refund_code
HAVING COUNT(*) > 1  -- 중복된 것만
ORDER BY refund_date_kst, duplicate_count DESC;

-- ✅ 3단계: 특정일의 모든 환불 데이터 확인 (과집계된 날짜 확인용)
-- 날짜를 원하는 날짜로 변경해서 실행하세요
SELECT 
    r.refund_date,
    r.order_id,
    r.order_item_code,
    r.refund_code,
    r.total_refund_amount,
    r.actual_refund_amount,
    r.used_points,
    r.used_credits,
    r.quantity
FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
WHERE r.mall_id = 'piscess1'
  AND DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) = '2025-12-XX'  -- XX를 특정 날짜로 변경
ORDER BY r.order_id, r.order_item_code, r.refund_code;

-- ✅ 4단계: 중복 제거 후 합계 (정상 환불 금액 계산)
SELECT 
    DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) AS refund_date_kst,
    COUNT(DISTINCT CONCAT(r.order_id, '_', r.order_item_code, '_', r.refund_code)) AS unique_refund_items,
    -- 중복 제거 후 금액 집계 (각 조합별 최신 금액 사용)
    SUM(DISTINCT_REFUND_AMOUNT) AS total_refund_amount
FROM (
    SELECT 
        r.refund_date,
        r.order_id,
        r.order_item_code,
        r.refund_code,
        -- 중복 중 가장 최신 금액 사용
        FIRST_VALUE(r.total_refund_amount) OVER (
            PARTITION BY r.order_id, r.order_item_code, r.refund_code 
            ORDER BY r.refund_date DESC
        ) AS DISTINCT_REFUND_AMOUNT
    FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
    WHERE r.mall_id = 'piscess1'
      AND DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) >= '2025-12-01'
      AND DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) <= '2025-12-31'
) r
GROUP BY refund_date_kst
ORDER BY refund_date_kst;

-- ✅ 5단계: 중복 환불 삭제 쿼리 (확인 후 실행)
-- 주의: 2단계 쿼리로 중복을 확인한 후 실행하세요!
/*
DELETE FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table`
WHERE STRUCT(mall_id, order_id, order_item_code, refund_code) IN (
    SELECT STRUCT(mall_id, order_id, order_item_code, refund_code)
    FROM (
        SELECT 
            mall_id,
            order_id,
            order_item_code,
            refund_code,
            ROW_NUMBER() OVER (
                PARTITION BY mall_id, order_id, order_item_code, refund_code
                ORDER BY refund_date DESC
            ) AS rn
        FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table`
        WHERE mall_id = 'piscess1'
          AND DATE(DATETIME(TIMESTAMP(refund_date), 'Asia/Seoul')) >= '2025-12-01'
          AND DATE(DATETIME(TIMESTAMP(refund_date), 'Asia/Seoul')) <= '2025-12-31'
    )
    WHERE rn > 1
);
*/

