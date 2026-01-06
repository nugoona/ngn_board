"""
Cafe24 토큰 갱신 핸들러
- Secret Manager에서 토큰 관리
- GCS 폴백 지원 (마이그레이션 기간)
- 갱신 실패 시 슬랙 알림
"""
import os
import sys
import json
import requests
import logging
from base64 import b64encode
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor
from tenacity import retry, stop_after_attempt, wait_fixed
import pytz

# 프로젝트 루트를 경로에 추가 (상대 import 지원)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 로깅 설정
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# KST 시간대
KST = timezone(timedelta(hours=9))

# 환경 변수 설정
BUCKET_NAME = os.getenv("BUCKET_NAME", "winged-precept-443218-v8.appspot.com")
TOKEN_FILE_NAME = "tokens.json"
LOCAL_TOKEN_PATH = "/app/tokens.json" if os.getenv("CLOUD_ENV") else os.path.join(os.getcwd(), TOKEN_FILE_NAME)

# 토큰 저장소 모드: "secret_manager" 또는 "gcs"
TOKEN_STORAGE_MODE = os.getenv("TOKEN_STORAGE_MODE", "secret_manager")

# 강제 갱신 모드
FORCE_REFRESH = True

# 갱신 실패 목록 (슬랙 알림용)
failed_refreshes = []


# ============================================================
# 슬랙 알림 함수 (직접 구현 - 독립 실행 지원)
# ============================================================
SLACK_WEBHOOK_URL = os.getenv(
    "SLACK_WEBHOOK_URL",
    "https://hooks.slack.com/services/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"
)


def send_slack_alert(mall_id: str, error_message: str) -> bool:
    """토큰 갱신 실패 슬랙 알림 전송"""
    if not SLACK_WEBHOOK_URL:
        logging.warning("슬랙 웹훅 URL이 설정되지 않았습니다.")
        return False

    now_kst = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST")

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": ":red_circle: Cafe24 토큰 갱신 실패",
                "emoji": True
            }
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Mall ID:*\n{mall_id}"},
                {"type": "mrkdwn", "text": f"*발생 시간:*\n{now_kst}"}
            ]
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*에러 메시지:*\n```{error_message}```"
            }
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": ":gear: *조치 필요:* Cafe24 관리자에서 토큰을 재발급하거나, Secret Manager의 토큰 정보를 확인하세요."
                }
            ]
        }
    ]

    payload = {
        "text": f"[ERROR] Cafe24 토큰 갱신 실패 - {mall_id}",
        "blocks": blocks
    }

    try:
        response = requests.post(
            SLACK_WEBHOOK_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        if response.status_code == 200:
            logging.info(f"슬랙 알림 전송 성공: {mall_id}")
            return True
        else:
            logging.error(f"슬랙 알림 전송 실패: {response.status_code}")
            return False
    except Exception as e:
        logging.error(f"슬랙 알림 전송 중 오류: {e}")
        return False


def send_slack_summary(total: int, success: int, failed: int, failed_malls: list) -> bool:
    """갱신 결과 요약 슬랙 알림"""
    if not SLACK_WEBHOOK_URL:
        return False

    now_kst = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST")
    status_emoji = ":white_check_mark:" if failed == 0 else ":warning:"

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{status_emoji} Cafe24 토큰 갱신 완료",
                "emoji": True
            }
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*전체:*\n{total}개"},
                {"type": "mrkdwn", "text": f"*성공:*\n{success}개"},
                {"type": "mrkdwn", "text": f"*실패:*\n{failed}개"},
                {"type": "mrkdwn", "text": f"*완료 시간:*\n{now_kst}"}
            ]
        }
    ]

    if failed_malls:
        failed_list = ", ".join(failed_malls[:5])
        if len(failed_malls) > 5:
            failed_list += f" 외 {len(failed_malls) - 5}개"
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*실패한 몰:*\n{failed_list}"
            }
        })

    payload = {
        "text": f"Cafe24 토큰 갱신 완료 - 성공 {success}/{total}",
        "blocks": blocks
    }

    try:
        response = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
        return response.status_code == 200
    except Exception:
        return False


# ============================================================
# Secret Manager 토큰 관리
# ============================================================

