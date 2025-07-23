# File: services/viewitem_summary.py

from google.cloud import bigquery

def get_bigquery_client():
    return bigquery.Client()

def get_viewitem_summary(company_name, start_date: str, end_date: str):
    if not start_date or not end_date:
        raise ValueError("start_date / end_date 값이 없습니다.")

    # ✅ 업체 필터링 분기 처리
    if isinstance(company_name, list):
        company_filter = "LOWER(c.company_name) IN UNNEST(@company_name_list)"
        query_params = [
            bigquery.ArrayQueryParameter("company_name_list", "STRING", company_name),
            bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
            bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
        ]
    else:
        company_filter = "LOWER(c.company_name) = LOWER(@company_name)"
        query_params = [
            bigquery.ScalarQueryParameter("company_name", "STRING", company_name),
            bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
            bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
        ]

    query = f"""
    SELECT
      LOWER(c.company_name) AS company_name,
      REGEXP_REPLACE(t.item_name, r'^\\[[^\\]]+\\]\\s*', '') AS product_name_cleaned,

      CASE
        WHEN t.first_user_source IN ('insta_linktree', 'linktr.ee', 'ig', 'l.instagram.com', 'instagram.com', 'LOOKBOOK') THEN 'instagram'
        WHEN t.first_user_source = '인트로 MDGT' THEN 'from madgoat'
        WHEN t.first_user_source = 'naver' THEN 'naver.com'
        WHEN LOWER(t.first_user_source) IN ('파이시스', 'piscess', 'piscess') THEN '(direct)'
        ELSE t.first_user_source
      END AS source_raw,

      t.country,
      SUM(t.view_item) AS total_view_item

    FROM `winged-precept-443218-v8.ngn_dataset.ga4_viewitem_ngn` t
    JOIN `winged-precept-443218-v8.ngn_dataset.company_info` c
      ON t.ga4_property_id = c.ga4_property_id
    WHERE DATE(t.event_date) BETWEEN @start_date AND @end_date
      AND {company_filter}
      AND REGEXP_REPLACE(t.item_name, r'^\\[[^\\]]+\\]\\s*', '') IS NOT NULL
      AND REGEXP_REPLACE(t.item_name, r'^\\[[^\\]]+\\]\\s*', '') != ''
      AND REGEXP_REPLACE(t.item_name, r'^\\[[^\\]]+\\]\\s*', '') != '(not set)'

    GROUP BY company_name, product_name_cleaned, source_raw, t.country
    ORDER BY total_view_item DESC
    """

    print("[DEBUG] ViewItem Summary 쿼리:\n", query)

    try:
        client = get_bigquery_client()
        rows = client.query(query, job_config=bigquery.QueryJobConfig(query_parameters=query_params)).result()
        data = [dict(row) for row in rows]
        print(f"[DEBUG] ViewItem Summary 결과 {len(data)}건")
        return data
    except Exception as ex:
        print("[ERROR] viewitem_summary 오류:", ex)
        return []

