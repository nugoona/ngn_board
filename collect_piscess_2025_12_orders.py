"""
piscess 2025년 12월 주문 데이터 재수집 스크립트
"""
import sys
import os
from datetime import datetime, timedelta

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from ngn_wep.cafe24_api.orders_handler import (
    fetch_orders_data,
    upload_to_temp_table,
    merge_temp_to_main,
    download_tokens
)
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def main():
    logging.info("=" * 60)
    logging.info("🔧 piscess 2025년 12월 주문 데이터 재수집 시작")
    logging.info("=" * 60)
    
    # 2025년 12월 1일 ~ 31일
    start_date = datetime(2025, 12, 1).date()
    end_date = datetime(2025, 12, 31).date()
    
    logging.info(f"📅 수집 기간: {start_date} ~ {end_date}")
    
    # piscess1 토큰 가져오기
    tokens = download_tokens()
    mall_id = 'piscess1'
    
    if mall_id not in tokens:
        logging.error(f"❌ {mall_id}의 토큰을 찾을 수 없습니다!")
        return
    
    access_token = tokens[mall_id].get("access_token")
    if not access_token:
        logging.error(f"❌ {mall_id}의 access_token이 없습니다!")
        return
    
    logging.info(f"✅ {mall_id} 토큰 확인 완료")
    
    # 주문 데이터 수집
    logging.info(f"📦 주문 데이터 수집 중... (기간: {start_date} ~ {end_date})")
    all_orders = fetch_orders_data(mall_id, access_token, start_date, end_date)
    
    logging.info(f"✅ 수집 완료: {len(all_orders)}건")
    
    if all_orders:
        # 임시 테이블 업로드
        logging.info("📤 BigQuery 임시 테이블 업로드 중...")
        upload_to_temp_table(all_orders)
        
        # 메인 테이블 병합
        logging.info("🔄 메인 테이블 병합 중...")
        merge_temp_to_main()
        
        logging.info("=" * 60)
        logging.info(f"✅ piscess 2025년 12월 주문 데이터 재수집 완료!")
        logging.info(f"   총 {len(all_orders)}건의 주문 데이터가 업데이트되었습니다.")
        logging.info("=" * 60)
    else:
        logging.warning("⚠️ 수집된 주문 데이터가 없습니다.")

if __name__ == "__main__":
    main()

