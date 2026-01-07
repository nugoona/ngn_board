import os
from google.cloud import bigquery
from datetime import datetime, timedelta
import logging

# ✅ 로깅 설정
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ✅ BigQuery 클라이언트 설정
client = bigquery.Client()

# ✅ daily_cafe24_items_handler.py의 execute_bigquery 함수와 동일한 로직
def execute_bigquery_for_date(process_date):
    """특정 날짜에 대한 daily_cafe24_items 데이터 수집"""
    start_date = end_date = process_date
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
        product_url = source.product_url,
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
        logging.info(f"🚀 daily_cafe24_items: '{process_date}' 처리 중...")
        start_time = datetime.now()
        
        client.query(create_temp_table_query).result()
        client.query(merge_query).result()
        client.query(drop_query).result()

        elapsed = (datetime.now() - start_time).total_seconds()
        logging.info(f"✅ daily_cafe24_items: '{process_date}' 완료! (소요 시간: {elapsed:.2f}초)")
        return True
    except Exception as e:
        logging.error(f"❌ daily_cafe24_items 실패 ({process_date}): {e}")
        return False


def delete_period_data(start_date, end_date):
    """특정 기간의 daily_cafe24_items 데이터 삭제"""
    delete_query = f"""
    DELETE FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_items`
    WHERE DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) >= '{start_date}' 
      AND DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) <= '{end_date}'
    """

    logging.info(f"🗑️  데이터 삭제 중: {start_date} ~ {end_date}")
    try:
        query_job = client.query(delete_query)
        query_job.result()
        logging.info(f"✅ 삭제 완료: {start_date} ~ {end_date}")
        return True
    except Exception as e:
        logging.error(f"❌ 삭제 실패: {e}")
        return False


def main():
    logging.info("=" * 80)
    logging.info("🔧 2025년 12월 daily_cafe24_items 데이터 재수집 시작")
    logging.info("=" * 80)

    start_date = datetime(2025, 12, 1)
    end_date = datetime(2025, 12, 31)

    # 데이터 삭제
    if not delete_period_data(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")):
        logging.error("❌ 데이터 삭제 실패. 재수집을 중단합니다.")
        return

    current_date = start_date
    total_days = (end_date - start_date).days + 1
    day_count = 0

    while current_date <= end_date:
        day_count += 1
        date_str = current_date.strftime("%Y-%m-%d")
        logging.info(f"📅 [{day_count}/{total_days}] {date_str} 처리 중...")

        # daily_cafe24_items 복구
        execute_bigquery_for_date(date_str)

        current_date += timedelta(days=1)

    logging.info("=" * 80)
    logging.info("✅ 2025년 12월 daily_cafe24_items 데이터 재수집 완료!")
    logging.info("=" * 80)


if __name__ == "__main__":
    main()

