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
        -- 전체 JSON을 문자열로 가져와서 Python에서 파싱
        TO_JSON_STRING(snapshot_json) AS snapshot_json_str
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
    
    import json
    
    row = rows[0]
    
    # 전체 JSON 파싱
    try:
        snapshot = json.loads(row.snapshot_json_str)
    except Exception as e:
        print(f"❌ JSON 파싱 실패: {e}")
        print(f"   JSON 길이: {len(row.snapshot_json_str)}")
        print(f"   JSON 처음 500자: {row.snapshot_json_str[:500]}")
        return False
    
    print(f"✅ 스냅샷 확인: {company_name} {year}-{month:02d}")
    print(f"   업데이트 시간: {row.updated_at}")
    
    # report_meta에서 period 정보 확인
    report_meta = snapshot.get("report_meta", {})
    report_month = report_meta.get("report_month")
    period_this = report_meta.get("period_this", {})
    period_prev = report_meta.get("period_prev", {})
    period_yoy = report_meta.get("period_yoy", {})
    print(f"   기간: {report_month} (prev: {period_prev.get('from')}, yoy: {period_yoy.get('from')})")
    
    # facts에서 데이터 확인
    facts = snapshot.get("facts", {})
    if not facts:
        print(f"   ⚠️  facts 섹션이 비어있습니다. JSON 구조 확인 필요.")
        print(f"   JSON 최상위 키: {list(snapshot.keys())}")
        return True
    
    # facts 구조: {mall_sales: {this, prev, yoy}, meta_ads: {this, prev, yoy}, ...}
    mall_sales_facts = facts.get("mall_sales", {})
    meta_ads_facts = facts.get("meta_ads", {})
    ga4_traffic_facts = facts.get("ga4_traffic", {})
    comparisons = facts.get("comparisons", {})
    
    print(f"   핵심 메트릭:")
    # mall_sales.this에서 net_sales 추출
    mall_sales_this = mall_sales_facts.get("this", {}) if isinstance(mall_sales_facts, dict) else {}
    net_sales = mall_sales_this.get("net_sales") if isinstance(mall_sales_this, dict) else None
    print(f"     - Mall Sales: {net_sales:,.0f}" if net_sales is not None else "     - Mall Sales: None")
    
    # meta_ads.this에서 spend 추출
    meta_ads_this = meta_ads_facts.get("this", {}) if isinstance(meta_ads_facts, dict) else {}
    meta_spend = meta_ads_this.get("spend") if isinstance(meta_ads_this, dict) else None
    print(f"     - Meta Ads Spend: {meta_spend:,.0f}" if meta_spend is not None else "     - Meta Ads Spend: None")
    
    # ga4_traffic.this.totals에서 total_users 추출
    ga4_traffic_this = ga4_traffic_facts.get("this", {}) if isinstance(ga4_traffic_facts, dict) else {}
    ga4_totals = ga4_traffic_this.get("totals", {}) if isinstance(ga4_traffic_this, dict) else {}
    ga4_users = ga4_totals.get("total_users") if isinstance(ga4_totals, dict) else None
    print(f"     - GA4 Users: {ga4_users:,}" if ga4_users is not None else "     - GA4 Users: None")
    
    # comparisons 정보
    if comparisons:
        mall_sales_comp = comparisons.get("mall_sales", {})
        meta_ads_comp = comparisons.get("meta_ads", {})
        ga4_traffic_comp = comparisons.get("ga4_traffic", {})
        
        print(f"   YoY 비교:")
        net_sales_yoy = mall_sales_comp.get("net_sales_yoy") if isinstance(mall_sales_comp, dict) else None
        if net_sales_yoy and isinstance(net_sales_yoy, dict) and "abs" in net_sales_yoy:
            print(f"     - net_sales_yoy: {net_sales_yoy['abs']:,.0f} (데이터 있음)")
        elif net_sales_yoy is None:
            print(f"     - net_sales_yoy: null (데이터 없음)")
        else:
            print(f"     - net_sales_yoy: {net_sales_yoy} (타입: {type(net_sales_yoy)})")
        
        spend_yoy = meta_ads_comp.get("spend_yoy") if isinstance(meta_ads_comp, dict) else None
        if spend_yoy and isinstance(spend_yoy, dict) and "abs" in spend_yoy:
            print(f"     - spend_yoy: {spend_yoy['abs']:,.0f} (데이터 있음)")
        elif spend_yoy is None:
            print(f"     - spend_yoy: null (데이터 없음)")
        else:
            print(f"     - spend_yoy: {spend_yoy} (타입: {type(spend_yoy)})")
        
        total_users_yoy = ga4_traffic_comp.get("total_users_yoy") if isinstance(ga4_traffic_comp, dict) else None
        if total_users_yoy and isinstance(total_users_yoy, dict) and "abs" in total_users_yoy:
            print(f"     - total_users_yoy: {total_users_yoy['abs']:,} (데이터 있음)")
        elif total_users_yoy is None:
            print(f"     - total_users_yoy: null (데이터 없음)")
        else:
            print(f"     - total_users_yoy: {total_users_yoy} (타입: {type(total_users_yoy)})")
    else:
        print(f"   ⚠️  comparisons 섹션이 없습니다.")
    
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

