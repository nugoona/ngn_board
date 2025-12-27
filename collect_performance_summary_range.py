#!/usr/bin/env python3
"""
성과 요약 데이터 일괄 수집 스크립트
사용법: python collect_performance_summary_range.py 2024-12-01 2025-12-25

실행 위치: 프로젝트 루트 (ngn_board)에서 실행
예시: cd ~/ngn_board && python collect_performance_summary_range.py 2024-12-01 2025-12-25
"""
import sys
from datetime import datetime, timedelta

# insert_performance_summary 함수 import (프로젝트 루트에서 실행하므로 직접 import 가능)
from ngn_wep.dashboard.services.insert_performance_summary import insert_performance_summary

def main():
    if len(sys.argv) < 3:
        print("사용법: python collect_performance_summary_range.py <시작일> <종료일>")
        print("예시: python collect_performance_summary_range.py 2024-12-01 2025-12-25")
        sys.exit(1)
    
    try:
        start_date = datetime.strptime(sys.argv[1], '%Y-%m-%d').date()
        end_date = datetime.strptime(sys.argv[2], '%Y-%m-%d').date()
    except ValueError as e:
        print(f"❌ 날짜 형식 오류: {e}")
        print("날짜 형식은 YYYY-MM-DD여야 합니다.")
        sys.exit(1)
    
    if start_date > end_date:
        print("❌ 시작일이 종료일보다 늦을 수 없습니다.")
        sys.exit(1)
    
    current_date = start_date
    total_days = (end_date - start_date).days + 1
    current_day = 0
    success_count = 0
    fail_count = 0
    
    print("="*50)
    print(f"성과 요약 데이터 수집 시작")
    print(f"기간: {start_date} ~ {end_date}")
    print(f"총 {total_days}일치")
    print("="*50)
    
    while current_date <= end_date:
        current_day += 1
        date_str = current_date.strftime('%Y-%m-%d')
        print(f"\n[{current_day}/{total_days}] {date_str} 처리 중...")
        
        try:
            insert_performance_summary(current_date)
            print(f"✅ {date_str} 완료")
            success_count += 1
        except Exception as e:
            print(f"❌ {date_str} 실패: {e}")
            import traceback
            traceback.print_exc()
            fail_count += 1
        
        current_date += timedelta(days=1)
    
    print("\n" + "="*50)
    print(f"수집 완료")
    print(f"  성공: {success_count}일")
    print(f"  실패: {fail_count}일")
    print(f"  전체: {total_days}일")
    print("="*50)

if __name__ == "__main__":
    main()
