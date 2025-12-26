# File: ngn_wep/GA4_API/ga4_cart_signup_test.py
# 테스트용: GA4에서 장바구니(add_to_cart)와 회원가입(sign_up) 이벤트 조회

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

# ✅ BigQuery 클라이언트 초기화 (ADC 사용)
bigquery_client = bigquery.Client(project=PROJECT_ID)

# ✅ GA4 API 클라이언트 초기화 (ADC 사용)
analytics = build("analyticsdata", "v1beta")

# ✅ company_info 테이블에서 파이시스의 GA4 Property ID 가져오기
def get_piscess_ga4_property_id():
    """company_info 테이블에서 piscess의 GA4 Property ID 가져오기"""
    query = f"""
    SELECT ga4_property_id
    FROM `{PROJECT_ID}.{DATASET_ID}.company_info`
    WHERE LOWER(company_name) = 'piscess'
      AND ga4_property_id IS NOT NULL
      AND ga4_property_id >= 10000
    LIMIT 1
    """
    try:
        results = bigquery_client.query(query).result()
        for row in results:
            property_id = int(row.ga4_property_id)
            logging.info(f"✅ 파이시스 GA4 Property ID: {property_id}")
            return property_id
        logging.warning("⚠️ 파이시스 GA4 Property ID를 찾을 수 없습니다.")
        return None
    except Exception as e:
        logging.error(f"❌ GA4 Property ID 조회 실패: {e}")
        return None

# ✅ GA4에서 특정 이벤트 조회 (장바구니, 회원가입)
def fetch_ga4_events(property_id, start_date, end_date, event_names):
    """
    GA4 API에서 특정 이벤트 데이터 조회
    
    Args:
        property_id: GA4 Property ID
        start_date: 시작 날짜 (YYYY-MM-DD)
        end_date: 종료 날짜 (YYYY-MM-DD)
        event_names: 조회할 이벤트 이름 리스트 (예: ['add_to_cart', 'sign_up'])
    """
    all_events = []
    
    for event_name in event_names:
        logging.info(f"📡 {event_name} 이벤트 조회 중... ({start_date} ~ {end_date})")
        
        try:
            # GA4 Data API에서 특정 이벤트 조회
            # 방법 1: eventName을 dimension에 포함하고 필터링
            request_body = {
                "dateRanges": [{"startDate": start_date, "endDate": end_date}],
                "dimensions": [
                    {"name": "date"},
                    {"name": "eventName"}
                ],
                "metrics": [
                    {"name": "eventCount"}
                ],
                "dimensionFilter": {
                    "filter": {
                        "fieldName": "eventName",
                        "stringFilter": {
                            "matchType": "EXACT",
                            "value": event_name,
                            "caseSensitive": False
                        }
                    }
                }
            }

            response = analytics.properties().runReport(
                property=f"properties/{property_id}", body=request_body
            ).execute()

            rows = response.get("rows", [])
            if not rows:
                logging.info(f"   ⚠️ {event_name} 이벤트 데이터 없음")
                continue

            for row in rows:
                dims = [dim["value"] for dim in row["dimensionValues"]]
                event_date, event_name_val = dims
                event_count = int(row["metricValues"][0]["value"])

                all_events.append({
                    "event_date": event_date,
                    "event_name": event_name_val,
                    "event_count": event_count
                })
                
                logging.info(f"   ✅ {event_date}: {event_name_val} = {event_count}건")

        except Exception as e:
            logging.error(f"❌ {event_name} 이벤트 조회 실패: {e}")
            continue
    
    return all_events

# ✅ 메인 실행 함수
def main():
    """최근 7일간 파이시스의 장바구니와 회원가입 이벤트 조회"""
    now_kst = datetime.now(timezone.utc).astimezone(KST)
    end_date = now_kst.strftime("%Y-%m-%d")
    start_date = (now_kst - timedelta(days=6)).strftime("%Y-%m-%d")
    
    logging.info(f"📅 조회 기간: {start_date} ~ {end_date} (최근 7일)")
    
    # 파이시스 GA4 Property ID 가져오기
    property_id = get_piscess_ga4_property_id()
    if not property_id:
        logging.error("❌ 파이시스 GA4 Property ID를 찾을 수 없습니다.")
        return
    
    # 장바구니(add_to_cart)와 회원가입(sign_up) 이벤트 조회
    event_names = ["add_to_cart", "sign_up"]
    events = fetch_ga4_events(property_id, start_date, end_date, event_names)
    
    if events:
        df = pd.DataFrame(events)
        logging.info("\n" + "="*50)
        logging.info("📊 조회 결과 요약")
        logging.info("="*50)
        
        # 날짜별, 이벤트별 집계
        summary = df.groupby(['event_date', 'event_name'])['event_count'].sum().reset_index()
        summary_pivot = summary.pivot(index='event_date', columns='event_name', values='event_count').fillna(0)
        
        logging.info("\n날짜별 이벤트 발생 건수:")
        logging.info(summary_pivot.to_string())
        
        # 전체 합계
        total_summary = df.groupby('event_name')['event_count'].sum()
        logging.info("\n전체 합계:")
        for event_name, total in total_summary.items():
            logging.info(f"  {event_name}: {int(total)}건")
    else:
        logging.info("⚠️ 조회된 이벤트 데이터가 없습니다.")
    
    logging.info("\n🎉 테스트 완료!")

if __name__ == "__main__":
    main()

