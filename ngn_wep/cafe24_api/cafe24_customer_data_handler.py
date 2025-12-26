# File: ngn_wep/cafe24_api/cafe24_customer_data_handler.py
# 테스트용 회원/고객 데이터 수집 핸들러

import os
import json
import requests
from google.cloud import storage  # BigQuery 제거
from datetime import datetime, timedelta, timezone
import logging

# ✅ 한국 시간대 설정
KST = timezone(timedelta(hours=9))
current_time = datetime.now(timezone.utc).astimezone(KST)

# ✅ 로깅 설정
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ✅ GCP 설정 (테스트용 - BigQuery 전송 제거됨)
BUCKET_NAME = "winged-precept-443218-v8.appspot.com"
TOKEN_FILE_NAME = "tokens.json"

# ✅ 안전한 데이터 변환 함수
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

# ✅ 토큰 다운로드 함수
def download_tokens():
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(TOKEN_FILE_NAME)

    try:
        token_data = blob.download_as_text()
        tokens = json.loads(token_data)
        if isinstance(tokens, list):
            logging.info(f"{TOKEN_FILE_NAME} 파일 다운로드 성공 (리스트 형태)")
            return tokens
        else:
            raise ValueError("토큰 파일의 JSON 구조가 [list]가 아닙니다.")
    except Exception as e:
        logging.error(f"토큰 다운로드 실패: {e}")
        return []

# ✅ Mall ID 기준으로 Token 찾는 함수
def get_token_info(mall_id):
    tokens_list = download_tokens()
    for token in tokens_list:
        if token.get("mall_id") == mall_id:
            return token
    return None

# ✅ 날짜 형식 변환
def parse_date(date_value):
    try:
        if date_value:
            # ISO8601 형식 변환
            if isinstance(date_value, str):
                if 'T' in date_value:
                    return datetime.fromisoformat(date_value.replace('Z', '+00:00')).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                else:
                    return datetime.strptime(date_value, "%Y-%m-%d").strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    except (ValueError, AttributeError) as e:
        logging.warning(f"날짜 변환 실패: {date_value}, 오류: {e}")
    return None

