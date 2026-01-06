"""
GCP Secret Manager 유틸리티 모듈
- 토큰 및 민감 정보 안전하게 관리
- GCS 대신 Secret Manager에서 토큰 읽기/쓰기
"""
import os
import json
import logging
from typing import Optional, Dict, List, Any
from google.cloud import secretmanager
from google.api_core import exceptions as gcp_exceptions

# 로깅 설정
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# 프로젝트 설정
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "winged-precept-443218-v8")

# Secret Manager 클라이언트 (싱글톤)
_sm_client = None


def get_secret_manager_client() -> secretmanager.SecretManagerServiceClient:
    """Secret Manager 클라이언트 싱글톤 반환"""
    global _sm_client
    if _sm_client is None:
        _sm_client = secretmanager.SecretManagerServiceClient()
    return _sm_client


def get_secret(
    secret_id: str,
    version: str = "latest",
    project_id: str = None
) -> Optional[str]:
    """
    Secret Manager에서 시크릿 값 가져오기

    Args:
        secret_id: 시크릿 ID
        version: 버전 (기본값: "latest")
        project_id: 프로젝트 ID (기본값: 환경변수)

    Returns:
        시크릿 값 (문자열) 또는 None
    """
    project = project_id or PROJECT_ID
    client = get_secret_manager_client()

    name = f"projects/{project}/secrets/{secret_id}/versions/{version}"

    try:
        response = client.access_secret_version(request={"name": name})
        secret_value = response.payload.data.decode("UTF-8")
        logging.info(f"시크릿 '{secret_id}' 로드 성공")
        return secret_value
    except gcp_exceptions.NotFound:
        logging.warning(f"시크릿 '{secret_id}'을(를) 찾을 수 없습니다.")
        return None
    except gcp_exceptions.PermissionDenied:
        logging.error(f"시크릿 '{secret_id}' 접근 권한이 없습니다.")
        return None
    except Exception as e:
        logging.error(f"시크릿 '{secret_id}' 로드 중 오류: {e}")
        return None


def get_secret_json(
    secret_id: str,
    version: str = "latest",
    project_id: str = None
) -> Optional[Dict[str, Any]]:
    """
    Secret Manager에서 JSON 형식 시크릿 가져오기

    Args:
        secret_id: 시크릿 ID
        version: 버전
        project_id: 프로젝트 ID

    Returns:
        파싱된 JSON 딕셔너리 또는 None
    """
    secret_value = get_secret(secret_id, version, project_id)
    if secret_value:
        try:
            return json.loads(secret_value)
        except json.JSONDecodeError as e:
            logging.error(f"시크릿 '{secret_id}' JSON 파싱 실패: {e}")
            return None
    return None


def create_or_update_secret(
    secret_id: str,
    secret_value: str,
    project_id: str = None
) -> bool:
    """
    시크릿 생성 또는 새 버전 추가

    Args:
        secret_id: 시크릿 ID
        secret_value: 시크릿 값
        project_id: 프로젝트 ID

    Returns:
        성공 여부
    """
    project = project_id or PROJECT_ID
    client = get_secret_manager_client()
    parent = f"projects/{project}"
    secret_name = f"{parent}/secrets/{secret_id}"

    try:
        # 시크릿 존재 여부 확인
        try:
            client.get_secret(request={"name": secret_name})
            secret_exists = True
        except gcp_exceptions.NotFound:
            secret_exists = False

        # 시크릿이 없으면 생성
        if not secret_exists:
            client.create_secret(
                request={
                    "parent": parent,
                    "secret_id": secret_id,
                    "secret": {
                        "replication": {"automatic": {}}
                    }
                }
            )
            logging.info(f"시크릿 '{secret_id}' 생성됨")

        # 새 버전 추가
        client.add_secret_version(
            request={
                "parent": secret_name,
                "payload": {"data": secret_value.encode("UTF-8")}
            }
        )
        logging.info(f"시크릿 '{secret_id}' 새 버전 추가됨")
        return True

    except Exception as e:
        logging.error(f"시크릿 '{secret_id}' 생성/업데이트 실패: {e}")
        return False


def create_or_update_secret_json(
    secret_id: str,
    secret_data: Dict[str, Any],
    project_id: str = None
) -> bool:
    """
    JSON 형식으로 시크릿 생성/업데이트

    Args:
        secret_id: 시크릿 ID
        secret_data: JSON으로 변환할 딕셔너리
        project_id: 프로젝트 ID

    Returns:
        성공 여부
    """
    try:
        secret_value = json.dumps(secret_data, ensure_ascii=False, indent=2)
        return create_or_update_secret(secret_id, secret_value, project_id)
    except json.JSONEncodeError as e:
        logging.error(f"JSON 직렬화 실패: {e}")
        return False


