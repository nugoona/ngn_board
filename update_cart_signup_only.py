#!/usr/bin/env python3
"""
장바구니 사용자 수와 회원가입 수만 수집하여 performance_summary_ngn 테이블 업데이트
사용법: python update_cart_signup_only.py 2024-12-01 2025-12-25

실행 위치: 프로젝트 루트 (ngn_board)에서 실행
"""
import sys
from datetime import datetime, timedelta, timezone
from google.cloud import bigquery
from googleapiclient.discovery import build
import os

# ✅ 환경변수 기반 프로젝트 설정
PROJECT_ID = os.getenv("PROJECT_ID", "winged-precept-443218-v8")
DATASET_ID = os.getenv("DATASET_ID", "ngn_dataset")
TABLE_ID = os.getenv("TABLE_ID", "performance_summary_ngn")

def get_bq_client():
    return bigquery.Client()

# ✅ GA4 API 클라이언트 초기화 (ADC 사용)
analytics = build("analyticsdata", "v1beta")

def get_ga4_property_ids_by_company(company_name, client):
    """company_info 테이블에서 특정 업체의 GA4 Property ID 조회"""
    query = f"""
    SELECT ga4_property_id
    FROM `{PROJECT_ID}.{DATASET_ID}.company_info`
    WHERE LOWER(company_name) = LOWER('{company_name}')
      AND ga4_property_id IS NOT NULL
      AND ga4_property_id >= 10000
    LIMIT 1
    """
    try:
        query_job = client.query(query)
        results = query_job.result()
        for row in results:
            return row.ga4_property_id
        return None
    except Exception as e:
        print(f"[WARN] GA4 Property ID 조회 실패 ({company_name}): {e}")
        return None

def fetch_ga4_cart_signup_data(property_id, target_date_str):
    """
    GA4 API에서 장바구니 사용자 수와 회원가입 수 조회
    
    Args:
        property_id: GA4 Property ID
        target_date_str: 날짜 문자열 (YYYY-MM-DD)
    
    Returns:
        dict: {'cart_users': int, 'signup_count': int}
    """
    result = {'cart_users': 0, 'signup_count': 0}
    
    if not property_id:
        return result
    
    try:
        # 장바구니 사용자 수 조회 (totalUsers 메트릭)
        cart_request = {
            "dateRanges": [{"startDate": target_date_str, "endDate": target_date_str}],
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
        
        cart_response = analytics.properties().runReport(
            property=f"properties/{property_id}", body=cart_request
        ).execute()
        
        for row in cart_response.get("rows", []):
            result['cart_users'] += int(row["metricValues"][0]["value"])
        
        # 회원가입 수 조회 (eventCount 메트릭)
        signup_request = {
            "dateRanges": [{"startDate": target_date_str, "endDate": target_date_str}],
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
        
        signup_response = analytics.properties().runReport(
            property=f"properties/{property_id}", body=signup_request
        ).execute()
        
        for row in signup_response.get("rows", []):
            result['signup_count'] += int(row["metricValues"][0]["value"])
            
    except Exception as e:
        error_msg = str(e)
        error_type = type(e).__name__
        print(f"[WARN] GA4 장바구니/회원가입 데이터 조회 실패 (property_id={property_id}, date={target_date_str})")
        print(f"[WARN] 오류 타입: {error_type}")
        print(f"[WARN] 오류 메시지: {error_msg}")
        
        # HTTP 오류 상세 정보
        if hasattr(e, 'status_code'):
            print(f"[WARN] HTTP 상태 코드: {e.status_code}")
        if hasattr(e, 'content'):
            try:
                import json
                error_content = json.loads(e.content) if isinstance(e.content, (str, bytes)) else e.content
                print(f"[WARN] 오류 상세: {error_content}")
            except:
                print(f"[WARN] 오류 내용 (원문): {e.content}")
        
        sys.stdout.flush()
        # 오류 발생 시 0 반환
        return result
    
    return result

def update_cart_signup_for_date(target_date, client):
    """특정 날짜에 대해 performance_summary_ngn 테이블의 장바구니/회원가입 데이터만 업데이트"""
    date_str = target_date.strftime("%Y-%m-%d")
    
    print(f"[INFO] {date_str} 처리 중...")
    sys.stdout.flush()
    
    # 해당 날짜의 업체 목록 조회 (performance_summary_ngn 테이블에서)
    company_query = f"""
    SELECT DISTINCT company_name
    FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
    WHERE DATE(date) = DATE('{date_str}')
    """
    
    try:
        companies = [row.company_name for row in client.query(company_query).result()]
    except Exception as e:
        print(f"[WARN] {date_str}: 업체 목록 조회 실패: {e}")
        return
    
    if not companies:
        print(f"[INFO] {date_str}: performance_summary_ngn 테이블에 데이터가 없습니다. insert_performance_summary.py를 먼저 실행하여 기본 데이터를 생성해주세요.")
        return
    
    updated_count = 0
    for company_name in companies:
        property_id = get_ga4_property_ids_by_company(company_name, client)
        if property_id:
            cart_signup_data = fetch_ga4_cart_signup_data(property_id, date_str)
            
            # UPDATE 쿼리 실행
            update_query = f"""
            UPDATE `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
            SET 
              cart_users = @cart_users,
              signup_count = @signup_count
            WHERE company_name = @company_name
              AND DATE(date) = DATE(@target_date)
            """
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("cart_users", "INTEGER", cart_signup_data['cart_users']),
                    bigquery.ScalarQueryParameter("signup_count", "INTEGER", cart_signup_data['signup_count']),
                    bigquery.ScalarQueryParameter("company_name", "STRING", company_name),
                    bigquery.ScalarQueryParameter("target_date", "DATE", date_str)
                ]
            )
            
            try:
                client.query(update_query, job_config=job_config).result()
                print(f"[INFO] {date_str} {company_name}: 장바구니={cart_signup_data['cart_users']}명, 회원가입={cart_signup_data['signup_count']}건 업데이트 완료")
                sys.stdout.flush()
                updated_count += 1
            except Exception as e:
                print(f"[ERROR] {date_str} {company_name}: 업데이트 실패: {e}")
                sys.stdout.flush()
        else:
            print(f"[WARN] {date_str} {company_name}: GA4 Property ID를 찾을 수 없습니다.")
            sys.stdout.flush()
    
    print(f"[SUCCESS] {date_str}: {updated_count}개 업체 업데이트 완료")
    sys.stdout.flush()

