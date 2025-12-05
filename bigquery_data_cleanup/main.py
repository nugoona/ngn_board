"""
BigQuery 오래된 데이터 자동 삭제 Cloud Run 서비스
한 달에 한 번씩 Cloud Scheduler로 호출되어 13개월 이전 데이터를 삭제합니다.
"""

import os
import logging
from datetime import datetime, timedelta, timezone
from flask import Flask, request, jsonify
from google.cloud import bigquery

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

app = Flask(__name__)

# BigQuery 설정
PROJECT_ID = os.getenv("PROJECT_ID", "winged-precept-443218-v8")
DATASET_ID = os.getenv("DATASET_ID", "ngn_dataset")
MONTHS_TO_KEEP = int(os.getenv("MONTHS_TO_KEEP", "13"))

# KST 시간대
KST = timezone(timedelta(hours=9))

# 테이블별 날짜 컬럼 매핑 (타입 정보 포함)
# 테이블명: [{"name": "컬럼명", "type": "타입"}] 또는 자동 탐지
# 타입: DATE, TIMESTAMP, DATETIME
TABLE_DATE_COLUMNS = {
    # Cafe24 관련 - TIMESTAMP 타입으로 저장됨
    "cafe24_orders": [{"name": "payment_date", "type": "TIMESTAMP"}],
    "cafe24_order_items_table": [
        {"name": "ordered_date", "type": "TIMESTAMP"},
        {"name": "payment_date", "type": "TIMESTAMP"}
    ],
    "daily_cafe24_sales": [{"name": "payment_date", "type": "TIMESTAMP"}],
    "daily_cafe24_items": [{"name": "payment_date", "type": "TIMESTAMP"}],
    "cafe24_products_table": [],  # 날짜 컬럼 없을 수 있음
    "cafe24_categories_table": [],  # 날짜 컬럼 없을 수 있음
    
    # Meta Ads 관련 - DATE 타입
    "meta_ads_ad_level": [{"name": "date", "type": "DATE"}],
    "ads_performance": [{"name": "date", "type": "DATE"}],
    "meta_ads_account_summary": [{"name": "date", "type": "DATE"}],
    "meta_ads_adset_summary": [{"name": "date", "type": "DATE"}],
    "meta_ads_campaign_summary": [{"name": "date", "type": "DATE"}],
    "highest_spend_data": [{"name": "date", "type": "DATE"}],
    
    # GA4 관련 - TIMESTAMP 타입
    "ga4_traffic_ngn": [{"name": "event_date", "type": "TIMESTAMP"}],
    "ga4_viewitem_ngn": [{"name": "event_date", "type": "TIMESTAMP"}],
    
    # 기타
    "performance_summary_ngn": [{"name": "date", "type": "DATE"}],
    "sheets_platform_sales_data": [],  # 확인 필요
}

def get_bigquery_client():
    """BigQuery 클라이언트 생성"""
    return bigquery.Client(project=PROJECT_ID)

def get_table_schema(client, table_id):
    """테이블 스키마에서 날짜 컬럼 찾기 (타입 정보 포함)"""
    try:
        table_ref = client.dataset(DATASET_ID).table(table_id)
        table = client.get_table(table_ref)
        
        date_columns = []
        for field in table.schema:
            if field.field_type in ['DATE', 'TIMESTAMP', 'DATETIME']:
                date_columns.append({
                    "name": field.name,
                    "type": field.field_type
                })
        
        return date_columns
    except Exception as e:
        logging.warning(f"테이블 {table_id} 스키마 확인 실패: {e}")
        return []

def check_table_exists(client, table_id):
    """테이블 존재 여부 확인"""
    try:
        table_ref = client.dataset(DATASET_ID).table(table_id)
        client.get_table(table_ref)
        return True
    except Exception:
        return False

def get_date_condition(date_column_name, date_column_type, cutoff_date):
    """날짜 컬럼 타입에 따라 적절한 WHERE 조건 생성"""
    if date_column_type == 'DATE':
        return f"DATE({date_column_name}) < DATE('{cutoff_date}')"
    elif date_column_type == 'TIMESTAMP':
        # TIMESTAMP는 타임존 고려하여 KST로 변환
        return f"DATE(TIMESTAMP({date_column_name}), 'Asia/Seoul') < DATE('{cutoff_date}')"
    elif date_column_type == 'DATETIME':
        return f"DATE({date_column_name}) < DATE('{cutoff_date}')"
    else:
        # 기본값: DATE로 가정
        return f"DATE({date_column_name}) < DATE('{cutoff_date}')"

def count_old_rows(client, table_id, date_column_info, cutoff_date):
    """삭제될 행 수 확인"""
    date_column_name = date_column_info if isinstance(date_column_info, str) else date_column_info["name"]
    date_column_type = date_column_info.get("type", "DATE") if isinstance(date_column_info, dict) else "DATE"
    
    condition = get_date_condition(date_column_name, date_column_type, cutoff_date)
    query = f"""
    SELECT COUNT(*) as count
    FROM `{PROJECT_ID}.{DATASET_ID}.{table_id}`
    WHERE {condition}
    """
    try:
        result = client.query(query).result()
        return list(result)[0].count
    except Exception as e:
        logging.error(f"행 수 확인 실패 ({table_id}.{date_column_name}): {e}")
        return 0

