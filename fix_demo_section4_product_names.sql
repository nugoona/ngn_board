-- ============================================
-- demo 계정 섹션4: 구매 탭의 상품명을 조회 탭과 일치시키기
-- daily_cafe24_items의 product_name을 ga4_viewitem_monthly_raw의 item_name과 매칭
-- 2024-12-01 ~ 2026-12-31
-- ============================================

MERGE `winged-precept-443218-v8.ngn_dataset.daily_cafe24_items` T
USING (
  WITH viewitem_names AS (
    SELECT DISTINCT
      item_name,
      ROW_NUMBER() OVER (ORDER BY item_name) - 1 AS name_index
    FROM `winged-precept-443218-v8.ngn_dataset.ga4_viewitem_monthly_raw`
    WHERE LOWER(company_name) = 'demo'
      AND ym >= '2024-12'
      AND ym <= '2026-12'
      AND item_name IS NOT NULL
      AND item_name != ''
      AND item_name != '(not set)'
    LIMIT 500
  ),
  viewitem_count AS (
    SELECT COUNT(*) AS cnt FROM viewitem_names
  ),
  target_records AS (
    SELECT
      payment_date,
      company_name,
      order_id,
      product_no,
      MOD(
        ABS(FARM_FINGERPRINT(CAST(payment_date AS STRING) || '_' || CAST(order_id AS STRING) || '_' || CAST(product_no AS STRING))),
        (SELECT cnt FROM viewitem_count)
      ) AS name_index
    FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_items`
    WHERE LOWER(company_name) = 'demo'
      AND payment_date >= '2024-12-01'
      AND payment_date <= '2026-12-31'
    GROUP BY payment_date, company_name, order_id, product_no
  )
  SELECT
    tr.payment_date,
    tr.company_name,
    tr.order_id,
    tr.product_no,
    vn.item_name AS new_product_name
  FROM target_records tr
  JOIN viewitem_names vn ON tr.name_index = vn.name_index
) S
ON T.payment_date = S.payment_date
  AND T.company_name = S.company_name
  AND T.order_id = S.order_id
  AND T.product_no = S.product_no
WHEN MATCHED THEN UPDATE SET
  product_name = S.new_product_name;

-- ============================================
-- 확인 쿼리: 업데이트 후 구매 탭과 조회 탭 상품명 매칭 확인
-- ============================================
-- 구매 탭 상품명 (정규화 후)
WITH purchase_products AS (
  SELECT DISTINCT
    LOWER(
      TRIM(
        REGEXP_REPLACE(
          CASE 
            WHEN REGEXP_CONTAINS(LOWER(product_name), r'^\[set\]') THEN product_name
            ELSE REGEXP_REPLACE(product_name, r'^\[[^\]]+\]\s*', '')
          END,
          r'[^\w\s]+', ''
        )
      )
    ) AS normalized_name,
    product_name AS original_name
  FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_items`
  WHERE LOWER(company_name) = 'demo'
    AND payment_date >= '2024-12-01'
    AND payment_date <= '2026-12-31'
),
-- 조회 탭 상품명 (정규화 후)
view_products AS (
  SELECT DISTINCT
    LOWER(
      TRIM(
        REGEXP_REPLACE(
          CASE 
            WHEN REGEXP_CONTAINS(LOWER(item_name), r'^\[set\]') THEN item_name
            ELSE REGEXP_REPLACE(item_name, r'^\[[^\]]+\]\s*', '')
          END,
          r'[^\w\s]+', ''
        )
      )
    ) AS normalized_name,
    item_name AS original_name
  FROM `winged-precept-443218-v8.ngn_dataset.ga4_viewitem_monthly_raw`
  WHERE LOWER(company_name) = 'demo'
    AND ym >= '2024-12'
    AND ym <= '2026-12'
)
-- 매칭 확인
SELECT 
  'matched' AS status,
  COUNT(*) AS count
FROM purchase_products pp
WHERE EXISTS (
  SELECT 1 FROM view_products vp WHERE pp.normalized_name = vp.normalized_name
)
UNION ALL
SELECT 
  'unmatched' AS status,
  COUNT(*) AS count
FROM purchase_products pp
WHERE NOT EXISTS (
  SELECT 1 FROM view_products vp WHERE pp.normalized_name = vp.normalized_name
);

-- 구매 탭에서 조회 탭에 없는 상품명 상위 10개
WITH purchase_products AS (
  SELECT DISTINCT
    LOWER(
      TRIM(
        REGEXP_REPLACE(
          CASE 
            WHEN REGEXP_CONTAINS(LOWER(product_name), r'^\[set\]') THEN product_name
            ELSE REGEXP_REPLACE(product_name, r'^\[[^\]]+\]\s*', '')
          END,
          r'[^\w\s]+', ''
        )
      )
    ) AS normalized_name,
    product_name AS original_name
  FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_items`
  WHERE LOWER(company_name) = 'demo'
    AND payment_date >= '2024-12-01'
    AND payment_date <= '2026-12-31'
),
view_products AS (
  SELECT DISTINCT
    LOWER(
      TRIM(
        REGEXP_REPLACE(
          CASE 
            WHEN REGEXP_CONTAINS(LOWER(item_name), r'^\[set\]') THEN item_name
            ELSE REGEXP_REPLACE(item_name, r'^\[[^\]]+\]\s*', '')
          END,
          r'[^\w\s]+', ''
        )
      )
    ) AS normalized_name,
    item_name AS original_name
  FROM `winged-precept-443218-v8.ngn_dataset.ga4_viewitem_monthly_raw`
  WHERE LOWER(company_name) = 'demo'
    AND ym >= '2024-12'
    AND ym <= '2026-12'
)
SELECT 
  pp.original_name AS purchase_product_name,
  COUNT(*) AS record_count
FROM purchase_products pp
WHERE NOT EXISTS (
  SELECT 1 FROM view_products vp WHERE pp.normalized_name = vp.normalized_name
)
GROUP BY pp.original_name
ORDER BY record_count DESC
LIMIT 10;
