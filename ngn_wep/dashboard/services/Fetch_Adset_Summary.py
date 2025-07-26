# File: services/fetch_adset_summary.py

from google.cloud import bigquery
from datetime import datetime

client = bigquery.Client()

def dictify_rows(rows):
    return [dict(row) for row in rows]

def get_meta_ads_adset_summary_by_type(account_id: str, period: str, start_date: str, end_date: str):
    """
    특정 기간과 광고 계정으로 META Ads 캠페인 목표별 성과 요약 조회 (adset 중복 제거)
    """

    today = datetime.today().strftime("%Y-%m-%d")
    start_date = start_date.strip() if start_date else today
    end_date = end_date.strip() if end_date else today

    # ✅ 1. 캠페인 목표별 요약 쿼리 (adset_id 중복 제거 포함)
    type_summary_query = f"""
    WITH deduplicated_adsets AS (
      SELECT
        account_id,
        adset_id,
        ANY_VALUE(account_name) AS account_name,
        ANY_VALUE(adset_name) AS adset_name,
        SUM(spend) AS spend,
        SUM(impressions) AS impressions,
        SUM(clicks) AS clicks,
        SUM(purchases) AS purchases,
        SUM(purchase_value) AS purchase_value
      FROM `winged-precept-443218-v8.ngn_dataset.meta_ads_adset_summary`
      WHERE DATE(date) BETWEEN '{start_date}' AND '{end_date}'
        AND account_id = '{account_id}'
      GROUP BY account_id, adset_id
    ),

    typed_adsets AS (
      SELECT *,
        CASE
          WHEN adset_name LIKE '%도달%' THEN '도달'
          WHEN adset_name LIKE '%유입%' THEN '유입'
          WHEN adset_name LIKE '%전환%' THEN '전환'
          ELSE '기타'
        END AS type
      FROM deduplicated_adsets
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
    FROM typed_adsets
    WHERE type != '기타'
    GROUP BY account_id, account_name, type
    ORDER BY account_name, type
    """

    # ✅ 2. 총 지출 합산 쿼리 (중복 제거)
    total_spend_query = f"""
    SELECT
      SUM(spend) AS total_spend
    FROM (
      SELECT
        adset_id,
        DATE(date) AS date,
        SUM(spend) AS spend
      FROM `winged-precept-443218-v8.ngn_dataset.meta_ads_adset_summary`
      WHERE DATE(date) BETWEEN '{start_date}' AND '{end_date}'
        AND account_id = '{account_id}'
      GROUP BY adset_id, DATE
    )
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
