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
      SELECT
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
    CanceledOrders AS (
      SELECT
        order_id,
        CAST(mall_id AS STRING) AS mall_id,
        CAST(product_no AS INT64) AS product_no,
        1 AS canceled
      FROM `winged-precept-443218-v8.ngn_dataset.cafe24_order_items_table`
      WHERE status_code IN ('C1', 'C2', 'C3')
    ),
    FirstOrderCount AS (
      SELECT
        o.payment_date,
        CAST(o.mall_id AS STRING) AS mall_id,
        CAST(oi.product_no AS INT64) AS product_no,
        oi.order_id,
        oi.product_name,
        SUM(CASE WHEN o.first_order THEN oi.quantity ELSE 0 END) AS first_order_quantity
      FROM FilteredOrders AS o
      JOIN `winged-precept-443218-v8.ngn_dataset.cafe24_order_items_table` AS oi
        ON o.order_id = oi.order_id AND o.mall_id = oi.mall_id
      GROUP BY o.payment_date, o.mall_id, oi.product_no, oi.order_id, oi.product_name
    ),
    OrderDetails AS (
      SELECT
        o.payment_date,
        o.mall_id,
        o.company_name,
        o.main_url,
        CAST(oi.product_no AS INT64) AS product_no,
        oi.order_id,
        REGEXP_REPLACE(
          ARRAY_AGG(oi.product_name ORDER BY oi.ordered_date DESC LIMIT 1)[SAFE_OFFSET(0)],
          r'^\\[(?i)(?!set\\])[^\\]]+\\]\\s*',
          ''
        ) AS product_name,
        CAST(oi.product_price AS FLOAT64) AS product_price,
        SUM(oi.quantity) AS quantity,
        COALESCE(c.canceled, 0) AS canceled,
        p.category_no
      FROM FilteredOrders AS o
      JOIN `winged-precept-443218-v8.ngn_dataset.cafe24_order_items_table` AS oi
        ON o.order_id = oi.order_id AND o.mall_id = oi.mall_id
      LEFT JOIN CanceledOrders AS c
        ON o.order_id = c.order_id AND o.mall_id = c.mall_id
      LEFT JOIN `winged-precept-443218-v8.ngn_dataset.cafe24_products_table` AS p
        ON oi.mall_id = p.mall_id AND oi.product_no = p.product_no
      GROUP BY o.payment_date, o.mall_id, o.company_name, o.main_url, oi.product_no, oi.order_id, oi.product_price, c.canceled, p.category_no
    )
    SELECT
      od.payment_date,
      od.mall_id,
      od.company_name,
      od.order_id,
      CAST(od.product_no AS INT64) AS product_no,
      MAX(od.product_name) AS product_name,
      MAX(od.product_price) AS product_price,
      SUM(od.quantity) AS total_quantity,
      SUM(CASE WHEN od.canceled = 1 THEN od.quantity ELSE 0 END) AS total_canceled,
      SUM(od.quantity) - SUM(CASE WHEN od.canceled = 1 THEN od.quantity ELSE 0 END) AS item_quantity,
      CAST(MAX(od.product_price) * (SUM(od.quantity) - SUM(CASE WHEN od.canceled = 1 THEN od.quantity ELSE 0 END)) AS FLOAT64) AS item_product_sales,
      SUM(COALESCE(fo.first_order_quantity, 0)) AS total_first_order,
      CONCAT(
        'https://', MAX(od.main_url),
        '/product/',
        REGEXP_REPLACE(
          LOWER(
            REPLACE(
              REGEXP_REPLACE(MAX(od.product_name), r'_', ''), 
              ' ', '-'
            )
          ),
          r'[^a-z0-9-]+', ''
        ),
        '/',
        CAST(MAX(od.product_no) AS STRING),
        '/category/',
        CAST(MAX(od.category_no) AS STRING),
        '/display/1/'
      ) AS product_url,
      CURRENT_TIMESTAMP() AS updated_at
    FROM OrderDetails AS od
    LEFT JOIN FirstOrderCount AS fo
      ON od.mall_id = fo.mall_id
     AND od.product_no = fo.product_no
     AND od.payment_date = fo.payment_date
     AND od.order_id = fo.order_id
    GROUP BY od.payment_date, od.mall_id, od.company_name, od.order_id, od.product_no
    """

    merge_query = f"""
    MERGE `winged-precept-443218-v8.ngn_dataset.daily_cafe24_items` AS target
    USING `{temp_table}` AS source
    ON target.payment_date = source.payment_date
       AND target.mall_id = source.mall_id
       AND target.product_no = source.product_no
       AND target.order_id = source.order_id
       AND (target.payment_date IS NULL OR DATE(target.payment_date) BETWEEN DATE('{start_date}') AND DATE('{end_date}'))
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
