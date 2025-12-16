import sys
import os
import json
import requests
from google.cloud import bigquery, storage
from datetime import datetime, timedelta, timezone
import subprocess
import logging
import time


KST = timezone(timedelta(hours=9))
current_time = datetime.now(timezone.utc).astimezone(KST)


# 로깅 설정
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# 로그 파일 경로 설정
LOG_FILE = "/home/oscar/ngn_board/ngn_wep/logs/product_catalog_data_handler.log"


# 로그 파일이 존재하지 않으면 생성
if not os.path.exists(os.path.dirname(LOG_FILE)):
    os.makedirs(os.path.dirname(LOG_FILE))

# Google Cloud Service Account Key 경로 설정
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "/home/oscar/ngn_board/service-account.json")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_APPLICATION_CREDENTIALS


# GCP Cloud Storage 설정
BUCKET_NAME = "winged-precept-443218-v8.appspot.com"
TOKEN_FILE_NAME = "tokens.json"

# BigQuery 클라이언트 초기화 (전역으로 선언)
client = bigquery.Client.from_service_account_json(GOOGLE_APPLICATION_CREDENTIALS)


# Cloud Storage에서 tokens.json 다운로드
def download_tokens():
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(TOKEN_FILE_NAME)

    try:
        token_data = blob.download_as_text()
        logging.info(f"{TOKEN_FILE_NAME} 파일이 GCP 버킷에서 다운로드되었습니다.")
        tokens = json.loads(token_data)
        if isinstance(tokens, list):  # JSON 구조 확인
            return tokens
        else:
            raise ValueError("다운로드된 토큰 파일 형식이 올바르지 않습니다.")
    except Exception as e:
        logging.error(f"토큰 파일 다운로드 실패: {e}")
        return []


# tokens.json 로컬 경로 설정
tokens_path = download_tokens()
TOKENS_JSON_PATH = tokens_path if tokens_path else TOKEN_FILE_NAME

# BigQuery 설정
PROJECT_ID = "winged-precept-443218-v8"
DATASET_ID = "ngn_dataset"
PRODUCTS_TABLE_ID = "cafe24_products_table"
TEMP_PRODUCTS_TABLE_ID = "temp_cafe24_products_table"
CATEGORIES_TABLE_ID = "cafe24_categories_table"
TEMP_CATEGORIES_TABLE_ID = "temp_cafe24_categories_table"

# tokens.json 파일에서 토큰 정보 로드
def load_tokens():
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(TOKEN_FILE_NAME)

    try:
        token_data = blob.download_as_text()
        logging.info(f"{TOKEN_FILE_NAME} 파일이 GCP 버킷에서 다운로드되었습니다.")

        tokens = json.loads(token_data)
        if isinstance(tokens, list):
            logging.info("토큰 파일이 성공적으로 로드되었습니다.")
            return {token["mall_id"]: token for token in tokens if "mall_id" in token}
        else:
            raise ValueError("토큰 파일의 형식이 올바르지 않습니다.")
    except json.JSONDecodeError as e:
        logging.error(f"토큰 파일 JSON 파싱 중 오류 발생: {e}")
    except Exception as e:
        logging.error(f"토큰 파일을 로드하는 중 오류 발생: {e}") 
    return {}

# 유틸리티 함수 정의 섹션
def get_dates():
    today = datetime.now(timezone.utc).astimezone(KST).strftime("%Y-%m-%d")
    yesterday = (datetime.now(timezone.utc).astimezone(KST) - timedelta(days=1)).strftime("%Y-%m-%d")
    return today, yesterday


# 특정 mall_id에 대한 토큰 정보 가져오기
def get_token_info(mall_id):
    tokens = load_tokens()
    return tokens.get(mall_id)


