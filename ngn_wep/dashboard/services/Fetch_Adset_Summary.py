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
    debug_query = f"""
    SELECT 
      'ad_level' as source,
      COUNT(*) as total_rows,
      COUNT(DISTINCT adset_id) as unique_adsets,
      COUNT(DISTINCT DATE(date)) as unique_dates,
      SUM(spend) as total_spend
    FROM `winged-precept-443218-v8.ngn_dataset.meta_ads_ad_level`
    WHERE DATE(date) BETWEEN '{start_date}' AND '{end_date}'
      AND account_id = '{account_id}'
      AND adset_id IS NOT NULL
    
    UNION ALL
    
    SELECT 
      'adset_summary' as source,
      COUNT(*) as total_rows,
      COUNT(DISTINCT adset_id) as unique_adsets,
      COUNT(DISTINCT DATE(date)) as unique_dates,
      SUM(spend) as total_spend
    FROM `winged-precept-443218-v8.ngn_dataset.meta_ads_adset_summary`
    WHERE DATE(date) BETWEEN '{start_date}' AND '{end_date}'
      AND account_id = '{account_id}'
      AND adset_id IS NOT NULL
    """
    
    try:
        results = client.query(debug_query).result()
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
    debug_query = f"""
    WITH all_adsets AS (
      SELECT DISTINCT
        adset_id,
        adset_name,
        SUM(spend) as total_spend
      FROM `winged-precept-443218-v8.ngn_dataset.meta_ads_ad_level`
      WHERE DATE(date) BETWEEN '{start_date}' AND '{end_date}'
        AND account_id = '{account_id}'
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
    
    try:
        results = client.query(debug_query).result()
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

    ‑ 원본 데이터(meta_ads_ad_level)에서 직접 집계하여 이중 집계 방지
    ‑ adset_id + date 단위로 중복 제거
    ‑ adset_id 당 *최신* adset_name 하나만 사용 → type 중복 완전 차단
    """

    today = datetime.today().strftime("%Y-%m-%d")
    start_date = (start_date or today).strip()
    end_date   = (end_date   or today).strip()

    # 디버깅: 데이터 소스 비교
    debug_data_source(account_id, start_date, end_date)
    
    # 디버깅: 누락된 데이터 확인
    debug_missing_data(account_id, start_date, end_date)

    # ─────────────────────────────────────────────────────────────
    # 1) 목표별 요약 쿼리 - 원본 데이터 직접 집계
    #    • deduplicated: adset_id + date + adset_name 조합으로 중복 제거
    #    • latest: adset_id 당 최신(adset_name) 1개 고정
    #    • typed: adset_name → type 매핑(CASE)
    # ─────────────────────────────────────────────────────────────
    type_summary_query = f"""
    WITH deduplicated AS (
      SELECT
        ad.account_id,
        ad.adset_id,
        DATE(ad.date) AS dt,
        ad.adset_name,
        ad.account_name,
        ad.spend,
        ad.impressions,
        ad.clicks,
        ad.purchases,
        ad.purchase_value,
        ROW_NUMBER() OVER (
          PARTITION BY ad.adset_id, DATE(ad.date), ad.adset_name 
          ORDER BY ad.date DESC, ad.updated_at DESC
        ) AS rn
      FROM `winged-precept-443218-v8.ngn_dataset.meta_ads_ad_level` ad
      WHERE DATE(ad.date) BETWEEN '{start_date}' AND '{end_date}'
        AND ad.account_id = '{account_id}'
        AND ad.adset_id IS NOT NULL
        AND ad.adset_name IS NOT NULL
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
          WHEN adset_name LIKE '%도달%' OR adset_name LIKE '%reach%' OR adset_name LIKE '%브랜드%' THEN '도달'
          WHEN adset_name LIKE '%유입%' OR adset_name LIKE '%traffic%' OR adset_name LIKE '%engagement%' OR adset_name LIKE '%참여%' OR adset_name LIKE '%유입목적%' THEN '유입'
          WHEN adset_name LIKE '%전환%' OR adset_name LIKE '%conversion%' OR adset_name LIKE '%구매%' OR adset_name LIKE '%sales%' OR adset_name LIKE '%전환목적%' THEN '전환'
          WHEN adset_name LIKE '%앱설치%' OR adset_name LIKE '%app%' THEN '앱설치'
          WHEN adset_name LIKE '%리드%' OR adset_name LIKE '%lead%' THEN '리드'
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
    GROUP BY account_id, account_name, type
    ORDER BY total_spend DESC;
    """

    # ─────────────────────────────────────────────────────────────
    # 2) 전체 지출 합계 (원본 데이터 직접 집계)
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
          ad.adset_id,
          ad.date,
          ad.spend,
          ROW_NUMBER() OVER (
            PARTITION BY ad.adset_id, DATE(ad.date) 
            ORDER BY ad.date DESC, ad.updated_at DESC
          ) AS rn
        FROM `winged-precept-443218-v8.ngn_dataset.meta_ads_ad_level` ad
        WHERE DATE(ad.date) BETWEEN '{start_date}' AND '{end_date}'
          AND ad.account_id = '{account_id}'
          AND ad.adset_id IS NOT NULL
      )
      WHERE rn = 1  -- 중복 제거
      GROUP BY adset_id, dt
    );
    """

    try:
        print(f"[DEBUG] 원본 데이터 직접 집계 시작: {start_date} ~ {end_date}, account_id: {account_id}")
        
        summary_rows = client.query(type_summary_query).result()
        type_summary = dictify_rows(summary_rows)

        spend_rows = client.query(total_spend_query).result()
        total_spend = list(spend_rows)[0].get("total_spend", 0.0) if spend_rows.total_rows else 0.0

        print(f"[DEBUG] 원본 데이터 집계 결과: {len(type_summary)}개 타입, 총 지출: {total_spend}")
        
        # 디버깅을 위한 상세 로그
        for row in type_summary:
            print(f"[DEBUG] 타입별 집계: {row['type']} - 지출: {row['total_spend']}, 구매: {row['total_purchases']}")
        
        return type_summary, total_spend

    except Exception as err:
        print("[ERROR] get_meta_ads_adset_summary_by_type:", err)
        return [], 0.0
