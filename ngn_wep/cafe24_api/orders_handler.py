# File: ngn_wep/cafe24_api/orders_handler.py

import os
import sys
import json
import requests
import logging
from datetime import datetime, timedelta, timezone
from google.cloud import bigquery, storage

# ─────────────────────────────────────
# ✅ 환경 설정
# ─────────────────────────────────────
KST = timezone(timedelta(hours=9))
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "/app/service-account.json")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_APPLICATION_CREDENTIALS

PROJECT_ID   = "winged-precept-443218-v8"
DATASET_ID   = "ngn_dataset"
ORDERS_TABLE_ID = "cafe24_orders"
TEMP_TABLE_ID   = "temp_orders"

BUCKET_NAME       = "winged-precept-443218-v8.appspot.com"
TOKEN_FILE_NAME   = "tokens.json"

bq_client = bigquery.Client()
gcs_client = storage.Client()

# ─────────────────────────────────────
# ✅ 유틸 함수
# ─────────────────────────────────────
def get_date_range(mode):
    today = datetime.now(tz=KST).date()
    if mode == "yesterday":
        return today - timedelta(days=1), today - timedelta(days=1)
    elif mode == "last_7_days":
        return today - timedelta(days=6), today
    else:
        return today, today

def to_bool(value):
    return str(value).lower() in ["true", "t", "1"]

KST = timezone(timedelta(hours=9))

def parse_date(date_value):
    if not date_value:
        return None
    try:
        dt_kst = datetime.strptime(date_value, "%Y-%m-%dT%H:%M:%S%z")  # 원본 Cafe24는 KST 포함
        dt_utc = dt_kst.astimezone(timezone.utc)
        return dt_utc.strftime("%Y-%m-%dT%H:%M:%S.%fZ")  # BigQuery 호환 ISO8601
    except Exception as e:
        logging.error(f"❌ 날짜 변환 오류: {e}, 입력값: {date_value}")
        return None


def download_tokens():
    bucket = gcs_client.bucket(BUCKET_NAME)
    blob = bucket.blob(TOKEN_FILE_NAME)
    token_data = blob.download_as_text()
    tokens = json.loads(token_data)
    return {t["mall_id"]: t for t in tokens if "mall_id" in t and "access_token" in t}

# ─────────────────────────────────────
# ✅ Cafe24 주문 수집
# ─────────────────────────────────────
def fetch_orders_data(mall_id, access_token, start_date, end_date):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    params = {
        "start_date": f"{start_date}T00:00:00+09:00",
        "end_date": f"{end_date}T23:59:59+09:00",
        "limit": 100,
        "include_fields": "order_id,order_date,payment_date,payment_method_name,canceled,"
                          "initial_order_amount,actual_order_amount,shipping_fee_detail,"
                          "first_order,paid,social_name,naver_point,naverpay_payment_information"
    }

    url = f"https://{mall_id}.cafe24api.com/api/v2/admin/orders"
    all_orders = []
    while True:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            logging.warning(f"[{mall_id}] API 요청 실패: {response.status_code} {response.text}")
            break

        orders = response.json().get("orders", [])
        if not orders:
            break

        for order in orders:
            try:
                initial = order.get("initial_order_amount", {})
                shipping_fee_detail = order.get("shipping_fee_detail", [])
                items_sold = sum(len(x.get("items", []) or []) for x in shipping_fee_detail)

                all_orders.append({
                    "mall_id": mall_id,
                    "order_id": order.get("order_id"),
                    "order_date": parse_date(order.get("order_date") or order.get("ordered_date")),
                    "payment_date": parse_date(order.get("payment_date")),
                    "payment_method": ",".join(order.get("payment_method_name", [])),
                    "first_order": to_bool(order.get("first_order")),
                    "naverpay_payment_information": order.get("naverpay_payment_information"),
                    "paid": to_bool(order.get("paid")),
                    "canceled": to_bool(order.get("canceled")),
                    "order_price_amount": float(initial.get("order_price_amount", 0)),
                    "shipping_fee": float(initial.get("shipping_fee", 0)),
                    "coupon_discount_price": float(initial.get("coupon_discount_price", 0)),
                    "points_spent_amount": float(initial.get("points_spent_amount", 0)),
                    "credits_spent_amount": float(initial.get("credits_spent_amount", 0)),
                    "membership_discount_amount": float(initial.get("membership_discount_amount", 0)),
                    "set_product_discount_amount": float(initial.get("set_product_discount_amount", 0)),
                    "app_discount_amount": float(initial.get("app_discount_amount", 0)),
                    "total_amount_due": float(initial.get("total_amount_due", 0)),
                    "payment_amount": float(initial.get("payment_amount", 0)),
                    "naverpay_point": float(order.get("naver_point", 0) or 0),
                    "social_name": order.get("social_name", ""),
                    "items_sold": items_sold
                })
            except Exception as e:
                logging.warning(f"❌ 주문 데이터 파싱 실패: {e}")

        if len(orders) < params["limit"]:
            break
        params["offset"] = params.get("offset", 0) + len(orders)

    logging.info(f"[{mall_id}] 수집 완료: {len(all_orders)}건")
    return all_orders

