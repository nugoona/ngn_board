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

# ✅ GCP 설정
PROJECT_ID = "winged-precept-443218-v8"
DATASET_ID = "ngn_dataset"
TEMP_REFUNDS_TABLE_ID = "temp_cafe24_refunds_table"
REFUNDS_TABLE_ID = "cafe24_refunds_table"
BUCKET_NAME = "winged-precept-443218-v8.appspot.com"
TOKEN_FILE_NAME = "tokens.json"

# ✅ BigQuery 클라이언트 초기화 (ADC 사용)
client = bigquery.Client()

# ✅ 안전한 데이터 변환 함수
def safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default

def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

# ✅ (수정) 토큰 다운로드 함수: 리스트 형태로 반환
def download_tokens():
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(TOKEN_FILE_NAME)

    try:
        token_data = blob.download_as_text()
        tokens = json.loads(token_data)
        if isinstance(tokens, list):
            logging.info(f"{TOKEN_FILE_NAME} 파일 다운로드 성공 (리스트 형태)")
            return tokens  # ==> list
        else:
            raise ValueError("토큰 파일의 JSON 구조가 [list]가 아닙니다.")
    except Exception as e:
        logging.error(f"토큰 다운로드 실패: {e}")
        return []  # 빈 리스트 반환

# ✅ (수정) Mall ID 기준으로 Token 찾는 함수
def get_token_info(mall_id):
    tokens_list = download_tokens()  # ==> list
    # 리스트를 dict로 변환하거나, 그때그때 검색
    for token in tokens_list:
        if token.get("mall_id") == mall_id:
            return token
    return None

# ✅ 날짜 형식 변환
def parse_date(date_value):
    try:
        if date_value:
            return datetime.fromisoformat(date_value).strftime("%Y-%m-%d")
    except ValueError:
        logging.warning(f"날짜 변환 실패: {date_value}")
    return None

# ✅ 환불 데이터 가져오기
def fetch_refund_data(mall_id, start_date, end_date):
    token_info = get_token_info(mall_id)
    if not token_info:
        logging.warning(f"{mall_id} - 토큰 정보 누락")
        return []

    access_token = token_info["access_token"]
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    url = f"https://{mall_id}.cafe24api.com/api/v2/admin/refunds"

    all_refunds = []
    offset = 0

    while True:
        params = {
            "start_date": f"{start_date}T00:00:00+09:00",
            "end_date": f"{end_date}T23:59:59+09:00",
            "limit": 100,
            "offset": offset
        }

        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            logging.error(f"{mall_id} - API 요청 실패: {response.status_code}, {response.text}")
            break

        refunds = response.json().get("refunds", [])
        if not refunds:
            break

        for refund in refunds:
            order_item_codes = refund.get("order_item_code", [])
            if not isinstance(order_item_codes, list):
                order_item_codes = [str(order_item_codes)] if order_item_codes else ["N/A"]

            for code in order_item_codes:
                all_refunds.append({
                    "mall_id": mall_id,
                    "order_id": refund.get("order_id"),
                    "order_item_code": code,
                    "order_date": parse_date(refund.get("order_date")),
                    "refund_date": parse_date(refund.get("refund_date")),
                    "actual_refund_amount": safe_float(refund.get("actual_refund_amount")),
                    "quantity": safe_int(refund.get("quantity")),
                    "used_points": safe_float(refund.get("used_points")),
                    "used_credits": safe_float(refund.get("used_credits")),
                    "total_refund_amount": (
                        safe_float(refund.get("actual_refund_amount")) +
                        safe_float(refund.get("used_points")) +
                        safe_float(refund.get("used_credits"))
                    ),
                    "refund_code": refund.get("refund_code")
                })



        offset += 100

    logging.info(f"{mall_id} - {len(all_refunds)}건의 환불 데이터 수집 완료")
    return all_refunds

