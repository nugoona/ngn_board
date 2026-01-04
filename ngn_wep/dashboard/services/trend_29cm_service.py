"""
29CM 트렌드 분석 서비스
주간 베스트 상품 데이터를 분석하여 급상승, 신규 진입, 순위 하락 상품을 조회
"""
import os
import json
import gzip
import io
from datetime import datetime, timezone, timedelta
from google.cloud import bigquery
from google.cloud import storage
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


# ─────────────────────────────────────────────────────────────
# 스냅샷 관련 함수
# ─────────────────────────────────────────────────────────────

def get_trend_snapshot_path(run_id: str) -> str:
    """
    스냅샷 파일 경로 생성
    형식: ai-reports/trend/29cm/{YYYY}-{MM}-{week}/snapshot.json.gz
    """
    import re
    
    # run_id 형식: {YYYY}W{WW}_WEEKLY_...
    match = re.match(r'(\d{4})W(\d{2})', run_id)
    if not match:
        raise ValueError(f"Invalid run_id format: {run_id}")
    
    year = match.group(1)
    week = match.group(2)
    
    # ISO 주차를 사용하여 월 계산 (간단한 방법)
    # 1월 4일을 기준으로 첫 번째 주 목요일 찾기
    jan4 = datetime(int(year), 1, 4)
    jan4_day = jan4.weekday()  # 0=월요일, 6=일요일
    days_to_thursday = (3 - jan4_day + 7) % 7
    first_thursday = datetime(int(year), 1, 4 + days_to_thursday)
    
    # 주차 시작일 계산
    week_start = first_thursday + timedelta(days=-3 + (int(week) - 1) * 7)
    month = week_start.month
    
    return f"ai-reports/trend/29cm/{year}-{month:02d}-{week}/snapshot.json.gz"


def load_trend_snapshot_from_gcs(run_id: str) -> Optional[Dict[str, Any]]:
    """
    GCS 버킷에서 트렌드 스냅샷 로드
    """
    try:
        PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "winged-precept-443218-v8")
        GCS_BUCKET = os.environ.get("GCS_BUCKET", "winged-precept-443218-v8.appspot.com")
        
        # 경로 생성 (중복 코드 제거, get_trend_snapshot_path 사용)
        try:
            blob_path = get_trend_snapshot_path(run_id)
        except ValueError:
            print(f"[ERROR] Invalid run_id format: {run_id}")
            return None
        
        client = storage.Client(project=PROJECT_ID)
        bucket = client.bucket(GCS_BUCKET)
        blob = bucket.blob(blob_path)
        
        print(f"[DEBUG] 스냅샷 경로 확인: gs://{GCS_BUCKET}/{blob_path}")
        
        if not blob.exists():
            print(f"[WARN] 스냅샷 파일이 존재하지 않음: {blob_path}")
            # 디버깅: 해당 폴더의 다른 파일들 확인
            try:
                prefix = f"ai-reports/trend/29cm/{year}-{month:02d}-{week}/"
                blobs = list(bucket.list_blobs(prefix=prefix))
                if blobs:
                    print(f"[DEBUG] 해당 폴더에 있는 파일들: {[b.name for b in blobs[:5]]}")
                else:
                    print(f"[DEBUG] 해당 폴더가 비어있거나 존재하지 않음")
            except Exception as e:
                print(f"[DEBUG] 폴더 확인 중 오류: {e}")
            return None
        
        # 파일 읽기 (Gzip 압축 해제)
        snapshot_bytes = blob.download_as_bytes()
        
        try:
            with gzip.GzipFile(fileobj=io.BytesIO(snapshot_bytes)) as gz_file:
                snapshot_json_str = gz_file.read().decode('utf-8')
        except (gzip.BadGzipFile, OSError):
            snapshot_json_str = snapshot_bytes.decode('utf-8')
        
        snapshot_data = json.loads(snapshot_json_str)
        print(f"[INFO] GCS에서 트렌드 스냅샷 로드: {blob_path}")
        return snapshot_data
        
    except Exception as e:
        print(f"[ERROR] load_trend_snapshot_from_gcs 실패: {e}")
        return None


def save_trend_snapshot_to_gcs(run_id: str, tabs_data: Dict[str, Dict[str, List[Dict]]], current_week: str) -> bool:
    """
    트렌드 데이터를 GCS 버킷에 스냅샷으로 저장
    썸네일 URL만 저장 (실제 이미지는 저장하지 않음)
    """
    try:
        import re
        
        PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "winged-precept-443218-v8")
        GCS_BUCKET = os.environ.get("GCS_BUCKET", "winged-precept-443218-v8.appspot.com")
        
        # run_id에서 경로 생성
        week_match = re.match(r'(\d{4})W(\d{2})', run_id)
        if not week_match:
            print(f"[ERROR] Invalid run_id format: {run_id}")
            return False
        
        year = week_match.group(1)
        week = week_match.group(2)
        
        # ISO 주차를 사용하여 월 계산
        jan4 = datetime(int(year), 1, 4)
        jan4_day = jan4.weekday()
        days_to_thursday = (3 - jan4_day + 7) % 7
        first_thursday = datetime(int(year), 1, 4 + days_to_thursday)
        week_start = first_thursday + timedelta(days=-3 + (int(week) - 1) * 7)
        month = week_start.month
        
        blob_path = f"ai-reports/trend/29cm/{year}-{month:02d}-{week}/snapshot.json.gz"
        
        # 스냅샷 데이터 구조 (썸네일 URL은 유지)
        snapshot_data = {
            "run_id": run_id,
            "current_week": current_week,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "tabs_data": tabs_data
        }
        
        # JSON 직렬화 및 Gzip 압축
        json_str = json.dumps(snapshot_data, ensure_ascii=False, indent=2)
        json_bytes = json_str.encode('utf-8')
        compressed_bytes = gzip.compress(json_bytes)
        
        # GCS에 업로드
        client = storage.Client(project=PROJECT_ID)
        bucket = client.bucket(GCS_BUCKET)
        blob = bucket.blob(blob_path)
        blob.upload_from_string(compressed_bytes, content_type='application/gzip')
        
        print(f"[INFO] 트렌드 스냅샷 저장 완료: {blob_path}")
        return True
        
    except Exception as e:
        print(f"[ERROR] save_trend_snapshot_to_gcs 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def get_all_tabs_data_from_bigquery(tab_names: List[str]) -> Dict[str, Dict[str, List[Dict]]]:
    """
    BigQuery에서 모든 탭 데이터 조회 (스냅샷 생성용)
    """
    result = {}
    
    for tab_name in tab_names:
        result[tab_name] = {
            "rising_star": get_rising_star(tab_name),
            "new_entry": get_new_entry(tab_name),
            "rank_drop": get_rank_drop(tab_name)
        }
    
    return result

