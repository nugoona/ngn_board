from google.cloud import bigquery
from flask import session
from typing import Optional

# ------------------------- 공통 ------------------------- #
def dictify_rows(rows):
    return [dict(row) for row in rows]

# 회사(계정) 드롭다운용
def get_meta_account_list_filtered(company_name: str):
    client = bigquery.Client()
    allowed = [c.lower() for c in session.get("company_names", [])]

    if company_name == "all":
        filtered = allowed or ["__no_company__"]
    elif isinstance(company_name, list):
        filtered = [c for c in company_name if c.lower() in allowed] or ["__no_company__"]
    else:
        filtered = [company_name.lower()] if company_name.lower() in allowed else ["__no_company__"]

    qry = """
      SELECT DISTINCT
        meta_acc_id   AS account_id,
        meta_acc_name AS account_name,
        catalog_id, 
        company_name
      FROM `winged-precept-443218-v8.ngn_dataset.metaAds_acc`
      WHERE LOWER(company_name) IN UNNEST(@filtered_companies)
      ORDER BY meta_acc_name
    """
    cfg = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ArrayQueryParameter("filtered_companies", "STRING", filtered)]
    )

    try:
        return dictify_rows(bigquery.Client().query(qry, job_config=cfg).result())
    except Exception as e:
        print(f"[ERROR] Meta 계정 리스트 조회 실패: {e}")
        return []

