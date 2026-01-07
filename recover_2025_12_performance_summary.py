"""
2025년 12월 performance_summary_ngn 재수집 스크립트
"""
import sys
import os
from datetime import datetime, timedelta, timezone

# 프로젝트 루트를 Python path에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'ngn_wep', 'dashboard', 'services')))

from insert_performance_summary import insert_performance_summary

# ✅ KST 설정
KST = timezone(timedelta(hours=9))

def main():
    print("=" * 60)
    print("🔧 2025년 12월 performance_summary_ngn 재수집 시작")
    print("=" * 60)
    
    # 2025년 12월 1일 ~ 31일
    start_date = datetime(2025, 12, 1).date()
    end_date = datetime(2025, 12, 31).date()
    
    current_date = start_date
    total_days = (end_date - start_date).days + 1
    day_count = 0
    
    while current_date <= end_date:
        day_count += 1
        print(f"\n📅 [{day_count}/{total_days}] {current_date} 처리 중...")
        print("-" * 60)
        
        try:
            insert_performance_summary(current_date, update_cart_signup_only=False)
            print(f"✅ {current_date} 완료!")
        except Exception as e:
            print(f"❌ {current_date} 실패: {e}")
            import traceback
            traceback.print_exc()
        
        current_date += timedelta(days=1)
    
    print("\n" + "=" * 60)
    print("✅ 2025년 12월 performance_summary_ngn 재수집 완료!")
    print("=" * 60)

if __name__ == "__main__":
    main()

