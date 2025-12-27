from datetime import datetime, timedelta, timezone
from google.cloud import bigquery
from googleapiclient.discovery import build
import os
import sys

# ✅ KST 설정
KST = timezone(timedelta(hours=9))

# ✅ 환경변수 기반 프로젝트 설정
PROJECT_ID = os.getenv("PROJECT_ID", "winged-precept-443218-v8")
DATASET_ID = os.getenv("DATASET_ID", "ngn_dataset")
TABLE_ID = os.getenv("TABLE_ID", "performance_summary_ngn")

def get_bq_client():
    return bigquery.Client()

# ✅ GA4 API 클라이언트 초기화 (ADC 사용)
analytics = build("analyticsdata", "v1beta")

def get_ga4_property_ids_by_company(company_name, client):
    """company_info 테이블에서 특정 업체의 GA4 Property ID 조회"""
    query = f"""
    SELECT ga4_property_id
    FROM `{PROJECT_ID}.{DATASET_ID}.company_info`
    WHERE LOWER(company_name) = LOWER('{company_name}')
      AND ga4_property_id IS NOT NULL
      AND ga4_property_id >= 10000
    LIMIT 1
    """
    try:
        results = client.query(query).result()
        for row in results:
            return int(row.ga4_property_id)
        return None
    except Exception as e:
        print(f"[WARN] GA4 Property ID 조회 실패 ({company_name}): {e}")
        return None

def fetch_ga4_cart_signup_data(property_id, target_date_str):
    """
    GA4 API에서 장바구니 사용자 수와 회원가입 수 조회
    
    Args:
        property_id: GA4 Property ID
        target_date_str: 날짜 문자열 (YYYY-MM-DD)
    
    Returns:
        dict: {'cart_users': int, 'signup_count': int}
    """
    result = {'cart_users': 0, 'signup_count': 0}
    
    if not property_id:
        return result
    
    try:
        # 장바구니 사용자 수 조회 (totalUsers 메트릭)
        cart_request = {
            "dateRanges": [{"startDate": target_date_str, "endDate": target_date_str}],
            "dimensions": [{"name": "date"}],
            "metrics": [{"name": "totalUsers"}],
            "dimensionFilter": {
                "filter": {
                    "fieldName": "eventName",
                    "stringFilter": {
                        "matchType": "EXACT",
                        "value": "add_to_cart",
                        "caseSensitive": False
                    }
                }
            }
        }
        
        cart_response = analytics.properties().runReport(
            property=f"properties/{property_id}", body=cart_request
        ).execute()
        
        for row in cart_response.get("rows", []):
            result['cart_users'] += int(row["metricValues"][0]["value"])
        
        # 회원가입 수 조회 (eventCount 메트릭)
        signup_request = {
            "dateRanges": [{"startDate": target_date_str, "endDate": target_date_str}],
            "dimensions": [{"name": "date"}],
            "metrics": [{"name": "eventCount"}],
            "dimensionFilter": {
                "filter": {
                    "fieldName": "eventName",
                    "stringFilter": {
                        "matchType": "EXACT",
                        "value": "sign_up",
                        "caseSensitive": False
                    }
                }
            }
        }
        
        signup_response = analytics.properties().runReport(
            property=f"properties/{property_id}", body=signup_request
        ).execute()
        
        for row in signup_response.get("rows", []):
            result['signup_count'] += int(row["metricValues"][0]["value"])
            
    except Exception as e:
        print(f"[WARN] GA4 장바구니/회원가입 데이터 조회 실패 (property_id={property_id}, date={target_date_str}): {e}")
        # 오류 발생 시 0 반환
        return result
    
    return result

