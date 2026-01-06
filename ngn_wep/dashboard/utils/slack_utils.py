"""
Slack 알림 유틸리티 모듈
- 웹훅을 통한 슬랙 메시지 전송
- 토큰 갱신 실패, 시스템 오류 등 알림 용도
"""
import os
import json
import logging
import requests
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

# 로깅 설정
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# KST 시간대
KST = timezone(timedelta(hours=9))

# 슬랙 웹훅 URL (환경변수 또는 Secret Manager에서 가져오기)
SLACK_WEBHOOK_URL = os.getenv(
    "SLACK_WEBHOOK_URL",
    "https://hooks.slack.com/services/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"
)


def send_slack_message(
    message: str,
    channel: str = None,
    username: str = "NGN Dashboard Bot",
    icon_emoji: str = ":robot_face:",
    webhook_url: str = None
) -> bool:
    """
    슬랙 웹훅으로 메시지 전송

    Args:
        message: 전송할 메시지 텍스트
        channel: 채널명 (웹훅 설정 기본값 사용 시 None)
        username: 봇 이름
        icon_emoji: 봇 아이콘 이모지
        webhook_url: 웹훅 URL (None이면 환경변수 사용)

    Returns:
        bool: 전송 성공 여부
    """
    url = webhook_url or SLACK_WEBHOOK_URL

    if not url:
        logging.error("슬랙 웹훅 URL이 설정되지 않았습니다.")
        return False

    payload = {
        "text": message,
        "username": username,
        "icon_emoji": icon_emoji
    }

    if channel:
        payload["channel"] = channel

    try:
        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )

        if response.status_code == 200:
            logging.info(f"슬랙 메시지 전송 성공: {message[:50]}...")
            return True
        else:
            logging.error(f"슬랙 메시지 전송 실패: {response.status_code} - {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        logging.error(f"슬랙 메시지 전송 중 오류: {e}")
        return False


def send_slack_block_message(
    blocks: list,
    text: str = "알림",
    webhook_url: str = None
) -> bool:
    """
    슬랙 Block Kit 형식으로 메시지 전송 (리치 포맷)

    Args:
        blocks: 슬랙 Block Kit 블록 리스트
        text: 폴백 텍스트
        webhook_url: 웹훅 URL

    Returns:
        bool: 전송 성공 여부
    """
    url = webhook_url or SLACK_WEBHOOK_URL

    if not url:
        logging.error("슬랙 웹훅 URL이 설정되지 않았습니다.")
        return False

    payload = {
        "text": text,
        "blocks": blocks
    }

    try:
        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )

        if response.status_code == 200:
            logging.info("슬랙 블록 메시지 전송 성공")
            return True
        else:
            logging.error(f"슬랙 블록 메시지 전송 실패: {response.status_code}")
            return False

    except requests.exceptions.RequestException as e:
        logging.error(f"슬랙 블록 메시지 전송 중 오류: {e}")
        return False


def send_token_refresh_alert(
    mall_id: str,
    error_message: str,
    severity: str = "error"
) -> bool:
    """
    카페24 토큰 갱신 실패 알림 전송

    Args:
        mall_id: 실패한 몰 ID
        error_message: 에러 메시지
        severity: 심각도 (error, warning, info)

    Returns:
        bool: 전송 성공 여부
    """
    now_kst = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST")

    emoji_map = {
        "error": ":red_circle:",
        "warning": ":warning:",
        "info": ":information_source:"
    }
    emoji = emoji_map.get(severity, ":red_circle:")

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{emoji} 카페24 토큰 갱신 실패",
                "emoji": True
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Mall ID:*\n{mall_id}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*발생 시간:*\n{now_kst}"
                }
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

    return send_slack_block_message(
        blocks=blocks,
        text=f"[{severity.upper()}] 카페24 토큰 갱신 실패 - {mall_id}"
    )


def send_system_alert(
    title: str,
    message: str,
    severity: str = "error",
    additional_fields: Optional[Dict[str, str]] = None
) -> bool:
    """
    일반 시스템 알림 전송

    Args:
        title: 알림 제목
        message: 알림 내용
        severity: 심각도 (error, warning, info, success)
        additional_fields: 추가 필드 (key-value 딕셔너리)

    Returns:
        bool: 전송 성공 여부
    """
    now_kst = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST")

    emoji_map = {
        "error": ":red_circle:",
        "warning": ":warning:",
        "info": ":information_source:",
        "success": ":white_check_mark:"
    }
    emoji = emoji_map.get(severity, ":bell:")

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{emoji} {title}",
                "emoji": True
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": message
            }
        }
    ]

    # 추가 필드가 있으면 추가
    if additional_fields:
        fields = [
            {"type": "mrkdwn", "text": f"*{k}:*\n{v}"}
            for k, v in additional_fields.items()
        ]
        blocks.append({
            "type": "section",
            "fields": fields[:10]  # 슬랙 제한: 최대 10개 필드
        })

    # 타임스탬프 추가
    blocks.append({
        "type": "context",
        "elements": [
            {"type": "mrkdwn", "text": f":clock1: {now_kst}"}
        ]
    })

    return send_slack_block_message(
        blocks=blocks,
        text=f"[{severity.upper()}] {title}"
    )


# 테스트용
if __name__ == "__main__":
    # 간단한 메시지 테스트
    send_slack_message("NGN Dashboard 슬랙 연동 테스트 메시지입니다.")

    # 토큰 갱신 실패 알림 테스트
    send_token_refresh_alert(
        mall_id="test-mall",
        error_message="Invalid refresh token",
        severity="error"
    )
