import sys
import os
import json
import requests
from google.cloud import bigquery, storage
from datetime import datetime, timedelta, timezone
import logging

# ✅ 한국 시간대 설정
KST = timezone(timedelta(hours=9))
current_time = datetime.now(timezone.utc).astimezone(KST)

# ✅ 로깅 설정
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ✅ 로그 파일 경로
LOG_FILE = "/home/oscar/ngn_board/ngn_wep/logs/product_data_handler.log"
if not os.path.exists(os.path.dirname(LOG_FILE)):
    os.makedirs(os.path.dirname(LOG_FILE))

# ✅ GCP 인증 정보
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "/home/oscar/ngn_board/service-account.json")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_APPLICATION_CREDENTIALS

# ✅ GCP 설정
BUCKET_NAME = "winged-precept-443218-v8.appspot.com"
TOKEN_FILE_NAME = "tokens.json"

# ✅ BigQuery 클라이언트
client = bigquery.Client.from_service_account_json(GOOGLE_APPLICATION_CREDENTIALS)

# ✅ Cloud Storage에서 tokens.json 다운로드
def download_tokens():
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(TOKEN_FILE_NAME)

    try:
        token_data = blob.download_as_text()
        logging.info(f"{TOKEN_FILE_NAME} 파일이 GCP 버킷에서 다운로드되었습니다.")
        tokens = json.loads(token_data)
        if isinstance(tokens, list):
            return tokens
        else:
            raise ValueError("❌ 토큰 파일 형식이 올바르지 않습니다.")
    except Exception as e:
        logging.error(f"❌ 토큰 파일 다운로드 실패: {e}")
        return []

# ✅ tokens.json 경로 설정
tokens_path = download_tokens()
TOKENS_JSON_PATH = tokens_path if tokens_path else TOKEN_FILE_NAME

# ✅ BigQuery 설정
PROJECT_ID = "winged-precept-443218-v8"
DATASET_ID = "ngn_dataset"
ITEMS_TABLE_ID = "cafe24_order_items_table"
TEMP_TABLE_ID = "temp_order_items_table"

# ✅ tokens.json 로드
def load_tokens():
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(TOKEN_FILE_NAME)

    try:
        token_data = blob.download_as_text()
        tokens = json.loads(token_data)
        if isinstance(tokens, list):
            return {token["mall_id"]: token for token in tokens if "mall_id" in token}
        else:
            raise ValueError("❌ 토큰 파일 형식이 올바르지 않습니다.")
    except json.JSONDecodeError as e:
        logging.error(f"❌ JSON 파싱 오류: {e}")
    except Exception as e:
        logging.error(f"❌ 토큰 로딩 오류: {e}")
    return {}

# ✅ 특정 mall_id 토큰 정보 가져오기
def get_token_info(mall_id):
    tokens = load_tokens()
    return tokens.get(mall_id)

# ✅ 날짜 파싱 함수
def parse_date(date_value):
    if not date_value:
        return None
    try:
        dt_kst = datetime.strptime(date_value, "%Y-%m-%dT%H:%M:%S%z")
        dt_utc = dt_kst.astimezone(timezone.utc)
        return dt_utc.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    except Exception as e:
        logging.error(f"❌ 날짜 변환 오류: {e}, 입력값: {date_value}")
        return None

# ✅ 주문 ID 가져오기
def fetch_order_ids(mall_id, start_date, end_date):
    token_info = get_token_info(mall_id)
    if not token_info:
        logging.error(f"❌ {mall_id} - 토큰 정보 누락")
        return []

    access_token = token_info["access_token"]
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    url = f"https://{mall_id}.cafe24api.com/api/v2/admin/orders"
    params = {
        "start_date": f"{start_date}T00:00:00+09:00",
        "end_date": f"{end_date}T23:59:59+09:00",
        "limit": 100,
        "include_fields": "order_id"
    }

    order_ids = []
    offset = 0

    while True:
        params["offset"] = offset
        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            logging.error(f"❌ {mall_id} - 주문 ID 조회 실패: {response.status_code}, {response.text}")
            break

        orders = response.json().get("orders", [])
        if not orders:
            break

        order_ids.extend([order["order_id"] for order in orders])
        offset += len(orders)

    logging.info(f"✅ {mall_id} - {len(order_ids)}개의 주문 ID 수집 완료")
    return order_ids

# ✅ 주문 상품 데이터 가져오기
def fetch_order_items(mall_id, order_id, retries=3):
    token_info = get_token_info(mall_id)
    if not token_info:
        logging.error(f"❌ {mall_id} - 토큰 정보 누락")
        return []

    access_token = token_info["access_token"]
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    url = f"https://{mall_id}.cafe24api.com/api/v2/admin/orders/{order_id}/items"

    for attempt in range(retries):
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            items = response.json().get("items", [])
            for item in items:
                item["mall_id"] = mall_id
                item["order_id"] = order_id
            return items
        else:
            logging.warning(f"⚠️ {mall_id} - 주문 상품 조회 실패 (시도 {attempt+1}/{retries}): {response.status_code}")

    logging.error(f"❌ {mall_id} - 주문 상품 조회 실패 (order_id: {order_id})")
    return []

