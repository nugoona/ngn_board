#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
데모 계정 스냅샷 로컬 테스트 (Cloud Run Job 방식)
환경 변수는 ~/ngn_board/config/ngn.env 파일에서 로드
"""

import os
import sys
from pathlib import Path

# 환경 변수 파일 로드
def load_env_file():
    """~/ngn_board/config/ngn.env 파일에서 환경 변수 로드"""
    env_file = Path.home() / "ngn_board" / "config" / "ngn.env"
    
    if env_file.exists():
        print(f"📄 환경 변수 파일 로드: {env_file}", file=sys.stderr)
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
        print("✅ 환경 변수 로드 완료", file=sys.stderr)
    else:
        print(f"⚠️  환경 변수 파일을 찾을 수 없습니다: {env_file}", file=sys.stderr)
        print("기본값 사용", file=sys.stderr)

# 프로젝트 루트를 Python 경로에 추가 (로컬 실행용)
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent if SCRIPT_DIR.name != 'tools' else SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 환경 변수 로드
load_env_file()

# 기본값 설정
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "winged-precept-443218-v8")
os.environ.setdefault("GCS_BUCKET", "winged-precept-443218-v8.appspot.com")
os.environ.setdefault("COMPANY_NAMES", "piscess,demo")

# Job 파일들 import 및 실행
if __name__ == "__main__":
    print("=" * 60, file=sys.stderr)
    print("데모 계정 스냅샷 로컬 테스트 (Job 방식)", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print(f"GOOGLE_CLOUD_PROJECT: {os.environ.get('GOOGLE_CLOUD_PROJECT')}", file=sys.stderr)
    print(f"GCS_BUCKET: {os.environ.get('GCS_BUCKET')}", file=sys.stderr)
    print(f"COMPANY_NAMES: {os.environ.get('COMPANY_NAMES')}", file=sys.stderr)
    print(f"GEMINI_API_KEY: {'설정됨' if os.environ.get('GEMINI_API_KEY') else '설정 안 됨'}", file=sys.stderr)
    print("", file=sys.stderr)
    
    # Job 파일들의 sys.path 설정을 수정하기 위해 직접 import
    import importlib.util
    
    jobs_to_run = [
        ("tools/ai_report_test/jobs/monthly_snapshot_job.py", "월간 스냅샷"),
        ("tools/ai_report_test/jobs/trend_29cm_snapshot_job.py", "29CM 트렌드"),
        ("tools/ai_report_test/jobs/trend_ably_snapshot_job.py", "에이블리 트렌드"),
    ]
    
    for job_path, job_name in jobs_to_run:
        print("", file=sys.stderr)
        print(f"📊 [{job_name}] Job 실행 중...", file=sys.stderr)
        print("-" * 60, file=sys.stderr)
        
        job_file = PROJECT_ROOT / job_path
        if not job_file.exists():
            print(f"❌ Job 파일을 찾을 수 없습니다: {job_file}", file=sys.stderr)
            continue
        
        # Job 파일의 sys.path 설정 수정
        spec = importlib.util.spec_from_file_location("job_module", job_file)
        job_module = importlib.util.module_from_spec(spec)
        
        # sys.path 수정: /app 대신 프로젝트 루트 사용
        original_path = sys.path.copy()
        if '/app' in sys.path:
            sys.path.remove('/app')
        sys.path.insert(0, str(PROJECT_ROOT))
        
        try:
            spec.loader.exec_module(job_module)
            print(f"✅ [{job_name}] Job 완료!", file=sys.stderr)
        except SystemExit as e:
            if e.code != 0:
                print(f"❌ [{job_name}] Job 실패 (exit code: {e.code})", file=sys.stderr)
                sys.exit(1)
        except Exception as e:
            print(f"❌ [{job_name}] Job 실행 중 오류: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            sys.exit(1)
        finally:
            sys.path[:] = original_path
    
    print("", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print("✅ 모든 Job 실행 완료!", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
