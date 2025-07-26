from google.cloud import bigquery
from datetime import datetime

client = bigquery.Client()

def dictify_rows(rows):
    return [dict(row) for row in rows]

def get_meta_ads_adset_summary_by_type(account_id: str, period: str, start_date: str, end_date: str):
    today = datetime.today().strftime("%Y-%m-%d")
    start_date = start_date.strip() if start_date else today
    end_date = end_date.strip() if end_date else today

    query = f"""
    WITH latest_names_by_day AS (
      SELECT
        adset_id,
        DATE(date) AS dt,
        LOWER(adset_name) AS latest_name,
        ROW_NUMBER() OVER (PARTITION BY adset_id, DATE(date) ORDER BY updated_at DESC) AS rn
      FROM `winged-precept-443218-v8.ngn_dataset.meta_ads_adset_summary`
    ),
    deduped AS (
      SELECT *
      FROM (
        SELECT
          adset_id,
          DATE(date) AS dt,
          account_id,
          spend,
          impressions,
          clicks,
          purchases,
          purchase_value,
          ROW_NUMBER() OVER (PARTITION BY adset_id, DATE(date) ORDER BY updated_at DESC) AS rn
        FROM `winged-precept-443218-v8.ngn_dataset.meta_ads_adset_summary`
        WHERE DATE(date) BETWEEN '{start_date}' AND '{end_date}'
          AND account_id = '{account_id}'
      )
      WHERE rn = 1
    ),
    tagged AS (
      SELECT
        d.*,
        CASE
          WHEN REGEXP_CONTAINS(n.latest_name, r'유입') THEN '유입'
          WHEN REGEXP_CONTAINS(n.latest_name, r'전환') THEN '전환'
          WHEN REGEXP_CONTAINS(n.latest_name, r'도달') THEN '도달'
          ELSE NULL
        END AS type
      FROM deduped d
      LEFT JOIN (
        SELECT adset_id, dt, latest_name
        FROM latest_names_by_day
        WHERE rn = 1
      ) n
      ON d.adset_id = n.adset_id AND d.dt = n.dt
    )
    SELECT
      '{start_date} ~ {end_date}' AS period,
      '{account_id}' AS account_id,
      COALESCE(type, '기타') AS type,
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
    FROM tagged
    GROUP BY type
    ORDER BY type
    """

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
        type_summary_rows = client.query(query).result()
        type_summary_list = dictify_rows(type_summary_rows)

        total_spend_rows = client.query(total_spend_query).result()
        total_spend = list(total_spend_rows)[0].get("total_spend", 0.0) if total_spend_rows.total_rows > 0 else 0.0

        return type_summary_list, total_spend

    except Exception as e:
        print(f"[ERROR] Failed to fetch adset summary by type: {e}")
        return [], 0.0
