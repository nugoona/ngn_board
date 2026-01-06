"""
Cafe24 토큰 로더 모듈
- Secret Manager 우선, GCS 폴백
- 여러 핸들러에서 공통 사용
"""
import os
import json
import logging
from typing import Dict, List, Optional, Any

# 로깅 설정
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# 환경 변수 설정
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "winged-precept-443218-v8")
BUCKET_NAME = os.getenv("BUCKET_NAME", "winged-precept-443218-v8.appspot.com")
TOKEN_FILE_NAME = "tokens.json"
TOKEN_STORAGE_MODE = os.getenv("TOKEN_STORAGE_MODE", "secret_manager")
SECRET_ID = "cafe24-tokens"


def load_tokens_from_secret_manager() -> Optional[List[Dict[str, Any]]]:
    """Secret Manager에서 토큰 로드"""
    try:
        from google.cloud import secretmanager
        from google.api_core import exceptions as gcp_exceptions

        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{PROJECT_ID}/secrets/{SECRET_ID}/versions/latest"

        response = client.access_secret_version(request={"name": name})
        secret_value = response.payload.data.decode("UTF-8")
        tokens = json.loads(secret_value)

        logging.info(f"[TokenLoader] Secret Manager에서 {len(tokens)}개 토큰 로드")
        return tokens

    except Exception as e:
        logging.warning(f"[TokenLoader] Secret Manager 로드 실패: {e}")
        return None


def load_tokens_from_gcs() -> List[Dict[str, Any]]:
    """GCS에서 토큰 로드 (폴백)"""
    from google.cloud import storage

    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(TOKEN_FILE_NAME)

        token_data = blob.download_as_text()
        tokens = json.loads(token_data)

        logging.info(f"[TokenLoader] GCS에서 {len(tokens)}개 토큰 로드")
        return tokens

    except Exception as e:
        logging.error(f"[TokenLoader] GCS 로드 실패: {e}")
        return []


def load_tokens() -> List[Dict[str, Any]]:
    """
    토큰 로드 (Secret Manager 우선, GCS 폴백)

    Returns:
        토큰 리스트
    """
    if TOKEN_STORAGE_MODE == "secret_manager":
        tokens = load_tokens_from_secret_manager()
        if tokens is not None:
            return tokens
        logging.warning("[TokenLoader] Secret Manager 실패, GCS 폴백...")

    return load_tokens_from_gcs()


def load_tokens_as_dict() -> Dict[str, Dict[str, Any]]:
    """
    mall_id를 키로 하는 딕셔너리 형태로 토큰 반환

    Returns:
        {mall_id: token_info} 딕셔너리
    """
    tokens = load_tokens()
    return {t["mall_id"]: t for t in tokens if "mall_id" in t and "access_token" in t}


def get_token_by_mall_id(mall_id: str) -> Optional[Dict[str, Any]]:
    """
    특정 mall_id의 토큰 정보 반환

    Args:
        mall_id: 몰 ID

    Returns:
        토큰 정보 딕셔너리 또는 None
    """
    tokens = load_tokens_as_dict()
    return tokens.get(mall_id)


# 하위 호환성을 위한 별칭
download_tokens = load_tokens_as_dict
