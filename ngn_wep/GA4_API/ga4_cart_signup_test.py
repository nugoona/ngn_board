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

# ✅ company_info 테이블에서 GA4 Property ID와 company_name 가져오기
def get_company_ga4_property_ids(company_name_filter=None):
    """
    company_info 테이블에서 GA4 Property ID와 company_name 가져오기
    
    Args:
        company_name_filter: 특정 업체만 조회하려면 업체명 입력 (예: 'piscess'), None이면 전체 업체
    """
    if company_name_filter:
        query = f"""
        SELECT ga4_property_id, company_name
        FROM `{PROJECT_ID}.{DATASET_ID}.company_info`
        WHERE LOWER(company_name) = LOWER('{company_name_filter}')
          AND ga4_property_id IS NOT NULL
          AND ga4_property_id >= 10000
        """
    else:
        query = f"""
        SELECT DISTINCT ga4_property_id, company_name
        FROM `{PROJECT_ID}.{DATASET_ID}.company_info`
        WHERE ga4_property_id IS NOT NULL
          AND ga4_property_id >= 10000
        ORDER BY company_name
        """
    
    try:
        results = bigquery_client.query(query).result()
        companies = []
        for row in results:
            companies.append({
                'property_id': int(row.ga4_property_id),
                'company_name': row.company_name
            })
        
        if companies:
            if company_name_filter:
                logging.info(f"✅ {company_name_filter} GA4 Property ID: {companies[0]['property_id']}")
            else:
                logging.info(f"✅ 총 {len(companies)}개 업체 발견: {[c['company_name'] for c in companies]}")
            return companies
        else:
            logging.warning(f"⚠️ GA4 Property ID를 찾을 수 없습니다.")
            return []
    except Exception as e:
        logging.error(f"❌ GA4 Property ID 조회 실패: {e}")
        return []

# ✅ GA4에서 특정 이벤트 조회 (장바구니: 사용자 수, 회원가입: 이벤트 수)
def fetch_ga4_events(property_id, start_date, end_date, event_names, use_user_count=False):
    """
    GA4 API에서 특정 이벤트 데이터 조회
    
    Args:
        property_id: GA4 Property ID
        start_date: 시작 날짜 (YYYY-MM-DD)
        end_date: 종료 날짜 (YYYY-MM-DD)
        event_names: 조회할 이벤트 이름 리스트 (예: ['add_to_cart', 'sign_up'])
        use_user_count: True이면 사용자 수(totalUsers), False이면 이벤트 수(eventCount)
    """
    all_events = []
    
    # 메트릭 선택: 사용자 수 또는 이벤트 수
    metric_name = "totalUsers" if use_user_count else "eventCount"
    metric_label = "사용자 수" if use_user_count else "건수"
    
    for event_name in event_names:
        logging.info(f"📡 {event_name} 이벤트 조회 중... ({start_date} ~ {end_date}) [{metric_label}]")
        
        try:
            # GA4 Data API에서 특정 이벤트 조회
            request_body = {
                "dateRanges": [{"startDate": start_date, "endDate": end_date}],
                "dimensions": [
                    {"name": "date"},
                    {"name": "eventName"}
                ],
                "metrics": [
                    {"name": metric_name}
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
                count_value = int(row["metricValues"][0]["value"])

                all_events.append({
                    "event_date": event_date,
                    "event_name": event_name_val,
                    "event_count": count_value  # 사용자 수 또는 이벤트 수
                })
                
                logging.info(f"   ✅ {event_date}: {event_name_val} = {count_value}{metric_label}")

        except Exception as e:
            logging.error(f"❌ {event_name} 이벤트 조회 실패: {e}")
            continue
    
    return all_events

# ✅ 메인 실행 함수
def main():
    """
    최근 7일간 파이시스의 장바구니(사용자 수)와 회원가입(이벤트 수) 이벤트 조회
    기본값: 파이시스만 조회
    """
    import sys
    
    now_kst = datetime.now(timezone.utc).astimezone(KST)
    end_date = now_kst.strftime("%Y-%m-%d")
    start_date = (now_kst - timedelta(days=6)).strftime("%Y-%m-%d")
    
    # 기본값: 파이시스만 조회
    company_filter = sys.argv[1] if len(sys.argv) > 1 else "piscess"
    
    logging.info(f"📅 조회 기간: {start_date} ~ {end_date} (최근 7일)")
    logging.info(f"🏢 조회 업체: {company_filter}")
    
    # GA4 Property ID 가져오기
    companies = get_company_ga4_property_ids(company_filter)
    if not companies:
        logging.error(f"❌ {company_filter} GA4 Property ID를 찾을 수 없습니다.")
        return
    
    all_events = []
    
    # 각 업체별로 이벤트 조회 (장바구니는 사용자 수, 회원가입은 이벤트 수)
    for company in companies:
        property_id = company['property_id']
        company_name = company['company_name']
        logging.info(f"\n🔄 {company_name} ({property_id}) 조회 중...")
        
        # 장바구니: 사용자 수로 조회
        cart_events = fetch_ga4_events(property_id, start_date, end_date, ["add_to_cart"], use_user_count=True)
        
        # 회원가입: 이벤트 수로 조회
        signup_events = fetch_ga4_events(property_id, start_date, end_date, ["sign_up"], use_user_count=False)
        
        # company_name 추가
        for event in cart_events + signup_events:
            event['company_name'] = company_name
        
        all_events.extend(cart_events + signup_events)
    
    if all_events:
        df = pd.DataFrame(all_events)
        logging.info("\n" + "="*50)
        logging.info("📊 조회 결과 요약")
        logging.info("="*50)
        
        # 날짜별, 이벤트별 집계
        summary = df.groupby(['event_date', 'event_name'])['event_count'].sum().reset_index()
        summary_pivot = summary.pivot(index='event_date', columns='event_name', values='event_count').fillna(0)
        
        logging.info(f"\n[{company_filter}] 날짜별 이벤트 발생:")
        logging.info("  (add_to_cart: 사용자 수, sign_up: 이벤트 수)")
        logging.info(summary_pivot.to_string())
        
        # 전체 합계
        total_summary = df.groupby('event_name')['event_count'].sum()
        logging.info("\n전체 합계:")
        for event_name, total in total_summary.items():
            if event_name == "add_to_cart":
                logging.info(f"  {event_name}: {int(total)}명 (사용자 수)")
            else:
                logging.info(f"  {event_name}: {int(total)}건 (이벤트 수)")
    else:
        logging.info("⚠️ 조회된 이벤트 데이터가 없습니다.")
    
    logging.info("\n🎉 테스트 완료!")

if __name__ == "__main__":
    main()

