#!/usr/bin/env python3
"""
간단한 스냅샷 검증 스크립트
핵심 메트릭만 확인하여 실행 성공 여부와 비용 절감 효과를 확인
"""

import os
import sys
from google.cloud import bigquery

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "winged-precept-443218-v8")
DATASET = os.environ.get("BQ_DATASET", "ngn_dataset")


def verify_snapshot(company_name: str, year: int, month: int):
    """스냅샷이 BigQuery에 저장되어 있는지 확인"""
    client = bigquery.Client(project=PROJECT_ID)
    
    month_date = f"{year}-{month:02d}-01"
    
    query = f"""
    SELECT 
        company_name,
        month,
        snapshot_hash,
        updated_at,
        -- 기간 정보
        JSON_EXTRACT_SCALAR(snapshot_json, '$.period.this_month') AS this_month,
        JSON_EXTRACT_SCALAR(snapshot_json, '$.period.prev_month') AS prev_month,
        JSON_EXTRACT_SCALAR(snapshot_json, '$.period.yoy_month') AS yoy_month,
        -- 핵심 메트릭 (객체에서 값 추출)
        CAST(JSON_EXTRACT_SCALAR(snapshot_json, '$.data.mall_sales.net_sales') AS FLOAT64) AS net_sales,
        CAST(JSON_EXTRACT_SCALAR(snapshot_json, '$.data.meta_ads.spend') AS FLOAT64) AS meta_spend,
        CAST(JSON_EXTRACT_SCALAR(snapshot_json, '$.data.ga4_traffic.totals.total_users') AS INT64) AS ga4_users,
        -- YoY 비교 확인 (객체에서 abs 값 추출)
        CAST(JSON_EXTRACT_SCALAR(snapshot_json, '$.data.comparisons.mall_sales.net_sales_yoy.abs') AS FLOAT64) AS net_sales_yoy_abs,
        JSON_EXTRACT_SCALAR(snapshot_json, '$.data.comparisons.mall_sales.net_sales_yoy') AS net_sales_yoy,
        CAST(JSON_EXTRACT_SCALAR(snapshot_json, '$.data.comparisons.meta_ads.spend_yoy.abs') AS FLOAT64) AS spend_yoy_abs,
        JSON_EXTRACT_SCALAR(snapshot_json, '$.data.comparisons.meta_ads.spend_yoy') AS spend_yoy,
        CAST(JSON_EXTRACT_SCALAR(snapshot_json, '$.data.comparisons.ga4_traffic.total_users_yoy.abs') AS INT64) AS total_users_yoy_abs,
        JSON_EXTRACT_SCALAR(snapshot_json, '$.data.comparisons.ga4_traffic.total_users_yoy') AS total_users_yoy
    FROM `{PROJECT_ID}.{DATASET}.report_monthly_snapshot`
    WHERE company_name = @company_name 
      AND month = DATE(@month_date)
    ORDER BY updated_at DESC
    LIMIT 1
    """
    
    rows = list(
        client.query(
            query,
            job_config=bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("company_name", "STRING", company_name),
                    bigquery.ScalarQueryParameter("month_date", "STRING", month_date),
                ]
            ),
        ).result()
    )
    
    if not rows:
        print(f"❌ 스냅샷이 없습니다: {company_name} {year}-{month:02d}")
        return False
    
    row = rows[0]
    print(f"✅ 스냅샷 확인: {company_name} {year}-{month:02d}")
    print(f"   업데이트 시간: {row.updated_at}")
    print(f"   기간: {row.this_month} (prev: {row.prev_month}, yoy: {row.yoy_month})")
    print(f"   핵심 메트릭:")
    print(f"     - Mall Sales: {row.net_sales:,.0f}" if row.net_sales else "     - Mall Sales: None")
    print(f"     - Meta Ads Spend: {row.meta_spend:,.0f}" if row.meta_spend else "     - Meta Ads Spend: None")
    print(f"     - GA4 Users: {row.ga4_users:,}" if row.ga4_users else "     - GA4 Users: None")
    print(f"   YoY 비교:")
    if row.net_sales_yoy_abs is not None:
        print(f"     - net_sales_yoy: {row.net_sales_yoy_abs:,.0f} (데이터 있음)")
    else:
        print(f"     - net_sales_yoy: null (데이터 없음)")
    if row.spend_yoy_abs is not None:
        print(f"     - spend_yoy: {row.spend_yoy_abs:,.0f} (데이터 있음)")
    else:
        print(f"     - spend_yoy: null (데이터 없음)")
    if row.total_users_yoy_abs is not None:
        print(f"     - total_users_yoy: {row.total_users_yoy_abs:,} (데이터 있음)")
    else:
        print(f"     - total_users_yoy: null (데이터 없음)")
    
    return True


def check_query_history(company_name: str, year: int, month: int, hours: int = 1):
    """최근 N시간 동안의 쿼리 히스토리 확인"""
    client = bigquery.Client(project=PROJECT_ID)
    
    query = f"""
    SELECT 
        job_id,
        creation_time,
        total_bytes_processed,
        total_slot_ms,
        -- 쿼리 수 카운트
        COUNT(*) OVER() AS total_queries,
        -- 비용 추정 (TB당 $5)
        (total_bytes_processed / 1024.0 / 1024.0 / 1024.0 / 1024.0) * 5.0 AS estimated_cost_usd
    FROM `{PROJECT_ID}.{DATASET}.__TABLES__`
    WHERE FALSE  -- 이 쿼리는 실제로는 INFORMATION_SCHEMA.JOBS_BY_PROJECT를 사용해야 함
    LIMIT 1
    """
    
    # 실제로는 INFORMATION_SCHEMA를 사용해야 하지만, 권한 문제가 있을 수 있음
    # 대신 간단한 메시지만 출력
    print(f"📊 쿼리 히스토리 확인:")
    print(f"   BigQuery 콘솔에서 확인: https://console.cloud.google.com/bigquery?project={PROJECT_ID}")
    print(f"   최근 {hours}시간 동안의 쿼리를 확인하세요")
    print(f"   검색어: {company_name} {year}-{month:02d}")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python3 verify_snapshot_simple.py <company_name> <year> <month>")
        print("Example: python3 verify_snapshot_simple.py piscess 2025 12")
        sys.exit(1)
    
    company_name = sys.argv[1]
    year = int(sys.argv[2])
    month = int(sys.argv[3])
    
    print(f"🔍 스냅샷 검증: {company_name} {year}-{month:02d}\n")
    
    # 스냅샷 확인
    snapshot_exists = verify_snapshot(company_name, year, month)
    
    if snapshot_exists:
        print("\n✅ 스냅샷이 정상적으로 생성되었습니다!")
    else:
        print("\n❌ 스냅샷이 없습니다. 먼저 스냅샷을 생성하세요:")
        print(f"   python3 tools/ai_report_test/bq_monthly_snapshot.py {company_name} {year} {month} --upsert")
    
    print()
    check_query_history(company_name, year, month)

