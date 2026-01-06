"""
스냅샷 데이터의 실제 날짜 범위 확인 스크립트
"""
import os
import sys
import json
import gzip
from datetime import date
from google.cloud import bigquery
from google.cloud import storage

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "winged-precept-443218-v8")
DATASET = "ngn_dataset"
GCS_BUCKET = os.environ.get("GCS_BUCKET", "winged-precept-443218-v8.appspot.com")

def check_bigquery_dates(company_name: str, year: int, month: int):
    """BigQuery 테이블에서 실제 날짜 범위 확인"""
    client = bigquery.Client(project=PROJECT_ID)
    
    # 1. daily_cafe24_sales 테이블 확인
    query = f"""
    SELECT 
        MIN(payment_date) AS min_date,
        MAX(payment_date) AS max_date,
        COUNT(DISTINCT payment_date) AS date_count
    FROM `{PROJECT_ID}.{DATASET}.daily_cafe24_sales`
    WHERE company_name = @company_name
      AND payment_date >= @start_date
      AND payment_date <= @end_date
    """
    
    start_date = date(year, month, 1).isoformat()
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)
    end_date = (end_date - date.resolution).isoformat()  # 월말
    
    rows = list(
        client.query(
            query,
            job_config=bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("company_name", "STRING", company_name),
                    bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
                    bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
                ]
            ),
        ).result()
    )
    
    if rows:
        row = rows[0]
        print(f"📊 BigQuery daily_cafe24_sales 테이블:")
        print(f"   최소 날짜: {row.min_date}")
        print(f"   최대 날짜: {row.max_date}")
        print(f"   날짜 개수: {row.date_count}")
        print(f"   예상 날짜 개수: 31일")
        if row.max_date and row.max_date.isoformat() < end_date:
            print(f"   ⚠️ 경고: 월말({end_date})까지 데이터가 없습니다!")
    
    # 2. 일별 데이터 상세 확인 (마지막 5일)
    query2 = f"""
    SELECT 
        payment_date,
        SUM(net_sales) AS net_sales,
        SUM(total_orders) AS total_orders
    FROM `{PROJECT_ID}.{DATASET}.daily_cafe24_sales`
    WHERE company_name = @company_name
      AND payment_date >= @start_date
      AND payment_date <= @end_date
    GROUP BY payment_date
    ORDER BY payment_date DESC
    LIMIT 5
    """
    
    rows2 = list(
        client.query(
            query2,
            job_config=bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("company_name", "STRING", company_name),
                    bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
                    bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
                ]
            ),
        ).result()
    )
    
    print(f"\n📅 일별 매출 데이터 (마지막 5일):")
    for row in rows2:
        print(f"   {row.payment_date}: 매출 {row.net_sales:,.0f}원, 주문 {row.total_orders}건")


def check_gcs_snapshot(company_name: str, year: int, month: int):
    """GCS 스냅샷 파일에서 실제 날짜 범위 확인"""
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(GCS_BUCKET)
    blob_path = f"ai-reports/monthly/{company_name}/{year}-{month:02d}/snapshot.json.gz"
    blob = bucket.blob(blob_path)
    
    if not blob.exists():
        print(f"❌ GCS 스냅샷 파일이 없습니다: {blob_path}")
        return
    
    # 파일 다운로드 및 파싱
    file_bytes = blob.download_as_bytes(raw_download=True)
    decompressed = gzip.decompress(file_bytes)
    snapshot = json.loads(decompressed.decode('utf-8'))
    
    # 스냅샷 생성 시간 확인
    print(f"\n📦 GCS 스냅샷 파일:")
    print(f"   경로: {blob_path}")
    print(f"   생성 시간: {blob.time_created}")
    print(f"   수정 시간: {blob.updated}")
    
    # daily_this 데이터 확인
    daily_this = snapshot.get("facts", {}).get("mall_sales", {}).get("daily_this", [])
    if daily_this:
        dates = [item.get("date") for item in daily_this if item.get("date")]
        if dates:
            dates.sort()
            print(f"\n📊 스냅샷 내 daily_this 데이터:")
            print(f"   최소 날짜: {dates[0]}")
            print(f"   최대 날짜: {dates[-1]}")
            print(f"   날짜 개수: {len(dates)}")
            print(f"   예상 날짜 개수: 31일")
            
            # 마지막 5일 확인
            print(f"\n📅 스냅샷 일별 매출 데이터 (마지막 5일):")
            for item in sorted(daily_this, key=lambda x: x.get("date", ""), reverse=True)[:5]:
                print(f"   {item.get('date')}: 매출 {item.get('net_sales', 0):,.0f}원, 주문 {item.get('total_orders', 0)}건")
            
            # 월말 데이터 확인
            expected_end = f"{year}-{month:02d}-31"
            if dates[-1] < expected_end:
                print(f"\n   ⚠️ 경고: 월말({expected_end})까지 데이터가 없습니다!")
                print(f"   마지막 날짜: {dates[-1]}")
    else:
        print(f"   ⚠️ daily_this 데이터가 없습니다.")


if __name__ == "__main__":
    company_name = "piscess"
    year = 2025
    month = 12
    
    print(f"🔍 스냅샷 데이터 날짜 범위 확인")
    print(f"   회사: {company_name}")
    print(f"   년월: {year}-{month:02d}\n")
    
    # BigQuery 확인
    print("=" * 60)
    check_bigquery_dates(company_name, year, month)
    
    # GCS 스냅샷 확인
    print("\n" + "=" * 60)
    check_gcs_snapshot(company_name, year, month)





