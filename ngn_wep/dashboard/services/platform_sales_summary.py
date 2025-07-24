from google.cloud import bigquery
from utils.cache_utils import cached_query

# ✅ 1. 일별 또는 요약 플랫폼 매출 조회
@cached_query(func_name="platform_sales", ttl=1800)  # 30분 캐싱
def get_platform_sales_by_day(company_names, start_date, end_date, date_type="daily", date_sort="asc"):
    if not company_names:
        print("[WARN] company_names is empty → 빈 결과 반환")
        return []

    client = bigquery.Client()

    base_query = """
    WITH base_data AS (
      SELECT
        DATE,
        LOWER(company_name) AS company_name,
        CASE
          WHEN LOWER(platform) = '자사몰' THEN 'site_official'
          WHEN LOWER(platform) = '지그재그' THEN 'zigzag'
          WHEN LOWER(platform) = '무신사' THEN 'musinsa'
          WHEN LOWER(platform) = '에이블리' THEN 'ably'
          ELSE LOWER(platform)
        END AS platform_grouped,
        sales_amount
      FROM `winged-precept-443218-v8.ngn_dataset.sheets_platform_sales_data`
      WHERE DATE BETWEEN @start_date AND @end_date
        AND LOWER(company_name) IN UNNEST(@company_names)
    ),
    """

    summary_query = """
    summary_row AS (
      SELECT
        company_name,
        @start_date || ' ~ ' || @end_date AS date,
        SUM(sales_amount) AS total_sales,
        IFNULL(SUM(IF(platform_grouped = 'site_official', sales_amount, 0)), 0) AS site_official,
        IFNULL(SUM(IF(platform_grouped = 'musinsa', sales_amount, 0)), 0) AS musinsa,
        IFNULL(SUM(IF(platform_grouped = '29cm', sales_amount, 0)), 0) AS `29cm`,
        IFNULL(SUM(IF(platform_grouped = 'shopee', sales_amount, 0)), 0) AS shopee,
        IFNULL(SUM(IF(platform_grouped = 'eql', sales_amount, 0)), 0) AS eql,
        IFNULL(SUM(IF(platform_grouped = 'llud', sales_amount, 0)), 0) AS llud,
        IFNULL(SUM(IF(platform_grouped = 'hana', sales_amount, 0)), 0) AS hana,
        IFNULL(SUM(IF(platform_grouped = 'heights', sales_amount, 0)), 0) AS heights,
        IFNULL(SUM(IF(platform_grouped = 'zigzag', sales_amount, 0)), 0) AS zigzag,
        IFNULL(SUM(IF(platform_grouped = 'ably', sales_amount, 0)), 0) AS ably
      FROM base_data
      GROUP BY company_name
    )
    """

    daily_query = """
    daily_rows AS (
      SELECT
        company_name,
        DATE AS date,
        SUM(sales_amount) AS total_sales,
        IFNULL(SUM(IF(platform_grouped = 'site_official', sales_amount, 0)), 0) AS site_official,
        IFNULL(SUM(IF(platform_grouped = 'musinsa', sales_amount, 0)), 0) AS musinsa,
        IFNULL(SUM(IF(platform_grouped = '29cm', sales_amount, 0)), 0) AS `29cm`,
        IFNULL(SUM(IF(platform_grouped = 'shopee', sales_amount, 0)), 0) AS shopee,
        IFNULL(SUM(IF(platform_grouped = 'eql', sales_amount, 0)), 0) AS eql,
        IFNULL(SUM(IF(platform_grouped = 'llud', sales_amount, 0)), 0) AS llud,
        IFNULL(SUM(IF(platform_grouped = 'hana', sales_amount, 0)), 0) AS hana,
        IFNULL(SUM(IF(platform_grouped = 'heights', sales_amount, 0)), 0) AS heights,
        IFNULL(SUM(IF(platform_grouped = 'zigzag', sales_amount, 0)), 0) AS zigzag,
        IFNULL(SUM(IF(platform_grouped = 'ably', sales_amount, 0)), 0) AS ably
      FROM base_data
      GROUP BY company_name, DATE
    )
    """

    order_clause = "ORDER BY date DESC" if date_sort.lower() == "desc" else "ORDER BY date ASC"
    final_query = base_query + (
        summary_query + "\nSELECT * FROM summary_row ORDER BY company_name"
        if date_type == "summary"
        else daily_query + f"\nSELECT * FROM daily_rows {order_clause}"
    )

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter("company_names", "STRING", company_names),
            bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
            bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
        ]
    )

    try:
        result = client.query(final_query, job_config=job_config).result()
        return [dict(row) for row in result]
    except Exception as e:
        print(f"[ERROR] get_platform_sales_by_day 실패: {e}")
        return []


