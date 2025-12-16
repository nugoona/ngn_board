import os
import sys
import time
import logging
import requests
from datetime import datetime, timedelta, timezone
from google.cloud import bigquery
from dotenv import load_dotenv

# ✅ KST 시간대
KST = timezone(timedelta(hours=9))

# ✅ 로깅 설정
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ✅ 환경 변수 로드
load_dotenv(dotenv_path="/app/.env")
ACCESS_TOKEN = os.getenv("META_SYSTEM_USER_TOKEN")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "/app/service-account.json")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_APPLICATION_CREDENTIALS


# ✅ BigQuery 설정
API_VERSION = "v24.0"
PROJECT_ID = "winged-precept-443218-v8"
DATASET_ID = "ngn_dataset"
TABLE_ID = "meta_ads_ad_level"
client = bigquery.Client(project=PROJECT_ID)

# ✅ 광고 계정 리스트
def get_account_list():
    query = f"""
        SELECT company_name, meta_acc_id AS id, meta_acc_name AS name
        FROM `{PROJECT_ID}.{DATASET_ID}.metaAds_acc`
    """
    return [dict(row) for row in client.query(query).result()]

# ✅ 액션 값 추출
def extract_first_match(actions, types):
    for action in actions:
        if action["action_type"] in types:
            return float(action["value"])
    return 0

# ✅ 광고 상태 조회
def fetch_ad_status(ad_id):
    url = f"https://graph.facebook.com/{API_VERSION}/{ad_id}"
    params = {"access_token": ACCESS_TOKEN, "fields": "status"}
    try:
        res = requests.get(url, params=params)
        return res.json().get("status") if res.status_code == 200 else None
    except Exception as e:
        logging.warning(f"⚠ Failed to fetch ad status: {e}")
        return None

# ✅ 광고 성과 수집
def fetch_ad_level_insights(account_id, date):
    base_url = f"https://graph.facebook.com/{API_VERSION}/act_{account_id}/insights"
    params = {
        "access_token": ACCESS_TOKEN,
        "level": "ad",
        "fields": ",".join([
            "date_start", "ad_id", "ad_name", "adset_id", "adset_name",
            "campaign_id", "campaign_name", "account_id", "account_name",
            "impressions", "reach", "clicks", "spend", "actions",
            "action_values", "catalog_segment_value"
        ]),
        "time_range[since]": date,
        "time_range[until]": date,
        "limit": 500
    }

    results = []
    now_ts = datetime.now(tz=KST).isoformat()
    url = base_url
    while True:
        res = requests.get(url, params=params)
        if res.status_code != 200:
            logging.warning(f"[❌ ERROR] {account_id} response: {res.text}")
            break

        data = res.json().get("data", [])
        for row in data:
            actions = row.get("actions", [])
            action_values = row.get("action_values", [])
            catalog_values = row.get("catalog_segment_value", [])
            ad_id = row.get("ad_id")

            results.append({
                "date": date,
                "ad_id": ad_id,
                "ad_name": row.get("ad_name"),
                "adset_id": row.get("adset_id"),
                "adset_name": row.get("adset_name"),
                "campaign_id": row.get("campaign_id"),
                "campaign_name": row.get("campaign_name"),
                "account_id": row.get("account_id"),
                "account_name": row.get("account_name"),
                "impressions": int(row.get("impressions", 0)),
                "reach": int(row.get("reach", 0)),
                "clicks": extract_first_match(actions, ["link_click"]),
                "spend": float(row.get("spend", 0)),
                "purchases": int(extract_first_match(actions, [
                    "purchase", "omni_purchase", "onsite_app_purchase", "offsite_conversion.fb_pixel_purchase"
                ])),
                "purchase_value": extract_first_match(action_values, [
                    "purchase", "omni_purchase", "onsite_app_purchase", "offsite_conversion.fb_pixel_purchase"
                ]),
                "shared_purchase_value": extract_first_match(catalog_values, [
                    "onsite_web_app_purchase", "purchase", "omni_purchase", "offsite_conversion.fb_pixel_purchase"
                ]),
                "ad_status": fetch_ad_status(ad_id),
                "updated_at": now_ts  # ✅ 수집 시각 추가
            })

        next_page = res.json().get("paging", {}).get("next")
        if not next_page:
            break
        url = next_page
        params = {}

    return results