def download_tokens_from_secret_manager() -> list:
    """Secret Manager에서 토큰 다운로드"""
    try:
        from google.cloud import secretmanager
        from google.api_core import exceptions as gcp_exceptions

        client = secretmanager.SecretManagerServiceClient()
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "winged-precept-443218-v8")
        secret_id = "cafe24-tokens"

        name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"

        response = client.access_secret_version(request={"name": name})
        secret_value = response.payload.data.decode("UTF-8")
        tokens = json.loads(secret_value)

        logging.info(f"Secret Manager에서 {len(tokens)}개 토큰 로드 성공")
        return tokens

    except gcp_exceptions.NotFound:
        logging.warning("Secret Manager에 cafe24-tokens 시크릿이 없습니다. GCS 폴백 시도...")
        return None
    except Exception as e:
        logging.error(f"Secret Manager 토큰 로드 실패: {e}")
        return None


def upload_tokens_to_secret_manager(tokens: list) -> bool:
    """Secret Manager에 토큰 업로드"""
    try:
        from google.cloud import secretmanager
        from google.api_core import exceptions as gcp_exceptions

        client = secretmanager.SecretManagerServiceClient()
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "winged-precept-443218-v8")
        secret_id = "cafe24-tokens"
        parent = f"projects/{project_id}"
        secret_name = f"{parent}/secrets/{secret_id}"

        # 시크릿 존재 여부 확인
        try:
            client.get_secret(request={"name": secret_name})
        except gcp_exceptions.NotFound:
            # 시크릿 생성
            client.create_secret(
                request={
                    "parent": parent,
                    "secret_id": secret_id,
                    "secret": {"replication": {"automatic": {}}}
                }
            )
            logging.info("cafe24-tokens 시크릿 생성됨")

        # 새 버전 추가
        secret_value = json.dumps(tokens, ensure_ascii=False, indent=2)
        client.add_secret_version(
            request={
                "parent": secret_name,
                "payload": {"data": secret_value.encode("UTF-8")}
            }
        )

        logging.info("Secret Manager에 토큰 업로드 성공")
        return True

    except Exception as e:
        logging.error(f"Secret Manager 토큰 업로드 실패: {e}")
        return False


# ============================================================
# GCS 토큰 관리 (폴백용)
# ============================================================

def download_tokens_from_gcs() -> list:
    """GCS에서 토큰 다운로드 (폴백)"""
    from google.cloud import storage

    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(TOKEN_FILE_NAME)

    try:
        if os.path.exists(LOCAL_TOKEN_PATH):
            os.remove(LOCAL_TOKEN_PATH)

        blob.download_to_filename(LOCAL_TOKEN_PATH)
        logging.info(f"GCS에서 {TOKEN_FILE_NAME} 다운로드 완료")

        with open(LOCAL_TOKEN_PATH, "r") as file:
            return json.load(file)
    except Exception as e:
        logging.error(f"GCS 토큰 다운로드 실패: {e}")
        return []


def upload_tokens_to_gcs(tokens: list) -> bool:
    """GCS에 토큰 업로드 (폴백)"""
    from google.cloud import storage

    try:
        with open(LOCAL_TOKEN_PATH, "w") as file:
            json.dump(tokens, file, indent=4)

        storage_client = storage.Client()
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(TOKEN_FILE_NAME)
        blob.upload_from_filename(LOCAL_TOKEN_PATH)

        logging.info("GCS에 토큰 업로드 성공")
        return True
    except Exception as e:
        logging.error(f"GCS 토큰 업로드 실패: {e}")
        return False


# ============================================================
# 토큰 다운로드/업로드 통합 함수
# ============================================================

def download_tokens() -> list:
    """토큰 다운로드 (Secret Manager 우선, GCS 폴백)"""
    if TOKEN_STORAGE_MODE == "secret_manager":
        tokens = download_tokens_from_secret_manager()
        if tokens is not None:
            return tokens
        logging.warning("Secret Manager 실패, GCS 폴백...")

    return download_tokens_from_gcs()


