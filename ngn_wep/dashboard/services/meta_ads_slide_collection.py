# File: services/meta_ads_slide_collection.py

from google.cloud import bigquery

def get_slide_collection_ads(account_id=None):
    """
    슬라이드/콜렉션 광고 리스트 조회 (단일/영상 광고 제외) - 광고명 기준으로 그룹핑
    """
    if not account_id or str(account_id).strip().lower() in ["none", "null", ""]:
        print("[INFO] [슬라이드광고] account_id가 선택되지 않아 쿼리 건너뜀")
        return []

    print(f"[DEBUG] [슬라이드광고] get_slide_collection_ads 호출됨 | account_id: {account_id}")

    client = bigquery.Client()

    query = """
        WITH filtered_ads AS (
          SELECT
            B.company_name,
            A.account_id,
            A.ad_id,
            C.meta_business_id,
            A.ad_name
          FROM `winged-precept-443218-v8.ngn_dataset.meta_ads_ad_level` A
          LEFT JOIN `winged-precept-443218-v8.ngn_dataset.metaAds_acc` B
            ON A.account_id = B.meta_acc_id
          LEFT JOIN `winged-precept-443218-v8.ngn_dataset.company_info` C
            ON B.company_name = C.company_name
          WHERE
            A.date = CURRENT_DATE('Asia/Seoul')
            AND A.ad_status = 'ACTIVE'
            AND NOT (LOWER(A.ad_name) LIKE '%단일%' OR LOWER(A.ad_name) LIKE '%영상%')
            AND A.account_id = @account_id
        )
        
        SELECT
          company_name,
          account_id,
          ANY_VALUE(ad_id) AS ad_id,             -- ✅ ad_id는 하나만 대표값으로
          ANY_VALUE(meta_business_id) AS meta_business_id,
          ad_name
        FROM filtered_ads
        GROUP BY
          company_name, account_id, ad_name
        ORDER BY
          company_name, ad_name
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("account_id", "STRING", account_id)
        ]
    )

    try:
        query_job = client.query(query, job_config=job_config)
        rows = query_job.result()
        result = [dict(row) for row in rows]
        print(f"[DEBUG] [슬라이드광고] BigQuery 결과 {len(result)}건 조회됨")
        return result

    except Exception as e:
        print(f"[ERROR] [슬라이드광고] 광고 목록 조회 실패: {e}")
        return []
