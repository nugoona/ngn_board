# File: services/Fetch_Adset_Summary.py

"""META Ads 캠페인 목표별 성과 요약 — 원본 데이터 직접 집계 버전"""

from google.cloud import bigquery
from datetime import datetime

client = bigquery.Client()


def dictify_rows(rows):
    """BigQuery RowIterator → list[dict]"""
    return [dict(r) for r in rows]


def debug_data_source(account_id: str, start_date: str, end_date: str):
    """데이터 소스 디버깅 함수"""
    debug_query = """
    SELECT
      'ad_level' as source,
      COUNT(*) as total_rows,
      COUNT(DISTINCT adset_id) as unique_adsets,
      COUNT(DISTINCT DATE(date)) as unique_dates,
      SUM(spend) as total_spend
    FROM `winged-precept-443218-v8.ngn_dataset.meta_ads_ad_level`
    WHERE DATE(date) BETWEEN @start_date AND @end_date
      AND account_id = @account_id
      AND adset_id IS NOT NULL

    UNION ALL

    SELECT
      'adset_summary' as source,
      COUNT(*) as total_rows,
      COUNT(DISTINCT adset_id) as unique_adsets,
      COUNT(DISTINCT DATE(date)) as unique_dates,
      SUM(spend) as total_spend
    FROM `winged-precept-443218-v8.ngn_dataset.meta_ads_adset_summary`
    WHERE DATE(date) BETWEEN @start_date AND @end_date
      AND account_id = @account_id
      AND adset_id IS NOT NULL
    """
    query_params = [
        bigquery.ScalarQueryParameter("account_id", "STRING", account_id),
        bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
        bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
    ]

    try:
        results = client.query(debug_query, job_config=bigquery.QueryJobConfig(query_parameters=query_params)).result()
        debug_data = dictify_rows(results)
        print(f"[DEBUG] 데이터 소스 비교:")
        for row in debug_data:
            print(f"  {row['source']}: {row['total_rows']}행, {row['unique_adsets']}개 adset, {row['unique_dates']}일, 총 지출: {row['total_spend']}")
        return debug_data
    except Exception as e:
        print(f"[ERROR] 디버깅 쿼리 실패: {e}")
        return []


def debug_missing_data(account_id: str, start_date: str, end_date: str):
    """누락된 데이터 디버깅 함수"""
    debug_query = """
    WITH all_adsets AS (
      SELECT DISTINCT
        adset_id,
        adset_name,
        SUM(spend) as total_spend
      FROM `winged-precept-443218-v8.ngn_dataset.meta_ads_ad_level`
      WHERE DATE(date) BETWEEN @start_date AND @end_date
        AND account_id = @account_id
        AND adset_id IS NOT NULL
      GROUP BY adset_id, adset_name
    ),
    classified_adsets AS (
      SELECT *,
        CASE
          WHEN adset_name LIKE '%도달%' OR adset_name LIKE '%reach%' OR adset_name LIKE '%브랜드%' THEN '도달'
          WHEN adset_name LIKE '%유입%' OR adset_name LIKE '%traffic%' OR adset_name LIKE '%engagement%' OR adset_name LIKE '%참여%' OR adset_name LIKE '%유입목적%' THEN '유입'
          WHEN adset_name LIKE '%전환%' OR adset_name LIKE '%conversion%' OR adset_name LIKE '%구매%' OR adset_name LIKE '%sales%' OR adset_name LIKE '%전환목적%' THEN '전환'
          WHEN adset_name LIKE '%앱설치%' OR adset_name LIKE '%app%' THEN '앱설치'
          WHEN adset_name LIKE '%리드%' OR adset_name LIKE '%lead%' THEN '리드'
          ELSE '기타'
        END AS type
      FROM all_adsets
    )
    SELECT
      type,
      COUNT(*) as adset_count,
      SUM(total_spend) as type_total_spend,
      STRING_AGG(adset_name, ', ') as adset_names
    FROM classified_adsets
    GROUP BY type
    ORDER BY type_total_spend DESC
    """
    query_params = [
        bigquery.ScalarQueryParameter("account_id", "STRING", account_id),
        bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
        bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
    ]

    try:
        results = client.query(debug_query, job_config=bigquery.QueryJobConfig(query_parameters=query_params)).result()
        debug_data = dictify_rows(results)
        print(f"[DEBUG] 광고세트별 분류 결과:")
        for row in debug_data:
            print(f"  {row['type']}: {row['adset_count']}개 광고세트, 총 지출: {row['type_total_spend']}")
            print(f"    광고세트명: {row['adset_names']}")
        return debug_data
    except Exception as e:
        print(f"[ERROR] 누락 데이터 디버깅 쿼리 실패: {e}")
        return []


