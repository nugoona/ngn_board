#!/usr/bin/env python3
"""
GCS tokens.json을 Secret Manager로 마이그레이션하는 스크립트

실행 방법:
    python tools/migrate_tokens_to_secret_manager.py

주의:
    - 이 스크립트는 한 번만 실행하면 됩니다.
    - 실행 전 Secret Manager API가 활성화되어 있어야 합니다.
    - 실행 후에도 GCS의 tokens.json은 유지됩니다 (백업용).
"""
import os
import sys
import json
import logging
from datetime import datetime, timezone, timedelta

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# 프로젝트 설정
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "winged-precept-443218-v8")
BUCKET_NAME = os.getenv("BUCKET_NAME", "winged-precept-443218-v8.appspot.com")
TOKEN_FILE_NAME = "tokens.json"
SECRET_ID = "cafe24-tokens"

KST = timezone(timedelta(hours=9))


def load_tokens_from_gcs():
    """GCS에서 토큰 로드"""
    from google.cloud import storage

    logging.info(f"GCS에서 토큰 로드 중: gs://{BUCKET_NAME}/{TOKEN_FILE_NAME}")

    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(TOKEN_FILE_NAME)

    try:
        token_data = blob.download_as_text()
        tokens = json.loads(token_data)
        logging.info(f"GCS에서 {len(tokens)}개 토큰 로드 성공")
        return tokens
    except Exception as e:
        logging.error(f"GCS 토큰 로드 실패: {e}")
        return None


def create_secret_in_secret_manager(tokens):
    """Secret Manager에 시크릿 생성"""
    from google.cloud import secretmanager
    from google.api_core import exceptions as gcp_exceptions

    client = secretmanager.SecretManagerServiceClient()
    parent = f"projects/{PROJECT_ID}"
    secret_name = f"{parent}/secrets/{SECRET_ID}"

    logging.info(f"Secret Manager에 시크릿 생성 중: {SECRET_ID}")

    try:
        # 기존 시크릿 확인
        try:
            existing_secret = client.get_secret(request={"name": secret_name})
            logging.warning(f"시크릿 '{SECRET_ID}'이(가) 이미 존재합니다.")

            # 기존 버전 확인
            versions = client.list_secret_versions(request={"parent": secret_name})
            version_count = sum(1 for _ in versions)
            logging.info(f"기존 버전 수: {version_count}")

            response = input("새 버전을 추가하시겠습니까? (y/n): ")
            if response.lower() != 'y':
                logging.info("마이그레이션 취소됨")
                return False

        except gcp_exceptions.NotFound:
            # 시크릿 생성
            client.create_secret(
                request={
                    "parent": parent,
                    "secret_id": SECRET_ID,
                    "secret": {
                        "replication": {"automatic": {}},
                        "labels": {
                            "purpose": "cafe24-api-tokens",
                            "migrated-from": "gcs",
                            "migrated-at": datetime.now(KST).strftime("%Y%m%d")
                        }
                    }
                }
            )
            logging.info(f"시크릿 '{SECRET_ID}' 생성 완료")

        # 새 버전 추가
        secret_value = json.dumps(tokens, ensure_ascii=False, indent=2)
        version = client.add_secret_version(
            request={
                "parent": secret_name,
                "payload": {"data": secret_value.encode("UTF-8")}
            }
        )

        logging.info(f"시크릿 버전 추가 완료: {version.name}")
        return True

    except Exception as e:
        logging.error(f"Secret Manager 시크릿 생성 실패: {e}")
        return False


def verify_secret():
    """생성된 시크릿 검증"""
    from google.cloud import secretmanager

    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{PROJECT_ID}/secrets/{SECRET_ID}/versions/latest"

    try:
        response = client.access_secret_version(request={"name": name})
        secret_value = response.payload.data.decode("UTF-8")
        tokens = json.loads(secret_value)

        logging.info(f"시크릿 검증 완료: {len(tokens)}개 토큰 확인됨")

        # 토큰 요약 출력
        for i, token in enumerate(tokens[:3], 1):
            mall_id = token.get("mall_id", "unknown")
            has_access_token = bool(token.get("access_token"))
            has_refresh_token = bool(token.get("refresh_token"))
            logging.info(f"  {i}. {mall_id} - access_token: {has_access_token}, refresh_token: {has_refresh_token}")

        if len(tokens) > 3:
            logging.info(f"  ... 외 {len(tokens) - 3}개")

        return True

    except Exception as e:
        logging.error(f"시크릿 검증 실패: {e}")
        return False


def main():
    logging.info("=" * 60)
    logging.info("GCS → Secret Manager 토큰 마이그레이션")
    logging.info("=" * 60)
    logging.info(f"프로젝트: {PROJECT_ID}")
    logging.info(f"GCS 버킷: {BUCKET_NAME}")
    logging.info(f"시크릿 ID: {SECRET_ID}")
    logging.info("=" * 60)

    # 1. GCS에서 토큰 로드
    tokens = load_tokens_from_gcs()
    if not tokens:
        logging.error("토큰 로드 실패. 마이그레이션 중단.")
        sys.exit(1)

    # 2. 토큰 데이터 확인
    logging.info(f"\n토큰 정보:")
    for token in tokens:
        mall_id = token.get("mall_id", "unknown")
        expires_at = token.get("expires_at", "N/A")
        logging.info(f"  - {mall_id}: expires_at={expires_at}")

    # 3. 사용자 확인
    print("\n")
    response = input("위 토큰들을 Secret Manager로 마이그레이션하시겠습니까? (y/n): ")
    if response.lower() != 'y':
        logging.info("마이그레이션 취소됨")
        sys.exit(0)

    # 4. Secret Manager에 저장
    success = create_secret_in_secret_manager(tokens)
    if not success:
        logging.error("Secret Manager 저장 실패. 마이그레이션 중단.")
        sys.exit(1)

    # 5. 검증
    logging.info("\n시크릿 검증 중...")
    if verify_secret():
        logging.info("\n" + "=" * 60)
        logging.info("마이그레이션 완료!")
        logging.info("=" * 60)
        logging.info("\n다음 단계:")
        logging.info("1. 환경변수 TOKEN_STORAGE_MODE=secret_manager 설정")
        logging.info("2. Cloud Run Job 재배포")
        logging.info("3. GCS의 tokens.json은 백업으로 유지")
    else:
        logging.error("검증 실패. Secret Manager를 확인하세요.")
        sys.exit(1)


if __name__ == "__main__":
    main()
