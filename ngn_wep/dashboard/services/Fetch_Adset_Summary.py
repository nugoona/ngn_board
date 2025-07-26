from google.cloud import bigquery
from datetime import datetime

client = bigquery.Client()

def dictify_rows(rows):
    return [dict(row) for row in rows]

def get_meta_ads_adset_summary_by_type(account_id: str, period: str, start_date: str, end_date: str):
    """
    특정 기간과 광고 계정으로 META Ads 캠페인 목표별 성과 요약 조회
    """

    # ✅ start_date, end_date가 None 또는 빈 문자열이면 오늘로 설정
    today = datetime.today().strftime("%Y-%m-%d")
    start_date = start_date.strip() if start_date else ""
    end_date = end_date.strip() if end_date else ""

    if not start_date:
        start_date = today
    if not end_date:
        end_date = today

    # ✅ 1. 캠페인 목표별 요약 (type_summary)
    type_summary_query = f"""
    WITH filtered_data AS (
      SELECT
        account_id,
        account_name,
        adset_name,
        spend,
        impressions,
        clicks,
        purchases,
        purchase_value
      FROM
        `winged-precept-443218-v8.ngn_dataset.meta_ads_adset_summary`
      WHERE
        DATE(date) BETWEEN '{start_date}' AND '{end_date}'
        AND account_id = '{account_id}'
    )

    SELECT
      '{start_date} ~ {end_date}' AS period,
      account_id,
      account_name,
      type,
      SUM(spend) AS total_spend,
      SUM(impressions) AS total_impressions,
      SAFE_MULTIPLY(SAFE_DIVIDE(SUM(spend), SUM(impressions)), 1000) AS CPM,
      SUM(clicks) AS total_clicks,
      SAFE_DIVIDE(SUM(spend), SUM(clicks)) AS CPC,
      SAFE_DIVIDE(SUM(clicks), SUM(impressions)) AS CTR,
      SUM(purchases) AS total_purchases,
      SUM(purchase_value) AS total_purchase_value,
      SAFE_DIVIDE(SUM(purchase_value), SUM(spend)) AS ROAS,
      SAFE_DIVIDE(SUM(spend), SUM(purchases)) AS CPA
    FROM (
      SELECT account_id, account_name, '유입' AS type, spend, impressions, clicks, purchases, purchase_value
      FROM filtered_data
      WHERE adset_name LIKE '%유입%'

      UNION ALL

      SELECT account_id, account_name, '전환' AS type, spend, impressions, clicks, purchases, purchase_value
      FROM filtered_data
      WHERE adset_name LIKE '%전환%'

      UNION ALL

      SELECT account_id, account_name, '도달' AS type, spend, impressions, clicks, purchases, purchase_value
      FROM filtered_data
      WHERE adset_name LIKE '%도달%'
    )
    GROUP BY account_id, account_name, type
    ORDER BY account_name, type
    """

    # ✅ 2. 총 지출 합산 (total_spend_sum)
    total_spend_query = f"""
    SELECT
      SUM(spend) AS total_spend
    FROM
      `winged-precept-443218-v8.ngn_dataset.meta_ads_adset_summary`
    WHERE
      DATE(date) BETWEEN '{start_date}' AND '{end_date}'
      AND account_id = '{account_id}'
    """

    try:
        type_summary_rows = client.query(type_summary_query).result()
        type_summary_list = dictify_rows(type_summary_rows)

        total_spend_rows = client.query(total_spend_query).result()
        total_spend = list(total_spend_rows)[0].get("total_spend", 0.0) if total_spend_rows.total_rows > 0 else 0.0

        return type_summary_list, total_spend

    except Exception as e:
        print(f"[ERROR] Failed to fetch adset summary by type: {e}")
        return [], 0.0
