#!/usr/bin/env python3
"""
월간 AI 분석 생성 Cloud Run Job
매월 1일 실행되어 전월 스냅샷에 AI 분석을 추가합니다.
"""

import os
import sys
from datetime import datetime, timezone

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from tools.ai_report_test.ai_analyst import generate_ai_analysis_from_file
from google.cloud import storage

def main():
    """전월 스냅샷에 AI 분석 추가"""
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
    
    # 회사명 목록 (환경 변수에서 가져오거나 기본값)
    company_names = os.environ.get("COMPANY_NAMES", "piscess").split(",")
    company_names = [name.strip() for name in company_names if name.strip()]
    
    print(f"📅 [INFO] AI 분석 대상: {target_year}년 {target_month}월", file=sys.stderr)
    print(f"🏢 [INFO] 대상 회사: {', '.join(company_names)}", file=sys.stderr)
    
    success_count = 0
    error_count = 0
    
    for company_name in company_names:
        try:
            print(f"\n{'='*60}", file=sys.stderr)
            print(f"🤖 [INFO] {company_name} AI 분석 시작...", file=sys.stderr)
            print(f"{'='*60}\n", file=sys.stderr)
            
            # GCS 스냅샷 경로
            snapshot_path = f"gs://{gcs_bucket}/ai-reports/monthly/{company_name}/{target_year}-{target_month:02d}/snapshot.json.gz"
            
            # 스냅샷 파일 존재 확인
            if not snapshot_path.startswith("gs://"):
                raise ValueError(f"GCS 경로가 올바르지 않습니다: {snapshot_path}")
            
            # GCS에서 파일 존재 확인
            parts = snapshot_path.replace("gs://", "").split("/", 1)
            if len(parts) != 2:
                raise ValueError(f"GCS 경로 파싱 실패: {snapshot_path}")
            
            bucket_name = parts[0]
            blob_path = parts[1]
            
            storage_client = storage.Client()
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_path)
            
            if not blob.exists():
                print(f"⚠️ [WARN] 스냅샷 파일이 존재하지 않습니다: {snapshot_path}", file=sys.stderr)
                print(f"   스냅샷 생성 Job이 먼저 실행되어야 합니다.", file=sys.stderr)
                error_count += 1
                continue
            
            print(f"📂 [INFO] 스냅샷 파일 확인: {snapshot_path}", file=sys.stderr)
            
            # AI 분석 생성 (같은 파일에 덮어쓰기)
            generate_ai_analysis_from_file(
                snapshot_file=snapshot_path,
                output_file=None,  # 입력 파일에 덮어쓰기
                system_prompt_file=None  # 자동으로 system_prompt_v44.txt 찾기
            )
            
            success_count += 1
            print(f"✅ [SUCCESS] {company_name} AI 분석 완료", file=sys.stderr)
            
        except Exception as e:
            error_count += 1
            print(f"❌ [ERROR] {company_name} AI 분석 실패: {e}", file=sys.stderr)
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

