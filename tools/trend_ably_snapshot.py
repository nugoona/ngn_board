#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ably 트렌드 스냅샷 생성 스크립트
로컬 또는 Cloud Shell에서 수동 실행

사용법:
    python3 tools/trend_ably_snapshot.py [--run-id RUN_ID]
    
옵션:
    --run-id RUN_ID    특정 run_id로 스냅샷 생성 (기본값: 최신 주차)
    --target-brand     분석 타겟 브랜드명 (한글명, 예: "썸웨어버터", "파이시스")
    --company-name     업체명 (영문, 예: "piscess") - target-brand로 자동 변환
"""

import os
import sys

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 서비스 함수 import
from ngn_wep.dashboard.services.trend_ably_service import (
    get_current_week_info,
    get_available_tabs,
    get_rising_star,
    get_new_entry,
    get_rank_drop,
    get_trend_snapshot_path,
    save_trend_snapshot_to_gcs
)

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "winged-precept-443218-v8")
GCS_BUCKET = os.environ.get("GCS_BUCKET", "winged-precept-443218-v8.appspot.com")


def get_company_korean_name_from_bq(company_name_en: str) -> str:
    """
    BigQuery company_info 테이블에서 한글명 조회
    
    Args:
        company_name_en: 업체명 (영문, 예: "piscess")
    
    Returns:
        한글명 (예: "파이시스") 또는 None
    """
    try:
        from google.cloud import bigquery
        client = bigquery.Client(project=PROJECT_ID)
        query = """
        SELECT korean_name
        FROM `winged-precept-443218-v8.ngn_dataset.company_info`
        WHERE LOWER(company_name) = LOWER(@company_name)
        LIMIT 1
        """
        from google.cloud.bigquery import ScalarQueryParameter, QueryJobConfig
        job_config = QueryJobConfig(
            query_parameters=[
                ScalarQueryParameter("company_name", "STRING", company_name_en)
            ]
        )
        rows = client.query(query, job_config=job_config).result()
        for row in rows:
            korean_name = row.korean_name
            if korean_name:
                return korean_name
        return None
    except Exception as e:
        print(f"⚠️ [WARN] BigQuery에서 한글명 조회 실패 ({company_name_en}): {e}", file=sys.stderr)
        return None


def get_all_companies_from_bq() -> list:
    """
    BigQuery company_info 테이블에서 모든 업체 목록 조회 (demo 포함)

    Returns:
        업체명 리스트 (예: ["piscess", "demo", "other_company", ...])
    """
    try:
        from google.cloud import bigquery
        client = bigquery.Client(project=PROJECT_ID)
        query = """
        SELECT DISTINCT company_name
        FROM `winged-precept-443218-v8.ngn_dataset.company_info`
        WHERE korean_name IS NOT NULL
        ORDER BY company_name
        """
        rows = client.query(query).result()
        return [row.company_name for row in rows]
    except Exception as e:
        print(f"⚠️ [WARN] BigQuery에서 업체 목록 조회 실패: {e}", file=sys.stderr)
        return []


def process_single_company(run_id: str, company_name: str, tabs_data: dict, target_brand: str = None) -> bool:
    """단일 업체에 대한 스냅샷 저장 및 AI 분석 수행"""
    print(f"\n{'='*60}")
    print(f"📊 [{company_name}] 스냅샷 처리 시작")
    print(f"{'='*60}")

    # 기존 스냅샷 확인
    blob_path = get_trend_snapshot_path(run_id, company_name)
    from google.cloud import storage
    client = storage.Client(project=PROJECT_ID)
    bucket = client.bucket(GCS_BUCKET)
    blob = bucket.blob(blob_path)
    if blob.exists():
        print(f"⚠️ 스냅샷이 이미 존재하지만 강제로 재생성합니다: {run_id} (업체: {company_name})")

    # 스냅샷 저장 (업체명 폴더 구조)
    print(f"💾 스냅샷 저장 중...")
    success = save_trend_snapshot_to_gcs(run_id, tabs_data, run_id, company_name=company_name, enable_ai_analysis=False)

    if not success:
        print(f"❌ [{company_name}] 스냅샷 생성 실패")
        return False

    snapshot_path = f"gs://{GCS_BUCKET}/{get_trend_snapshot_path(run_id, company_name)}"
    print(f"✅ 스냅샷 생성 완료: {snapshot_path}")

    # AI 분석 자동 추가
    print(f"🤖 AI 분석 리포트 생성 중...")
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        tools_path = os.path.join(project_root, 'tools', 'ai_report_test')
        if tools_path not in sys.path:
            sys.path.insert(0, tools_path)

        from trend_29cm_ai_analyst import generate_ai_analysis_from_file

        # target_brand 결정
        if not target_brand:
            target_brand = get_company_korean_name_from_bq(company_name.lower())

        if target_brand:
            generate_ai_analysis_from_file(
                snapshot_file=snapshot_path,
                output_file=None,
                api_key=None,
                target_brand=target_brand,
                platform="Ably"
            )
            print(f"✅ AI 분석 리포트 추가 완료! (브랜드: {target_brand})")
        else:
            print(f"⚠️ [WARN] 한글명을 찾을 수 없어 AI 리포트를 생성하지 않습니다.", file=sys.stderr)
    except Exception as e:
        print(f"⚠️ AI 분석 리포트 생성 실패 (스냅샷은 정상 저장됨): {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)

    return True


def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description='Ably 트렌드 스냅샷 생성')
    parser.add_argument('--run-id', type=str, help='특정 run_id로 스냅샷 생성 (기본값: 최신 주차)')
    parser.add_argument('--target-brand', type=str, help='분석 타겟 브랜드명 (한글명, 예: "썸웨어버터", "파이시스")')
    parser.add_argument('--company-name', type=str, help='업체명 (영문, 예: "piscess") - 지정하지 않으면 모든 업체 처리')

    args = parser.parse_args()

    # run_id 결정
    if args.run_id:
        run_id = args.run_id
        print(f"📅 지정된 run_id 사용: {run_id}")
    else:
        run_id = get_current_week_info()
        if not run_id:
            print("❌ 주차 데이터를 찾을 수 없습니다.")
            sys.exit(1)
        print(f"📅 최신 주차 사용: {run_id}")

    # 탭 목록 조회 (모든 업체 공통)
    print(f"📂 탭 목록 조회 중...")
    tabs = get_available_tabs()
    print(f"   찾은 탭: {', '.join(tabs)}")

    # 각 탭별 데이터 조회 (모든 업체 공통)
    print(f"\n📊 데이터 조회 중...")
    tabs_data = {}

    for tab in tabs:
        print(f"   [{tab}] 조회 중...")
        tabs_data[tab] = {
            "rising_star": get_rising_star(tab),
            "new_entry": get_new_entry(tab),
            "rank_drop": get_rank_drop(tab)
        }
        print(f"      - 급상승: {len(tabs_data[tab]['rising_star'])}개")
        print(f"      - 신규진입: {len(tabs_data[tab]['new_entry'])}개")
        print(f"      - 순위하락: {len(tabs_data[tab]['rank_drop'])}개")

    # 처리할 업체 목록 결정
    if args.company_name:
        # 특정 업체만 처리
        companies_to_process = [args.company_name]
        print(f"\n📌 지정된 업체 처리: {args.company_name}")
    else:
        # 모든 업체 처리
        companies_to_process = get_all_companies_from_bq()
        if not companies_to_process:
            print(f"⚠️ [WARN] 업체 목록을 찾을 수 없습니다.", file=sys.stderr)
            sys.exit(1)
        print(f"\n📌 전체 업체 처리: {', '.join(companies_to_process)}")

    # 각 업체별 스냅샷 생성 및 AI 분석
    success_count = 0
    fail_count = 0

    for company_name in companies_to_process:
        target_brand = args.target_brand if args.company_name else None
        if process_single_company(run_id, company_name, tabs_data, target_brand):
            success_count += 1
        else:
            fail_count += 1

    # 최종 결과 출력
    print(f"\n{'='*60}")
    print(f"📊 [SUMMARY] 성공: {success_count}, 실패: {fail_count}")
    print(f"   Run ID: {run_id}")
    print(f"   처리 업체: {', '.join(companies_to_process)}")
    print(f"{'='*60}")

    if fail_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()