# ─────────────────────────────────────
# ✅ BigQuery 업로드 및 병합
# ─────────────────────────────────────
def upload_to_temp_table(data):
    if not data:
        return
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TEMP_TABLE_ID}"
    bq_client.insert_rows_json(table_ref, data)
    logging.info(f"✅ {len(data)}건 임시 테이블 업로드 완료")

def merge_temp_to_main():
    query = f"""
    MERGE `{PROJECT_ID}.{DATASET_ID}.{ORDERS_TABLE_ID}` T
    USING (
        SELECT * EXCEPT(row_num) FROM (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY mall_id, order_id ORDER BY order_date DESC) AS row_num
            FROM `{PROJECT_ID}.{DATASET_ID}.{TEMP_TABLE_ID}`
        )
        WHERE row_num = 1
    ) S
    ON T.mall_id = S.mall_id 
       AND T.order_id = S.order_id
       AND T.payment_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 2 DAY)
    WHEN MATCHED THEN UPDATE SET
        payment_date = S.payment_date,
        payment_method = S.payment_method,
        first_order = S.first_order,
        naverpay_payment_information = S.naverpay_payment_information,
        paid = S.paid,
        canceled = S.canceled,
        order_price_amount = S.order_price_amount,
        shipping_fee = S.shipping_fee,
        coupon_discount_price = S.coupon_discount_price,
        points_spent_amount = S.points_spent_amount,
        credits_spent_amount = S.credits_spent_amount,
        membership_discount_amount = S.membership_discount_amount,
        set_product_discount_amount = S.set_product_discount_amount,
        app_discount_amount = S.app_discount_amount,
        total_amount_due = S.total_amount_due,
        payment_amount = S.payment_amount,
        naverpay_point = S.naverpay_point,
        social_name = S.social_name,
        items_sold = S.items_sold,
        order_date = S.order_date
    WHEN NOT MATCHED THEN INSERT ROW;
    """
    bq_client.query(query).result()
    logging.info("✅ 메인 테이블 병합 완료")

# ─────────────────────────────────────
# ✅ 실행 함수
# ─────────────────────────────────────
def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "today"
    start_date, end_date = get_date_range(mode)
    logging.info(f"📅 실행 모드: {mode} ({start_date} ~ {end_date})")

    tokens = download_tokens()
    all_data = []
    for mall_id, info in tokens.items():
        access_token = info.get("access_token")
        orders = fetch_orders_data(mall_id, access_token, start_date, end_date)
        all_data.extend(orders)

    upload_to_temp_table(all_data)
    merge_temp_to_main()

if __name__ == "__main__":
    main()
