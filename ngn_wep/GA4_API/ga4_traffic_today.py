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

# ✅ 환경 변수 설정 (Cloud Run 환경)
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "/home/oscar/ngn_board/service-account.json")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_APPLICATION_CREDENTIALS  # ✅ 환경변수 적용

PROJECT_ID = "winged-precept-443218-v8"
DATASET_ID = "ngn_dataset"
TABLE_ID_TRAFFIC = "ga4_traffic"
TABLE_ID_TRAFFIC_NGN = "ga4_traffic_ngn"
GA4_PROPERTY_IDS = [443411644, 449713217, 452725867]  # ✅ 3개 업체 GA4 ID 리스트

# ✅ 인증 정보 설정
credentials = service_account.Credentials.from_service_account_file(GOOGLE_APPLICATION_CREDENTIALS)

# ✅ BigQuery 클라이언트 초기화
bigquery_client = bigquery.Client(credentials=credentials, project=PROJECT_ID)

# ✅ GA4 API 클라이언트 초기화
analytics = build("analyticsdata", "v1beta", credentials=credentials)


def collect_ga4_traffic(start_date, end_date):
    """ ✅ GA4 API에서 트래픽 데이터를 수집하여 BigQuery에 저장 """
    date_range = pd.date_range(start=start_date, end=end_date).strftime("%Y-%m-%d").tolist()
    all_rows_traffic = []

    for target_date in date_range:
        for GA4_PROPERTY_ID in GA4_PROPERTY_IDS:
            logging.info(f"📡 {GA4_PROPERTY_ID} ({target_date}) 트래픽 데이터 수집 중...")

            request_body = {
                "dateRanges": [{"startDate": target_date, "endDate": target_date}],
                "dimensions": [{"name": "date"}, {"name": "firstUserSource"}],
                "metrics": [
                    {"name": "totalUsers"},
                    {"name": "engagementRate"},
                    {"name": "bounceRate"},
                    {"name": "eventCount"},
                    {"name": "screenPageViews"}
                ]
            }

            response = analytics.properties().runReport(
                property=f"properties/{GA4_PROPERTY_ID}", body=request_body
            ).execute()

            for row in response.get("rows", []):
                dims = [dim["value"] for dim in row["dimensionValues"]]
                event_date, first_user_source = dims  
                metrics = [float(metric["value"]) for metric in row["metricValues"]]

                all_rows_traffic.append({
                    "event_date": event_date,
                    "ga4_property_id": GA4_PROPERTY_ID,
                    "first_user_source": first_user_source,
                    "total_users": int(metrics[0]),
                    "engagement_rate": round(metrics[1] * 100, 2),
                    "bounce_rate": round(metrics[2] * 100, 2),
                    "event_count": int(metrics[3]),
                    "screen_page_views": int(metrics[4])
                })

    df_traffic = pd.DataFrame(all_rows_traffic)
    if not df_traffic.empty:
        df_traffic["event_date"] = pd.to_datetime(df_traffic["event_date"]).dt.date
        df_traffic["ga4_property_id"] = df_traffic["ga4_property_id"].astype(int)

        table_ref_traffic = bigquery_client.dataset(DATASET_ID).table(TABLE_ID_TRAFFIC)
        load_job_traffic = bigquery_client.load_table_from_dataframe(df_traffic, table_ref_traffic)
        load_job_traffic.result()

        logging.info(f"✅ GA4 트래픽 데이터 {len(df_traffic)}개 적재 완료!")
    else:
        logging.info(f"✅ {start_date} ~ {end_date} 구간에 대한 트래픽 데이터가 없습니다.")


def update_ga4_traffic_ngn(start_date, end_date):
    """ ✅ ga4_traffic 데이터를 기반으로 ga4_traffic_ngn 테이블 업데이트 """
    logging.info(f"📡 {TABLE_ID_TRAFFIC_NGN} 테이블 업데이트 중...")

    merge_query = f"""
    MERGE `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID_TRAFFIC_NGN}` AS target
    USING (
        SELECT 
            t.event_date, 
            c.company_name,
            t.ga4_property_id, 
            t.first_user_source,
            MAX(t.total_users) AS total_users,
            MAX(t.engagement_rate) AS engagement_rate,
            MAX(t.bounce_rate) AS bounce_rate,
            MAX(t.event_count) AS event_count,
            MAX(t.screen_page_views) AS screen_page_views
        FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID_TRAFFIC}` t
        LEFT JOIN `{PROJECT_ID}.{DATASET_ID}.company_info` c 
            ON t.ga4_property_id = c.ga4_property_id
        WHERE t.event_date BETWEEN "{start_date}" AND "{end_date}"
        GROUP BY t.event_date, c.company_name, t.ga4_property_id, t.first_user_source
    ) AS source
    ON target.event_date = source.event_date
    AND target.company_name = source.company_name
    AND target.ga4_property_id = source.ga4_property_id
    AND target.first_user_source = source.first_user_source
    WHEN MATCHED THEN
        UPDATE SET 
            target.total_users = source.total_users,
            target.engagement_rate = source.engagement_rate,
            target.bounce_rate = source.bounce_rate,
            target.event_count = source.event_count,
            target.screen_page_views = source.screen_page_views
    WHEN NOT MATCHED THEN
        INSERT (
            event_date, company_name, ga4_property_id, first_user_source, 
            total_users, engagement_rate, bounce_rate, event_count, screen_page_views
        )
        VALUES (
            source.event_date, source.company_name, source.ga4_property_id, 
            source.first_user_source, source.total_users, 
            source.engagement_rate, source.bounce_rate, 
            source.event_count, source.screen_page_views
        );
    """

    query_job = bigquery_client.query(merge_query)
    query_job.result()
    logging.info(f"✅ {TABLE_ID_TRAFFIC_NGN} 테이블 업데이트 완료!")


if __name__ == "__main__":
    now_kst = datetime.now(timezone.utc).astimezone(KST)
    today = now_kst.strftime("%Y-%m-%d")
    yesterday = (now_kst - timedelta(days=1)).strftime("%Y-%m-%d")

    # ✅ 오늘 실행
    if os.getenv("RUN_MODE", "today") == "today":
        collect_ga4_traffic(today, today)
        update_ga4_traffic_ngn(today, today)

    # ✅ 어제 실행
    elif os.getenv("RUN_MODE", "yesterday") == "yesterday":
        collect_ga4_traffic(yesterday, yesterday)
        update_ga4_traffic_ngn(yesterday, yesterday)

    logging.info("✅ 모든 데이터 수집 및 업데이트 완료!")
