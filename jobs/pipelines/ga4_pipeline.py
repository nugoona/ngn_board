#!/usr/bin/env python3
"""
GA4 파이프라인 통합 스크립트
- ngn-ga4-traffic-job + ngn-ga4-view-job → ngn-ga4-pipeline-job

순서:
1. ga4_traffic_today.py - 트래픽 데이터 수집
2. ga4_viewitem_today.py - ViewItem 이벤트 수집

Usage:
    python ga4_pipeline.py today
    python ga4_pipeline.py yesterday
"""
import os
import sys
import logging
import time
import subprocess
from datetime import datetime, timedelta, timezone

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

KST = timezone(timedelta(hours=9))

# 스크립트 경로 (Cloud Run 환경)
SCRIPTS_DIR = "/app"


def run_script_with_env(script_name: str, run_mode: str, step_name: str):
    """Python 스크립트를 환경변수와 함께 실행"""
    script_path = os.path.join(SCRIPTS_DIR, script_name)
    cmd = ["python", script_path]

    # RUN_MODE 환경변수 설정
    env = os.environ.copy()
    env["RUN_MODE"] = run_mode

    logging.info(f"실행: {' '.join(cmd)} (RUN_MODE={run_mode})")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5분 타임아웃
            env=env
        )

        # stdout 출력
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                logging.info(f"  {line}")

        # stderr 출력
        if result.stderr:
            for line in result.stderr.strip().split('\n'):
                if "ERROR" in line.upper():
                    logging.error(f"  {line}")
                else:
                    logging.info(f"  {line}")

        if result.returncode != 0:
            logging.error(f"{step_name} 실패 (exit code: {result.returncode})")
            return False

        logging.info(f"{step_name} 완료")
        return True

    except subprocess.TimeoutExpired:
        logging.error(f"{step_name} 타임아웃 (5분 초과)")
        return False
    except Exception as e:
        logging.error(f"{step_name} 실행 중 오류: {e}")
        return False


def main(mode: str = "today"):
    """GA4 파이프라인 메인 함수"""
    start_time = time.time()

    logging.info(f"{'#' * 60}")
    logging.info(f"# GA4 Pipeline 시작 - mode: {mode}")
    logging.info(f"# 시작 시간: {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S KST')}")
    logging.info(f"{'#' * 60}")

    # 1단계: 트래픽 데이터 수집
    logging.info(f"=" * 60)
    logging.info(f"[1/2] GA4 트래픽 데이터 수집 시작")
    logging.info(f"=" * 60)
    if not run_script_with_env("ga4_traffic_today.py", mode, "[1/2] 트래픽 수집"):
        logging.error("트래픽 데이터 수집 실패")
        # 실패해도 viewitem은 시도

    # 2단계: ViewItem 이벤트 수집
    logging.info(f"=" * 60)
    logging.info(f"[2/2] GA4 ViewItem 이벤트 수집 시작")
    logging.info(f"=" * 60)
    if not run_script_with_env("ga4_viewitem_today.py", mode, "[2/2] ViewItem 수집"):
        logging.error("ViewItem 데이터 수집 실패")

    elapsed = time.time() - start_time
    logging.info(f"{'#' * 60}")
    logging.info(f"# GA4 Pipeline 완료")
    logging.info(f"# 총 소요 시간: {elapsed:.1f}초")
    logging.info(f"{'#' * 60}")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "today"
    main(mode=mode)
