import os
import json
import requests
from base64 import b64encode
from google.cloud import storage
from datetime import datetime, timezone, timedelta
import logging
from concurrent.futures import ThreadPoolExecutor
from tenacity import retry, stop_after_attempt, wait_fixed
import pytz

# 🔹 로깅 설정
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# 🔹 환경 변수 설정 (로컬/클라우드 환경 자동 감지)
BUCKET_NAME = os.getenv("BUCKET_NAME", "winged-precept-443218-v8.appspot.com")
TOKEN_FILE_NAME = "tokens.json"

# 🔹 실행 환경에 따른 파일 경로 설정 (Cloud Run & 로컬 테스트 모두 지원)
LOCAL_TOKEN_PATH = "/app/tokens.json" if os.getenv("CLOUD_ENV") else os.path.join(os.getcwd(), TOKEN_FILE_NAME)

# 🔹 강제 갱신 모드
FORCE_REFRESH = True  # 🚀 항상 강제 갱신 실행!

# 🔹 Cloud Storage에서 `tokens.json` 다운로드 및 로컬 저장 (항상 최신 다운로드)
def download_tokens():
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(TOKEN_FILE_NAME)

    try:
        # ✅ 기존 파일 삭제 (Cloud Run 실행 시 항상 최신 다운로드 보장)
        if os.path.exists(LOCAL_TOKEN_PATH):
            os.remove(LOCAL_TOKEN_PATH)

        blob.download_to_filename(LOCAL_TOKEN_PATH)
        logging.info(f"✅ {TOKEN_FILE_NAME} 파일이 GCP 버킷에서 다운로드됨: {LOCAL_TOKEN_PATH}")

        with open(LOCAL_TOKEN_PATH, "r") as file:
            return json.load(file)
    except Exception as e:
        logging.error(f"❌ 토큰 파일 다운로드 실패: {e}")
        return []

# 🔹 갱신된 토큰 정보를 Cloud Storage에 업로드
def upload_tokens(tokens):
    try:
        with open(LOCAL_TOKEN_PATH, "w") as file:
            json.dump(tokens, file, indent=4)

        storage_client = storage.Client()
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(TOKEN_FILE_NAME)

        # ✅ 업로드 전 변경 사항 로그 확인
        logging.info(f"📝 업로드 전 최신 토큰 데이터: {json.dumps(tokens, indent=4)}")

        blob.upload_from_filename(LOCAL_TOKEN_PATH)

        logging.info("✅ 토큰 정보가 Cloud Storage에 성공적으로 업데이트됨")
    except Exception as e:
        logging.error(f"❌ Cloud Storage에 토큰 저장 중 오류 발생: {e}")

# 🔹 Access Token 갱신 함수 (재시도 로직 포함)
@retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
def refresh_access_token(mall_id, client_id, client_secret, refresh_token):
    url = f"https://{mall_id}.cafe24api.com/api/v2/oauth/token"
    auth_str = f"{client_id}:{client_secret}"
    auth_header = b64encode(auth_str.encode()).decode()

    headers = {
        "Authorization": f"Basic {auth_header}",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }

    try:
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        logging.info(f"[{mall_id}] ✅ Access Token 갱신 성공!")
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"[{mall_id}] ❌ Access Token 갱신 실패: {e}")
        return None

# 🔹 토큰 유효성 확인 (강제 갱신 모드 포함)
def is_token_expired_soon(expires_at, buffer_minutes=5):
    if FORCE_REFRESH:
        logging.info("🚀 토큰 강제 갱신 모드 활성화됨.")
        return True

    try:
        # KST (Korea Standard Time) 변환
        kst = pytz.timezone("Asia/Seoul")
        expiry_time = datetime.fromisoformat(expires_at).replace(tzinfo=timezone.utc).astimezone(kst)
        current_time = datetime.now(timezone.utc).astimezone(kst)

        logging.info(f"⏳ 현재 시간(KST): {current_time}, 만료 시간(KST): {expiry_time}")
        return current_time >= (expiry_time - timedelta(minutes=buffer_minutes))
    except Exception as e:
        logging.warning(f"⚠️ 만료 시간 파싱 중 오류 발생: {e}")
        return True

# 🔹 개별 mall_id 토큰 갱신 작업
def process_mall_token(token_info):
    mall_id = token_info.get("mall_id")
    client_id = token_info.get("client_id")
    client_secret = token_info.get("client_secret")
    refresh_token = token_info.get("refresh_token")
    expires_at = token_info.get("expires_at")

    if not (mall_id and client_id and client_secret and refresh_token):
        logging.warning(f"[{mall_id}] ⚠️ 필수 정보 누락. 갱신 불가.")
        return

    # ✅ 기존 refresh_token 저장 (비교용)
    old_refresh_token = refresh_token

    updated_token = refresh_access_token(mall_id, client_id, client_secret, refresh_token)
    if updated_token:
        token_info["access_token"] = updated_token.get("access_token", "")
        token_info["expires_at"] = updated_token.get("expires_at", "")
        token_info["refresh_token"] = updated_token.get("refresh_token", refresh_token)

        logging.info(f"[{mall_id}] ✅ 토큰이 성공적으로 갱신되었습니다.")

        # ✅ refresh_token 변경 여부 확인
        if token_info["refresh_token"] != old_refresh_token:
            logging.info(f"[{mall_id}] 🔄 refresh_token 변경됨: {old_refresh_token} → {token_info['refresh_token']}")
        else:
            logging.warning(f"[{mall_id}] ⚠️ refresh_token이 변경되지 않음! 다시 확인 필요.")

    else:
        logging.error(f"[{mall_id}] ❌ 토큰 갱신에 실패하였습니다.")

# 🔹 메인 실행 함수
def main():
    logging.info("🚀 토큰 갱신 프로세스를 시작합니다.")
    tokens = download_tokens()
    
    if not tokens:
        logging.error("❌ 갱신할 토큰 정보가 없습니다.")
        return

    with ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(process_mall_token, tokens)

    upload_tokens(tokens)
    logging.info("✅ 토큰 갱신 프로세스 완료.")

if __name__ == "__main__":
    main()

