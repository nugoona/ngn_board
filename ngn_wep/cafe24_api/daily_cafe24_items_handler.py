import os
import sys
from google.cloud import bigquery
from datetime import datetime, timedelta, timezone
import logging

# 한국 시간대 설정
KST = timezone(timedelta(hours=9))
today = datetime.now(KST).strftime("%Y-%m-%d")

# 로깅 설정
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# BigQuery 클라이언트 초기화 (ADC 사용)
client = bigquery.Client()

def execute_bigquery(process_type="today"):
    if process_type == "last7days":
        start_date = (datetime.now(KST) - timedelta(days=6)).strftime("%Y-%m-%d")
        end_date = datetime.now(KST).strftime("%Y-%m-%d")
    elif process_type == "last30days":
        start_date = (datetime.now(KST) - timedelta(days=29)).strftime("%Y-%m-%d")
        end_date = datetime.now(KST).strftime("%Y-%m-%d")
    elif process_type == "yesterday":
        start_date = end_date = (datetime.now(KST) - timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        start_date = end_date = datetime.now(KST).strftime("%Y-%m-%d")

    temp_table = "winged-precept-443218-v8.ngn_dataset.temp_daily_cafe24_items"

    create_temp_table_query = f"""
    CREATE OR REPLACE TABLE `{temp_table}` AS
    WITH valid_mall_ids AS (
      SELECT DISTINCT mall_id
      FROM `winged-precept-443218-v8.ngn_dataset.mall_mapping`
      WHERE LOWER(company_name) != 'demo'
    ),
    FilteredOrders AS (
      SELECT DISTINCT
        o.order_id,
        DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) AS payment_date,
        m.company_name,
        m.main_url,
        CAST(o.mall_id AS STRING) AS mall_id,
        COALESCE(o.first_order, FALSE) AS first_order
      FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders` AS o
      JOIN `winged-precept-443218-v8.ngn_dataset.mall_mapping` AS m
        ON o.mall_id = m.mall_id
      WHERE o.mall_id IN (SELECT mall_id FROM valid_mall_ids)
        AND DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
        AND m.company_name IS NOT NULL 
    ),
    -- ✅ 핵심 수정: order_item_code별로 먼저 중복 제거 (ordered_date DESC로 최신 것만), 그 다음 order_id + product_no별로 수량 합산
    -- ⚠️ 중요: FilteredOrders에 있는 주문의 아이템만 포함 (취소된 주문 포함)
    OrderItemsDeduped AS (
      SELECT 
        order_id,
        CAST(mall_id AS STRING) AS mall_id,
        CAST(product_no AS INT64) AS product_no,
        SUM(CAST(quantity AS INT64)) AS quantity,
        SUM(CASE WHEN status_code IN ('C1', 'C2', 'C3') THEN CAST(quantity AS INT64) ELSE 0 END) AS canceled_quantity,
        MAX(product_name) AS product_name,
        MAX(CAST(product_price AS FLOAT64)) AS product_price
      FROM (
        -- 1단계: order_item_code별 유니크 행 추출 (ROW_NUMBER로 ordered_date DESC 기준 최신 것만)
        SELECT * EXCEPT(row_num)
        FROM (
          SELECT 
            oi.order_id,
            CAST(oi.mall_id AS STRING) AS mall_id,
            CAST(oi.product_no AS INT64) AS product_no,
            oi.product_name,
            oi.quantity,
            oi.product_price,
            oi.status_code,
            ROW_NUMBER() OVER(
              PARTITION BY CAST(oi.mall_id AS STRING), oi.order_item_code 
              ORDER BY oi.ordered_date DESC
            ) AS row_num
          FROM `winged-precept-443218-v8.ngn_dataset.cafe24_order_items_table` AS oi
          INNER JOIN FilteredOrders AS fo
            ON oi.order_id = fo.order_id 
            AND CAST(oi.mall_id AS STRING) = fo.mall_id
        )
        WHERE row_num = 1
      )
      -- 2단계: order_id + product_no별로 수량 합산 (같은 상품 여러 개 주문한 경우 정상 합산)
      GROUP BY order_id, mall_id, product_no
    ),
    FirstOrderCount AS (
      SELECT
        o.payment_date,
        CAST(o.mall_id AS STRING) AS mall_id,
        oid.product_no,
        o.order_id,
        SUM(CASE WHEN o.first_order THEN oid.quantity ELSE 0 END) AS first_order_quantity
      FROM FilteredOrders AS o
      JOIN OrderItemsDeduped AS oid
        ON o.order_id = oid.order_id AND o.mall_id = oid.mall_id
      GROUP BY o.payment_date, o.mall_id, oid.product_no, o.order_id
    ),
    OrderDetails AS (
      SELECT
        o.payment_date,
        o.mall_id,
        o.company_name,
        o.main_url,
        oid.product_no,
        o.order_id,
        REGEXP_REPLACE(
          oid.product_name,
          r'^\\[(?i)(?!set\\])[^\\]]+\\]\\s*',
          ''
        ) AS product_name,
        CAST(oid.product_price AS FLOAT64) AS product_price,
        oid.quantity,
        oid.canceled_quantity,
        MAX(p.category_no) AS category_no
      FROM FilteredOrders AS o
      JOIN OrderItemsDeduped AS oid
        ON o.order_id = oid.order_id AND o.mall_id = oid.mall_id
      LEFT JOIN `winged-precept-443218-v8.ngn_dataset.cafe24_products_table` AS p
        ON oid.mall_id = p.mall_id AND CAST(oid.product_no AS STRING) = p.product_no
      GROUP BY o.payment_date, o.mall_id, o.company_name, o.main_url, oid.product_no, o.order_id, oid.product_price, oid.quantity, oid.canceled_quantity, oid.product_name, p.category_no
    )
    SELECT
      od.payment_date,
      od.mall_id,
      od.company_name,
      od.order_id,
      CAST(od.product_no AS INT64) AS product_no,
      od.product_name,
      od.product_price,
      od.quantity AS total_quantity,
      od.canceled_quantity AS total_canceled,
      od.quantity - od.canceled_quantity AS item_quantity,
      CAST(od.product_price * (od.quantity - od.canceled_quantity) AS FLOAT64) AS item_product_sales,
      COALESCE(fo.first_order_quantity, 0) AS total_first_order,
      CONCAT(
        'https://', od.main_url,
        '/product/',
        REGEXP_REPLACE(
          LOWER(
            REPLACE(
              REGEXP_REPLACE(od.product_name, r'_', ''), 
              ' ', '-'
            )
          ),
          r'[^a-z0-9-]+', ''
        ),
        '/',
        CAST(od.product_no AS STRING),
        '/category/',
        CAST(od.category_no AS STRING),
        '/display/1/'
      ) AS product_url,
      CURRENT_TIMESTAMP() AS updated_at
    FROM OrderDetails AS od
    LEFT JOIN FirstOrderCount AS fo
      ON od.mall_id = fo.mall_id
     AND od.product_no = fo.product_no
     AND od.payment_date = fo.payment_date
     AND od.order_id = fo.order_id
    """

    merge_query = f"""
    MERGE `winged-precept-443218-v8.ngn_dataset.daily_cafe24_items` AS target
    USING `{temp_table}` AS source
    ON target.payment_date = source.payment_date
       AND target.mall_id = source.mall_id
       AND target.product_no = source.product_no
       AND target.order_id = source.order_id
    WHEN MATCHED THEN
      UPDATE SET
        product_url = source.product_url,  -- ✅ 강제 갱신
        product_name = source.product_name,
        product_price = source.product_price,
        total_quantity = source.total_quantity,
        total_canceled = source.total_canceled,
        item_quantity = source.item_quantity,
        item_product_sales = source.item_product_sales,
        total_first_order = source.total_first_order,
        updated_at = CURRENT_TIMESTAMP()
    WHEN NOT MATCHED THEN
      INSERT (
        payment_date, mall_id, company_name, order_id, product_no,
        product_name, product_price, total_quantity, total_canceled,
        item_quantity, item_product_sales, total_first_order,
        product_url, updated_at
      )
      VALUES (
        source.payment_date, source.mall_id, source.company_name, source.order_id, source.product_no,
        source.product_name, source.product_price, source.total_quantity, source.total_canceled,
        source.item_quantity, source.item_product_sales, source.total_first_order,
        source.product_url, CURRENT_TIMESTAMP()
      );
    """

    drop_query = f"DROP TABLE `{temp_table}`"

    try:
        logging.info(f"🚀 임시 테이블 생성 중... ({process_type})")
        client.query(create_temp_table_query).result()

        logging.info("🔄 메인 테이블 병합 중...")
        client.query(merge_query).result()

        logging.info("🧹 임시 테이블 삭제 중...")
        client.query(drop_query).result()

        logging.info("✅ 전체 쿼리 완료! 최근 데이터가 반영되었습니다.")

    except Exception as err:
        logging.error(f"❌ 쿼리 실행 중 오류 발생: {err}")

if __name__ == "__main__":
    process_type = sys.argv[1] if len(sys.argv) > 1 else "today"
    execute_bigquery(process_type)
