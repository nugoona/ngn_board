from datetime import datetime, timedelta, timezone
from google.cloud import bigquery
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

    merge_query = f"""
    MERGE `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}` AS main
    USING `{PROJECT_ID}.{temp_table}` AS temp
    ON main.date = temp.date AND main.company_name = temp.company_name AND main.ad_media = temp.ad_media
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
    else:
        target_date = datetime.now(KST).date()

    print(f"[INFO] performance summary 삽입 실행 → {target_date}")
    sys.stdout.flush()
    insert_performance_summary(target_date)

if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "today"
    run(arg)