# ✅ 임시 테이블 생성
def create_temp_table(temp_table_id):
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{temp_table_id}"
    client.delete_table(table_ref, not_found_ok=True)
    logging.info("🧹 Deleted previous temp table if exists")

    schema = [
        bigquery.SchemaField("date", "DATE"),
        bigquery.SchemaField("ad_id", "STRING"),
        bigquery.SchemaField("ad_name", "STRING"),
        bigquery.SchemaField("adset_id", "STRING"),
        bigquery.SchemaField("adset_name", "STRING"),
        bigquery.SchemaField("campaign_id", "STRING"),
        bigquery.SchemaField("campaign_name", "STRING"),
        bigquery.SchemaField("account_id", "STRING"),
        bigquery.SchemaField("account_name", "STRING"),
        bigquery.SchemaField("impressions", "INTEGER"),
        bigquery.SchemaField("reach", "INTEGER"),
        bigquery.SchemaField("clicks", "FLOAT"),
        bigquery.SchemaField("spend", "FLOAT"),
        bigquery.SchemaField("purchases", "INTEGER"),
        bigquery.SchemaField("purchase_value", "FLOAT"),
        bigquery.SchemaField("shared_purchase_value", "FLOAT"),
        bigquery.SchemaField("ad_status", "STRING"),
        bigquery.SchemaField("updated_at", "TIMESTAMP")  # ✅ 추가됨
    ]
    client.create_table(bigquery.Table(table_ref, schema=schema))
    logging.info("✅ Temp table creation requested")

    for _ in range(10):
        try:
            client.get_table(table_ref)
            logging.info("✅ Temp table verified")
            return
        except Exception:
            logging.info("⏳ Waiting for table propagation...")
            time.sleep(1)

    raise RuntimeError(f"❌ Temp table not found after retries: {table_ref}")

# ✅ Insert 재시도 로직
def insert_with_retry(table_id, rows, max_retries=5, wait_sec=2):
    for i in range(max_retries):
        try:
            client.insert_rows_json(table_id, rows)
            logging.info("📥 Insert succeeded")
            return
        except Exception as e:
            logging.warning(f"⏳ Retry {i+1}/{max_retries} - Insert failed: {e}")
            time.sleep(wait_sec)
    raise RuntimeError("❌ Insert failed after all retries")

# ✅ MERGE 수행
def merge_into_main_table(temp_table_id, target_date=None):
    date_filter = f"AND T.date = DATE('{target_date}')" if target_date else ""
    query = f"""
        MERGE `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}` T
        USING `{PROJECT_ID}.{DATASET_ID}.{temp_table_id}` S
        ON T.date = S.date 
           AND T.ad_id = S.ad_id
           {date_filter}
        WHEN MATCHED THEN UPDATE SET
            ad_name = S.ad_name,
            adset_id = S.adset_id,
            adset_name = S.adset_name,
            campaign_id = S.campaign_id,
            campaign_name = S.campaign_name,
            account_id = S.account_id,
            account_name = S.account_name,
            impressions = S.impressions,
            reach = S.reach,
            clicks = SAFE_CAST(S.clicks AS INT64),
            spend = S.spend,
            purchases = S.purchases,
            purchase_value = S.purchase_value,
            shared_purchase_value = S.shared_purchase_value,
            ad_status = S.ad_status,
            updated_at = S.updated_at
        WHEN NOT MATCHED THEN
            INSERT (
                date, ad_id, ad_name, adset_id, adset_name,
                campaign_id, campaign_name, account_id, account_name,
                impressions, reach, clicks, spend,
                purchases, purchase_value, shared_purchase_value, ad_status, updated_at
            )
            VALUES (
                S.date, S.ad_id, S.ad_name, S.adset_id, S.adset_name,
                S.campaign_id, S.campaign_name, S.account_id, S.account_name,
                S.impressions, S.reach, SAFE_CAST(S.clicks AS INT64), S.spend,
                S.purchases, S.purchase_value, S.shared_purchase_value, S.ad_status, S.updated_at
            )
    """
    client.query(query).result()
    logging.info("🔁 Merged into main table")

# ✅ 임시 테이블 제거
def drop_temp_table(temp_table_id):
    client.delete_table(f"{PROJECT_ID}.{DATASET_ID}.{temp_table_id}", not_found_ok=True)
    logging.info("🧹 Temp table dropped")

# ✅ 메인 실행
def main(mode='yesterday'):
    now = datetime.now(tz=KST)
    date = now.date() if mode == "today" else (now - timedelta(days=1)).date()

    temp_table_id = f"meta_ads_ad_level_temp_{mode}"
    logging.info(f"⭐ Mode: {mode}")
    logging.info(f"📅 Target date (KST): {date}")
    logging.info(f"🔐 ACCESS_TOKEN 시작: {ACCESS_TOKEN[:40]}...")

    accounts = get_account_list()
    all_data = []

    create_temp_table(temp_table_id)
    time.sleep(2)

    try:
        for acc in accounts:
            logging.info(f"📡 Fetching: {acc['name']} ({acc['id']})")
            rows = fetch_ad_level_insights(acc["id"], str(date))
            all_data.extend(rows)

        if not all_data:
            logging.warning("⚠ No data collected.")
            return

        insert_with_retry(f"{PROJECT_ID}.{DATASET_ID}.{temp_table_id}", all_data)

    except Exception as e:
        logging.error(f"❌ Insertion failed: {e}")
        return

    try:
        merge_into_main_table(temp_table_id, str(date))
        logging.info(f"✅ Done! Total rows processed: {len(all_data)}")
    finally:
        drop_temp_table(temp_table_id)

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "yesterday"
    main(mode=mode)
