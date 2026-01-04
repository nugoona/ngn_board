"""
29CM 트렌드 분석 서비스
주간 베스트 상품 데이터를 분석하여 급상승, 신규 진입, 순위 하락 상품을 조회
"""
from google.cloud import bigquery
from ..utils.cache_utils import cached_query
from typing import List, Dict, Any, Optional

def get_bigquery_client():
    """BigQuery Client 생성"""
    return bigquery.Client()


@cached_query(func_name="trend_29cm_rising", ttl=604800)  # 7일 캐싱 (주간 데이터)
def get_rising_star(tab_name: str = "전체") -> List[Dict[str, Any]]:
    """
    급상승 랭킹 (Rising Star) 조회
    지난주 대비 이번주 순위가 상승한 상품
    """
    client = get_bigquery_client()
    
    query = """
    DECLARE target_tab STRING DEFAULT @tab_name;
    
    WITH weeks AS (
      SELECT DISTINCT run_id 
      FROM `winged-precept-443218-v8.ngn_dataset.platform_29cm_best`
      WHERE period_type = 'WEEKLY' 
      ORDER BY run_id DESC 
      LIMIT 2
    ),
    base_data AS (
      SELECT *,
        DENSE_RANK() OVER (ORDER BY run_id DESC) as week_idx,
        REGEXP_EXTRACT(item_url, r'catalog/([0-9]+)') as product_id
      FROM `winged-precept-443218-v8.ngn_dataset.platform_29cm_best`
      WHERE period_type = 'WEEKLY' 
        AND best_page_name = target_tab 
        AND run_id IN (SELECT run_id FROM weeks)
      QUALIFY ROW_NUMBER() OVER (PARTITION BY run_id, item_url ORDER BY collected_at DESC) = 1
    ),
    curr_week AS (SELECT * FROM base_data WHERE week_idx = 1),
    prev_week AS (SELECT * FROM base_data WHERE week_idx = 2)
    
    SELECT 
      CONCAT(curr.best_page_name, ' ', CAST(curr.rank AS STRING), '위') AS Ranking,
      curr.brand_name AS Brand_Name,
      curr.product_name AS Product_Name,
      (prev.rank - curr.rank) AS Rank_Change,
      curr.rank AS This_Week_Rank,
      prev.rank AS Last_Week_Rank,
      curr.thumbnail_url,
      curr.price,
      curr.item_url,
      curr.run_id AS current_run_id
    FROM curr_week curr
    JOIN prev_week prev ON curr.product_id = prev.product_id
    WHERE prev.rank > curr.rank  -- 순위가 상승 (숫자가 작아짐)
    ORDER BY Rank_Change DESC
    LIMIT 20
    """
    
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("tab_name", "STRING", tab_name)
        ]
    )
    
    try:
        rows = client.query(query, job_config=job_config).result()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"[ERROR] get_rising_star 실패: {e}")
        return []


@cached_query(func_name="trend_29cm_new_entry", ttl=604800)  # 7일 캐싱
def get_new_entry(tab_name: str = "전체") -> List[Dict[str, Any]]:
    """
    신규 진입 (New Entry) 조회
    지난주에는 없었고 이번주에 새로 등장한 상품
    """
    client = get_bigquery_client()
    
    query = """
    DECLARE target_tab STRING DEFAULT @tab_name;
    
    WITH weeks AS (
      SELECT DISTINCT run_id 
      FROM `winged-precept-443218-v8.ngn_dataset.platform_29cm_best`
      WHERE period_type = 'WEEKLY' 
      ORDER BY run_id DESC 
      LIMIT 2
    ),
    base_data AS (
      SELECT *,
        DENSE_RANK() OVER (ORDER BY run_id DESC) as week_idx,
        REGEXP_EXTRACT(item_url, r'catalog/([0-9]+)') as product_id
      FROM `winged-precept-443218-v8.ngn_dataset.platform_29cm_best`
      WHERE period_type = 'WEEKLY' 
        AND best_page_name = target_tab 
        AND run_id IN (SELECT run_id FROM weeks)
      QUALIFY ROW_NUMBER() OVER (PARTITION BY run_id, item_url ORDER BY collected_at DESC) = 1
    ),
    curr_week AS (SELECT * FROM base_data WHERE week_idx = 1),
    prev_week AS (SELECT * FROM base_data WHERE week_idx = 2)
    
    SELECT 
      CONCAT(curr.best_page_name, ' ', CAST(curr.rank AS STRING), '위') AS Ranking,
      curr.brand_name AS Brand_Name,
      curr.product_name AS Product_Name,
      NULL AS Rank_Change,  -- 신규 진입이므로 변동폭 없음
      curr.rank AS This_Week_Rank,
      NULL AS Last_Week_Rank,  -- 신규 진입이므로 지난주 순위 없음
      curr.thumbnail_url,
      curr.price,
      curr.item_url,
      curr.run_id AS current_run_id
    FROM curr_week curr
    LEFT JOIN prev_week prev ON curr.product_id = prev.product_id
    WHERE prev.product_id IS NULL  -- 지난주에 없던 상품
    ORDER BY curr.rank ASC
    LIMIT 20
    """
    
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("tab_name", "STRING", tab_name)
        ]
    )
    
    try:
        rows = client.query(query, job_config=job_config).result()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"[ERROR] get_new_entry 실패: {e}")
        return []


