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


# check_snapshot_exists 함수는 더 이상 사용하지 않음 (main에서 직접 확인)


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Ably 트렌드 스냅샷 생성')
    parser.add_argument('--run-id', type=str, help='특정 run_id로 스냅샷 생성 (기본값: 최신 주차)')
    parser.add_argument('--target-brand', type=str, help='분석 타겟 브랜드명 (한글명, 예: "썸웨어버터", "파이시스")')
    parser.add_argument('--company-name', type=str, help='업체명 (영문, 예: "piscess") - target-brand로 자동 변환 (자동 스케줄에서는 첫 번째 업체 사용)')
    
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
    
    # ✅ company_name 결정 (--company-name이 있으면 사용, 없으면 첫 번째 업체 사용)
    company_name = args.company_name
    if not company_name:
        companies = get_all_companies_from_bq()
        if companies:
            company_name = companies[0]
            print(f"📌 업체명 자동 선택: {company_name}")
        else:
            print(f"⚠️ [WARN] 업체 목록을 찾을 수 없어 업체명 없이 저장합니다.", file=sys.stderr)
    
    # 기존 스냅샷 확인
    if company_name:
        blob_path = get_trend_snapshot_path(run_id, company_name)
        from google.cloud import storage
        client = storage.Client(project=PROJECT_ID)
        bucket = client.bucket(GCS_BUCKET)
        blob = bucket.blob(blob_path)
        if blob.exists():
            print(f"⚠️ 스냅샷이 이미 존재하지만 강제로 재생성합니다: {run_id} (업체: {company_name})")
    
    # 탭 목록 조회
    print(f"📂 탭 목록 조회 중...")
    tabs = get_available_tabs()
    print(f"   찾은 탭: {', '.join(tabs)}")
    
    # 각 탭별 데이터 조회
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
    
    # 스냅샷 저장 (업체명 폴더 구조, 먼저 저장, AI 분석은 나중에 추가)
    print(f"\n💾 스냅샷 저장 중...")
    success = save_trend_snapshot_to_gcs(run_id, tabs_data, run_id, company_name=company_name, enable_ai_analysis=False)
    
    if not success:
        print(f"\n❌ 스냅샷 생성 실패")
        sys.exit(1)
    
    snapshot_path = f"gs://{GCS_BUCKET}/{get_trend_snapshot_path(run_id, company_name)}"
    print(f"\n✅ 스냅샷 생성 완료!")
    print(f"   Run ID: {run_id}")
    print(f"   업체명: {company_name or '(없음)'}")
    print(f"   탭 개수: {len(tabs)}")
    print(f"   경로: {snapshot_path}")
    
    # AI 분석 자동 추가
    # --company-name 또는 --target-brand가 지정되면 해당 업체로 리포트 생성
    # 둘 다 없으면 첫 번째 업체로 생성 (자동 스케줄용)
    if args.company_name or args.target_brand:
        # 단일 업체에 대한 리포트 생성 (기존 방식)
        print(f"\n🤖 AI 분석 리포트 생성 중...")
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(script_dir)
            tools_path = os.path.join(project_root, 'tools', 'ai_report_test')
            if tools_path not in sys.path:
                sys.path.insert(0, tools_path)
            
            from trend_29cm_ai_analyst import generate_ai_analysis_from_file
            
            # target_brand 결정
            target_brand = args.target_brand
            if not target_brand and args.company_name:
                target_brand = get_company_korean_name_from_bq(args.company_name.lower())
                if not target_brand:
                    print(f"⚠️ [WARN] BigQuery에서 한글명을 찾을 수 없습니다: {args.company_name}", file=sys.stderr)
            
            generate_ai_analysis_from_file(
                snapshot_file=snapshot_path,
                output_file=None,
                api_key=None,
                target_brand=target_brand,
                platform="Ably"
            )
            
            print(f"✅ AI 분석 리포트 추가 완료!")
        except Exception as e:
            print(f"⚠️ AI 분석 리포트 생성 실패 (스냅샷은 정상 저장됨): {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
    else:
        # --company-name과 --target-brand가 모두 없으면 첫 번째 업체로 생성 (자동 스케줄용)
        print(f"\n🤖 AI 분석 리포트 생성 중 (첫 번째 업체 사용)...")
        try:
            companies = get_all_companies_from_bq()
            if companies:
                first_company = companies[0]
                print(f"   첫 번째 업체 사용: {first_company}")
                script_dir = os.path.dirname(os.path.abspath(__file__))
                project_root = os.path.dirname(script_dir)
                tools_path = os.path.join(project_root, 'tools', 'ai_report_test')
                if tools_path not in sys.path:
                    sys.path.insert(0, tools_path)
                
                from trend_29cm_ai_analyst import generate_ai_analysis_from_file
                
                target_brand = get_company_korean_name_from_bq(first_company.lower())
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
            else:
                print(f"⚠️ [WARN] 업체 목록을 찾을 수 없어 AI 리포트를 생성하지 않습니다.", file=sys.stderr)
        except Exception as e:
            print(f"⚠️ AI 분석 리포트 생성 실패 (스냅샷은 정상 저장됨): {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)


if __name__ == "__main__":
    main()

