"""
2025년 12월 데이터 재수집 스크립트
- daily_cafe24_sales
- cafe24_refunds_table
"""
import os
from google.cloud import bigquery
from datetime import datetime, timedelta
import logging

# ✅ 로깅 설정
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ✅ BigQuery 클라이언트 설정
client = bigquery.Client()

# ✅ daily_cafe24_sales 쿼리 (daily_cafe24_sales_handler.py에서 가져옴)
def run_daily_sales_query(process_date):
    query = f"""
    MERGE `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales` AS target
    USING (
      WITH company_mall_ids AS (
          SELECT mall_id, company_name
          FROM `winged-precept-443218-v8.ngn_dataset.company_info`
      ),
      refund_summary AS (
          -- ✅ 환불을 환불 발생일(refund_date) 기준으로 집계
          -- ⚠️ 중요: refund_code별로 먼저 집계하여 중복 방지 (하나의 refund_code는 한 번만 집계)
          SELECT
              refund_by_date.mall_id,
              refund_by_date.company_name,
              refund_by_date.refund_date,
              SUM(refund_by_date.total_refund_amount) AS total_refund_amount
          FROM (
              -- refund_code별로 먼저 집계 (같은 refund_code는 한 번만 집계)
              SELECT
                  r.mall_id,
                  c.company_name,
                  DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) AS refund_date,
                  r.refund_code,
                  MAX(r.total_refund_amount) AS total_refund_amount  -- refund_code별로 하나의 금액만 사용
              FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
              JOIN `winged-precept-443218-v8.ngn_dataset.company_info` c
                  ON r.mall_id = c.mall_id
              WHERE DATE(DATETIME(TIMESTAMP(r.refund_date), 'Asia/Seoul')) = '{process_date}'
              GROUP BY r.mall_id, c.company_name, refund_date, r.refund_code
          ) refund_by_date
          GROUP BY refund_by_date.mall_id, refund_by_date.company_name, refund_by_date.refund_date
      ),
      order_item_summary AS (
          SELECT
              oi.mall_id,  
              oi.order_id,  
              COUNT(DISTINCT oi.order_item_code) AS total_sold_quantity  
          FROM `winged-precept-443218-v8.ngn_dataset.cafe24_order_items_table` AS oi
          GROUP BY oi.mall_id, oi.order_id
      ),
      order_summary AS (
          SELECT
              o.mall_id,
              o.order_id,
              DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) AS payment_date,
              MAX(
                  CASE 
                      WHEN o.order_price_amount = 0 THEN o.payment_amount + o.naverpay_point
                      ELSE o.order_price_amount
                  END
              ) AS item_product_price,
              MAX(o.shipping_fee) AS shipping_fee,
              MAX(o.coupon_discount_price) AS coupon_discount_price,
              MAX(o.payment_amount) AS payment_amount,
              MAX(o.points_spent_amount) AS points_spent_amount,
              MAX(o.naverpay_point) AS naverpay_point,
              MAX(CASE WHEN LOWER(o.payment_method) LIKE '%선불금%' THEN 1 ELSE 0 END) AS is_prepayment,
              MAX(CASE WHEN o.first_order = TRUE THEN 1 ELSE 0 END) AS is_first_order,
              MAX(CASE WHEN o.canceled = TRUE THEN 1 ELSE 0 END) AS is_canceled,
              MAX(CASE WHEN o.naverpay_payment_information = 'N' THEN 1 ELSE 0 END) AS is_naverpay_payment_info
          FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders` AS o
          WHERE DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) = '{process_date}'
          GROUP BY o.mall_id, o.order_id, payment_date
      ),
      order_agg AS (
          SELECT
              os.payment_date,
              os.mall_id,
              c.company_name,
              COUNT(DISTINCT os.order_id) AS total_orders,
              0 AS item_orders,
              SUM(os.item_product_price) AS item_product_price,
              SUM(os.shipping_fee) AS total_shipping_fee,
              SUM(os.coupon_discount_price) AS total_coupon_discount,
              SUM(os.payment_amount) + SUM(os.points_spent_amount) + SUM(os.naverpay_point) AS total_payment,
              SUM(os.naverpay_point) AS total_naverpay_point,
              SUM(os.is_prepayment) AS total_prepayment,
              SUM(os.is_first_order) AS total_first_order,
              SUM(os.is_canceled) AS total_canceled,
              SUM(os.is_naverpay_payment_info) AS total_naverpay_payment_info
          FROM order_summary AS os
          JOIN `winged-precept-443218-v8.ngn_dataset.company_info` AS c
          ON os.mall_id = c.mall_id  
          GROUP BY os.payment_date, os.mall_id, c.company_name
      ),
      -- ✅ 모든 날짜 수집 (주문 또는 환불이 있는 날짜)
      all_dates AS (
          SELECT payment_date AS process_date, mall_id, company_name FROM order_agg
          UNION DISTINCT
          SELECT refund_date AS process_date, mall_id, company_name FROM refund_summary
      )
      -- ✅ 최종 집계 쿼리 (환불 금액 별도 추가)
      -- ⚠️ 환불은 refund_date 기준으로 집계되므로, 환불만 있는 날짜도 포함
      SELECT
          ad.process_date AS payment_date,
          ad.mall_id,
          ad.company_name,
          COALESCE(oa.total_orders, 0) AS total_orders,
          COALESCE(oa.item_orders, 0) AS item_orders,
          COALESCE(oa.item_product_price, 0) AS item_product_price,
          COALESCE(oa.total_shipping_fee, 0) AS total_shipping_fee,
          COALESCE(oa.total_coupon_discount, 0) AS total_coupon_discount,
          COALESCE(oa.total_payment, 0) AS total_payment,
          COALESCE(r.total_refund_amount, 0) AS total_refund_amount,
          (COALESCE(oa.total_payment, 0) - COALESCE(r.total_refund_amount, 0)) AS net_sales,
          COALESCE(oa.total_naverpay_point, 0) AS total_naverpay_point,
          COALESCE(oa.total_prepayment, 0) AS total_prepayment,
          COALESCE(oa.total_first_order, 0) AS total_first_order,
          COALESCE(oa.total_canceled, 0) AS total_canceled,
          COALESCE(oa.total_naverpay_payment_info, 0) AS total_naverpay_payment_info,
          CURRENT_TIMESTAMP() AS updated_at
      FROM all_dates AS ad
      LEFT JOIN order_agg AS oa
      ON ad.process_date = oa.payment_date
      AND ad.mall_id = oa.mall_id
      LEFT JOIN refund_summary AS r
      ON ad.process_date = r.refund_date
      AND ad.mall_id = r.mall_id
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
        payment_date, mall_id, company_name, total_orders, item_orders,
        item_product_price, total_shipping_fee, total_coupon_discount,
        total_payment, total_refund_amount, net_sales, total_naverpay_point,
        total_prepayment, total_first_order, total_canceled,
        total_naverpay_payment_info, updated_at
    )
    VALUES (
        source.payment_date, source.mall_id, source.company_name,
        source.total_orders, source.item_orders, source.item_product_price,
        source.total_shipping_fee, source.total_coupon_discount,
        source.total_payment, source.total_refund_amount, source.net_sales,
        source.total_naverpay_point, source.total_prepayment,
        source.total_first_order, source.total_canceled,
        source.total_naverpay_payment_info, CURRENT_TIMESTAMP()
    );
    """

    logging.info(f"🚀 daily_cafe24_sales: '{process_date}' 처리 중...")
    try:
        query_job = client.query(query)
        query_job.result()
        logging.info(f"✅ daily_cafe24_sales: '{process_date}' 완료!")
    except Exception as e:
        logging.error(f"❌ daily_cafe24_sales 실패 ({process_date}): {e}")


def main():
    logging.info("=" * 60)
    logging.info("🔧 2025년 12월 데이터 재수집 시작")
    logging.info("=" * 60)
    
    # 2025년 12월 1일 ~ 31일
    start_date = datetime(2025, 12, 1)
    end_date = datetime(2025, 12, 31)
    
    current_date = start_date
    total_days = (end_date - start_date).days + 1
    day_count = 0
    
    while current_date <= end_date:
        day_count += 1
        date_str = current_date.strftime("%Y-%m-%d")
        logging.info(f"📅 [{day_count}/{total_days}] {date_str} 처리 중...")
        
        # daily_cafe24_sales 복구
        run_daily_sales_query(date_str)
        
        current_date += timedelta(days=1)
    
    logging.info("=" * 60)
    logging.info("✅ 2025년 12월 데이터 재수집 완료!")
    logging.info("=" * 60)


if __name__ == "__main__":
    main()