# ✅ 2. 플랫폼별 매출 비율 조회
@cached_query(func_name="platform_sales_ratio", ttl=1800)  # 30분 캐싱
def get_platform_sales_ratio(company_names, start_date, end_date):
    if not company_names:
        print("[WARN] company_names is empty → 빈 결과 반환")
        return []

    client = bigquery.Client()

    query = """
    WITH platform_data AS (
      SELECT
        LOWER(company_name) AS company_name,
        CASE
          WHEN LOWER(platform) = '자사몰' THEN 'site_official'
          WHEN LOWER(platform) = '지그재그' THEN 'zigzag'
          WHEN LOWER(platform) = '무신사' THEN 'musinsa'
          WHEN LOWER(platform) = '에이블리' THEN 'ably'
          ELSE LOWER(platform)
        END AS platform_grouped,
        SUM(sales_amount) AS total_sales
      FROM `winged-precept-443218-v8.ngn_dataset.sheets_platform_sales_data`
      WHERE DATE BETWEEN @start_date AND @end_date
        AND LOWER(company_name) IN UNNEST(@company_names)
        AND sales_amount > 0
      GROUP BY company_name, platform_grouped
    ),
    
    company_totals AS (
      SELECT
        company_name,
        SUM(total_sales) AS company_total
      FROM platform_data
      GROUP BY company_name
    )
    
    SELECT
      p.company_name,
      p.platform_grouped AS platform,
      p.total_sales,
      ROUND((p.total_sales / ct.company_total) * 100, 1) AS sales_ratio_percent
    FROM platform_data p
    JOIN company_totals ct ON p.company_name = ct.company_name
    ORDER BY p.company_name, p.total_sales DESC
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter("company_names", "STRING", company_names),
            bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
            bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
        ]
    )

    try:
        result = client.query(query, job_config=job_config).result()
        return [dict(row) for row in result]
    except Exception as e:
        print(f"[ERROR] get_platform_sales_ratio 실패: {e}")
        return []


# ✅ 3. 월별 플랫폼 매출 조회
@cached_query(func_name="monthly_platform_sales", ttl=3600)  # 1시간 캐싱
def get_monthly_platform_sales(company_names, months_back=6):
    if not company_names:
        print("[WARN] company_names is empty → 빈 결과 반환")
        return []

    client = bigquery.Client()

    query = """
    WITH monthly_data AS (
      SELECT
        LOWER(company_name) AS company_name,
        FORMAT_DATE('%Y-%m', DATE) AS month,
        CASE
          WHEN LOWER(platform) = '자사몰' THEN 'site_official'
          WHEN LOWER(platform) = '지그재그' THEN 'zigzag'
          WHEN LOWER(platform) = '무신사' THEN 'musinsa'
          WHEN LOWER(platform) = '에이블리' THEN 'ably'
          ELSE LOWER(platform)
        END AS platform_grouped,
        SUM(sales_amount) AS monthly_sales
      FROM `winged-precept-443218-v8.ngn_dataset.sheets_platform_sales_data`
      WHERE DATE >= DATE_SUB(DATE_TRUNC(CURRENT_DATE(), MONTH), INTERVAL @months_back MONTH)
        AND LOWER(company_name) IN UNNEST(@company_names)
        AND sales_amount > 0
      GROUP BY company_name, month, platform_grouped
    )
    
    SELECT
      company_name,
      month,
      platform_grouped AS platform,
      monthly_sales,
      SUM(monthly_sales) OVER (PARTITION BY company_name, month) AS total_monthly_sales
    FROM monthly_data
    ORDER BY company_name, month DESC, monthly_sales DESC
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter("company_names", "STRING", company_names),
            bigquery.ScalarQueryParameter("months_back", "INT64", months_back),
        ]
    )

    try:
        result = client.query(query, job_config=job_config).result()
        return [dict(row) for row in result]
    except Exception as e:
        print(f"[ERROR] get_monthly_platform_sales 실패: {e}")
        return []
