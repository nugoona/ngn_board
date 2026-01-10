#!/usr/bin/env python3
"""
29CM 트렌드 스냅샷 생성 Cloud Run Job
매주 월요일 실행되어 최신 주차 데이터의 스냅샷을 생성합니다.
"""

import os
import sys
from pathlib import Path

# 환경 변수 로드 (로컬 실행 시 ~/ngn_board/config/ngn.env 파일에서)
def load_env_file():
    """로컬 환경에서 ~/ngn_board/config/ngn.env 파일에서 환경 변수 로드"""
    if os.path.exists('/app'):
        # Cloud Run Job 환경: 환경 변수는 이미 설정되어 있음
        return
    
    env_file = Path.home() / "ngn_board" / "config" / "ngn.env"
    if env_file.exists():
        print(f"📄 [INFO] 환경 변수 파일 로드: {env_file}", file=sys.stderr)
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 주석과 빈 줄 건너뛰기
                if not line or line.startswith('#'):
                    continue
                # KEY=value 형식 파싱
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    # 따옴표 제거
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    # 환경 변수 설정 (이미 설정되어 있으면 덮어쓰지 않음)
                    if key and value:
                        os.environ.setdefault(key, value)
        print(f"✅ [INFO] 환경 변수 로드 완료", file=sys.stderr)

# 환경 변수 로드
load_env_file()

# 프로젝트 루트를 Python 경로에 추가
# Cloud Run Job에서는 /app 사용, 로컬에서는 현재 스크립트 기준으로 찾기
if os.path.exists('/app'):
    # Cloud Run Job 환경
    sys.path.insert(0, '/app')
else:
    # 로컬 환경: 현재 파일 기준으로 프로젝트 루트 찾기
    current_file = Path(__file__).resolve()
    # tools/ai_report_test/jobs/xxx.py -> 프로젝트 루트
    project_root = current_file.parent.parent.parent.parent
    sys.path.insert(0, str(project_root))

# trend_29cm_snapshot 모듈에서 필요한 함수들을 직접 호출하기 위해
# 메인 함수 로직을 재사용
from tools.trend_29cm_snapshot import (
    get_current_week_run_id,
    get_available_tabs,
    get_rising_star,
    get_new_entry,
    get_rank_drop,
    get_snapshot_path,
    save_snapshot_to_gcs,
    get_all_companies_from_bq,
    get_company_korean_name_from_bq
)

def main():
    """최신 주차 데이터로 업체별 스냅샷 생성"""
    try:
        # 최신 주차 run_id 조회
        run_id = get_current_week_run_id()
        print(f"📅 [INFO] 최신 주차 사용: {run_id}", file=sys.stderr)
        
        # 탭 목록 조회
        print(f"📂 [INFO] 탭 목록 조회 중...", file=sys.stderr)
        tabs = get_available_tabs(run_id)
        print(f"   [INFO] 찾은 탭: {', '.join(tabs)}", file=sys.stderr)
        
        # 각 탭별 데이터 조회 (모든 업체 공통)
        print(f"\n📊 [INFO] 데이터 조회 중...", file=sys.stderr)
        tabs_data = {}
        
        for tab in tabs:
            print(f"   [INFO] [{tab}] 조회 중...", file=sys.stderr)
            tabs_data[tab] = {
                "rising_star": get_rising_star(tab, run_id),
                "new_entry": get_new_entry(tab, run_id),
                "rank_drop": get_rank_drop(tab, run_id)
            }
            print(f"      [INFO] - 급상승: {len(tabs_data[tab]['rising_star'])}개", file=sys.stderr)
            print(f"      [INFO] - 신규진입: {len(tabs_data[tab]['new_entry'])}개", file=sys.stderr)
            print(f"      [INFO] - 순위하락: {len(tabs_data[tab]['rank_drop'])}개", file=sys.stderr)
        
        # 처리할 업체 목록 조회 (demo 포함)
        companies_to_process = get_all_companies_from_bq()
        if not companies_to_process:
            print(f"⚠️ [WARN] 업체 목록을 찾을 수 없습니다.", file=sys.stderr)
            sys.exit(1)
        print(f"\n📌 [INFO] 처리할 업체: {', '.join(companies_to_process)}", file=sys.stderr)
        
        # 각 업체별 스냅샷 생성 및 AI 분석
        from tools.trend_29cm_snapshot import process_single_company
        
        success_count = 0
        fail_count = 0
        
        for company_name in companies_to_process:
            if process_single_company(run_id, company_name, tabs_data, target_brand=None):
                success_count += 1
            else:
                fail_count += 1
        
        # 최종 결과 출력
        print(f"\n{'='*60}", file=sys.stderr)
        print(f"📊 [SUMMARY] 성공: {success_count}, 실패: {fail_count}", file=sys.stderr)
        print(f"   [INFO] Run ID: {run_id}", file=sys.stderr)
        print(f"   [INFO] 처리 업체: {', '.join(companies_to_process)}", file=sys.stderr)
        print(f"{'='*60}\n", file=sys.stderr)
        
        if fail_count > 0:
            sys.exit(1)
        
    except Exception as e:
        print(f"❌ [ERROR] 스냅샷 생성 중 오류 발생: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

