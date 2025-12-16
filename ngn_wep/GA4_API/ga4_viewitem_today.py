import os
import pandas as pd
from google.cloud import bigquery
from googleapiclient.discovery import build
from google.oauth2 import service_account
from datetime import datetime, timezone, timedelta
import logging

# ✅ 한국 시간대 설정
KST = timezone(timedelta(hours=9))

# ✅ 로깅 설정
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ✅ 환경 변수 설정 (클라우드 환경 경로)
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "/home/oscar/ngn_board/service-account.json")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_APPLICATION_CREDENTIALS

PROJECT_ID = "winged-precept-443218-v8"
DATASET_ID = "ngn_dataset"
TABLE_ID_EVENTS = "ga4_viewItem"
TABLE_ID_ITEMS = "ga4_items"
TABLE_ID_TARGET = "ga4_viewitem_ngn"  # ✅ MERGE 할 대상 테이블

# ✅ 인증 정보 설정
credentials = service_account.Credentials.from_service_account_file(GOOGLE_APPLICATION_CREDENTIALS)

# ✅ BigQuery 클라이언트 초기화
bigquery_client = bigquery.Client(credentials=credentials, project=PROJECT_ID)

# ✅ GA4 API 클라이언트 초기화
analytics = build("analyticsdata", "v1beta", credentials=credentials)

# ✅ company_info 테이블에서 GA4 Property ID 동적으로 가져오기
def get_ga4_property_ids():
    """company_info 테이블에서 ga4_property_id가 NULL이 아니고 5자리 이상인 것들만 가져오기"""
    query = f"""
    SELECT DISTINCT ga4_property_id
    FROM `{PROJECT_ID}.{DATASET_ID}.company_info`
    WHERE ga4_property_id IS NOT NULL
      AND ga4_property_id >= 10000
    ORDER BY ga4_property_id
    """
    try:
        results = bigquery_client.query(query).result()
        property_ids = [int(row.ga4_property_id) for row in results]
        logging.info(f"✅ GA4 Property IDs 로드 완료: {property_ids}")
        return property_ids
    except Exception as e:
        logging.error(f"❌ GA4 Property IDs 조회 실패: {e}")
        # 실패 시 기본값 반환
        return [443411644, 449713217, 452725867]


def collect_ga4_events(target_date):
    """ ✅ 특정 날짜의 GA4 이벤트 데이터를 수집하여 BigQuery에 저장 """
    # ✅ 동적으로 GA4 Property IDs 가져오기
    GA4_PROPERTY_IDS = get_ga4_property_ids()
    
    all_rows_events = []

    for GA4_PROPERTY_ID in GA4_PROPERTY_IDS:
        logging.info(f"📡 {GA4_PROPERTY_ID} ({target_date}) 이벤트 데이터 수집 중...")

        try:
            request_body = {
                "dateRanges": [{"startDate": target_date, "endDate": target_date}],
                "dimensions": [
                    {"name": "date"},
                    {"name": "country"},
                    {"name": "firstUserSource"},
                    {"name": "itemId"}
                ],
                "metrics": [
                    {"name": "itemsViewed"}  
                ]
            }

            response = analytics.properties().runReport(
                property=f"properties/{GA4_PROPERTY_ID}", body=request_body
            ).execute()

            for row in response.get("rows", []):
                dims = [dim["value"] for dim in row["dimensionValues"]]
                event_date, country, first_user_source, item_id = dims
                items_viewed = int(row["metricValues"][0]["value"])

                all_rows_events.append({
                    "event_date": event_date,
                    "country": country,
                    "first_user_source": first_user_source,
                    "item_id": item_id,
                    "view_item": items_viewed,
                    "ga4_property_id": GA4_PROPERTY_ID
                })
        except Exception as e:
            logging.error(f"❌ {GA4_PROPERTY_ID} ({target_date}) 이벤트 데이터 수집 실패: {e}")
            continue

    df_events = pd.DataFrame(all_rows_events)
    df_events["event_date"] = pd.to_datetime(df_events["event_date"]).dt.date
    df_events["ga4_property_id"] = df_events["ga4_property_id"].astype(int)

    table_ref_events = bigquery_client.dataset(DATASET_ID).table(TABLE_ID_EVENTS)
    bigquery_client.load_table_from_dataframe(df_events, table_ref_events).result()

    logging.info(f"✅ GA4 이벤트 데이터 {len(df_events)}개 ({target_date}) 적재 완료!")


