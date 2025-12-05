"""
BigQuery 테이블 구조 확인 스크립트
실제 테이블의 날짜 컬럼과 타입을 확인합니다.
"""

import os
from google.cloud import bigquery

PROJECT_ID = "winged-precept-443218-v8"
DATASET_ID = "ngn_dataset"

def get_bigquery_client():
    return bigquery.Client(project=PROJECT_ID)

def check_table_schema(client, table_id):
    """테이블 스키마 확인"""
    try:
        table_ref = client.dataset(DATASET_ID).table(table_id)
        table = client.get_table(table_ref)
        
        date_columns = []
        for field in table.schema:
            if field.field_type in ['DATE', 'TIMESTAMP', 'DATETIME']:
                date_columns.append({
                    "name": field.name,
                    "type": field.field_type,
                    "mode": field.mode
                })
        
        return {
            "exists": True,
            "date_columns": date_columns,
            "total_fields": len(table.schema)
        }
    except Exception as e:
        return {
            "exists": False,
            "error": str(e)
        }

def main():
    client = get_bigquery_client()
    
    # 데이터셋의 모든 테이블 목록 가져오기
    dataset_ref = client.dataset(DATASET_ID)
    tables = list(client.list_tables(dataset_ref))
    
    print(f"📊 {DATASET_ID} 데이터셋의 테이블 목록 ({len(tables)}개)\n")
    print("=" * 80)
    
    results = {}
    
    for table in tables:
        table_id = table.table_id
        schema_info = check_table_schema(client, table_id)
        results[table_id] = schema_info
        
        if schema_info.get("exists"):
            date_cols = schema_info.get("date_columns", [])
            if date_cols:
                print(f"✅ {table_id}")
                print(f"   날짜 컬럼: {len(date_cols)}개")
                for col in date_cols:
                    print(f"     - {col['name']} ({col['type']}, {col['mode']})")
                print()
            else:
                print(f"⚠️  {table_id} - 날짜 컬럼 없음\n")
        else:
            print(f"❌ {table_id} - 테이블 없음: {schema_info.get('error')}\n")
    
    print("=" * 80)
    print("\n📋 날짜 컬럼이 있는 테이블 요약:")
    print("-" * 80)
    
    for table_id, info in results.items():
        if info.get("exists") and info.get("date_columns"):
            cols = [f"{c['name']} ({c['type']})" for c in info["date_columns"]]
            print(f"{table_id}: {', '.join(cols)}")

if __name__ == "__main__":
    main()