# ✅ 회원/고객 데이터 가져오기
def fetch_customer_data(mall_id, start_date, end_date):
    """
    카페24 회원/고객 API 호출
    API 엔드포인트: GET /api/v2/admin/customers
    파라미터: join_start_date, join_end_date (YYYY-MM-DD 형식)
    응답: {"count": 가입자수, "customers": [...]}
    """
    token_info = get_token_info(mall_id)
    if not token_info:
        logging.warning(f"{mall_id} - 토큰 정보 누락")
        return []

    access_token = token_info["access_token"]
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    
    # 카페24 회원 목록 조회 API
    # 엔드포인트: GET /api/v2/admin/customers
    # 파라미터: join_start_date, join_end_date (YYYY-MM-DD 형식)
    # 응답: count (가입자 수), customers (회원 목록)
    url = f"https://{mall_id}.cafe24api.com/api/v2/admin/customers"
    
    all_customers = []
    offset = 0

    while True:
        # 카페24 회원 목록 조회 파라미터
        # join_start_date, join_end_date: 회원가입일 기준 (YYYY-MM-DD 형식)
        params = {
            "join_start_date": start_date,  # YYYY-MM-DD 형식
            "join_end_date": end_date,      # YYYY-MM-DD 형식
            "limit": 100,
            "offset": offset
        }

        try:
            logging.info(f"{mall_id} - API 요청: {url}")
            logging.info(f"{mall_id} - 요청 파라미터: {params}")
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code != 200:
                logging.error(f"❌ {mall_id} - API 요청 실패")
                logging.error(f"   Status Code: {response.status_code}")
                logging.error(f"   URL: {url}")
                logging.error(f"   Headers: {dict(headers)}")
                logging.error(f"   Params: {params}")
                logging.error(f"   Response Text: {response.text}")
                logging.error(f"   Response Headers: {dict(response.headers)}")
                
                # 422 에러: 파라미터 문제
                if response.status_code == 422:
                    error_data = response.json().get("error", {})
                    logging.error(f"   💡 422 에러: 파라미터가 올바르지 않습니다.")
                    logging.error(f"   💡 에러 메시지: {error_data.get('message', 'N/A')}")
                    logging.error(f"   💡 현재 엔드포인트: {url}")
                    logging.error(f"   💡 요청 파라미터: {params}")
                    logging.error(f"   💡 올바른 파라미터: join_start_date, join_end_date (YYYY-MM-DD 형식)")
                    logging.error(f"   💡 예시: ?join_start_date=2024-12-23&join_end_date=2024-12-23")
                # 404 에러인 경우 다른 엔드포인트 시도 안내
                elif response.status_code == 404:
                    logging.error(f"   💡 404 에러: 이 엔드포인트가 존재하지 않을 수 있습니다.")
                    logging.error(f"   💡 다른 가능한 엔드포인트:")
                    logging.error(f"      - /api/v2/admin/members")
                    logging.error(f"      - /api/v2/admin/customers/list")
                
                break

            # 카페24 API 응답 구조: { "count": 숫자, "customers": [...] }
            data = response.json()
            
            # 응답 구조 디버깅을 위한 로그
            total_count = data.get("count", 0)  # 해당 기간의 총 가입자 수
            customers = data.get("customers", [])
            
            if offset == 0:  # 첫 요청에서만 총 개수 로그 출력
                logging.info(f"{mall_id} - {start_date} ~ {end_date} 기간 총 가입자 수: {total_count}명")
            
            if not customers:
                if offset == 0:  # 첫 요청에서 데이터가 없으면 실제로 없는 것
                    logging.info(f"{mall_id} - {start_date} ~ {end_date} 기간에 가입한 회원이 없습니다.")
                break

            for customer in customers:
                try:
                    # TODO: 실제 API 응답 필드에 맞게 수정 필요
                    all_customers.append({
                        "mall_id": mall_id,
                        "customer_id": customer.get("customer_id") or customer.get("member_id"),
                        "member_id": customer.get("member_id") or customer.get("customer_id"),
                        "email": customer.get("email"),
                        "name": customer.get("name") or customer.get("customer_name"),
                        "phone": customer.get("phone") or customer.get("phone_number"),
                        "created_date": parse_date(customer.get("created_date") or customer.get("join_date") or customer.get("register_date")),
                        "last_login_date": parse_date(customer.get("last_login_date") or customer.get("last_login")),
                        "grade": customer.get("grade") or customer.get("member_grade"),
                        "status": customer.get("status") or customer.get("member_status"),
                        "total_order_count": safe_int(customer.get("total_order_count") or customer.get("order_count")),
                        "total_order_amount": safe_float(customer.get("total_order_amount") or customer.get("order_amount")),
                        "birth_date": parse_date(customer.get("birth_date") or customer.get("birthday")),
                        "gender": customer.get("gender"),
                        "postcode": customer.get("postcode") or customer.get("zipcode"),
                        "address": customer.get("address"),
                        "address_detail": customer.get("address_detail") or customer.get("address2"),
                    })
                except Exception as e:
                    logging.warning(f"{mall_id} - 회원 데이터 파싱 실패: {e}, 데이터: {customer}")
                    continue

            offset += len(customers)
            
            # 더 이상 데이터가 없으면 종료
            if len(customers) < params["limit"]:
                break
                
        except requests.exceptions.RequestException as e:
            logging.error(f"❌ {mall_id} - API 요청 중 네트워크 오류")
            logging.error(f"   URL: {url}")
            logging.error(f"   오류 타입: {type(e).__name__}")
            logging.error(f"   오류 메시지: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logging.error(f"   Response Status: {e.response.status_code}")
                logging.error(f"   Response Text: {e.response.text}")
            break
        except json.JSONDecodeError as e:
            logging.error(f"❌ {mall_id} - JSON 파싱 오류")
            logging.error(f"   URL: {url}")
            logging.error(f"   Response Text (첫 500자): {response.text[:500] if 'response' in locals() else 'N/A'}")
            logging.error(f"   오류: {str(e)}")
            break
        except Exception as e:
            logging.error(f"❌ {mall_id} - 예상치 못한 오류")
            logging.error(f"   URL: {url}")
            logging.error(f"   오류 타입: {type(e).__name__}")
            logging.error(f"   오류 메시지: {str(e)}")
            import traceback
            logging.error(f"   Traceback: {traceback.format_exc()}")
            break

    logging.info(f"{mall_id} - {len(all_customers)}건의 회원 데이터 수집 완료")
    return all_customers

# 테스트 코드이므로 BigQuery 업로드 기능 제거

# ✅ 메인 실행 함수 (테스트용)
def main():
    """
    테스트용 메인 함수
    기본값: 최근 7일간 데이터 수집
    사용법: python cafe24_customer_data_handler.py [start_date] [end_date]
    예시: python cafe24_customer_data_handler.py 2025-12-20 2025-12-23
    """
    import sys
    
    if len(sys.argv) >= 3:
        start_date = sys.argv[1]
        end_date = sys.argv[2]
    else:
        # 기본값: 최근 7일간
        start_date = (current_time - timedelta(days=6)).strftime("%Y-%m-%d")
        end_date = current_time.strftime("%Y-%m-%d")

    logging.info(f"📅 회원 데이터 수집 기간: {start_date} ~ {end_date} (최근 7일)")

    tokens_list = download_tokens()
    mall_ids = [t["mall_id"] for t in tokens_list if "mall_id" in t]
    
    logging.info(f"🔍 총 {len(mall_ids)}개 몰 ID 발견: {mall_ids}")

    # 각 mall_id로 회원 데이터 수집 (테스트용 - BigQuery 전송 없음)
    for mall_id in mall_ids:
        logging.info(f"🔄 {mall_id} - 회원 데이터 수집 시작")
        try:
            customers_data = fetch_customer_data(mall_id, start_date, end_date)
            if customers_data:
                logging.info(f"✅ {mall_id} - {len(customers_data)}건의 회원 데이터 수집 완료")
                # 테스트용: 첫 번째 회원 데이터 샘플 출력
                if customers_data:
                    logging.info(f"📋 {mall_id} - 첫 번째 회원 데이터 샘플: {customers_data[0]}")
            else:
                logging.info(f"{mall_id} - 수집된 데이터 없음")
        except Exception as e:
            logging.error(f"{mall_id} - 데이터 수집 중 오류: {e}")
    
    logging.info("🎉 테스트 완료 (BigQuery 전송 기능 제거됨)")

if __name__ == "__main__":
    main()