# ✅ 임시 테이블에 데이터 업로드
def upload_to_temp_refunds_table(mall_id, refunds_data):
    if not refunds_data:
        logging.warning(f"{mall_id} - 업로드할 데이터 없음")
        return

    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TEMP_REFUNDS_TABLE_ID}"

    try:
        errors = client.insert_rows_json(table_ref, refunds_data)
        if errors:
            logging.error(f"{mall_id} - BigQuery 업로드 실패: {errors}")
        else:
            logging.info(f"{mall_id} - BigQuery 업로드 성공!")
    except Exception as e:
        logging.error(f"{mall_id} - BigQuery 업로드 오류: {e}")

# ✅ 메인 테이블로 병합
def merge_temp_to_main_table():
    query = f"""
    MERGE {PROJECT_ID}.{DATASET_ID}.{REFUNDS_TABLE_ID} AS target
    USING (
        SELECT *
        FROM (
            SELECT
                t.mall_id,
                t.order_id,
                t.order_item_code,
                t.order_date,
                t.refund_date,
                t.actual_refund_amount,
                t.quantity,
                t.used_points,
                t.used_credits,
                t.total_refund_amount,
                t.refund_code,
                c.company_name,
                ROW_NUMBER() OVER (
                    PARTITION BY t.refund_code, t.mall_id, c.company_name 
                    ORDER BY t.refund_date DESC
                ) AS rn
            FROM {PROJECT_ID}.{DATASET_ID}.{TEMP_REFUNDS_TABLE_ID} t
            JOIN `{PROJECT_ID}.{DATASET_ID}.cafe24_orders` o
                ON t.order_id = o.order_id
                AND t.mall_id = o.mall_id
            JOIN `{PROJECT_ID}.{DATASET_ID}.company_info` c
                ON o.mall_id = c.mall_id
        )
        WHERE rn = 1
    ) AS source
    ON target.refund_code = source.refund_code
       AND (target.refund_date IS NULL OR DATE(target.refund_date) >= DATE_SUB(CURRENT_DATE(), INTERVAL 2 DAY))

    WHEN MATCHED THEN
    UPDATE SET
        target.mall_id = source.mall_id,
        target.order_id = source.order_id,
        target.order_item_code = source.order_item_code,
        target.order_date = source.order_date,
        target.refund_date = source.refund_date,
        target.actual_refund_amount = source.actual_refund_amount,
        target.quantity = source.quantity,
        target.used_points = source.used_points,
        target.used_credits = source.used_credits,
        target.total_refund_amount = source.total_refund_amount

    WHEN NOT MATCHED THEN
    INSERT (
        mall_id, order_id, order_item_code, order_date, refund_date,
        actual_refund_amount, quantity, used_points, used_credits,
        total_refund_amount, refund_code
    )
    VALUES (
        source.mall_id, source.order_id, source.order_item_code, source.order_date, source.refund_date,
        source.actual_refund_amount, source.quantity, source.used_points, source.used_credits,
        source.total_refund_amount, source.refund_code
    );
    """

    try:
        client.query(query).result()
        logging.info("✅ 테이블 병합 완료!")
    except Exception as e:
        logging.error(f"❌ 병합 실패: {e}")


# ✅ 메인 실행 함수 (오늘부터 어제까지)
def main():
    start_date = (current_time - timedelta(days=1)).strftime("%Y-%m-%d")
    end_date = current_time.strftime("%Y-%m-%d")

    # (수정) download_tokens()는 list 반환
    tokens_list = download_tokens()
    # tokens_list: [ {"mall_id": ..., "access_token": ...}, ... ]

    # 각 mall_id로 환불 데이터 수집
    mall_ids = [ t["mall_id"] for t in tokens_list if "mall_id" in t ]
    for mall_id in mall_ids:
        logging.info(f"{mall_id} - {start_date}부터 {end_date}까지 데이터 수집 시작")
        refunds_data = fetch_refund_data(mall_id, start_date, end_date)
        upload_to_temp_refunds_table(mall_id, refunds_data)

    # 임시 테이블 → 메인 테이블 MERGE
    merge_temp_to_main_table()

if __name__ == "__main__":
    main()
