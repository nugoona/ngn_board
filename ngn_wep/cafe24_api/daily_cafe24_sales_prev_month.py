"""
매월 지난달 daily_cafe24_sales 데이터 재수집 스크립트
- 매월 5일경 실행하여 지난달 전체 데이터를 삭제 후 재수집
- 정확도 향상: 월말 정산 후 카페24 데이터 변경 사항 반영
"""
import os
from google.cloud import bigquery
from datetime import datetime, timedelta, timezone
from calendar import monthrange
import logging
import time

# ✅ 한국 시간대 설정
KST = timezone(timedelta(hours=9))
current_time = datetime.now(timezone.utc).astimezone(KST)

# ✅ BigQuery 클라이언트 설정
client = bigquery.Client()

# ✅ 로깅 설정
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ✅ daily_cafe24_sales 쿼리 (daily_cafe24_sales_handler.py와 동일)
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
      all_dates AS (
          SELECT payment_date AS process_date, mall_id, company_name FROM order_agg
          UNION DISTINCT
          SELECT refund_date AS process_date, mall_id, company_name FROM refund_summary
      )
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
          COALESCE(oa.total_payment, 0) - COALESCE(r.total_refund_amount, 0) AS net_sales,
          COALESCE(oa.total_naverpay_point, 0) AS total_naverpay_point,
          COALESCE(oa.total_prepayment, 0) AS total_prepayment,
          COALESCE(oa.total_first_order, 0) AS total_first_order,
          COALESCE(oa.total_canceled, 0) AS total_canceled,
          COALESCE(oa.total_naverpay_payment_info, 0) AS total_naverpay_payment_info
      FROM all_dates AS ad
      LEFT JOIN order_agg AS oa 
          ON ad.process_date = oa.payment_date 
          AND ad.mall_id = oa.mall_id 
          AND ad.company_name = oa.company_name
      LEFT JOIN refund_summary AS r 
          ON ad.process_date = r.refund_date 
          AND ad.mall_id = r.mall_id 
          AND ad.company_name = r.company_name
    ) AS source
    ON target.payment_date = source.payment_date
       AND target.mall_id = source.mall_id
       AND target.company_name = source.company_name
    WHEN MATCHED THEN
    UPDATE SET
        target.total_orders = source.total_orders,
        target.item_orders = source.item_orders,
        target.item_product_price = source.item_product_price,
        target.total_shipping_fee = source.total_shipping_fee,
        target.total_coupon_discount = source.total_coupon_discount,
        target.total_payment = source.total_payment,
        target.total_refund_amount = source.total_refund_amount,
        target.net_sales = source.net_sales,
        target.total_naverpay_point = source.total_naverpay_point,
        target.total_prepayment = source.total_prepayment,
        target.total_first_order = source.total_first_order,
        target.total_canceled = source.total_canceled,
        target.total_naverpay_payment_info = source.total_naverpay_payment_info,
        target.updated_at = CURRENT_TIMESTAMP()
    WHEN NOT MATCHED THEN
    INSERT (
        payment_date, mall_id, company_name,
        total_orders, item_orders, item_product_price,
        total_shipping_fee, total_coupon_discount, total_payment,
        total_refund_amount, net_sales, total_naverpay_point,
        total_prepayment, total_first_order, total_canceled,
        total_naverpay_payment_info, updated_at
    )
    VALUES (
        source.payment_date, source.mall_id, source.company_name,
        source.total_orders, source.item_orders, source.item_product_price,
        source.total_shipping_fee, source.total_coupon_discount, source.total_payment,
        source.total_refund_amount, source.net_sales, source.total_naverpay_point,
        source.total_prepayment, source.total_first_order, source.total_canceled,
        source.total_naverpay_payment_info, CURRENT_TIMESTAMP()
    );
    """

    logging.info(f"🚀 daily_cafe24_sales: '{process_date}' 처리 중...")
    try:
        start_time = time.time()
        query_job = client.query(query)
        query_job.result()
        elapsed = time.time() - start_time
        logging.info(f"✅ daily_cafe24_sales: '{process_date}' 완료! (소요 시간: {elapsed:.2f}초)")
        return True
    except Exception as e:
        logging.error(f"❌ daily_cafe24_sales 실패 ({process_date}): {e}")
        return False


def delete_period_data(start_date, end_date):
    """특정 기간의 daily_cafe24_sales 데이터 삭제"""
    delete_query = f"""
    DELETE FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
    WHERE payment_date >= '{start_date}' AND payment_date <= '{end_date}'
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


def get_previous_month_range():
    """지난달의 시작일과 종료일 계산"""
    # 현재 날짜에서 한 달 전 계산
    if current_time.month == 1:
        prev_year = current_time.year - 1
        prev_month = 12
    else:
        prev_year = current_time.year
        prev_month = current_time.month - 1
    
    # 지난달 첫날
    start_date = datetime(prev_year, prev_month, 1, tzinfo=KST)
    
    # 지난달 마지막날
    _, last_day = monthrange(prev_year, prev_month)
    end_date = datetime(prev_year, prev_month, last_day, tzinfo=KST)
    
    return start_date, end_date


def main():
    # 지난달 기간 계산
    start_date, end_date = get_previous_month_range()
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    
    logging.info("=" * 80)
    logging.info(f"🔧 지난달({start_date.strftime('%Y년 %m월')}) 데이터 재수집 시작")
    logging.info(f"📅 기간: {start_str} ~ {end_str}")
    logging.info("=" * 80)
    
    # 1. 기존 데이터 삭제
    logging.info("⚠️  기존 데이터 삭제 시작...")
    if not delete_period_data(start_str, end_str):
        logging.error("❌ 데이터 삭제 실패! 작업을 중단합니다.")
        return
    
    # 2. 재수집 시작
    current_date = start_date
    total_days = (end_date - start_date).days + 1
    day_count = 0
    success_count = 0
    fail_count = 0
    
    start_time = time.time()
    
    while current_date <= end_date:
        day_count += 1
        date_str = current_date.strftime("%Y-%m-%d")
        logging.info(f"📅 [{day_count}/{total_days}] {date_str} 처리 중...")
        
        if run_daily_sales_query(date_str):
            success_count += 1
        else:
            fail_count += 1
        
        # 진행 상황 로그 (10일마다)
        if day_count % 10 == 0:
            elapsed = time.time() - start_time
            avg_time = elapsed / day_count
            remaining_days = total_days - day_count
            estimated_remaining = avg_time * remaining_days
            logging.info(f"📊 진행 상황: {day_count}/{total_days}일 완료 ({day_count*100//total_days}%)")
            logging.info(f"⏱️  예상 남은 시간: 약 {estimated_remaining/60:.1f}분")
        
        current_date += timedelta(days=1)
    
    total_elapsed = time.time() - start_time
    
    logging.info("=" * 80)
    logging.info("✅ 지난달 데이터 재수집 작업 완료!")
    logging.info(f"📅 처리 기간: {start_str} ~ {end_str}")
    logging.info(f"📊 총 처리일: {total_days}일")
    logging.info(f"✅ 성공: {success_count}일")
    logging.info(f"❌ 실패: {fail_count}일")
    logging.info(f"⏱️  총 소요 시간: {total_elapsed/60:.1f}분 ({total_elapsed:.0f}초)")
    logging.info("=" * 80)


if __name__ == "__main__":
    main()