# 날짜 파싱 함수
def parse_date(date_value):
    if isinstance(date_value, str):
        try:
            return datetime.strptime(date_value.split("T")[0], "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            logging.warning(f"Invalid date format: {date_value}")
            return None
    return None


# 카테고리 데이터 수집
def fetch_categories_data(mall_id, seen_categories):
    token_info = get_token_info(mall_id)
    if not token_info:
        print(f"{mall_id}에 대한 토큰 정보를 찾을 수 없습니다.")
        return []

    access_token = token_info.get("access_token")
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    base_url_categories = f"https://{mall_id}.cafe24api.com/api/v2/admin/categories"
    params = {"offset": 0, "limit": 100}
    all_categories = []

    while True:
        response = requests.get(base_url_categories, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json().get("categories", [])
            if not data:
                break
            for category in data:
                category_no = category.get("category_no")
                if category_no in seen_categories:
                    continue
                seen_categories.add(category_no)
                all_categories.append({
                    "mall_id": mall_id,
                    "category_no": category_no,
                    "category_name": category.get("category_name"),
                    "parent_category_no": category.get("parent_category_no"),
                    "category_depth": category.get("category_depth"),
                    "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                })
            params["offset"] += len(data)
        else:
            print(f"{mall_id} - Categories API 요청 실패: {response.status_code}")
            break

    print(f"{mall_id} - 총 수집된 카테고리 수: {len(all_categories)}")
    return all_categories

# 상품 단건 조회 API로 대표 카테고리 가져오기
def fetch_product_primary_category(mall_id, product_no, access_token):
    url = f"https://{mall_id}.cafe24api.com/api/v2/admin/products/{product_no}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    try:
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            product = resp.json().get("product", {})
            categories = product.get("category", [])
            if categories and isinstance(categories, list):
                return categories[0].get("category_no")  # ✅ 대표 category
    except Exception as e:
        print(f"[ERROR] 상품 {product_no} 카테고리 조회 실패: {e}")
    return None


# 카테고리별 상품 수집
def fetch_products_by_category(mall_id, category_no, seen_products):
    token_info = get_token_info(mall_id)
    if not token_info:
        print(f"{mall_id}에 대한 토큰 정보를 찾을 수 없습니다.")
        return []

    access_token = token_info.get("access_token")
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    base_url = f"https://{mall_id}.cafe24api.com/api/v2/admin/categories/{category_no}/products"
    params = {"offset": 0, "limit": 100, "display_group": 1}
    all_products = []
    previous_data = None

    while True:
        try:
            response = requests.get(base_url, headers=headers, params=params)
            if response.status_code == 200:
                data = response.json().get("products", [])
                if not data:
                    break

                if previous_data == data:
                    break
                previous_data = data

                for product in data:
                    product_no = product.get("product_no")
                    product_key = f"{mall_id}_{product_no}"

                    # ✅ 중복 방지: 이미 처리한 product_no는 건너뜀
                    if product_key in seen_products:
                        continue
                    seen_products.add(product_key)

                    # ✅ 상품 API를 통해 정확한 category_no 덮어쓰기 시도
                    primary_category_no = fetch_product_primary_category(mall_id, product_no, access_token)
                    final_category_no = primary_category_no or category_no

                    all_products.append({
                        "mall_id": mall_id,
                        "product_no": product_no,
                        "category_no": final_category_no,
                        "display": product.get("display") == "T",
                        "selling": product.get("selling") == "T",
                        "sold_out": product.get("sold_out") == "T",
                        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                    })


                if len(data) < params["limit"]:
                    break
                params["offset"] += len(data)

            elif response.status_code == 429:
                time.sleep(5)
                continue
            else:
                break

        except Exception as e:
            print(f"예외 발생: {e}. 종료합니다.")
            break

    print(f"{mall_id} - 카테고리 {category_no} - 총 수집된 상품 수: {len(all_products)}")
    return all_products


# BigQuery MERGE 쿼리 실행
def merge_to_bigquery(temp_table_id, final_table_id, schema, data, merge_condition, update_set, insert_values):
    try:
        # TEMP 테이블에 데이터 로드
        job = client.load_table_from_json(
            data,
            f"{PROJECT_ID}.{DATASET_ID}.{temp_table_id}",
            job_config=bigquery.LoadJobConfig(schema=schema, write_disposition="WRITE_TRUNCATE")
        )
        job.result()
        print(f"임시 테이블 {temp_table_id} 데이터 업로드 완료!")

        # MERGE 쿼리 - 테이블별 조건 분기
        if final_table_id == "cafe24_products_table":
            update_set = """
                category_no = S.category_no,
                display = S.display,
                selling = S.selling,
                sold_out = S.sold_out,
                updated_at = S.updated_at
            """
        elif final_table_id == "cafe24_categories_table":
            update_set = """
                category_name = S.category_name,
                parent_category_no = S.parent_category_no,
                category_depth = S.category_depth,
                updated_at = S.updated_at
            """

        merge_query = f"""
        MERGE `{PROJECT_ID}.{DATASET_ID}.{final_table_id}` T
        USING `{PROJECT_ID}.{DATASET_ID}.{temp_table_id}` S
        ON {merge_condition}
           AND T.updated_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
        WHEN MATCHED THEN
          UPDATE SET
            {update_set}
        WHEN NOT MATCHED THEN
          INSERT ({', '.join([field.name for field in schema])})
          VALUES ({insert_values})
        """

        print("[DEBUG] MERGE 쿼리 ↓↓↓")
        print(merge_query)

        client.query(merge_query).result()
        print(f"{final_table_id} 테이블 MERGE 완료!")

        client.delete_table(f"{PROJECT_ID}.{DATASET_ID}.{temp_table_id}", not_found_ok=True)
        print(f"임시 테이블 {temp_table_id} 삭제 완료")

    except Exception as e:
        print(f"merge_to_bigquery에서 오류 발생: {e}")

# 모든 mall_id에 대한 데이터 처리

def process_all_malls():
    tokens = load_tokens()
    today, yesterday = get_dates()
    for mall_id in tokens.keys():
        print(f"{mall_id} - 카테고리 데이터 수집 시작...")
        seen_categories = set()
        categories_data = fetch_categories_data(mall_id, seen_categories)

        if categories_data:
            merge_to_bigquery(
                TEMP_CATEGORIES_TABLE_ID,
                CATEGORIES_TABLE_ID,
                [
                    bigquery.SchemaField("mall_id", "STRING"),
                    bigquery.SchemaField("category_no", "STRING"),
                    bigquery.SchemaField("category_name", "STRING"),
                    bigquery.SchemaField("parent_category_no", "STRING"),
                    bigquery.SchemaField("category_depth", "FLOAT"),
                    bigquery.SchemaField("updated_at", "TIMESTAMP")
                ],
                categories_data,
                "T.mall_id = S.mall_id AND T.category_no = S.category_no",
                """
                category_name = S.category_name,
                parent_category_no = S.parent_category_no,
                category_depth = S.category_depth,
                updated_at = S.updated_at
                """,
                "S.mall_id, S.category_no, S.category_name, S.parent_category_no, S.category_depth, S.updated_at"
            )

        print(f"{mall_id} - 상품 데이터 수집 시작...")
        seen_products = set()
        all_products = []
        for category in categories_data:
            category_no = category.get("category_no")
            if category_no:
                all_products.extend(fetch_products_by_category(mall_id, category_no, seen_products))

        if all_products:
            merge_to_bigquery(
                TEMP_PRODUCTS_TABLE_ID,
                PRODUCTS_TABLE_ID,
                [
                    bigquery.SchemaField("mall_id", "STRING"),
                    bigquery.SchemaField("product_no", "STRING"),
                    bigquery.SchemaField("category_no", "STRING"),
                    bigquery.SchemaField("display", "BOOLEAN"),
                    bigquery.SchemaField("selling", "BOOLEAN"),
                    bigquery.SchemaField("sold_out", "BOOLEAN"),
                    bigquery.SchemaField("updated_at", "TIMESTAMP")
                ],
                all_products,
                "T.mall_id = S.mall_id AND T.product_no = S.product_no",
                """
                category_no = S.category_no,
                display = S.display,
                selling = S.selling,
                sold_out = S.sold_out,
                updated_at = S.updated_at
                """,
                "S.mall_id, S.product_no, S.category_no, S.display, S.selling, S.sold_out, S.updated_at"
            )
        else:
            print(f"{mall_id} - 상품 데이터가 없어 업로드를 생략합니다.")

# 실행 

if __name__ == "__main__": 
    logging.info("하루에 한 번 실행됩니다.")
    process_all_malls()
