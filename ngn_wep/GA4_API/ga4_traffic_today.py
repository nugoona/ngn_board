import os
import pandas as pd
from google.cloud import bigquery
from googleapiclient.discovery import build
from datetime import datetime, timezone, timedelta
import logging

# ✅ 한국 시간대 설정
KST = timezone(timedelta(hours=9))

# ✅ 로깅 설정
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

PROJECT_ID = "winged-precept-443218-v8"
DATASET_ID = "ngn_dataset"
TABLE_ID_TRAFFIC = "ga4_traffic"
TABLE_ID_TRAFFIC_NGN = "ga4_traffic_ngn"

# ✅ BigQuery 클라이언트 초기화 (ADC 사용)
bigquery_client = bigquery.Client(project=PROJECT_ID)

# ✅ GA4 API 클라이언트 초기화 (ADC 사용)
analytics = build("analyticsdata", "v1beta")

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


def collect_ga4_traffic(start_date, end_date):
    """ ✅ GA4 API에서 트래픽 데이터를 수집하여 BigQuery에 저장 """
    # ✅ 1. 중복 방지: 해당 기간의 기존 데이터 삭제
    logging.info(f"🗑️ 중복 방지: {start_date} ~ {end_date} 기간의 기존 데이터 삭제 중...")
    delete_query = f"""
    DELETE FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID_TRAFFIC}`
    WHERE event_date BETWEEN DATE("{start_date}") AND DATE("{end_date}")
    """
    try:
        delete_job = bigquery_client.query(delete_query)
        delete_job.result()
        logging.info(f"✅ 기존 데이터 삭제 완료")
    except Exception as e:
        logging.error(f"❌ 기존 데이터 삭제 실패: {e}")
        raise
    
    # ✅ 2. 동적으로 GA4 Property IDs 가져오기
    GA4_PROPERTY_IDS = get_ga4_property_ids()
    
    date_range = pd.date_range(start=start_date, end=end_date).strftime("%Y-%m-%d").tolist()
    all_rows_traffic = []

    for target_date in date_range:
        for GA4_PROPERTY_ID in GA4_PROPERTY_IDS:
            logging.info(f"📡 {GA4_PROPERTY_ID} ({target_date}) 트래픽 데이터 수집 중...")

            try:
                request_body = {
                    "dateRanges": [{"startDate": target_date, "endDate": target_date}],
                    "dimensions": [{"name": "date"}, {"name": "firstUserSource"}],
                    "metrics": [
                        {"name": "activeUsers"},  # ✅ 봇 트래픽 제거를 위해 totalUsers 대신 activeUsers 사용
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
                    
                    # ✅ 원본 값 확인 (디버깅용)
                    original_engagement = metrics[1]
                    original_bounce = metrics[2]
                    
                    # ✅ engagement_rate 처리 (0~1 소수 값을 퍼센트로 변환)
                    if original_engagement > 1.0:
                        logging.error(f"❌ 이상한 engagement_rate 값: {GA4_PROPERTY_ID} {event_date} {first_user_source} - 원본: {original_engagement} (1.0보다 큼)")
                        engagement_rate_final = round(original_engagement, 2)
                    else:
                        engagement_rate_final = round(original_engagement * 100, 2)
                    
                    # ✅ bounce_rate 계산: GA4에서는 이탈률 = 1 - 참여율
                    # GA4 API의 bounceRate 메트릭이 실제 대시보드와 다를 수 있으므로,
                    # engagementRate를 기준으로 계산하는 것이 더 정확함
                    bounce_rate_from_engagement = round((1.0 - original_engagement) * 100, 2)
                    
                    # ✅ GA4 API의 bounceRate도 수집하되, engagement 기반 계산값과 비교
                    if original_bounce > 1.0:
                        bounce_rate_from_api = round(original_bounce, 2)
                    else:
                        bounce_rate_from_api = round(original_bounce * 100, 2)
                    
                    # ✅ 두 값이 크게 다르면 로깅 (차이가 5% 이상)
                    if abs(bounce_rate_from_engagement - bounce_rate_from_api) > 5.0:
                        logging.warning(f"⚠️ bounce_rate 불일치: {GA4_PROPERTY_ID} {event_date} {first_user_source} - engagement 기반: {bounce_rate_from_engagement}%, API bounceRate: {bounce_rate_from_api}%")
                    
                    # ✅ engagement 기반 계산값 사용 (GA4 대시보드와 일치)
                    bounce_rate_final = bounce_rate_from_engagement

                    all_rows_traffic.append({
                        "event_date": event_date,
                        "ga4_property_id": GA4_PROPERTY_ID,
                        "first_user_source": first_user_source,
                        "total_users": int(metrics[0]),  # ✅ activeUsers 값을 total_users 컬럼에 매핑 (스키마 유지)
                        "engagement_rate": engagement_rate_final,
                        "bounce_rate": bounce_rate_final,
                        "event_count": int(metrics[3]),
                        "screen_page_views": int(metrics[4])
                    })
            except Exception as e:
                logging.error(f"❌ {GA4_PROPERTY_ID} ({target_date}) 트래픽 데이터 수집 실패: {e}")
                continue

    df_traffic = pd.DataFrame(all_rows_traffic)
    if not df_traffic.empty:
        df_traffic["event_date"] = pd.to_datetime(df_traffic["event_date"]).dt.date
        df_traffic["ga4_property_id"] = df_traffic["ga4_property_id"].astype(int)
        
        # ✅ 3. DataFrame 레벨 중복 데이터 확인 및 로깅 (API 응답에서 중복이 올 수 있으므로)
        before_dedup = len(df_traffic)
        # 같은 날짜/소스/property_id에 중복이 있는지 확인
        duplicates = df_traffic.duplicated(subset=['event_date', 'ga4_property_id', 'first_user_source'], keep=False)
        if duplicates.any():
            dup_count = duplicates.sum()
            logging.warning(f"⚠️ DataFrame 내 중복 데이터 발견: {dup_count}개 행 (전체: {before_dedup}개)")
            # 중복된 행의 샘플 로깅
            dup_rows = df_traffic[duplicates].head(5)
            for _, row in dup_rows.iterrows():
                logging.warning(f"  중복: {row['event_date']} {row['ga4_property_id']} {row['first_user_source']} - users: {row['total_users']}, bounce: {row['bounce_rate']}%")
        
        # ✅ 중복 제거 (같은 날짜/소스/property_id 중 가장 큰 total_users를 가진 행 유지)
        df_traffic = df_traffic.sort_values('total_users', ascending=False).drop_duplicates(
            subset=['event_date', 'ga4_property_id', 'first_user_source'], 
            keep='first'
        )
        after_dedup = len(df_traffic)
        if before_dedup != after_dedup:
            logging.info(f"✅ DataFrame 중복 제거: {before_dedup}개 → {after_dedup}개")

        # ✅ 4. BigQuery 적재
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
            SUM(t.total_users) AS total_users,
            -- engagement_rate와 bounce_rate는 가중평균으로 계산
            SAFE_DIVIDE(
                SUM(t.engagement_rate * t.total_users),
                SUM(t.total_users)
            ) AS engagement_rate,
            SAFE_DIVIDE(
                SUM(t.bounce_rate * t.total_users),
                SUM(t.total_users)
            ) AS bounce_rate,
            SUM(t.event_count) AS event_count,
            SUM(t.screen_page_views) AS screen_page_views
        FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID_TRAFFIC}` t
        LEFT JOIN `{PROJECT_ID}.{DATASET_ID}.company_info` c 
            ON t.ga4_property_id = c.ga4_property_id
        WHERE t.event_date BETWEEN DATE("{start_date}") AND DATE("{end_date}")
          AND c.company_name IS NOT NULL
        GROUP BY t.event_date, c.company_name, t.ga4_property_id, t.first_user_source
    ) AS source
    ON target.event_date = source.event_date
       AND target.company_name = source.company_name
       AND target.ga4_property_id = source.ga4_property_id
       AND target.first_user_source = source.first_user_source
       AND target.event_date BETWEEN DATE("{start_date}") AND DATE("{end_date}")
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
