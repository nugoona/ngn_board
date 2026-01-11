#!/usr/bin/env python3
"""
Meta 파이프라인 통합 스크립트
- ngn-meta-ads-job + ngn-meta-query-job → ngn-meta-pipeline-job

순서:
1. meta_ads_handler.py - Meta API 호출 → BigQuery 저장
2. Merge_Meta_Ads_Summary.py - BigQuery 집계 쿼리 실행

Usage:
    python meta_pipeline.py today
    python meta_pipeline.py yesterday
"""
import os
import sys
import logging
import time
from datetime import datetime, timedelta, timezone

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# 프로젝트 루트를 PYTHONPATH에 추가
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/ngn_wep')

KST = timezone(timedelta(hours=9))


def run_meta_ads_collection(mode: str):
    """1단계: Meta API 호출 → BigQuery 저장"""
    logging.info(f"=" * 60)
    logging.info(f"[1/2] Meta Ads 데이터 수집 시작 (mode={mode})")
    logging.info(f"=" * 60)

    try:
        # meta_ads_handler 모듈의 main 함수 import 및 실행
        from meta_api.meta_ads_handler import main as meta_ads_main
        meta_ads_main(mode=mode)
        logging.info(f"[1/2] Meta Ads 데이터 수집 완료")
        return True
    except Exception as e:
        logging.error(f"[1/2] Meta Ads 데이터 수집 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_meta_summary_merge(mode: str):
    """2단계: BigQuery 집계 쿼리 실행"""
    logging.info(f"=" * 60)
    logging.info(f"[2/2] Meta Ads Summary MERGE 시작 (mode={mode})")
    logging.info(f"=" * 60)

    try:
        # Merge_Meta_Ads_Summary 모듈의 main 함수 import 및 실행
        from meta_api.Merge_Meta_Ads_Summary import main as merge_main

        # 날짜 계산
        now = datetime.now(timezone.utc).astimezone(KST)
        if mode == "today":
            target_date = now.strftime("%Y-%m-%d")
        else:
            target_date = (now - timedelta(days=1)).strftime("%Y-%m-%d")

        merge_main(target_date)
        logging.info(f"[2/2] Meta Ads Summary MERGE 완료")
        return True
    except Exception as e:
        logging.error(f"[2/2] Meta Ads Summary MERGE 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def main(mode: str = "today"):
    """Meta 파이프라인 메인 함수"""
    start_time = time.time()

    logging.info(f"{'#' * 60}")
    logging.info(f"# Meta Pipeline 시작 - mode: {mode}")
    logging.info(f"# 시작 시간: {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S KST')}")
    logging.info(f"{'#' * 60}")

    # 1단계: Meta API 호출 → BigQuery 저장
    if not run_meta_ads_collection(mode):
        logging.error("Meta Ads 데이터 수집 실패로 파이프라인 중단")
        sys.exit(1)

    # 데이터 안정화를 위한 짧은 대기
    logging.info("데이터 안정화 대기 (5초)...")
    time.sleep(5)

    # 2단계: BigQuery 집계 쿼리 실행
    if not run_meta_summary_merge(mode):
        logging.error("Meta Ads Summary MERGE 실패")
        sys.exit(1)

    elapsed = time.time() - start_time
    logging.info(f"{'#' * 60}")
    logging.info(f"# Meta Pipeline 완료")
    logging.info(f"# 총 소요 시간: {elapsed:.1f}초")
    logging.info(f"{'#' * 60}")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "today"
    main(mode=mode)
