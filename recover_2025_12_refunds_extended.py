"""
2025년 12월 환불 데이터 재수집 스크립트 (확장 범위)
- payment_date가 12월인 환불을 모두 찾기 위해 refund_date 범위를 확장
"""
import os
import json
import requests
from google.cloud import bigquery, storage
from datetime import datetime, timedelta, timezone
import logging

# ✅ 로깅 설정
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ✅ GCP 설정
PROJECT_ID = "winged-precept-443218-v8"
DATASET_ID = "ngn_dataset"
TEMP_REFUNDS_TABLE_ID = "temp_cafe24_refunds_table"
REFUNDS_TABLE_ID = "cafe24_refunds_table"
BUCKET_NAME = "winged-precept-443218-v8.appspot.com"
TOKEN_FILE_NAME = "tokens.json"

client = bigquery.Client()

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

def download_tokens():
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(TOKEN_FILE_NAME)
    try:
        token_data = blob.download_as_text()
        tokens = json.loads(token_data)
        if isinstance(tokens, list):
            logging.info(f"{TOKEN_FILE_NAME} 파일 다운로드 성공")
            return tokens
        else:
            raise ValueError("토큰 파일의 JSON 구조가 [list]가 아닙니다.")
    except Exception as e:
        logging.error(f"토큰 다운로드 실패: {e}")
        return []

def get_token_info(mall_id):
    tokens_list = download_tokens()
    for token in tokens_list:
        if token.get("mall_id") == mall_id:
            return token
    return None

def parse_date(date_value):
    try:
        if date_value:
            return datetime.fromisoformat(date_value).strftime("%Y-%m-%d")
    except ValueError:
        logging.warning(f"날짜 변환 실패: {date_value}")
    return None

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
                    PARTITION BY t.refund_code, t.mall_id, t.order_id, t.order_item_code, c.company_name 
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
    ON target.mall_id = source.mall_id
       AND target.order_id = source.order_id
       AND target.order_item_code = source.order_item_code
       AND target.refund_code = source.refund_code

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

def main():
    logging.info("=" * 60)
    logging.info("🔧 2025년 12월 환불 데이터 재수집 시작 (확장 범위)")
    logging.info("=" * 60)
    
    # ⚠️ 중요: payment_date가 12월인 환불을 모두 찾기 위해
    # refund_date 범위를 넓게 설정 (11월 1일 ~ 1월 31일)
    # 이후 BigQuery에서 payment_date 기준으로 필터링
    start_date = "2025-11-01"  # 확장 시작일
    end_date = "2026-01-31"    # 확장 종료일

    tokens_list = download_tokens()
    mall_ids = [t["mall_id"] for t in tokens_list if "mall_id" in t]
    
    for mall_id in mall_ids:
        logging.info(f"{mall_id} - {start_date}부터 {end_date}까지 데이터 수집 시작")
        logging.info("⚠️  이후 BigQuery에서 payment_date 기준으로 필터링하세요!")
        refunds_data = fetch_refund_data(mall_id, start_date, end_date)
        upload_to_temp_refunds_table(mall_id, refunds_data)

    merge_temp_to_main_table()
    
    logging.info("=" * 60)
    logging.info("✅ 환불 데이터 재수집 완료!")
    logging.info("=" * 60)
    logging.info("💡 이제 BigQuery에서 payment_date 기준으로 확인하세요:")
    logging.info("   SELECT SUM(total_refund_amount) FROM ... WHERE payment_date >= '2025-12-01' AND payment_date <= '2025-12-31'")

if __name__ == "__main__":
    main()