def upload_tokens(tokens: list) -> bool:
    """토큰 업로드 (Secret Manager 우선, GCS 폴백)"""
    success = False

    if TOKEN_STORAGE_MODE == "secret_manager":
        success = upload_tokens_to_secret_manager(tokens)
        if success:
            # GCS에도 백업
            upload_tokens_to_gcs(tokens)
            return True

    return upload_tokens_to_gcs(tokens)


# ============================================================
# 토큰 갱신 로직
# ============================================================

@retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
def refresh_access_token(mall_id, client_id, client_secret, refresh_token):
    """Access Token 갱신 (재시도 로직 포함)"""
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
        response = requests.post(url, headers=headers, data=data, timeout=30)
        response.raise_for_status()
        logging.info(f"[{mall_id}] Access Token 갱신 성공!")
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"[{mall_id}] Access Token 갱신 실패: {e}")
        raise


def is_token_expired_soon(expires_at, buffer_minutes=5):
    """토큰 만료 임박 여부 확인"""
    if FORCE_REFRESH:
        logging.info("토큰 강제 갱신 모드 활성화됨.")
        return True

    try:
        kst = pytz.timezone("Asia/Seoul")
        expiry_time = datetime.fromisoformat(expires_at).replace(tzinfo=timezone.utc).astimezone(kst)
        current_time = datetime.now(timezone.utc).astimezone(kst)

        logging.info(f"현재 시간(KST): {current_time}, 만료 시간(KST): {expiry_time}")
        return current_time >= (expiry_time - timedelta(minutes=buffer_minutes))
    except Exception as e:
        logging.warning(f"만료 시간 파싱 오류: {e}")
        return True


def process_mall_token(token_info):
    """개별 mall_id 토큰 갱신"""
    global failed_refreshes

    mall_id = token_info.get("mall_id")
    client_id = token_info.get("client_id")
    client_secret = token_info.get("client_secret")
    refresh_token = token_info.get("refresh_token")
    expires_at = token_info.get("expires_at")

    if not (mall_id and client_id and client_secret and refresh_token):
        logging.warning(f"[{mall_id}] 필수 정보 누락. 갱신 불가.")
        return False

    old_refresh_token = refresh_token

    try:
        updated_token = refresh_access_token(mall_id, client_id, client_secret, refresh_token)

        if updated_token:
            token_info["access_token"] = updated_token.get("access_token", "")
            token_info["expires_at"] = updated_token.get("expires_at", "")
            token_info["refresh_token"] = updated_token.get("refresh_token", refresh_token)

            logging.info(f"[{mall_id}] 토큰 갱신 성공")

            if token_info["refresh_token"] != old_refresh_token:
                logging.info(f"[{mall_id}] refresh_token 변경됨")

            return True

    except Exception as e:
        error_msg = str(e)
        logging.error(f"[{mall_id}] 토큰 갱신 실패: {error_msg}")

        # 실패 목록에 추가
        failed_refreshes.append({
            "mall_id": mall_id,
            "error": error_msg
        })

        # 슬랙 알림 전송
        send_slack_alert(mall_id, error_msg)

        return False


# ============================================================
# 메인 함수
# ============================================================

def main():
    global failed_refreshes
    failed_refreshes = []

    logging.info("=" * 60)
    logging.info("Cafe24 토큰 갱신 프로세스 시작")
    logging.info(f"토큰 저장소 모드: {TOKEN_STORAGE_MODE}")
    logging.info("=" * 60)

    tokens = download_tokens()

    if not tokens:
        logging.error("갱신할 토큰 정보가 없습니다.")
        send_slack_alert("ALL", "토큰 파일을 로드할 수 없습니다.")
        return

    total_count = len(tokens)
    success_count = 0

    # 병렬 처리
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(process_mall_token, tokens))
        success_count = sum(1 for r in results if r)

    # 토큰 저장
    upload_tokens(tokens)

    # 결과 요약
    failed_count = total_count - success_count
    failed_malls = [f["mall_id"] for f in failed_refreshes]

    logging.info("=" * 60)
    logging.info(f"토큰 갱신 완료: 성공 {success_count}/{total_count}, 실패 {failed_count}")
    logging.info("=" * 60)

    # 요약 슬랙 알림 전송
    send_slack_summary(total_count, success_count, failed_count, failed_malls)


if __name__ == "__main__":
    main()
