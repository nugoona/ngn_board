#!/usr/bin/env python3
"""
월간 스냅샷 생성 및 AI 분석 Cloud Run Job
매월 1일 실행되어 전월 데이터의 스냅샷을 생성하고 AI 분석을 추가합니다.
"""

import os
import sys
from datetime import datetime, timezone, timedelta

# 프로젝트 루트를 Python 경로에 추가 (/app에 tools/ 디렉토리가 있음)
sys.path.insert(0, '/app')

from tools.ai_report_test.bq_monthly_snapshot import run
from tools.ai_report_test.ai_analyst import generate_ai_analysis_from_file

def main():
    """전월 데이터로 스냅샷 생성 및 AI 분석"""
    # 현재 시간 (UTC)
    now = datetime.now(timezone.utc)
    
    # 전월 계산 (매월 1일 실행이므로 전월이 대상)
    if now.month == 1:
        target_year = now.year - 1
        target_month = 12
    else:
        target_year = now.year
        target_month = now.month - 1
    
    # GCS 버킷 정보
    gcs_bucket = os.environ.get("GCS_BUCKET", "winged-precept-443218-v8.appspot.com")
    
    # 회사명 목록 (환경 변수에서 가져오거나 기본값 - demo 포함)
    company_names = os.environ.get("COMPANY_NAMES", "piscess,demo").split(",")
    company_names = [name.strip() for name in company_names if name.strip()]
    
    print(f"📅 [INFO] 스냅샷 생성 대상: {target_year}년 {target_month}월", file=sys.stderr)
    print(f"🏢 [INFO] 대상 회사: {', '.join(company_names)}", file=sys.stderr)
    
    success_count = 0
    error_count = 0
    
    for company_name in company_names:
        try:
            print(f"\n{'='*60}", file=sys.stderr)
            print(f"📊 [INFO] {company_name} 스냅샷 생성 시작...", file=sys.stderr)
            print(f"{'='*60}\n", file=sys.stderr)
            
            # 스냅샷 생성 (GCS에 저장, 강제 재생성)
            # use_current_month_events=True: 리포트 대상 월의 이벤트를 조회
            # 예: 12월 리포트 생성 시 → 12월 이벤트 조회 (동월 이벤트)
            run(
                company_name=company_name,
                year=target_year,
                month=target_month,
                upsert_flag=False,
                save_to_gcs_flag=True,
                load_from_gcs_flag=False,  # --force와 동일 (재생성)
                use_current_month_events=True  # 동월 이벤트 조회 (리포트 대상 월의 이벤트)
            )
            
            print(f"✅ [SUCCESS] {company_name} 스냅샷 생성 완료", file=sys.stderr)
            
            # AI 분석 자동 추가
            print(f"\n🤖 [INFO] {company_name} AI 분석 생성 중...", file=sys.stderr)
            try:
                snapshot_path = f"gs://{gcs_bucket}/ai-reports/monthly/{company_name}/{target_year}-{target_month:02d}/snapshot.json.gz"
                
                # AI 분석 생성 (같은 파일에 덮어쓰기)
                generate_ai_analysis_from_file(
                    snapshot_file=snapshot_path,
                    output_file=None,  # 입력 파일에 덮어쓰기
                    system_prompt_file=None  # 자동으로 system_prompt_v44.txt 찾기
                )
                
                print(f"✅ [SUCCESS] {company_name} AI 분석 완료", file=sys.stderr)
                success_count += 1
                
            except Exception as ai_error:
                # AI 분석 실패해도 스냅샷은 성공했으므로 경고만 출력
                print(f"⚠️ [WARN] {company_name} AI 분석 실패 (스냅샷은 정상 저장됨): {ai_error}", file=sys.stderr)
                import traceback
                traceback.print_exc(file=sys.stderr)
                # 스냅샷은 성공했으므로 success_count 증가
                success_count += 1
            
        except Exception as e:
            error_count += 1
            print(f"❌ [ERROR] {company_name} 스냅샷 생성 실패: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            # 하나 실패해도 다른 회사는 계속 진행
    
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"📊 [SUMMARY] 성공: {success_count}, 실패: {error_count}", file=sys.stderr)
    print(f"{'='*60}\n", file=sys.stderr)
    
    # 실패가 있으면 종료 코드 1 반환
    if error_count > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()