def insert_performance_summary(target_date):
    date_str = target_date.strftime("%Y-%m-%d")
    now_str = datetime.now(KST).strftime("%Y-%m-%d-%H-%M")
    client = get_bq_client()
    temp_table = f"{DATASET_ID}.performance_summary_temp"

    print(f"[INFO] 임시테이블 생성 중: {temp_table}")
    sys.stdout.flush()

    create_temp_query = f"""
    CREATE OR REPLACE TABLE `{PROJECT_ID}.{temp_table}` AS

    WITH excluded_campaigns AS (
      SELECT DISTINCT campaign_id
      FROM `{PROJECT_ID}.{DATASET_ID}.meta_ads_campaign_summary`
      WHERE campaign_name IS NOT NULL
        AND LOWER(campaign_name) LIKE '%instagram%'
    ),

    filtered_ads AS (
      SELECT *
      FROM `{PROJECT_ID}.{DATASET_ID}.meta_ads_campaign_summary`
      WHERE campaign_name IS NOT NULL
        AND campaign_id NOT IN (SELECT campaign_id FROM excluded_campaigns)
        AND company_name IS NOT NULL
    ),

    base AS (
      SELECT DISTINCT company_name, DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) AS date
      FROM `{PROJECT_ID}.{DATASET_ID}.daily_cafe24_sales`
      WHERE DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) = DATE('{date_str}') AND company_name IS NOT NULL
      UNION DISTINCT
      SELECT DISTINCT company_name, DATE(DATETIME(TIMESTAMP(event_date), 'Asia/Seoul'))
      FROM `{PROJECT_ID}.{DATASET_ID}.ga4_traffic_ngn`
      WHERE DATE(DATETIME(TIMESTAMP(event_date), 'Asia/Seoul')) = DATE('{date_str}') AND company_name IS NOT NULL
      UNION DISTINCT
      SELECT DISTINCT company_name, DATE(DATETIME(TIMESTAMP(event_date), 'Asia/Seoul'))
      FROM `{PROJECT_ID}.{DATASET_ID}.ga4_viewitem_ngn`
      WHERE DATE(DATETIME(TIMESTAMP(event_date), 'Asia/Seoul')) = DATE('{date_str}') AND company_name IS NOT NULL
    )

    SELECT
      b.date,
      b.company_name,
      'meta' AS ad_media,
      COALESCE(SUM(a.spend), 0) AS ad_spend,
      COALESCE(SUM(a.clicks), 0) AS total_clicks,
      COALESCE(SUM(a.purchases), 0) AS total_purchases,
      COALESCE(SUM(a.purchase_value), 0) AS total_purchase_value,
      AVG(a.ROAS) AS roas_percentage,
      AVG(a.CPC) AS avg_cpc,
      AVG(a.CTR) AS click_through_rate,
      AVG(a.CVR) AS conversion_rate,
      COALESCE(s.site_revenue, 0) AS site_revenue,
      COALESCE(t.total_visitors, 0) AS total_visitors,
      COALESCE(v.product_views, 0) AS product_views,
      ROUND(COALESCE(v.product_views, 0) / NULLIF(COALESCE(t.total_visitors, 0), 0), 2) AS views_per_visit,
      CASE WHEN COALESCE(s.site_revenue, 0) = 0 THEN 0
           ELSE ROUND(COALESCE(SUM(a.spend), 0) / s.site_revenue * 100, 2)
      END AS ad_spend_ratio,
      CASE WHEN COALESCE(SUM(a.purchases), 0) = 0 THEN 0
           ELSE ROUND(COALESCE(SUM(a.purchase_value), 0) / SUM(a.purchases), 2)
      END AS avg_order_value,
      0 AS cart_users,  -- 임시로 0 설정, 이후 Python 로직에서 업데이트
      0 AS signup_count,  -- 임시로 0 설정, 이후 Python 로직에서 업데이트
      '{now_str}' AS updated_at
    
    FROM base b
    LEFT JOIN filtered_ads a
      ON b.company_name = a.company_name AND b.date = a.date
    LEFT JOIN (
      SELECT company_name, DATE(DATETIME(TIMESTAMP(payment_date), 'Asia/Seoul')) AS date, SUM(net_sales) AS site_revenue
      FROM `{PROJECT_ID}.{DATASET_ID}.daily_cafe24_sales`
      WHERE company_name IS NOT NULL
      GROUP BY company_name, date
    ) s ON b.company_name = s.company_name AND b.date = s.date
    LEFT JOIN (
      SELECT company_name, DATE(DATETIME(TIMESTAMP(event_date), 'Asia/Seoul')) AS date, SUM(total_users) AS total_visitors
      FROM `{PROJECT_ID}.{DATASET_ID}.ga4_traffic_ngn`
      WHERE company_name IS NOT NULL
        AND (first_user_source != '(not set)' AND first_user_source != 'not set' AND first_user_source IS NOT NULL)
      GROUP BY company_name, date
    ) t ON b.company_name = t.company_name AND b.date = t.date
    LEFT JOIN (
      SELECT company_name, DATE(DATETIME(TIMESTAMP(event_date), 'Asia/Seoul')) AS date, SUM(view_item) AS product_views
      FROM `{PROJECT_ID}.{DATASET_ID}.ga4_viewitem_ngn`
      WHERE company_name IS NOT NULL
      GROUP BY company_name, date
    ) v ON b.company_name = v.company_name AND b.date = v.date
    -- ✅ demo 제외
    WHERE LOWER(b.company_name) != 'demo'
    GROUP BY b.date, b.company_name, s.site_revenue, t.total_visitors, v.product_views

    """

    client.query(create_temp_query).result()
    print(f"[SUCCESS] 임시테이블 생성 완료 → {temp_table}")
    sys.stdout.flush()
    
    # ✅ GA4 장바구니/회원가입 데이터 수집 및 임시 테이블 업데이트
    print(f"[INFO] GA4 장바구니/회원가입 데이터 수집 중...")
    sys.stdout.flush()
    
    # 임시 테이블에서 업체 목록 조회
    company_query = f"""
    SELECT DISTINCT company_name
    FROM `{PROJECT_ID}.{temp_table}`
    """
    companies = [row.company_name for row in client.query(company_query).result()]
    
    # 각 업체별로 GA4 데이터 수집 및 업데이트
    for company_name in companies:
        property_id = get_ga4_property_ids_by_company(company_name, client)
        if property_id:
            cart_signup_data = fetch_ga4_cart_signup_data(property_id, date_str)
            # 0이어도 업데이트 (데이터가 없다는 것도 정보)
            # SQL 인젝션 방지를 위한 파라미터화
            update_query = f"""
            UPDATE `{PROJECT_ID}.{temp_table}`
            SET 
              cart_users = @cart_users,
              signup_count = @signup_count
            WHERE company_name = @company_name
              AND date = DATE(@target_date)
            """
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("cart_users", "INTEGER", cart_signup_data['cart_users']),
                    bigquery.ScalarQueryParameter("signup_count", "INTEGER", cart_signup_data['signup_count']),
                    bigquery.ScalarQueryParameter("company_name", "STRING", company_name),
                    bigquery.ScalarQueryParameter("target_date", "DATE", date_str)
                ]
            )
            client.query(update_query, job_config=job_config).result()
            print(f"[INFO] {company_name}: 장바구니={cart_signup_data['cart_users']}명, 회원가입={cart_signup_data['signup_count']}건")
            sys.stdout.flush()
        else:
            print(f"[WARN] {company_name}: GA4 Property ID를 찾을 수 없어 장바구니/회원가입 데이터를 수집하지 않습니다.")
            sys.stdout.flush()

    merge_query = f"""
    MERGE `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}` AS main
    USING `{PROJECT_ID}.{temp_table}` AS temp
    ON main.date = temp.date 
       AND main.company_name = temp.company_name 
       AND main.ad_media = temp.ad_media
       AND (main.date IS NULL OR DATE(main.date) = DATE('{date_str}'))
    WHEN MATCHED THEN
      UPDATE SET
        ad_spend = temp.ad_spend,
        total_clicks = temp.total_clicks,
        total_purchases = temp.total_purchases,
        total_purchase_value = temp.total_purchase_value,
        roas_percentage = temp.roas_percentage,
        avg_cpc = temp.avg_cpc,
        click_through_rate = temp.click_through_rate,
        conversion_rate = temp.conversion_rate,
        site_revenue = temp.site_revenue,
        total_visitors = temp.total_visitors,
        product_views = temp.product_views,
        views_per_visit = temp.views_per_visit,
        ad_spend_ratio = temp.ad_spend_ratio,
        avg_order_value = temp.avg_order_value,
        cart_users = temp.cart_users,
        signup_count = temp.signup_count,
        updated_at = temp.updated_at
    WHEN NOT MATCHED THEN
      INSERT ROW
    """

    client.query(merge_query).result()
    print(f"[SUCCESS] 메인 테이블 병합 완료 → {TABLE_ID}")
    sys.stdout.flush()

    drop_query = f"DROP TABLE `{PROJECT_ID}.{temp_table}`"
    client.query(drop_query).result()
    print(f"[SUCCESS] 임시테이블 삭제 완료 → {temp_table}")
    sys.stdout.flush()

def run(mode="today"):
    if mode == "yesterday":
        target_date = datetime.now(KST).date() - timedelta(days=1)
        print(f"[INFO] performance summary 삽입 실행 → {target_date}")
        sys.stdout.flush()
        insert_performance_summary(target_date)
    elif mode == "last_7_days":
        # 최근 7일간 일괄 실행
        for i in range(7):
            target_date = datetime.now(KST).date() - timedelta(days=i)
            print(f"[INFO] performance summary 삽입 실행 → {target_date} ({i+1}/7)")
            sys.stdout.flush()
            insert_performance_summary(target_date)
        print("[SUCCESS] 최근 7일간 performance summary 처리 완료!")
    else:
        target_date = datetime.now(KST).date()
        print(f"[INFO] performance summary 삽입 실행 → {target_date}")
        sys.stdout.flush()
        insert_performance_summary(target_date)

if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "today"
    run(arg)
