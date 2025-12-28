#!/usr/bin/env python3
"""
과거 월간 집계 데이터 채우기 스크립트
사용법: python3 fill_past_months.py <start_year> <start_month> <end_year> <end_month>
예: python3 fill_past_months.py 2024 1 2025 11
"""

import os
import sys
from datetime import date, timedelta
from google.cloud import bigquery

# monthly_rollup_job의 함수들을 import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from monthly_rollup_job import (
    create_tables_if_not_exists,
    merge_mall_sales_monthly,
    merge_meta_ads_monthly,
    merge_ga4_traffic_monthly,
    merge_ga4_viewitem_monthly_raw,
    PROJECT_ID,
    DATASET,
)


def month_range(year: int, month: int):
    """월 시작~월말(end inclusive)"""
    start = date(year, month, 1)
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    end = next_month - timedelta(days=1)
    return start.isoformat(), end.isoformat()


def month_to_ym(year: int, month: int) -> str:
    """YYYY-MM 형식으로 변환"""
    return f"{year:04d}-{month:02d}"


def fill_months(start_year: int, start_month: int, end_year: int, end_month: int):
    """지정된 기간의 모든 월 데이터 채우기"""
    client = bigquery.Client(project=PROJECT_ID)
    
    print(f"[INFO] PROJECT_ID={PROJECT_ID} DATASET={DATASET}")
    print(f"[INFO] 기간: {start_year}-{start_month:02d} ~ {end_year}-{end_month:02d}")
    
    # 테이블 생성 확인
    print("[INFO] Checking/creating monthly tables...")
    create_tables_if_not_exists(client)
    
    # 각 월 처리
    current = date(start_year, start_month, 1)
    end_date = date(end_year, end_month, 1)
    
    months_processed = 0
    while current <= end_date:
        year = current.year
        month = current.month
        start_date, end_date_str = month_range(year, month)
        ym = month_to_ym(year, month)
        
        print(f"\n[INFO] Processing {ym} ({start_date} ~ {end_date_str})...")
        
        try:
            merge_mall_sales_monthly(client, start_date, end_date_str)
            merge_meta_ads_monthly(client, start_date, end_date_str)
            merge_ga4_traffic_monthly(client, start_date, end_date_str)
            merge_ga4_viewitem_monthly_raw(client, start_date, end_date_str, ym)
            print(f"[OK] {ym} 완료")
            months_processed += 1
        except Exception as e:
            print(f"[ERROR] {ym} 실패: {e}")
        
        # 다음 달로 이동
        if month == 12:
            current = date(year + 1, 1, 1)
        else:
            current = date(year, month + 1, 1)
    
    print(f"\n[DONE] 총 {months_processed}개월 처리 완료")


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python3 fill_past_months.py <start_year> <start_month> <end_year> <end_month>")
        print("Example: python3 fill_past_months.py 2024 1 2025 11")
        sys.exit(1)
    
    start_year = int(sys.argv[1])
    start_month = int(sys.argv[2])
    end_year = int(sys.argv[3])
    end_month = int(sys.argv[4])
    
    fill_months(start_year, start_month, end_year, end_month)

