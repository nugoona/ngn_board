#!/usr/bin/env python3
"""
섹션 7만 재생성하는 스크립트
기존 리포트의 섹션 7 데이터를 수정된 파싱 로직으로 재생성합니다.
"""

import os
import sys

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tools.ai_report_test.ai_analyst import generate_ai_analysis_from_file

def main():
    """섹션 7만 재생성"""
    if len(sys.argv) < 4:
        print("Usage: python3 regenerate_section7.py <company_name> <year> <month>")
        print("예시: python3 regenerate_section7.py piscess 2025 1")
        print("")
        print("GCS 경로: gs://{bucket}/ai-reports/monthly/{company}/{YYYY-MM}/snapshot.json.gz")
        sys.exit(1)
    
    company_name = sys.argv[1]
    year = int(sys.argv[2])
    month = int(sys.argv[3])
    
    # GCS 버킷 정보
    gcs_bucket = os.environ.get("GCS_BUCKET", "winged-precept-443218-v8.appspot.com")
    
    # GCS 스냅샷 경로
    month_str = f"{year}-{month:02d}"
    snapshot_path = f"gs://{gcs_bucket}/ai-reports/monthly/{company_name}/{month_str}/snapshot.json.gz"
    
    print(f"🔄 [INFO] 섹션 7 재생성 시작")
    print(f"📂 [INFO] 파일: {snapshot_path}")
    print(f"📅 [INFO] 대상: {company_name} {year}년 {month}월")
    print("")
    
    try:
        # 섹션 7만 재생성 (sections=[7] 사용)
        generate_ai_analysis_from_file(
            snapshot_file=snapshot_path,
            output_file=None,  # 같은 파일에 덮어쓰기
            system_prompt_file=None,  # 자동으로 system_prompt_v44.txt 찾기
            sections=[7]  # 섹션 7만 재생성
        )
        
        print("")
        print("✅ [SUCCESS] 섹션 7 재생성 완료!")
        print(f"   프론트엔드에서 리포트를 새로고침하면 변경사항이 반영됩니다.")
        
    except Exception as e:
        print(f"❌ [ERROR] 섹션 7 재생성 실패: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
