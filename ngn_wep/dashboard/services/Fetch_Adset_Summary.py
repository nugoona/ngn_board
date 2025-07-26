# File: services/Fetch_Adset_Summary.py

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
    # 1) 목표별 요약 쿼리 - 중복 제거 로직 개선
    #    • deduplicated: adset_id + date + adset_name 조합으로 중복 제거
    #    • latest: adset_id 당 최신(adset_name) 1개 고정
    #    • typed: adset_name → type 매핑(CASE)
    # ─────────────────────────────────────────────────────────────
    type_summary_query = f"""
    WITH deduplicated AS (
      SELECT
        account_id,
        adset_id,
        DATE(date) AS dt,
        adset_name,
        account_name,
        spend,
        impressions,
        clicks,
        purchases,
        purchase_value,
        ROW_NUMBER() OVER (
          PARTITION BY adset_id, DATE(date), adset_name 
          ORDER BY date DESC, updated_at DESC
        ) AS rn
      FROM `winged-precept-443218-v8.ngn_dataset.meta_ads_adset_summary`
      WHERE DATE(date) BETWEEN '{start_date}' AND '{end_date}'
        AND account_id = '{account_id}'
    ),
    daily AS (
      SELECT
        account_id,
        adset_id,
        dt,
        adset_name,
        account_name,
        SUM(spend) AS spend,
        SUM(impressions) AS impressions,
        SUM(clicks) AS clicks,
        SUM(purchases) AS purchases,
        SUM(purchase_value) AS purchase_value
      FROM deduplicated
      WHERE rn = 1  -- 중복 제거
      GROUP BY account_id, adset_id, dt, adset_name, account_name
    ),
    latest AS (
      SELECT
        d.* EXCEPT(adset_name),
        FIRST_VALUE(adset_name) OVER (
          PARTITION BY adset_id ORDER BY dt DESC, spend DESC
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
    # 2) 전체 지출 합계 (동일 중복 제거 로직 적용)
    # ─────────────────────────────────────────────────────────────
    total_spend_query = f"""
    SELECT SUM(spend) AS total_spend
    FROM (
      SELECT 
        adset_id, 
        DATE(date) AS dt, 
        SUM(spend) AS spend
      FROM (
        SELECT
          adset_id,
          date,
          spend,
          ROW_NUMBER() OVER (
            PARTITION BY adset_id, DATE(date) 
            ORDER BY date DESC, updated_at DESC
          ) AS rn
        FROM `winged-precept-443218-v8.ngn_dataset.meta_ads_adset_summary`
        WHERE DATE(date) BETWEEN '{start_date}' AND '{end_date}'
          AND account_id = '{account_id}'
      )
      WHERE rn = 1  -- 중복 제거
      GROUP BY adset_id, dt
    );
    """

    try:
        summary_rows = client.query(type_summary_query).result()
        type_summary = dictify_rows(summary_rows)

        spend_rows = client.query(total_spend_query).result()
        total_spend = list(spend_rows)[0].get("total_spend", 0.0) if spend_rows.total_rows else 0.0

        print(f"[DEBUG] get_meta_ads_adset_summary_by_type 결과: {len(type_summary)}개 타입, 총 지출: {total_spend}")
        return type_summary, total_spend

    except Exception as err:
        print("[ERROR] get_meta_ads_adset_summary_by_type:", err)
        return [], 0.0
