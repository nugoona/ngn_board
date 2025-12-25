import os
from datetime import date, timedelta
from google.cloud import bigquery


PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "winged-precept-443218-v8")
DATASET = os.environ.get("BQ_DATASET", "ngn_dataset")

# 원본 테이블
T_SALES_DAILY = f"{PROJECT_ID}.{DATASET}.daily_cafe24_sales"
T_META_DAILY = f"{PROJECT_ID}.{DATASET}.meta_ads_account_summary"
T_GA_TRAFFIC_DAILY = f"{PROJECT_ID}.{DATASET}.ga4_traffic_ngn"
T_GA_VIEWITEM_DAILY = f"{PROJECT_ID}.{DATASET}.ga4_viewitem_ngn"

# 대상(월 집계) 테이블
T_SALES_MONTHLY = f"{PROJECT_ID}.{DATASET}.mall_sales_monthly"
T_META_MONTHLY = f"{PROJECT_ID}.{DATASET}.meta_ads_monthly"
T_GA_TRAFFIC_MONTHLY = f"{PROJECT_ID}.{DATASET}.ga4_traffic_monthly"
T_GA_VIEWITEM_MONTHLY_RAW = f"{PROJECT_ID}.{DATASET}.ga4_viewitem_monthly_raw"


def prev_month_range(today: date) -> tuple[str, str, str]:
    """전월 [start, end] (end inclusive) + ym('YYYY-MM')"""
    if today.month == 1:
        y, m = today.year - 1, 12
    else:
        y, m = today.year, today.month - 1

    start = date(y, m, 1)
    if m == 12:
        next_m = date(y + 1, 1, 1)
    else:
        next_m = date(y, m + 1, 1)
    end = next_m - timedelta(days=1)  # 수정: fromordinal 대신 timedelta 사용

    ym = f"{y:04d}-{m:02d}"
    return start.isoformat(), end.isoformat(), ym


def run_query(client: bigquery.Client, sql: str, params: list[bigquery.ScalarQueryParameter]) -> None:
    job = client.query(
        sql,
        job_config=bigquery.QueryJobConfig(query_parameters=params),
    )
    job.result()  # wait
    print(f"[OK] {job.job_id} bytes_processed={job.total_bytes_processed}")


def create_tables_if_not_exists(client: bigquery.Client) -> None:
    """월간 집계 테이블이 없으면 생성"""
    tables = [
        {
            "name": T_SALES_MONTHLY,
            "sql": f"""
CREATE TABLE IF NOT EXISTS `{T_SALES_MONTHLY}` (
  company_name STRING NOT NULL,
  month_date DATE NOT NULL,
  net_sales NUMERIC,
  total_orders INT64,
  total_first_order INT64,
  total_canceled INT64,
  updated_at TIMESTAMP
)
PARTITION BY month_date
CLUSTER BY company_name
""",
        },
        {
            "name": T_META_MONTHLY,
            "sql": f"""
CREATE TABLE IF NOT EXISTS `{T_META_MONTHLY}` (
  company_name STRING NOT NULL,
  month_date DATE NOT NULL,
  spend NUMERIC,
  impressions INT64,
  clicks INT64,
  purchases INT64,
  purchase_value NUMERIC,
  updated_at TIMESTAMP
)
PARTITION BY month_date
CLUSTER BY company_name
""",
        },
        {
            "name": T_GA_TRAFFIC_MONTHLY,
            "sql": f"""
CREATE TABLE IF NOT EXISTS `{T_GA_TRAFFIC_MONTHLY}` (
  company_name STRING NOT NULL,
  month_date DATE NOT NULL,
  total_users INT64,
  screen_page_views INT64,
  event_count INT64,
  updated_at TIMESTAMP
)
PARTITION BY month_date
CLUSTER BY company_name
""",
        },
        {
            "name": T_GA_VIEWITEM_MONTHLY_RAW,
            "sql": f"""
CREATE TABLE IF NOT EXISTS `{T_GA_VIEWITEM_MONTHLY_RAW}` (
  company_name STRING NOT NULL,
  ym STRING NOT NULL,
  item_name STRING NOT NULL,
  view_item INT64,
  updated_at TIMESTAMP
)
PARTITION BY ym
CLUSTER BY company_name, item_name
""",
        },
    ]

    for table in tables:
        try:
            client.query(table["sql"]).result()
            print(f"[OK] Table checked/created: {table['name']}")
        except Exception as e:
            print(f"[WARN] Table creation failed for {table['name']}: {e}")


def merge_mall_sales_monthly(client: bigquery.Client, start_date: str, end_date: str) -> None:
    sql = f"""
MERGE `{T_SALES_MONTHLY}` T
USING (
  SELECT
    company_name,
    DATE_TRUNC(payment_date, MONTH) AS month_date,
    CAST(SUM(net_sales) AS NUMERIC) AS net_sales,
    SUM(total_orders) AS total_orders,
    SUM(total_first_order) AS total_first_order,
    SUM(total_canceled) AS total_canceled,
    CURRENT_TIMESTAMP() AS updated_at
  FROM `{T_SALES_DAILY}`
  WHERE payment_date BETWEEN @start_date AND @end_date
  GROUP BY company_name, month_date
) S
ON T.company_name = S.company_name AND T.month_date = S.month_date
WHEN MATCHED THEN UPDATE SET
  net_sales=S.net_sales,
  total_orders=S.total_orders,
  total_first_order=S.total_first_order,
  total_canceled=S.total_canceled,
  updated_at=S.updated_at
WHEN NOT MATCHED THEN INSERT (
  company_name, month_date, net_sales, total_orders, total_first_order, total_canceled, updated_at
) VALUES (
  S.company_name, S.month_date, S.net_sales, S.total_orders, S.total_first_order, S.total_canceled, S.updated_at
);
"""
    run_query(
        client,
        sql,
        [
            bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
            bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
        ],
    )