def get_meta_ads_adset_summary_by_type(
    account_id: str,
    period: str,
    start_date: str,
    end_date: str
):
    """광고 계정(account_id)‑기간(start~end) 기준 / 캠페인 목표별(도달·유입·전환) 성과 요약 반환.

    ‑ 광고세트별 데이터로 목표 분류
    ‑ adset_name → type 매핑(CASE)
    """

    # period 기반으로 올바른 날짜 계산
    from ngn_wep.dashboard.handlers.data_handler import get_start_end_dates
    start_date, end_date = get_start_end_dates(period, start_date, end_date)
    
    today = datetime.today().strftime("%Y-%m-%d")
    start_date = (start_date or today).strip()
    end_date   = (end_date   or today).strip()

    # 디버깅: 데이터 소스 비교 (실제 사용되는 날짜 범위로)
    print(f"[DEBUG] 실제 요청 날짜 범위: {start_date} ~ {end_date}")
    debug_data_source(account_id, start_date, end_date)
    
    # 디버깅: 누락된 데이터 확인 (실제 사용되는 날짜 범위로)
    debug_missing_data(account_id, start_date, end_date)

    # ─────────────────────────────────────────────────────────────
    # 1) 목표별 요약 쿼리 - 광고세트별 목표 분류
    #    • adset_summary: 광고세트별 데이터로 목표 분류 가능
    #    • typed: adset_name → type 매핑(CASE)
    # ─────────────────────────────────────────────────────────────
    type_summary_query = """
    WITH adset_data AS (
      SELECT
        account_id,
        account_name,
        adset_name,
        SUM(spend) AS total_spend,
        SUM(impressions) AS total_impressions,
        SUM(clicks) AS total_clicks,
        SUM(purchases) AS total_purchases,
        SUM(purchase_value) AS total_purchase_value
      FROM `winged-precept-443218-v8.ngn_dataset.meta_ads_adset_summary`
      WHERE date BETWEEN @start_date AND @end_date
        AND account_id = @account_id
      GROUP BY account_id, account_name, adset_name
    ),
    typed AS (
      SELECT
        CONCAT(@start_date, ' ~ ', @end_date) AS period,
        account_id,
        account_name,
        CASE
          WHEN adset_name LIKE '%도달%' OR adset_name LIKE '%reach%' OR adset_name LIKE '%브랜드%' THEN '도달'
          WHEN adset_name LIKE '%유입%' OR adset_name LIKE '%traffic%' OR adset_name LIKE '%engagement%' OR adset_name LIKE '%참여%' OR adset_name LIKE '%유입목적%' THEN '유입'
          WHEN adset_name LIKE '%전환%' OR adset_name LIKE '%conversion%' OR adset_name LIKE '%구매%' OR adset_name LIKE '%sales%' OR adset_name LIKE '%전환목적%' THEN '전환'
          WHEN adset_name LIKE '%앱설치%' OR adset_name LIKE '%app%' THEN '앱설치'
          WHEN adset_name LIKE '%리드%' OR adset_name LIKE '%lead%' THEN '리드'
          ELSE '기타'
        END AS type,
        total_spend,
        total_impressions,
        total_clicks,
        total_purchases,
        total_purchase_value
      FROM adset_data
    )
    SELECT
      period,
      account_id,
      account_name,
      type,
      SUM(total_spend) AS total_spend,
      SUM(total_impressions) AS total_impressions,
      SAFE_MULTIPLY(SAFE_DIVIDE(SUM(total_spend), SUM(total_impressions)), 1000) AS CPM,
      SUM(total_clicks) AS total_clicks,
      SAFE_DIVIDE(SUM(total_spend), SUM(total_clicks)) AS CPC,
      SAFE_DIVIDE(SUM(total_clicks), SUM(total_impressions)) AS CTR,
      SUM(total_purchases) AS total_purchases,
      SUM(total_purchase_value) AS total_purchase_value,
      SAFE_DIVIDE(SUM(total_purchase_value), SUM(total_spend)) AS ROAS,
      SAFE_DIVIDE(SUM(total_spend), SUM(total_purchases)) AS CPA
    FROM typed
    WHERE type <> '기타'
    GROUP BY period, account_id, account_name, type
    ORDER BY total_spend DESC;
    """

    # ─────────────────────────────────────────────────────────────
    # 2) 전체 지출 합계 (광고세트별 데이터에서 계산)
    # ─────────────────────────────────────────────────────────────
    total_spend_query = """
    SELECT SUM(spend) AS total_spend
    FROM `winged-precept-443218-v8.ngn_dataset.meta_ads_adset_summary`
    WHERE date BETWEEN @start_date AND @end_date
      AND account_id = @account_id;
    """

    query_params = [
        bigquery.ScalarQueryParameter("account_id", "STRING", account_id),
        bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
        bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
    ]

    try:
        print(f"[DEBUG] 원본 데이터 직접 집계 시작: {start_date} ~ {end_date}, account_id: {account_id}")

        job_config = bigquery.QueryJobConfig(query_parameters=query_params)
        summary_rows = client.query(type_summary_query, job_config=job_config).result()
        type_summary = dictify_rows(summary_rows)

        spend_rows = client.query(total_spend_query, job_config=job_config).result()
        total_spend = list(spend_rows)[0].get("total_spend", 0.0) if spend_rows.total_rows else 0.0

        print(f"[DEBUG] 원본 데이터 집계 결과: {len(type_summary)}개 타입, 총 지출: {total_spend}")

        # 디버깅을 위한 상세 로그
        for row in type_summary:
            print(f"[DEBUG] 타입별 집계: {row['type']} - 지출: {row['total_spend']}, 구매: {row['total_purchases']}")

        return type_summary, total_spend

    except Exception as err:
        print("[ERROR] get_meta_ads_adset_summary_by_type:", err)
        return [], 0.0
