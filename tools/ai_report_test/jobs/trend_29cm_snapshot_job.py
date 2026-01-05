#!/usr/bin/env python3
"""
29CM 트렌드 스냅샷 생성 Cloud Run Job
매주 월요일 실행되어 최신 주차 데이터의 스냅샷을 생성합니다.
"""

import os
import sys

# 프로젝트 루트를 Python 경로에 추가 (/app에 tools/ 디렉토리가 있음)
sys.path.insert(0, '/app')

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
    """최신 주차 데이터로 스냅샷 생성"""
    try:
        # 최신 주차 run_id 조회
        run_id = get_current_week_run_id()
        print(f"📅 [INFO] 최신 주차 사용: {run_id}", file=sys.stderr)
        
        # 탭 목록 조회
        print(f"📂 [INFO] 탭 목록 조회 중...", file=sys.stderr)
        tabs = get_available_tabs(run_id)
        print(f"   [INFO] 찾은 탭: {', '.join(tabs)}", file=sys.stderr)
        
        # 각 탭별 데이터 조회
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
        
        # 스냅샷 저장
        print(f"\n💾 [INFO] 스냅샷 저장 중...", file=sys.stderr)
        success = save_snapshot_to_gcs(run_id, tabs_data)
        
        if not success:
            print(f"\n❌ [ERROR] 스냅샷 생성 실패", file=sys.stderr)
            sys.exit(1)
        
        gcs_bucket = os.environ.get("GCS_BUCKET", "winged-precept-443218-v8.appspot.com")
        snapshot_path = f"gs://{gcs_bucket}/{get_snapshot_path(run_id)}"
        print(f"\n✅ [SUCCESS] 스냅샷 생성 완료!", file=sys.stderr)
        print(f"   [INFO] Run ID: {run_id}", file=sys.stderr)
        print(f"   [INFO] 탭 개수: {len(tabs)}", file=sys.stderr)
        print(f"   [INFO] 경로: {snapshot_path}", file=sys.stderr)
        
        # AI 분석 자동 추가 (첫 번째 업체 사용)
        print(f"\n🤖 [INFO] AI 분석 리포트 생성 중 (첫 번째 업체 사용)...", file=sys.stderr)
        try:
            from tools.ai_report_test.trend_29cm_ai_analyst import generate_ai_analysis_from_file
            
            companies = get_all_companies_from_bq()
            if companies:
                first_company = companies[0]
                print(f"   [INFO] 첫 번째 업체 사용: {first_company}", file=sys.stderr)
                
                target_brand = get_company_korean_name_from_bq(first_company.lower())
                if target_brand:
                    generate_ai_analysis_from_file(
                        snapshot_file=snapshot_path,
                        output_file=None,
                        api_key=None,
                        target_brand=target_brand
                    )
                    print(f"✅ [SUCCESS] AI 분석 리포트 추가 완료! (브랜드: {target_brand})", file=sys.stderr)
                else:
                    print(f"⚠️ [WARN] 한글명을 찾을 수 없어 AI 리포트를 생성하지 않습니다.", file=sys.stderr)
            else:
                print(f"⚠️ [WARN] 업체 목록을 찾을 수 없어 AI 리포트를 생성하지 않습니다.", file=sys.stderr)
        except Exception as e:
            print(f"⚠️ [WARN] AI 분석 리포트 생성 실패 (스냅샷은 정상 저장됨): {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            # AI 리포트 실패해도 스냅샷은 성공이므로 계속 진행
        
    except Exception as e:
        print(f"❌ [ERROR] 스냅샷 생성 중 오류 발생: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

