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

      -- ✅ 주문 상품 총 판매 개수 (order_id 기준으로 개수 집계)
      order_item_summary AS (
          SELECT
              oi.mall_id,  
              oi.order_id,  
              COUNT(DISTINCT oi.order_item_code) AS total_sold_quantity  
          FROM `winged-precept-443218-v8.ngn_dataset.cafe24_order_items_table` AS oi
          GROUP BY oi.mall_id, oi.order_id
      ),

      -- ✅ 주문 데이터 중복 제거 (order_id 기준 먼저 집계)
      -- ⚠️ payment_date는 이미 UTC TIMESTAMP로 저장되어 있으므로, DATETIME() 변환 시 KST 적용
      order_summary AS (
          SELECT
              o.mall_id,
              o.order_id,
              DATE(TIMESTAMP(o.payment_date), 'Asia/Seoul') AS payment_date,
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
          WHERE DATE(TIMESTAMP(o.payment_date), 'Asia/Seoul') = '{process_date}'
          GROUP BY o.mall_id, o.order_id, payment_date
      ),
      
      -- ✅ 주문 집계 (환불 제외)
      order_agg AS (
          SELECT
              os.payment_date,
              os.mall_id,
              c.company_name,
              COUNT(DISTINCT os.order_id) AS total_orders,
              0 AS item_orders,  -- 임시로 0으로 설정
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
       AND (target.payment_date IS NULL OR DATE(target.payment_date) = DATE('{process_date}'))

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
    elif len(process_type) == 10 and process_type.count('-') == 2:
        # 날짜 형식 (YYYY-MM-DD) 직접 지정
        run_query(process_type)
    else:
        logging.error("❌ 잘못된 파라미터입니다. 'today', 'yesterday', 'last_7_days', 또는 'YYYY-MM-DD' 형식의 날짜를 지원합니다.")