# ✅ BigQuery 임시 테이블 업로드
def upload_to_temp_table(mall_id, items_data):
    if not items_data:
        logging.warning(f"⚠️ {mall_id} - 전송할 데이터 없음")
        return

    transformed_data = []
    for item in items_data:
        try:
            transformed_data.append({
                "mall_id": mall_id,
                "order_id": item.get("order_id"),
                "order_item_code": item.get("order_item_code"),
                "product_no": item.get("product_no"),
                "product_name": item.get("product_name"),
                "product_price": float(item.get("product_price") or 0),
                "additional_discount_price": float(item.get("additional_discount_price") or 0),
                "coupon_discount_price": float(item.get("coupon_discount_price") or 0),
                "app_item_discount_amount": float(item.get("app_item_discount_amount") or 0),
                "individual_shipping_fee": float(item.get("individual_shipping_fee") or 0),
                "quantity": int(item.get("quantity") or 0),
                "ordered_date": parse_date(item.get("ordered_date")),
                "payment_amount": float(item.get("payment_amount") or 0),
                "claim_code": item.get("claim_code"),
                "status_code": item.get("status_code")
            })
        except Exception as e:
            logging.error(f"❌ {mall_id} - 데이터 변환 중 오류 발생: {e}")

    if not transformed_data:
        logging.warning(f"⚠️ {mall_id} - 변환된 데이터가 없습니다.")
        return

    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TEMP_TABLE_ID}"
    errors = client.insert_rows_json(table_ref, transformed_data)

    if errors:
        logging.error(f"❌ {mall_id} - BigQuery 업로드 실패: {errors}")
    else:
        logging.info(f"✅ {mall_id} - BigQuery 임시 테이블 업로드 성공!")

# ✅ BigQuery 병합
def merge_temp_to_main_table():
    query = f"""
    MERGE `{PROJECT_ID}.{DATASET_ID}.{ITEMS_TABLE_ID}` AS target
    USING (
        SELECT * EXCEPT(row_num)
        FROM (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY mall_id, order_item_code ORDER BY ordered_date DESC) AS row_num
            FROM `{PROJECT_ID}.{DATASET_ID}.{TEMP_TABLE_ID}`
        )
        WHERE row_num = 1
    ) AS source
    ON target.mall_id = source.mall_id 
       AND target.order_item_code = source.order_item_code
       AND (target.ordered_date IS NULL OR DATE(target.ordered_date) >= DATE_SUB(CURRENT_DATE(), INTERVAL 2 DAY))

    WHEN MATCHED THEN
    UPDATE SET
        target.order_id = source.order_id,
        target.product_no = source.product_no,
        target.product_name = source.product_name,
        target.product_price = source.product_price,
        target.additional_discount_price = source.additional_discount_price,
        target.coupon_discount_price = source.coupon_discount_price,
        target.app_item_discount_amount = source.app_item_discount_amount,
        target.individual_shipping_fee = source.individual_shipping_fee,
        target.quantity = source.quantity,
        target.ordered_date = source.ordered_date,
        target.payment_amount = source.payment_amount,
        target.claim_code = COALESCE(source.claim_code, target.claim_code),
        target.status_code = COALESCE(source.status_code, target.status_code)

    WHEN NOT MATCHED THEN
    INSERT (
        mall_id, order_id, order_item_code, product_no, product_name,
        product_price, additional_discount_price, coupon_discount_price,
        app_item_discount_amount, individual_shipping_fee, quantity,
        ordered_date, payment_amount, claim_code, status_code
    )
    VALUES (
        source.mall_id, source.order_id, source.order_item_code, source.product_no, source.product_name,
        source.product_price, source.additional_discount_price, source.coupon_discount_price,
        source.app_item_discount_amount, source.individual_shipping_fee, source.quantity,
        source.ordered_date, source.payment_amount, source.claim_code, source.status_code
    );
    """
    try:
        client.query(query).result()
        logging.info("✅ 임시 테이블 데이터를 메인 테이블로 병합 완료!")
    except Exception as e:
        logging.error(f"❌ 병합 실패: {e}")

# ✅ 실행 함수
def main(process_type="today"):
    today = datetime.now(KST).strftime("%Y-%m-%d")
    yesterday = (datetime.now(KST) - timedelta(days=1)).strftime("%Y-%m-%d")
    start_date_7 = (datetime.now(KST) - timedelta(days=6)).strftime("%Y-%m-%d")

    tokens = load_tokens()
    if not tokens:
        logging.error("❌ 토큰 정보를 가져오지 못했습니다.")
        return

    for mall_id in tokens:
        logging.info(f"🚀 {mall_id} - 제품 데이터 처리 시작...")

        if process_type == "today":
            logging.info(f"📅 {mall_id} - 오늘({today}) 주문 ID 가져오는 중...")
            order_ids = fetch_order_ids(mall_id, today, today)

        elif process_type == "yesterday":
            logging.info(f"📅 {mall_id} - 어제({yesterday}) 주문 ID 가져오는 중...")
            order_ids = fetch_order_ids(mall_id, yesterday, yesterday)

        elif process_type == "last_7_days":
            logging.info(f"📅 {mall_id} - 최근 7일({start_date_7} ~ {today}) 주문 ID 가져오는 중...")
            order_ids = fetch_order_ids(mall_id, start_date_7, today)

        all_items = []
        for order_id in order_ids:
            all_items.extend(fetch_order_items(mall_id, order_id))

        upload_to_temp_table(mall_id, all_items)

    merge_temp_to_main_table()
    logging.info("🎉 모든 작업이 완료되었습니다!")

if __name__ == "__main__":
    process_type = sys.argv[1] if len(sys.argv) > 1 else "today"
    main(process_type)
