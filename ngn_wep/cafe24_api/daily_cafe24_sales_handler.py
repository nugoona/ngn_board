import os
from google.cloud import bigquery
from datetime import datetime, timedelta, timezone
import logging

# ✅ 한국 시간대 설정
KST = timezone(timedelta(hours=9))
current_time = datetime.now(timezone.utc).astimezone(KST)
today = current_time.strftime("%Y-%m-%d")
yesterday = (current_time - timedelta(days=1)).strftime("%Y-%m-%d")

# ✅ BigQuery 클라이언트 설정
client = bigquery.Client()

# ✅ 로깅 설정
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ✅ 쿼리 실행 함수
def run_query(process_date):
    query = f"""
    -- ✅ MERGE INTO daily_cafe24_sales
    MERGE `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales` AS target
    USING (
      -- ✅ 환불 요약 테이블 (업체명 포함)
      WITH company_mall_ids AS (
          SELECT mall_id, company_name
          FROM `winged-precept-443218-v8.ngn_dataset.company_info`
      ),
      refund_summary AS (
          SELECT
              o.mall_id,  
              c.company_name,  
              DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) AS refund_date,  
              SUM(r.total_refund_amount) AS total_refund_amount  
          FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
          JOIN company_mall_ids c
              ON r.mall_id = c.mall_id  -- 먼저 업체별 mall_id로 환불 데이터 필터링
          JOIN `winged-precept-443218-v8.ngn_dataset.cafe24_orders` o
              ON r.order_id = o.order_id
              AND r.mall_id = o.mall_id  -- 동일한 몰의 주문-환불 데이터만 매칭
          WHERE DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) = '{process_date}'
          GROUP BY o.mall_id, c.company_name, refund_date
      ),

      -- ✅ 주문 상품 총 판매 개수 (order_id 기준으로 개수 집계)
      order_item_summary AS (
          SELECT
              oi.mall_id,  
              oi.order_id,  
              COUNT(DISTINCT oi.order_item_code) AS total_sold_quantity  
          FROM `winged-precept-443218-v8.ngn_dataset.cafe24_order_items_table` AS oi
          GROUP BY oi.mall_id, oi.order_id
      )

      -- ✅ 최종 집계 쿼리
      SELECT
          DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) AS payment_date,
          o.mall_id,
          c.company_name,
          COUNT(DISTINCT o.order_id) AS total_orders,
          0 AS item_orders,  -- 임시로 0으로 설정
          SUM(
              CASE 
                  WHEN o.order_price_amount = 0 THEN o.payment_amount + o.naverpay_point
                  ELSE o.order_price_amount
              END
          ) AS item_product_price,
          SUM(o.shipping_fee) AS total_shipping_fee,
          SUM(o.coupon_discount_price) AS total_coupon_discount,
          SUM(o.payment_amount) + SUM(o.points_spent_amount) + SUM(o.naverpay_point) AS total_payment,
          COALESCE(r.total_refund_amount, 0) AS total_refund_amount,
          (SUM(o.payment_amount) + SUM(o.points_spent_amount) + SUM(o.naverpay_point) - COALESCE(r.total_refund_amount, 0)) AS net_sales,
          SUM(o.naverpay_point) AS total_naverpay_point,
          SUM(CASE WHEN LOWER(o.payment_method) LIKE '%선불금%' THEN 1 ELSE 0 END) AS total_prepayment,
          SUM(CASE WHEN o.first_order = TRUE THEN 1 ELSE 0 END) AS total_first_order,
          SUM(CASE WHEN o.canceled = TRUE THEN 1 ELSE 0 END) AS total_canceled,
          SUM(CASE WHEN o.naverpay_payment_information = 'N' THEN 1 ELSE 0 END) AS total_naverpay_payment_info,
          CURRENT_TIMESTAMP() AS updated_at
      FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders` AS o
      JOIN `winged-precept-443218-v8.ngn_dataset.company_info` AS c
      ON o.mall_id = c.mall_id  
      LEFT JOIN refund_summary AS r
      ON o.mall_id = r.mall_id
      AND DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) = r.refund_date  
      -- LEFT JOIN order_item_summary AS oi
      -- ON o.mall_id = oi.mall_id
      -- AND o.order_id = oi.order_id  
      WHERE DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) = '{process_date}'
      GROUP BY payment_date, o.mall_id, c.company_name, r.total_refund_amount
    ) AS source

    ON target.payment_date = source.payment_date
    AND target.company_name = source.company_name

    WHEN MATCHED THEN
    UPDATE SET
        total_orders = source.total_orders,
        item_orders = source.item_orders,
        item_product_price = source.item_product_price,
        total_shipping_fee = source.total_shipping_fee,
        total_coupon_discount = source.total_coupon_discount,
        total_payment = source.total_payment,
        total_refund_amount = source.total_refund_amount,
        net_sales = source.net_sales,
        total_naverpay_point = source.total_naverpay_point,
        total_prepayment = source.total_prepayment,
        total_first_order = source.total_first_order,
        total_canceled = source.total_canceled,
        total_naverpay_payment_info = source.total_naverpay_payment_info,
        updated_at = CURRENT_TIMESTAMP()

    WHEN NOT MATCHED THEN
    INSERT (
        payment_date,
        mall_id,
        company_name,
        total_orders,
        item_orders,
        item_product_price,
        total_shipping_fee,
        total_coupon_discount,
        total_payment,
        total_refund_amount,
        net_sales,
        total_naverpay_point,
        total_prepayment,
        total_first_order,
        total_canceled,
        total_naverpay_payment_info,
        updated_at
    )
    VALUES (
        source.payment_date,
        source.mall_id,
        source.company_name,
        source.total_orders,
        source.item_orders,
        source.item_product_price,
        source.total_shipping_fee,
        source.total_coupon_discount,
        source.total_payment,
        source.total_refund_amount,
        source.net_sales,
        source.total_naverpay_point,
        source.total_prepayment,
        source.total_first_order,
        source.total_canceled,
        source.total_naverpay_payment_info,
        CURRENT_TIMESTAMP()
    );
    """

    logging.info(f"🚀 '{process_date}' 기준으로 쿼리 실행 중...")
    try:
        query_job = client.query(query)
        query_job.result()
        logging.info(f"✅ '{process_date}' 기준으로 데이터 성공적으로 처리되었습니다!")
    except Exception as e:
        logging.error(f"❌ 쿼리 실행 실패: {e}")



# ✅ 실행
if __name__ == "__main__":
    import sys
    process_type = sys.argv[1] if len(sys.argv) > 1 else "today"

    if process_type == "today":
        run_query(today)
    elif process_type == "yesterday":
        run_query(yesterday)
    elif process_type == "last_7_days":
        # 최근 7일간 일괄 실행
        for i in range(7):
            target_date = (current_time - timedelta(days=i)).strftime("%Y-%m-%d")
            logging.info(f"📅 {target_date} 처리 중... ({i+1}/7)")
            run_query(target_date)
        logging.info("✅ 최근 7일간 데이터 처리 완료!")
    else:
        logging.error("❌ 잘못된 파라미터입니다. 'today', 'yesterday', 또는 'last_7_days'만 지원됩니다.")
