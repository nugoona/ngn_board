#!/usr/bin/env python3
"""
월간 스냅샷 생성 Cloud Run Job
매월 1일 실행되어 전월 데이터의 스냅샷을 생성합니다.
"""

import os
import sys
from datetime import datetime, timezone, timedelta

# 프로젝트 루트를 Python 경로에 추가 (/app에 tools/ 디렉토리가 있음)
sys.path.insert(0, '/app')

from tools.ai_report_test.bq_monthly_snapshot import run

def main():
    """전월 데이터로 스냅샷 생성"""
    # 현재 시간 (UTC)
    now = datetime.now(timezone.utc)
    
    # 전월 계산 (매월 1일 실행이므로 전월이 대상)
    if now.month == 1:
        target_year = now.year - 1
        target_month = 12
    else:
        target_year = now.year
        target_month = now.month - 1
    
    # 회사명 목록 (환경 변수에서 가져오거나 기본값)
    company_names = os.environ.get("COMPANY_NAMES", "piscess").split(",")
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
            run(
                company_name=company_name,
                year=target_year,
                month=target_month,
                upsert_flag=False,
                save_to_gcs_flag=True,
                load_from_gcs_flag=False  # --force와 동일 (재생성)
            )
            
            success_count += 1
            print(f"✅ [SUCCESS] {company_name} 스냅샷 생성 완료", file=sys.stderr)
            
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

