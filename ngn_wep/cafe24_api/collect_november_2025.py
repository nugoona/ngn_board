"""
2025년 11월 daily_cafe24_sales 재집계 스크립트
- 11월 1일 ~ 30일 전체 재집계
"""
from daily_cafe24_sales_handler import run_query
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def main():
    logging.info("=" * 60)
    logging.info("2025년 11월 데이터 재집계 시작")
    logging.info("=" * 60)

    success = 0
    fail = 0

    for day in range(1, 31):
        date_str = f"2025-11-{day:02d}"
        logging.info(f"[{day}/30] {date_str} 처리 중...")
        try:
            run_query(date_str)
            success += 1
        except Exception as e:
            logging.error(f"{date_str} 실패: {e}")
            fail += 1

    logging.info("=" * 60)
    logging.info(f"완료! 성공: {success}, 실패: {fail}")
    logging.info("=" * 60)

if __name__ == "__main__":
    main()
