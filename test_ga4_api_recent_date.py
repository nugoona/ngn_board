#!/usr/bin/env python3
"""
GA4 API로 최근 날짜 데이터 조회 테스트
"""
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import os

# GA4 API 클라이언트 초기화
analytics = build("analyticsdata", "v1beta")

# 파이시스 GA4 Property ID
PROPERTY_ID = "443411644"  # piscess의 GA4 Property ID

def test_ga4_date(date_str):
    """특정 날짜의 GA4 데이터 조회 테스트"""
    print(f"\n{'='*50}")
    print(f"테스트 날짜: {date_str}")
    print(f"{'='*50}")
    
    try:
        # 장바구니 사용자 수 조회
        cart_request = {
            "dateRanges": [{"startDate": date_str, "endDate": date_str}],
            "dimensions": [{"name": "date"}],
            "metrics": [{"name": "totalUsers"}],
            "dimensionFilter": {
                "filter": {
                    "fieldName": "eventName",
                    "stringFilter": {
                        "matchType": "EXACT",
                        "value": "add_to_cart",
                        "caseSensitive": False
                    }
                }
            }
        }
        
        print(f"장바구니 데이터 조회 시도...")
        cart_response = analytics.properties().runReport(
            property=f"properties/{PROPERTY_ID}", body=cart_request
        ).execute()
        
        cart_count = 0
        for row in cart_response.get("rows", []):
            cart_count += int(row["metricValues"][0]["value"])
        
        print(f"✅ 장바구니 사용자 수: {cart_count}명")
        
        # 회원가입 수 조회
        signup_request = {
            "dateRanges": [{"startDate": date_str, "endDate": date_str}],
            "dimensions": [{"name": "date"}],
            "metrics": [{"name": "eventCount"}],
            "dimensionFilter": {
                "filter": {
                    "fieldName": "eventName",
                    "stringFilter": {
                        "matchType": "EXACT",
                        "value": "sign_up",
                        "caseSensitive": False
                    }
                }
            }
        }
        
        print(f"회원가입 데이터 조회 시도...")
        signup_response = analytics.properties().runReport(
            property=f"properties/{PROPERTY_ID}", body=signup_request
        ).execute()
        
        signup_count = 0
        for row in signup_response.get("rows", []):
            signup_count += int(row["metricValues"][0]["value"])
        
        print(f"✅ 회원가입 수: {signup_count}건")
        
        return True
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ 오류 발생: {error_msg}")
        print(f"오류 타입: {type(e).__name__}")
        
        # 오류 상세 정보
        if hasattr(e, 'content'):
            print(f"오류 내용: {e.content}")
        
        return False

def main():
    # 오늘 날짜부터 역순으로 7일 테스트
    today = datetime.now().date()
    print(f"현재 날짜: {today}")
    
    for i in range(7):
        test_date = today - timedelta(days=i)
        date_str = test_date.strftime('%Y-%m-%d')
        success = test_ga4_date(date_str)
        
        if not success:
            print(f"\n⚠️ {date_str}부터 GA4 API 조회가 실패합니다.")
            break
    
    # 특정 날짜들도 테스트
    test_dates = ['2025-12-25', '2025-12-01', '2025-08-02', '2025-08-01']
    print(f"\n{'='*50}")
    print("특정 날짜 테스트")
    print(f"{'='*50}")
    
    for date_str in test_dates:
        test_ga4_date(date_str)

if __name__ == "__main__":
    main()