def merge_meta_ads_monthly(client: bigquery.Client, start_date: str, end_date: str) -> None:
    sql = f"""
MERGE `{T_META_MONTHLY}` T
USING (
  SELECT
    company_name,
    DATE_TRUNC(date, MONTH) AS month_date,
    CAST(SUM(spend) AS NUMERIC) AS spend,
    SUM(impressions) AS impressions,
    SUM(clicks) AS clicks,
    SUM(purchases) AS purchases,
    CAST(SUM(purchase_value) AS NUMERIC) AS purchase_value,
    CURRENT_TIMESTAMP() AS updated_at
  FROM `{T_META_DAILY}`
  WHERE date BETWEEN @start_date AND @end_date
  GROUP BY company_name, month_date
) S
ON T.company_name = S.company_name AND T.month_date = S.month_date
WHEN MATCHED THEN UPDATE SET
  spend=S.spend,
  impressions=S.impressions,
  clicks=S.clicks,
  purchases=S.purchases,
  purchase_value=S.purchase_value,
  updated_at=S.updated_at
WHEN NOT MATCHED THEN INSERT (
  company_name, month_date, spend, impressions, clicks, purchases, purchase_value, updated_at
) VALUES (
  S.company_name, S.month_date, S.spend, S.impressions, S.clicks, S.purchases, S.purchase_value, S.updated_at
);
"""
    run_query(
        client,
        sql,
        [
            bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
            bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
        ],
    )


def merge_ga4_traffic_monthly(client: bigquery.Client, start_date: str, end_date: str) -> None:
    sql = f"""
MERGE `{T_GA_TRAFFIC_MONTHLY}` T
USING (
  SELECT
    company_name,
    DATE_TRUNC(event_date, MONTH) AS month_date,
    SUM(total_users) AS total_users,
    SUM(screen_page_views) AS screen_page_views,
    SUM(event_count) AS event_count,
    CURRENT_TIMESTAMP() AS updated_at
  FROM `{T_GA_TRAFFIC_DAILY}`
  WHERE event_date BETWEEN @start_date AND @end_date
  GROUP BY company_name, month_date
) S
ON T.company_name = S.company_name AND T.month_date = S.month_date
WHEN MATCHED THEN UPDATE SET
  total_users=S.total_users,
  screen_page_views=S.screen_page_views,
  event_count=S.event_count,
  updated_at=S.updated_at
WHEN NOT MATCHED THEN INSERT (
  company_name, month_date, total_users, screen_page_views, event_count, updated_at
) VALUES (
  S.company_name, S.month_date, S.total_users, S.screen_page_views, S.event_count, S.updated_at
);
"""
    run_query(
        client,
        sql,
        [
            bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
            bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
        ],
    )


def merge_ga4_viewitem_monthly_raw(client: bigquery.Client, start_date: str, end_date: str, ym: str) -> None:
    # item_name 단위 raw 집계
    sql = f"""
MERGE `{T_GA_VIEWITEM_MONTHLY_RAW}` T
USING (
  SELECT
    company_name,
    @ym AS ym,
    item_name,
    SUM(view_item) AS view_item,
    CURRENT_TIMESTAMP() AS updated_at
  FROM `{T_GA_VIEWITEM_DAILY}`
  WHERE event_date BETWEEN @start_date AND @end_date
  GROUP BY company_name, item_name
) S
ON T.company_name = S.company_name
AND T.ym = S.ym
AND T.item_name = S.item_name
WHEN MATCHED THEN UPDATE SET
  view_item=S.view_item,
  updated_at=S.updated_at
WHEN NOT MATCHED THEN INSERT (
  company_name, ym, item_name, view_item, updated_at
) VALUES (
  S.company_name, S.ym, S.item_name, S.view_item, S.updated_at
);
"""
    run_query(
        client,
        sql,
        [
            bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
            bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
            bigquery.ScalarQueryParameter("ym", "STRING", ym),
        ],
    )


def main():
    client = bigquery.Client(project=PROJECT_ID)

    today = date.today()
    start_date, end_date, ym = prev_month_range(today)

    print(f"[INFO] PROJECT_ID={PROJECT_ID} DATASET={DATASET}")
    print(f"[INFO] prev_month ym={ym} range={start_date}..{end_date}")

    # 테이블이 없으면 생성
    print("[INFO] Checking/creating monthly tables...")
    create_tables_if_not_exists(client)

    # MERGE 실행
    merge_mall_sales_monthly(client, start_date, end_date)
    merge_meta_ads_monthly(client, start_date, end_date)
    merge_ga4_traffic_monthly(client, start_date, end_date)
    merge_ga4_viewitem_monthly_raw(client, start_date, end_date, ym)

    print("[DONE] monthly rollup completed")


if __name__ == "__main__":
    main()