# ---------------------- 핵심 분석 테이블 ---------------------- #
def get_meta_ads_insight_table(
    level: str,
    company_name,
    start_date: str,
    end_date: str,
    account_id: Optional[str] = None,
    campaign_id: Optional[str] = None,
    adset_id: Optional[str] = None,
    date_type: str = "summary",
    limit: int = None,
    page: int = 1
):
    client = bigquery.Client()
    query_params = [
        bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
        bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
    ]
    conditions = ["A.date BETWEEN @start_date AND @end_date"]

    if date_type == "daily":
        select_date = "FORMAT_DATE('%Y-%m-%d', A.date) AS date,"
        group_date = "date"
    else:
        select_date = "CONCAT(@start_date, ' ~ ', @end_date) AS report_date,"
        group_date = ""

    updated_at_sub = """
      (SELECT MAX(updated_at)
       FROM `winged-precept-443218-v8.ngn_dataset.meta_ads_account_summary`) AS updated_at
    """

    if level == "account":
        base_tbl = "meta_ads_account_summary"
        latest_alias = "acc_latest"
        latest_join = f"""
          LEFT JOIN (
              SELECT * EXCEPT(rn) FROM (
                  SELECT account_id,
                         account_name,
                         company_name,
                         ROW_NUMBER() OVER (PARTITION BY account_id ORDER BY updated_at DESC) AS rn
                  FROM `winged-precept-443218-v8.ngn_dataset.{base_tbl}`
              )
              WHERE rn = 1
          ) AS {latest_alias}
          ON A.account_id = {latest_alias}.account_id
        """
        select_cols = f"""
            A.account_id,
            MAX({latest_alias}.account_name) AS account_name,
            MAX({latest_alias}.company_name) AS company_name,
            {updated_at_sub}
        """
        group_cols = "A.account_id"
        company_ref = f"{latest_alias}.company_name"

    elif level == "campaign":
        base_tbl, latest_alias = "meta_ads_campaign_summary", "camp_latest"
        latest_join = f"""
          LEFT JOIN (
              SELECT * EXCEPT(rn) FROM (
                  SELECT account_id,
                         campaign_id,
                         account_name,
                         company_name,
                         campaign_name,
                         ROW_NUMBER() OVER (PARTITION BY campaign_id ORDER BY updated_at DESC) AS rn
                  FROM `winged-precept-443218-v8.ngn_dataset.{base_tbl}`
              )
              WHERE rn = 1
          ) AS {latest_alias}
          ON A.campaign_id = {latest_alias}.campaign_id
        """
        select_cols = f"""
            A.account_id,
            A.campaign_id,
            MAX({latest_alias}.account_name)   AS account_name,
            MAX({latest_alias}.company_name)   AS company_name,
            MAX({latest_alias}.campaign_name)  AS campaign_name,
            {updated_at_sub}
        """
        group_cols = "A.account_id, A.campaign_id"
        company_ref = f"{latest_alias}.company_name"

    elif level == "adset":
        base_tbl, latest_alias = "meta_ads_adset_summary", "adset_latest"
        latest_join = f"""
          LEFT JOIN (
              SELECT * EXCEPT(rn) FROM (
                  SELECT adset_id,
                         campaign_id,
                         account_id,
                         account_name,
                         company_name,
                         campaign_name,
                         adset_name,
                         ROW_NUMBER() OVER (PARTITION BY adset_id ORDER BY updated_at DESC) AS rn
                  FROM `winged-precept-443218-v8.ngn_dataset.{base_tbl}`
              )
              WHERE rn = 1
          ) AS {latest_alias}
          ON A.adset_id = {latest_alias}.adset_id
        """
        select_cols = f"""
            A.account_id,
            A.campaign_id,
            A.adset_id,
            MAX({latest_alias}.account_name)   AS account_name,
            MAX({latest_alias}.company_name)   AS company_name,
            MAX({latest_alias}.campaign_name)  AS campaign_name,
            MAX({latest_alias}.adset_name)     AS adset_name,
            {updated_at_sub}
        """
        group_cols = "A.account_id, A.campaign_id, A.adset_id"
        company_ref = f"{latest_alias}.company_name"

    elif level == "ad":
        base_tbl, latest_alias = "meta_ads_ad_summary", "ad_latest"
        latest_join = f"""
          LEFT JOIN (
              SELECT * EXCEPT(rn) FROM (
                  SELECT ad_id,
                         adset_id,
                         campaign_id,
                         account_id,
                         account_name,
                         company_name,
                         campaign_name,
                         adset_name,
                         ad_name,
                         ad_status,
                         ROW_NUMBER() OVER (PARTITION BY ad_id ORDER BY updated_at DESC) AS rn
                  FROM `winged-precept-443218-v8.ngn_dataset.{base_tbl}`
              )
              WHERE rn = 1
          ) AS {latest_alias}
          ON A.ad_id = {latest_alias}.ad_id

          LEFT JOIN `winged-precept-443218-v8.ngn_dataset.company_info` C
          ON LOWER({latest_alias}.company_name) = LOWER(C.company_name)
        """
        select_cols = f"""
            A.account_id,
            A.campaign_id,
            A.adset_id,
            A.ad_id,
            MAX({latest_alias}.account_name)   AS account_name,
            MAX({latest_alias}.company_name)   AS company_name,
            MAX({latest_alias}.campaign_name)  AS campaign_name,
            MAX({latest_alias}.adset_name)     AS adset_name,
            MAX({latest_alias}.ad_name)        AS ad_name,
            MAX({latest_alias}.ad_status)      AS ad_status,
            CONCAT(
               'https://adsmanager.facebook.com/adsmanager/manage/ads/edit/standalone?',
               'act=', A.account_id,
               '&selected_ad_ids=', A.ad_id,
               '&business_id=', MAX(C.meta_business_id),
               '&nav_source=no_referrer#'
            ) AS ad_url,
            {updated_at_sub}
        """
        group_cols = "A.account_id, A.campaign_id, A.adset_id, A.ad_id"
        company_ref = f"{latest_alias}.company_name"

    else:
        print(f"[ERROR] 잘못된 level 파라미터: {level}")
        return []

    # ✅ campaign/adset/ad level일 때는 account_id 필수
    if level in ["campaign", "adset", "ad"] and not account_id:
        print(f"[ERROR] {level} level은 account_id가 필수입니다.")
        return {"rows": [], "total_count": 0} if limit is not None else []

    if account_id:
        conditions.append("A.account_id = @account_id")
        query_params.append(bigquery.ScalarQueryParameter("account_id", "STRING", account_id))
    else:
        # account level일 때만 account_id 없이 company_name으로 필터링
        if isinstance(company_name, list):
            conditions.append(f"LOWER({company_ref}) IN UNNEST(@company_names)")
            query_params.append(bigquery.ArrayQueryParameter("company_names", "STRING", [c.lower() for c in company_name]))
        elif company_name != "all":
            conditions.append(f"LOWER({company_ref}) = @company_name")
            query_params.append(bigquery.ScalarQueryParameter("company_name", "STRING", company_name.lower()))

    if campaign_id:
        campaign_ids = [x.strip() for x in campaign_id.split(",") if x.strip()]
        conditions.append("A.campaign_id IN UNNEST(@campaign_ids)")
        query_params.append(bigquery.ArrayQueryParameter("campaign_ids", "STRING", campaign_ids))

    if adset_id:
        adset_ids = [x.strip() for x in adset_id.split(",") if x.strip()]
        conditions.append("A.adset_id IN UNNEST(@adset_ids)")
        query_params.append(bigquery.ArrayQueryParameter("adset_ids", "STRING", adset_ids))

    if level == "ad":
        conditions.append(f"({latest_alias}.campaign_name IS NULL OR NOT LOWER({latest_alias}.campaign_name) LIKE '%instagram%')")
        
        # 광고 상태 필터링: 기간 길이로 판단하도록 수정
        from datetime import datetime, timedelta
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
        
        # 기간의 길이로 판단 (7일 이내면 최근, 그 이상이면 과거)
        period_length = (end_date_obj - start_date_obj).days
        is_recent_period = period_length <= 7
        
        print(f"[DEBUG] 광고 상태 필터링 - 기간: {start_date} ~ {end_date}, 기간 길이: {period_length}일, 최근 기간: {is_recent_period}")

        # 🔥 수정: 해당 기간에 지출 데이터가 있는 모든 광고 포함 (상태 무관)
        # HAVING SUM(A.spend) > 0 조건이 이미 있으므로 지출 있는 광고만 포함됨
        # 광고 상태 필터 제거 - PAUSED 광고도 지출 데이터가 있으면 ROAS 계산에 포함
        print(f"[DEBUG] 모든 광고 상태 포함 (지출 데이터가 있는 광고만 - HAVING 조건)")
            
    elif level != "account":
        conditions.append("(A.campaign_name IS NULL OR NOT LOWER(A.campaign_name) LIKE '%instagram%')")

    order_by = "ORDER BY date DESC" if date_type == "daily" else ""

    # 페이지네이션 처리 (웹 UI에 영향 없도록 기본값 유지)
    limit_clause = ""
    if limit is not None and page > 0:
        offset = (page - 1) * limit
        limit_clause = " LIMIT @limit OFFSET @offset"
        query_params.append(bigquery.ScalarQueryParameter("limit", "INT64", limit))
        query_params.append(bigquery.ScalarQueryParameter("offset", "INT64", offset))
    
    query = f"""
      SELECT
        {select_date}
        {select_cols},
        SUM(A.spend)          AS spend,
        SUM(A.impressions)    AS impressions,
        SUM(A.clicks)         AS clicks,
        SUM(A.purchases)      AS purchases,
        SUM(A.purchase_value) AS purchase_value
      FROM `winged-precept-443218-v8.ngn_dataset.{base_tbl}` A
      {latest_join}
      WHERE {" AND ".join(conditions)}
      GROUP BY { (group_date + ', ' if group_date else '') + group_cols }
      HAVING SUM(A.spend) > 0 OR SUM(A.purchases) > 0
      {order_by}
      {limit_clause}
    """

    try:
        # 파라미터화된 쿼리 실행
        job_config = bigquery.QueryJobConfig(query_parameters=query_params)
        rows = client.query(query, job_config=job_config).result()
        result = dictify_rows(rows)
        if date_type == "summary":
            for r in result:
                r["start_date"], r["end_date"] = start_date, end_date

        # 페이지네이션이 적용된 경우 전체 개수도 조회
        if limit is not None and page > 0:
            # 전체 개수 조회 쿼리 (페이지네이션 없이) - limit/offset 파라미터 제외
            count_params = [p for p in query_params if p.name not in ("limit", "offset")]
            count_query = f"""
              SELECT COUNT(*) AS total_count
              FROM (
                SELECT 1
                FROM `winged-precept-443218-v8.ngn_dataset.{base_tbl}` A
                {latest_join}
                WHERE {" AND ".join(conditions)}
                GROUP BY { (group_date + ', ' if group_date else '') + group_cols }
                HAVING SUM(A.spend) > 0 OR SUM(A.purchases) > 0
              )
            """

            try:
                count_job_config = bigquery.QueryJobConfig(query_parameters=count_params)
                count_rows = client.query(count_query, job_config=count_job_config).result()
                total_count = next(count_rows)["total_count"]
                print(f"[DEBUG] 메타 광고 전체 개수: {total_count}, 현재 페이지: {len(result)}개")
                return {
                    "rows": result,
                    "total_count": total_count
                }
            except Exception as count_error:
                print(f"[ERROR] 전체 개수 조회 실패: {count_error}")
                return {
                    "rows": result,
                    "total_count": len(result)
                }

        return result

    except Exception as e:
        print(f"[ERROR] BigQuery 실행 오류: {e}")
        return []
