#!/usr/bin/env python3
"""
Cafe24 파이프라인 통합 스크립트
- ngn-orders-job + query-sales-today-job + query-items-today-job → ngn-cafe24-pipeline-job

순서:
1. orders_handler.py - Cafe24 주문 API 호출 → cafe24_orders 저장
2. product_handler.py - Cafe24 주문아이템 API 호출 → cafe24_order_items_table 저장
3. daily_cafe24_sales_handler.py - 매출 집계 쿼리
4. daily_cafe24_items_handler.py - 아이템 집계 쿼리

Usage:
    python cafe24_pipeline.py today
    python cafe24_pipeline.py yesterday
    python cafe24_pipeline.py last_7_days
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


def run_script(script_name: str, args: list, step_name: str):
    """Python 스크립트 실행"""
    script_path = os.path.join(SCRIPTS_DIR, script_name)
    cmd = ["python", script_path] + args

    logging.info(f"실행: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5분 타임아웃
        )

        # stdout 출력
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                logging.info(f"  {line}")

        # stderr 출력 (에러가 아닌 경우도 있음)
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
    """Cafe24 파이프라인 메인 함수"""
    start_time = time.time()

    logging.info(f"{'#' * 60}")
    logging.info(f"# Cafe24 Pipeline 시작 - mode: {mode}")
    logging.info(f"# 시작 시간: {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S KST')}")
    logging.info(f"{'#' * 60}")

    # 1단계: 주문 데이터 수집
    logging.info(f"=" * 60)
    logging.info(f"[1/4] Cafe24 주문 데이터 수집 시작")
    logging.info(f"=" * 60)
    if not run_script("orders_handler.py", [mode], "[1/4] 주문 수집"):
        logging.error("주문 데이터 수집 실패로 파이프라인 중단")
        sys.exit(1)

    # 데이터 안정화를 위한 대기
    logging.info("데이터 안정화 대기 (5초)...")
    time.sleep(5)

    # 2단계: 주문 아이템 수집 (cafe24_order_items_table)
    logging.info(f"=" * 60)
    logging.info(f"[2/4] Cafe24 주문 아이템 수집 시작")
    logging.info(f"=" * 60)
    if not run_script("product_handler.py", [mode], "[2/4] 주문 아이템 수집"):
        logging.error("주문 아이템 수집 실패")
        # 실패해도 집계는 시도

    # 데이터 안정화를 위한 대기
    logging.info("데이터 안정화 대기 (5초)...")
    time.sleep(5)

    # 3단계: 매출 집계
    logging.info(f"=" * 60)
    logging.info(f"[3/4] 매출 집계 시작")
    logging.info(f"=" * 60)
    if not run_script("daily_cafe24_sales_handler.py", [mode], "[3/4] 매출 집계"):
        logging.error("매출 집계 실패")
        # 매출 집계 실패해도 아이템 집계는 시도

    # 4단계: 아이템 집계
    logging.info(f"=" * 60)
    logging.info(f"[4/4] 아이템 집계 시작")
    logging.info(f"=" * 60)
    if not run_script("daily_cafe24_items_handler.py", [mode], "[4/4] 아이템 집계"):
        logging.error("아이템 집계 실패")

    elapsed = time.time() - start_time
    logging.info(f"{'#' * 60}")
    logging.info(f"# Cafe24 Pipeline 완료")
    logging.info(f"# 총 소요 시간: {elapsed:.1f}초")
    logging.info(f"{'#' * 60}")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "today"
    main(mode=mode)