def main():
    if len(sys.argv) < 3:
        print("사용법: python update_cart_signup_only.py <시작일> <종료일>")
        print("예시: python update_cart_signup_only.py 2024-12-01 2025-12-25")
        sys.exit(1)
    
    try:
        start_date = datetime.strptime(sys.argv[1], '%Y-%m-%d').date()
        end_date = datetime.strptime(sys.argv[2], '%Y-%m-%d').date()
    except ValueError as e:
        print(f"❌ 날짜 형식 오류: {e}")
        print("날짜 형식은 YYYY-MM-DD여야 합니다.")
        sys.exit(1)
    
    if start_date > end_date:
        print("❌ 시작일이 종료일보다 늦을 수 없습니다.")
        sys.exit(1)
    
    client = get_bq_client()
    
    current_date = start_date
    total_days = (end_date - start_date).days + 1
    current_day = 0
    success_count = 0
    fail_count = 0
    
    print("="*50)
    print(f"장바구니/회원가입 데이터 업데이트 시작")
    print(f"기간: {start_date} ~ {end_date}")
    print(f"총 {total_days}일치")
    print("="*50)
    
    while current_date <= end_date:
        current_day += 1
        date_str = current_date.strftime('%Y-%m-%d')
        print(f"\n[{current_day}/{total_days}] {date_str} 처리 중...")
        
        try:
            update_cart_signup_for_date(current_date, client)
            success_count += 1
            print(f"✅ {date_str} 완료")
        except Exception as e:
            print(f"❌ {date_str} 실패: {e}")
            import traceback
            traceback.print_exc()
            fail_count += 1
        
        current_date += timedelta(days=1)
    
    print("\n" + "="*50)
    print(f"업데이트 완료")
    print(f"  성공: {success_count}일")
    print(f"  실패: {fail_count}일")
    print(f"  전체: {total_days}일")
    print("="*50)

if __name__ == "__main__":
    main()