def list_secrets(project_id: str = None) -> List[str]:
    """
    프로젝트의 모든 시크릿 목록 조회

    Args:
        project_id: 프로젝트 ID

    Returns:
        시크릿 ID 목록
    """
    project = project_id or PROJECT_ID
    client = get_secret_manager_client()
    parent = f"projects/{project}"

    try:
        secrets = client.list_secrets(request={"parent": parent})
        return [s.name.split("/")[-1] for s in secrets]
    except Exception as e:
        logging.error(f"시크릿 목록 조회 실패: {e}")
        return []


def delete_secret(secret_id: str, project_id: str = None) -> bool:
    """
    시크릿 삭제

    Args:
        secret_id: 시크릿 ID
        project_id: 프로젝트 ID

    Returns:
        성공 여부
    """
    project = project_id or PROJECT_ID
    client = get_secret_manager_client()
    secret_name = f"projects/{project}/secrets/{secret_id}"

    try:
        client.delete_secret(request={"name": secret_name})
        logging.info(f"시크릿 '{secret_id}' 삭제됨")
        return True
    except gcp_exceptions.NotFound:
        logging.warning(f"시크릿 '{secret_id}'이(가) 존재하지 않습니다.")
        return True
    except Exception as e:
        logging.error(f"시크릿 '{secret_id}' 삭제 실패: {e}")
        return False


# ============================================================
# Cafe24 토큰 전용 함수
# ============================================================

CAFE24_TOKENS_SECRET_ID = "cafe24-tokens"


def get_cafe24_tokens() -> List[Dict[str, Any]]:
    """
    Secret Manager에서 Cafe24 토큰 목록 가져오기

    Returns:
        토큰 정보 리스트
    """
    tokens = get_secret_json(CAFE24_TOKENS_SECRET_ID)
    if tokens is None:
        logging.warning("Cafe24 토큰을 Secret Manager에서 찾을 수 없습니다.")
        return []

    # 리스트인지 확인
    if isinstance(tokens, list):
        return tokens
    elif isinstance(tokens, dict) and "tokens" in tokens:
        return tokens["tokens"]
    else:
        logging.warning("Cafe24 토큰 형식이 올바르지 않습니다.")
        return []


def get_cafe24_token_by_mall_id(mall_id: str) -> Optional[Dict[str, Any]]:
    """
    특정 mall_id의 토큰 정보 가져오기

    Args:
        mall_id: 몰 ID

    Returns:
        토큰 정보 딕셔너리 또는 None
    """
    tokens = get_cafe24_tokens()
    for token in tokens:
        if token.get("mall_id") == mall_id:
            return token
    return None


def update_cafe24_tokens(tokens: List[Dict[str, Any]]) -> bool:
    """
    Cafe24 토큰 목록 업데이트

    Args:
        tokens: 업데이트할 토큰 리스트

    Returns:
        성공 여부
    """
    return create_or_update_secret_json(CAFE24_TOKENS_SECRET_ID, tokens)


def get_cafe24_tokens_as_dict() -> Dict[str, Dict[str, Any]]:
    """
    mall_id를 키로 하는 딕셔너리 형태로 토큰 반환

    Returns:
        {mall_id: token_info} 딕셔너리
    """
    tokens = get_cafe24_tokens()
    return {t["mall_id"]: t for t in tokens if "mall_id" in t and "access_token" in t}


# ============================================================
# GCS에서 Secret Manager로 마이그레이션 헬퍼
# ============================================================

def migrate_tokens_from_gcs(
    bucket_name: str = "winged-precept-443218-v8.appspot.com",
    blob_name: str = "tokens.json"
) -> bool:
    """
    GCS의 tokens.json을 Secret Manager로 마이그레이션

    Args:
        bucket_name: GCS 버킷명
        blob_name: 파일명

    Returns:
        성공 여부
    """
    from google.cloud import storage

    try:
        # GCS에서 토큰 다운로드
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        token_data = blob.download_as_text()
        tokens = json.loads(token_data)

        logging.info(f"GCS에서 {len(tokens)}개의 토큰 로드됨")

        # Secret Manager에 저장
        success = create_or_update_secret_json(CAFE24_TOKENS_SECRET_ID, tokens)

        if success:
            logging.info("토큰이 Secret Manager로 성공적으로 마이그레이션됨")
        return success

    except Exception as e:
        logging.error(f"마이그레이션 실패: {e}")
        return False


# 테스트용
if __name__ == "__main__":
    # 시크릿 목록 조회
    secrets = list_secrets()
    print(f"현재 시크릿 목록: {secrets}")

    # Cafe24 토큰 조회 테스트
    tokens = get_cafe24_tokens()
    print(f"Cafe24 토큰 수: {len(tokens)}")
