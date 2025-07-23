from google.cloud import bigquery

# ✅ 1. 일별 또는 요약 플랫폼 매출 조회
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
        CAST(CONCAT(FORMAT_DATE('%Y-%m-%d', @start_date), ' ~ ', FORMAT_DATE('%Y-%m-%d', @end_date)) AS STRING) AS date,
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


# ✅ 2. 플랫폼 비중 차트용 (파이차트)
def get_platform_sales_ratio(company_names, start_date, end_date):
    client = bigquery.Client()

    query = """
    WITH base_data AS (
      SELECT
        LOWER(company_name) AS company_name,
        CASE
          WHEN platform = '자사몰' THEN 'site_official'
          WHEN platform = '지그재그' THEN 'zigzag'
          WHEN platform = '무신사' THEN 'musinsa'
          WHEN platform = '에이블리' THEN 'ably'
          ELSE platform
        END AS platform_grouped,
        sales_amount
      FROM `winged-precept-443218-v8.ngn_dataset.sheets_platform_sales_data`
      WHERE DATE BETWEEN @start_date AND @end_date
        AND LOWER(company_name) IN UNNEST(@company_names)
    ),
    grouped AS (
      SELECT platform_grouped, SUM(sales_amount) AS sales FROM base_data GROUP BY platform_grouped
    ),
    total AS (
      SELECT SUM(sales) AS total_sales FROM grouped
    )

    SELECT
      g.platform_grouped AS platform,
      g.sales,
      t.total_sales,
      ROUND(100 * g.sales / NULLIF(t.total_sales, 0), 1) AS sales_ratio_percent
    FROM grouped g
    CROSS JOIN total t
    ORDER BY g.sales DESC
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


# ✅ 3. 월별 플랫폼 매출 (막대 차트)
def get_monthly_platform_sales(company_names):
    client = bigquery.Client()

    query = """
    WITH base_data AS (
      SELECT
        FORMAT_DATE('%Y-%m', DATE) AS year_month,
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
      WHERE DATE >= DATE_TRUNC(DATE_SUB(CURRENT_DATE(), INTERVAL 13 MONTH), MONTH)
        AND LOWER(company_name) IN UNNEST(@company_names)
    ),
    grouped AS (
      SELECT
        year_month,
        platform_grouped,
        SUM(sales_amount) AS sales
      FROM base_data
      GROUP BY year_month, platform_grouped
    )

    SELECT
      year_month,
      SUM(CASE WHEN platform_grouped = 'site_official' THEN sales ELSE 0 END) AS site_official,
      SUM(CASE WHEN platform_grouped = 'zigzag' THEN sales ELSE 0 END) AS zigzag,
      SUM(CASE WHEN platform_grouped = 'musinsa' THEN sales ELSE 0 END) AS musinsa,
      SUM(CASE WHEN platform_grouped = 'ably' THEN sales ELSE 0 END) AS ably,
      SUM(CASE WHEN platform_grouped = '29cm' THEN sales ELSE 0 END) AS `29cm`,
      SUM(CASE WHEN platform_grouped = 'shopee' THEN sales ELSE 0 END) AS shopee,
      SUM(CASE WHEN platform_grouped = 'eql' THEN sales ELSE 0 END) AS eql,
      SUM(CASE WHEN platform_grouped = 'llud' THEN sales ELSE 0 END) AS llud,
      SUM(CASE WHEN platform_grouped = 'hana' THEN sales ELSE 0 END) AS hana,
      SUM(CASE WHEN platform_grouped = 'heights' THEN sales ELSE 0 END) AS heights
    FROM grouped
    GROUP BY year_month
    ORDER BY year_month DESC
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter("company_names", "STRING", company_names)
        ]
    )

    try:
        result = client.query(query, job_config=job_config).result()
        return [dict(row) for row in result]
    except Exception as e:
        print(f"[ERROR] get_monthly_platform_sales 실패: {e}")
        return []