def collect_ga4_items(target_date):
    """ ✅ 특정 날짜의 GA4 상품명을 수집하여 BigQuery에 저장 """
    # ✅ 동적으로 GA4 Property IDs 가져오기
    GA4_PROPERTY_IDS = get_ga4_property_ids()
    
    all_rows_items = []

    for GA4_PROPERTY_ID in GA4_PROPERTY_IDS:
        logging.info(f"📡 {GA4_PROPERTY_ID} ({target_date}) 상품명 데이터 수집 중...")

        try:
            request_body_items = {
                "dateRanges": [{"startDate": target_date, "endDate": target_date}],
                "dimensions": [
                    {"name": "itemId"},
                    {"name": "itemName"}
                ],
                "metrics": [
                    {"name": "itemsViewed"}  
                ]
            }

            response_items = analytics.properties().runReport(
                property=f"properties/{GA4_PROPERTY_ID}", body=request_body_items
            ).execute()

            for row in response_items.get("rows", []):
                dims = [dim["value"] for dim in row["dimensionValues"]]
                item_id, item_name = dims

                all_rows_items.append({
                    "ga4_property_id": GA4_PROPERTY_ID,
                    "item_id": item_id,
                    "item_name": item_name
                })
        except Exception as e:
            logging.error(f"❌ {GA4_PROPERTY_ID} ({target_date}) 상품명 데이터 수집 실패: {e}")
            continue

    df_items = pd.DataFrame(all_rows_items).drop_duplicates(subset=['ga4_property_id', 'item_id'])
    df_items["ga4_property_id"] = df_items["ga4_property_id"].astype(int)

    table_ref_items = bigquery_client.dataset(DATASET_ID).table(TABLE_ID_ITEMS)
    bigquery_client.load_table_from_dataframe(df_items, table_ref_items).result()

    logging.info(f"✅ GA4 상품 데이터 {len(df_items)}개 ({target_date}) 적재 완료!")


def update_ga4_viewitem_ngn(target_date=None):
    """ ✅ `ga4_viewItem` 데이터를 `ga4_viewitem_ngn` 테이블로 업데이트 (중복 방지 및 업데이트) """
    logging.info(f"📡 {TABLE_ID_TARGET} 테이블 업데이트 중...")
    
    # 날짜 필터 설정 (최근 7일 또는 특정 날짜)
    if target_date:
        date_filter = f"AND DATE(v.event_date) = DATE('{target_date}')"
        target_date_filter = f"AND (target.event_date IS NULL OR DATE(target.event_date) = DATE('{target_date}'))"
    else:
        date_filter = "AND DATE(v.event_date) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)"
        target_date_filter = "AND (target.event_date IS NULL OR DATE(target.event_date) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY))"

    merge_query = f"""
    MERGE `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID_TARGET}` AS target
    USING (
        SELECT 
            v.event_date, 
            c.company_name,
            v.ga4_property_id, 
            v.country, 
            v.first_user_source, 
            i.item_name,
            MAX(v.view_item) AS view_item  -- 동일 그룹 내 하나의 값만 유지
        FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID_EVENTS}` v
        LEFT JOIN `{PROJECT_ID}.{DATASET_ID}.company_info` c 
            ON v.ga4_property_id = c.ga4_property_id
        LEFT JOIN `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID_ITEMS}` i 
            ON v.ga4_property_id = i.ga4_property_id 
            AND v.item_id = i.item_id
        WHERE 1=1 {date_filter}
        GROUP BY 
            v.event_date, 
            c.company_name, 
            v.ga4_property_id, 
            v.country, 
            v.first_user_source, 
            i.item_name
    ) AS source
    ON target.event_date = source.event_date
       AND target.company_name = source.company_name
       AND target.ga4_property_id = source.ga4_property_id 
       AND target.country = source.country
       AND target.first_user_source = source.first_user_source
       AND target.item_name = source.item_name
       {target_date_filter}
    WHEN MATCHED THEN
        UPDATE SET target.view_item = source.view_item
    WHEN NOT MATCHED THEN
        INSERT (
            event_date, company_name, ga4_property_id, 
            country, first_user_source, item_name, view_item
        )
        VALUES (
            source.event_date, source.company_name, source.ga4_property_id, 
            source.country, source.first_user_source, source.item_name, source.view_item
        );
    """

    bigquery_client.query(merge_query).result()
    logging.info(f"✅ {TABLE_ID_TARGET} 테이블 업데이트 완료!")


if __name__ == "__main__":
    # ✅ 오늘과 어제 날짜 계산
    now_kst = datetime.now(timezone.utc).astimezone(KST)
    today = now_kst.strftime("%Y-%m-%d")
    yesterday = (now_kst - timedelta(days=1)).strftime("%Y-%m-%d")

    # ✅ RUN_MODE에 따라 분기 (기본값: today)
    run_mode = os.getenv("RUN_MODE", "today")

    if run_mode == "today":
        logging.info("🔽 오늘 날짜만 수집합니다.")
        collect_ga4_events(today)
        collect_ga4_items(today)
        update_ga4_viewitem_ngn(today)

    elif run_mode == "yesterday":
        logging.info("🔽 어제 날짜만 수집합니다.")
        collect_ga4_events(yesterday)
        collect_ga4_items(yesterday)
        update_ga4_viewitem_ngn(yesterday)

    logging.info("✅ 모든 GA4 데이터 수집 및 업데이트 완료!")
