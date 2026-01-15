#!/usr/bin/env python3
"""
Daily Batch 파이프라인 통합 스크립트 (Yesterday 전용)
- 9개 스텝 통합

실행 순서:
1. Cafe24 주문 수집 (orders_handler.py)
2. Cafe24 주문 아이템 수집 (product_handler.py)
3. Cafe24 매출 집계 (daily_cafe24_sales_handler.py)
4. Cafe24 아이템 집계 (daily_cafe24_items_handler.py)
5. Meta Ads 수집 (meta_ads_handler.py)
6. Meta Ads Summary (Merge_Meta_Ads_Summary.py)
7. GA4 Traffic 수집 (ga4_traffic_today.py)
8. GA4 ViewItem 수집 (ga4_viewitem_today.py)
9. Performance Summary 업데이트 (insert_performance_summary.py)

Usage:
    python daily_batch_pipeline.py
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
SCRIPTS_DIR = "/app"


def run_script(script_name: str, args: list, step_name: str, env_vars: dict = None):
    """Python 스크립트 실행"""
    script_path = os.path.join(SCRIPTS_DIR, script_name)
    cmd = ["python", script_path] + args

    env = os.environ.copy()
    if env_vars:
        env.update(env_vars)

    env_str = f" (env: {env_vars})" if env_vars else ""
    logging.info(f"실행: {' '.join(cmd)}{env_str}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10분 타임아웃
            env=env
        )

        if result.stdout:
            for line in result.stdout.strip().split('\n')[-20:]:  # 마지막 20줄만
                logging.info(f"  {line}")

        if result.stderr:
            for line in result.stderr.strip().split('\n')[-10:]:
                if "ERROR" in line.upper():
                    logging.error(f"  {line}")

        if result.returncode != 0:
            logging.error(f"{step_name} 실패 (exit code: {result.returncode})")
            return False

        logging.info(f"{step_name} 완료")
        return True

    except subprocess.TimeoutExpired:
        logging.error(f"{step_name} 타임아웃")
        return False
    except Exception as e:
        logging.error(f"{step_name} 오류: {e}")
        return False


def main():
    """Daily Batch 파이프라인 메인 함수 (Yesterday 전용)"""
    start_time = time.time()
    mode = "yesterday"

    logging.info(f"{'#' * 70}")
    logging.info(f"# Daily Batch Pipeline 시작 (Yesterday)")
    logging.info(f"# 시작 시간: {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S KST')}")
    logging.info(f"{'#' * 70}")

    results = {}

    # ============================================
    # Phase 1: Cafe24 데이터 수집
    # ============================================
    logging.info(f"\n{'=' * 70}")
    logging.info(f"Phase 1: Cafe24 데이터 수집")
    logging.info(f"{'=' * 70}")

    # 1-1. 주문 데이터 수집
    results["orders"] = run_script("orders_handler.py", [mode], "[1/9] 주문 수집")
    time.sleep(3)

    # 1-2. 주문 아이템 수집
    results["products"] = run_script("product_handler.py", [mode], "[2/9] 주문 아이템 수집")
    time.sleep(3)

    # ============================================
    # Phase 2: Cafe24 집계 쿼리
    # ============================================
    logging.info(f"\n{'=' * 70}")
    logging.info(f"Phase 2: Cafe24 집계 쿼리")
    logging.info(f"{'=' * 70}")

    # 2-1. 매출 집계
    results["sales"] = run_script("daily_cafe24_sales_handler.py", [mode], "[3/9] 매출 집계")

    # 2-2. 아이템 집계
    results["items"] = run_script("daily_cafe24_items_handler.py", [mode], "[4/9] 아이템 집계")
    time.sleep(3)

    # ============================================
    # Phase 3: Meta Ads 수집 + 집계
    # ============================================
    logging.info(f"\n{'=' * 70}")
    logging.info(f"Phase 3: Meta Ads 수집 + 집계")
    logging.info(f"{'=' * 70}")

    # 3-1. Meta Ads API 호출
    results["meta_ads"] = run_script("meta_ads_handler.py", [mode], "[5/9] Meta Ads 수집")
    time.sleep(5)

    # 3-2. Meta Ads Summary MERGE
    results["meta_summary"] = run_script("Merge_Meta_Ads_Summary.py", [mode], "[6/9] Meta Summary")
    time.sleep(3)

    # ============================================
    # Phase 4: GA4 데이터 수집
    # ============================================
    logging.info(f"\n{'=' * 70}")
    logging.info(f"Phase 4: GA4 데이터 수집")
    logging.info(f"{'=' * 70}")

    # 4-1. GA4 Traffic
    results["ga4_traffic"] = run_script(
        "ga4_traffic_today.py", [], "[7/9] GA4 Traffic",
        env_vars={"RUN_MODE": mode}
    )

    # 4-2. GA4 ViewItem
    results["ga4_viewitem"] = run_script(
        "ga4_viewitem_today.py", [], "[8/9] GA4 ViewItem",
        env_vars={"RUN_MODE": mode}
    )
    time.sleep(3)

    # ============================================
    # Phase 5: Performance Summary
    # ============================================
    logging.info(f"\n{'=' * 70}")
    logging.info(f"Phase 5: Performance Summary")
    logging.info(f"{'=' * 70}")

    results["perf_summary"] = run_script(
        "insert_performance_summary.py", [mode], "[9/9] Performance Summary"
    )

    # ============================================
    # 결과 요약
    # ============================================
    elapsed = time.time() - start_time
    success_count = sum(1 for v in results.values() if v)
    total_count = len(results)

    logging.info(f"\n{'#' * 70}")
    logging.info(f"# Daily Batch Pipeline 완료")
    logging.info(f"# 성공: {success_count}/{total_count}")
    logging.info(f"# 총 소요 시간: {elapsed:.1f}초 ({elapsed/60:.1f}분)")
    logging.info(f"{'#' * 70}")

    # 결과 상세
    logging.info("\n[결과 상세]")
    for name, success in results.items():
        status = "✅ 성공" if success else "❌ 실패"
        logging.info(f"  {name}: {status}")

    # 하나라도 실패하면 exit code 1
    if success_count < total_count:
        sys.exit(1)


if __name__ == "__main__":
    main()
