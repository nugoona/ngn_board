#!/usr/bin/env python
"""
로컬 캐시 무효화 스크립트
사용법:
  python clear_cache_local.py                    # 전체 캐시 삭제
  python clear_cache_local.py cafe24_product_sales  # 특정 패턴만 삭제
"""
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ngn_wep.dashboard.utils.cache_utils import invalidate_cache_by_pattern, clear_all_cache

def main():
    if len(sys.argv) > 1:
        pattern = sys.argv[1]
        print(f"캐시 무효화 중: {pattern}")
        deleted_count = invalidate_cache_by_pattern(pattern)
        print(f"✅ {deleted_count}개 캐시 키가 삭제되었습니다.")
    else:
        print("전체 캐시 삭제 중...")
        clear_all_cache()
        print("✅ 전체 캐시가 삭제되었습니다.")

if __name__ == "__main__":
    main()