def delete_old_data(client, table_id, date_column_info, cutoff_date):
    """오래된 데이터 삭제"""
    date_column_name = date_column_info if isinstance(date_column_info, str) else date_column_info["name"]
    date_column_type = date_column_info.get("type", "DATE") if isinstance(date_column_info, dict) else "DATE"
    
    condition = get_date_condition(date_column_name, date_column_type, cutoff_date)
    delete_query = f"""
    DELETE FROM `{PROJECT_ID}.{DATASET_ID}.{table_id}`
    WHERE {condition}
    """
    
    try:
        query_job = client.query(delete_query)
        query_job.result()  # 작업 완료 대기
        deleted_rows = query_job.num_dml_affected_rows
        logging.info(f"✅ {table_id}: {deleted_rows}개 행 삭제 완료 (날짜 컬럼: {date_column_name}, 타입: {date_column_type})")
        return deleted_rows
    except Exception as e:
        logging.error(f"❌ {table_id} 삭제 실패: {e}")
        raise

@app.route("/", methods=["GET", "POST"])
def cleanup_old_data():
    """메인 엔드포인트 - Cloud Scheduler가 호출"""
    try:
        # 삭제 기준 날짜 계산
        cutoff_date = (datetime.now(KST) - timedelta(days=MONTHS_TO_KEEP * 30)).date()
        
        logging.info(f"🔍 BigQuery 오래된 데이터 삭제 시작")
        logging.info(f"📅 삭제 기준 날짜: {cutoff_date} ({MONTHS_TO_KEEP}개월 이전)")
        logging.info(f"📊 프로젝트: {PROJECT_ID}, 데이터셋: {DATASET_ID}")
        
        client = get_bigquery_client()
        
        # 데이터셋의 모든 테이블 목록 가져오기
        dataset_ref = client.dataset(DATASET_ID)
        tables = list(client.list_tables(dataset_ref))
        
        results = {
            "cutoff_date": str(cutoff_date),
            "processed_tables": [],
            "deleted_rows": 0,
            "errors": []
        }
        
        for table in tables:
            table_id = table.table_id
            logging.info(f"📋 처리 중: {table_id}")
            
            # 테이블 존재 확인
            if not check_table_exists(client, table_id):
                logging.warning(f"⚠️  테이블 {table_id} 존재하지 않음, 건너뜀")
                continue
            
            # 날짜 컬럼 확인
            date_columns = TABLE_DATE_COLUMNS.get(table_id, [])
            
            if not date_columns:
                # 스키마에서 날짜 컬럼 자동 탐지
                detected_columns = get_table_schema(client, table_id)
                if detected_columns:
                    date_columns = detected_columns
                    logging.info(f"📋 {table_id}: 자동 탐지된 날짜 컬럼 = {[c['name'] for c in detected_columns]}")
                else:
                    logging.info(f"ℹ️  {table_id}: 날짜 컬럼 없음, 건너뜀")
                    results["processed_tables"].append({
                        "table": table_id,
                        "status": "skipped",
                        "reason": "no_date_column"
                    })
                    continue
            
            # 각 날짜 컬럼에 대해 삭제 수행
            table_deleted = 0
            for date_column_info in date_columns:
                try:
                    # date_column_info가 문자열이면 dict로 변환
                    if isinstance(date_column_info, str):
                        date_column_info = {"name": date_column_info, "type": "DATE"}
                    
                    date_column_name = date_column_info["name"]
                    
                    # 삭제될 행 수 확인
                    old_count = count_old_rows(client, table_id, date_column_info, cutoff_date)
                    
                    if old_count == 0:
                        logging.info(f"✓ {table_id}.{date_column_name}: 삭제할 데이터 없음")
                        continue
                    
                    logging.info(f"📊 {table_id}.{date_column_name}: {old_count:,}개 행 삭제 예정")
                    
                    # 실제 삭제 실행
                    deleted = delete_old_data(client, table_id, date_column_info, cutoff_date)
                    table_deleted += deleted
                    
                except Exception as e:
                    date_col_name = date_column_info.get("name", "unknown") if isinstance(date_column_info, dict) else str(date_column_info)
                    error_msg = f"{table_id}.{date_col_name} 삭제 실패: {str(e)}"
                    logging.error(f"❌ {error_msg}")
                    results["errors"].append(error_msg)
            
            if table_deleted > 0:
                results["processed_tables"].append({
                    "table": table_id,
                    "status": "deleted",
                    "deleted_rows": table_deleted
                })
                results["deleted_rows"] += table_deleted
        
        logging.info(f"✅ 완료! 총 {results['deleted_rows']:,}개 행 삭제됨")
        logging.info(f"📋 처리된 테이블: {len(results['processed_tables'])}개")
        
        return jsonify({
            "success": True,
            "message": f"총 {results['deleted_rows']:,}개 행 삭제 완료",
            "results": results
        }), 200
        
    except Exception as e:
        error_msg = f"오류 발생: {str(e)}"
        logging.error(f"❌ {error_msg}")
        return jsonify({
            "success": False,
            "error": error_msg
        }), 500

@app.route("/health", methods=["GET"])
def health_check():
    """헬스 체크 엔드포인트"""
    return jsonify({"status": "healthy"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
