# File: services/fetch_adset_summary.py

"""META Ads 캠페인 목표별 성과 요약 — adset 중복(날짜·이름) 완전 제거 버전"""

from google.cloud import bigquery
from datetime import datetime

client = bigquery.Client()


def dictify_rows(rows):
    """BigQuery RowIterator → list[dict]"""
    return [dict(r) for r in rows]


def get_meta_ads_adset_summary_by_type(
    account_id: str,
    period: str,
    start_date: str,
    end_date: str
):
    """광고 계정(account_id)‑기간(start~end) 기준 / 캠페인 목표별(도달·유입·전환) 성과 요약 반환.

    ‑ adset_id + date 단위로 중복 제거 (하루 1 adset)
    ‑ adset_id 당 *최신* adset_name 하나만 사용 → type 중복 완전 차단
    """

    today = datetime.today().strftime("%Y-%m-%d")
    start_date = (start_date or today).strip()
    end_date   = (end_date   or today).strip()

    # ─────────────────────────────────────────────────────────────
    # 1) 목표별 요약 쿼리
    #    • daily  : adset_id  +  date  단위 집계
    #    • latest : adset_id 당 최신(adset_name) 1개 고정
    #    • typed  : adset_name → type 매핑(CASE)
    # ─────────────────────────────────────────────────────────────
    type_summary_query = f"""
    WITH daily AS (
      SELECT
        account_id,
        adset_id,
        DATE(date)                                 AS dt,
        ANY_VALUE(adset_name)                      AS adset_name,
        ANY_VALUE(account_name)                    AS account_name,
        SUM(spend)            AS spend,
        SUM(impressions)      AS impressions,
        SUM(clicks)           AS clicks,
        SUM(purchases)        AS purchases,
        SUM(purchase_value)   AS purchase_value
      FROM `winged-precept-443218-v8.ngn_dataset.meta_ads_adset_summary`
      WHERE DATE(date) BETWEEN '{start_date}' AND '{end_date}'
        AND account_id = '{account_id}'
      GROUP BY account_id, adset_id, dt
    ),
    latest AS (
      SELECT
        d.* EXCEPT(adset_name),
        FIRST_VALUE(adset_name) OVER (
          PARTITION BY adset_id ORDER BY dt DESC
        ) AS adset_name
      FROM daily AS d
    ),
    typed AS (
      SELECT *,
        CASE
          WHEN adset_name LIKE '%도달%'  THEN '도달'
          WHEN adset_name LIKE '%유입%'  THEN '유입'
          WHEN adset_name LIKE '%전환%' THEN '전환'
          ELSE '기타'
        END AS type
      FROM latest
    )
    SELECT
      '{start_date} ~ {end_date}'   AS period,
      account_id,
      account_name,
      type,
      SUM(spend)          AS total_spend,
      SUM(impressions)    AS total_impressions,
      SAFE_MULTIPLY(SAFE_DIVIDE(SUM(spend), SUM(impressions)), 1000) AS CPM,
      SUM(clicks)         AS total_clicks,
      SAFE_DIVIDE(SUM(spend), SUM(clicks))                         AS CPC,
      SAFE_DIVIDE(SUM(clicks), SUM(impressions))                   AS CTR,
      SUM(purchases)      AS total_purchases,
      SUM(purchase_value) AS total_purchase_value,
      SAFE_DIVIDE(SUM(purchase_value), SUM(spend))                 AS ROAS,
      SAFE_DIVIDE(SUM(spend), SUM(purchases))                      AS CPA
    FROM typed
    WHERE type <> '기타'
    GROUP BY account_id, account_name, type
    ORDER BY total_spend DESC;
    """

    # ─────────────────────────────────────────────────────────────
    # 2) 전체 지출 합계 (동일 중복 제거 로직)
    # ─────────────────────────────────────────────────────────────
    total_spend_query = f"""
    SELECT SUM(spend) AS total_spend
    FROM (
      SELECT adset_id, DATE(date) AS dt, SUM(spend) AS spend
      FROM `winged-precept-443218-v8.ngn_dataset.meta_ads_adset_summary`
      WHERE DATE(date) BETWEEN '{start_date}' AND '{end_date}'
        AND account_id = '{account_id}'
      GROUP BY adset_id, dt
    );
    """

    try:
        summary_rows = client.query(type_summary_query).result()
        type_summary = dictify_rows(summary_rows)

        spend_rows = client.query(total_spend_query).result()
        total_spend = list(spend_rows)[0].get("total_spend", 0.0) if spend_rows.total_rows else 0.0

        return type_summary, total_spend

    except Exception as err:
        print("[ERROR] get_meta_ads_adset_summary_by_type:", err)
        return [], 0.0