@cached_query(func_name="trend_29cm_rank_drop", ttl=604800)  # 7일 캐싱
def get_rank_drop(tab_name: str = "전체") -> List[Dict[str, Any]]:
    """
    순위 하락 (Rank Drop) 조회
    지난주 대비 이번주 순위가 하락한 상품
    """
    client = get_bigquery_client()
    
    query = """
    DECLARE target_tab STRING DEFAULT @tab_name;
    
    WITH weeks AS (
      SELECT DISTINCT run_id 
      FROM `winged-precept-443218-v8.ngn_dataset.platform_29cm_best`
      WHERE period_type = 'WEEKLY' 
      ORDER BY run_id DESC 
      LIMIT 2
    ),
    base_data AS (
      SELECT *,
        DENSE_RANK() OVER (ORDER BY run_id DESC) as week_idx,
        REGEXP_EXTRACT(item_url, r'catalog/([0-9]+)') as product_id
      FROM `winged-precept-443218-v8.ngn_dataset.platform_29cm_best`
      WHERE period_type = 'WEEKLY' 
        AND best_page_name = target_tab 
        AND run_id IN (SELECT run_id FROM weeks)
      QUALIFY ROW_NUMBER() OVER (PARTITION BY run_id, item_url ORDER BY collected_at DESC) = 1
    ),
    curr_week AS (SELECT * FROM base_data WHERE week_idx = 1),
    prev_week AS (SELECT * FROM base_data WHERE week_idx = 2)
    
    SELECT 
      CONCAT(curr.best_page_name, ' ', CAST(curr.rank AS STRING), '위') AS Ranking,
      curr.brand_name AS Brand_Name,
      curr.product_name AS Product_Name,
      (prev.rank - curr.rank) AS Rank_Change,  -- 음수값 (순위 하락)
      curr.rank AS This_Week_Rank,
      prev.rank AS Last_Week_Rank,
      curr.thumbnail_url,
      curr.price,
      curr.item_url,
      curr.run_id AS current_run_id
    FROM curr_week curr
    JOIN prev_week prev ON curr.product_id = prev.product_id
    WHERE prev.rank < curr.rank  -- 순위가 하락 (숫자가 커짐)
    ORDER BY Rank_Change ASC  -- 가장 많이 하락한 순서
    LIMIT 20
    """
    
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("tab_name", "STRING", tab_name)
        ]
    )
    
    try:
        rows = client.query(query, job_config=job_config).result()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"[ERROR] get_rank_drop 실패: {e}")
        return []


@cached_query(func_name="trend_29cm_current_week", ttl=604800)  # 7일 캐싱
def get_current_week_info() -> Optional[str]:
    """
    현재 주차 정보 조회 (run_id 반환)
    """
    client = get_bigquery_client()
    
    query = """
    SELECT DISTINCT run_id
    FROM `winged-precept-443218-v8.ngn_dataset.platform_29cm_best`
    WHERE period_type = 'WEEKLY'
    ORDER BY run_id DESC
    LIMIT 1
    """
    
    try:
        rows = client.query(query).result()
        for row in rows:
            return row.run_id
        return None
    except Exception as e:
        print(f"[ERROR] get_current_week_info 실패: {e}")
        return None


@cached_query(func_name="trend_29cm_available_tabs", ttl=86400)  # 24시간 캐싱
def get_available_tabs() -> List[str]:
    """
    사용 가능한 탭(best_page_name) 목록 조회
    """
    client = get_bigquery_client()
    
    query = """
    SELECT DISTINCT best_page_name
    FROM `winged-precept-443218-v8.ngn_dataset.platform_29cm_best`
    WHERE period_type = 'WEEKLY'
      AND run_id IN (
        SELECT DISTINCT run_id
        FROM `winged-precept-443218-v8.ngn_dataset.platform_29cm_best`
        WHERE period_type = 'WEEKLY'
        ORDER BY run_id DESC
        LIMIT 1
      )
    ORDER BY 
      CASE 
        WHEN best_page_name = '전체' THEN 0
        ELSE 1
      END,
      best_page_name
    """
    
    try:
        rows = client.query(query).result()
        return [row.best_page_name for row in rows]
    except Exception as e:
        print(f"[ERROR] get_available_tabs 실패: {e}")
        return ["전체"]  # 기본값 반환

