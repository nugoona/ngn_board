#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
29CM 트렌드 스냅샷 생성 스크립트
로컬 또는 Cloud Shell에서 수동 실행

사용법:
    python3 tools/trend_29cm_snapshot.py [--run-id RUN_ID] [--force]
    
옵션:
    --run-id RUN_ID    특정 run_id로 스냅샷 생성 (기본값: 최신 주차)
    --force            기존 스냅샷이 있어도 재생성
"""

import os
import sys
import re
from datetime import datetime, timezone, timedelta

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.cloud import bigquery
from google.cloud import storage
import json
import gzip
import io

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "winged-precept-443218-v8")
DATASET = "ngn_dataset"
GCS_BUCKET = os.environ.get("GCS_BUCKET", "winged-precept-443218-v8.appspot.com")


def get_current_week_run_id() -> str:
    """최신 주차 run_id 조회"""
    client = bigquery.Client(project=PROJECT_ID)
    
    query = """
    SELECT DISTINCT run_id
    FROM `{}.{}.platform_29cm_best`
    WHERE period_type = 'WEEKLY'
    ORDER BY run_id DESC
    LIMIT 1
    """.format(PROJECT_ID, DATASET)
    
    rows = list(client.query(query).result())
    if not rows:
        raise RuntimeError("주차 데이터를 찾을 수 없습니다.")
    
    return rows[0].run_id


def get_available_tabs(run_id: str) -> list:
    """사용 가능한 탭 목록 조회"""
    client = bigquery.Client(project=PROJECT_ID)
    
    query = """
    SELECT DISTINCT best_page_name
    FROM `{}.{}.platform_29cm_best`
    WHERE period_type = 'WEEKLY'
      AND run_id = @run_id
    ORDER BY 
      CASE 
        WHEN best_page_name = '전체' THEN 0
        ELSE 1
      END,
      best_page_name
    """.format(PROJECT_ID, DATASET)
    
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("run_id", "STRING", run_id)
        ]
    )
    
    rows = list(client.query(query, job_config=job_config).result())
    return [row.best_page_name for row in rows]


def get_rising_star(tab_name: str, run_id: str) -> list:
    """급상승 랭킹 조회"""
    client = bigquery.Client(project=PROJECT_ID)
    
    query = """
    DECLARE target_tab STRING DEFAULT @tab_name;
    DECLARE target_run_id STRING DEFAULT @run_id;
    
    WITH all_weeks AS (
      SELECT DISTINCT run_id 
      FROM `{}.{}.platform_29cm_best`
      WHERE period_type = 'WEEKLY'
      ORDER BY run_id DESC
    ),
    target_week_idx AS (
      SELECT 
        run_id,
        ROW_NUMBER() OVER (ORDER BY run_id DESC) as week_idx
      FROM all_weeks
    ),
    target_week_info AS (
      SELECT week_idx
      FROM target_week_idx
      WHERE run_id = target_run_id
    ),
    weeks AS (
      SELECT t1.run_id
      FROM target_week_idx t1
      CROSS JOIN target_week_info t2
      WHERE t1.week_idx IN (t2.week_idx, t2.week_idx + 1)
      ORDER BY t1.run_id DESC
      LIMIT 2
    ),
    base_data AS (
      SELECT *,
        DENSE_RANK() OVER (ORDER BY run_id DESC) as week_idx,
        REGEXP_EXTRACT(item_url, r'catalog/([0-9]+)') as product_id
      FROM `{}.{}.platform_29cm_best`
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
    WHERE prev.rank > curr.rank
    ORDER BY Rank_Change DESC
    LIMIT 20
    """.format(PROJECT_ID, DATASET, PROJECT_ID, DATASET, PROJECT_ID, DATASET)
    
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("tab_name", "STRING", tab_name),
            bigquery.ScalarQueryParameter("run_id", "STRING", run_id)
        ]
    )
    
    rows = client.query(query, job_config=job_config).result()
    return [dict(row) for row in rows]


def get_new_entry(tab_name: str, run_id: str) -> list:
    """신규 진입 조회"""
    client = bigquery.Client(project=PROJECT_ID)
    
    query = """
    DECLARE target_tab STRING DEFAULT @tab_name;
    DECLARE target_run_id STRING DEFAULT @run_id;
    
    WITH all_weeks AS (
      SELECT DISTINCT run_id 
      FROM `{}.{}.platform_29cm_best`
      WHERE period_type = 'WEEKLY'
      ORDER BY run_id DESC
    ),
    target_week_idx AS (
      SELECT 
        run_id,
        ROW_NUMBER() OVER (ORDER BY run_id DESC) as week_idx
      FROM all_weeks
    ),
    target_week_info AS (
      SELECT week_idx
      FROM target_week_idx
      WHERE run_id = target_run_id
    ),
    weeks AS (
      SELECT t1.run_id
      FROM target_week_idx t1
      CROSS JOIN target_week_info t2
      WHERE t1.week_idx IN (t2.week_idx, t2.week_idx + 1)
      ORDER BY t1.run_id DESC
      LIMIT 2
    ),
    base_data AS (
      SELECT *,
        DENSE_RANK() OVER (ORDER BY run_id DESC) as week_idx,
        REGEXP_EXTRACT(item_url, r'catalog/([0-9]+)') as product_id
      FROM `{}.{}.platform_29cm_best`
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
      NULL AS Rank_Change,
      curr.rank AS This_Week_Rank,
      NULL AS Last_Week_Rank,
      curr.thumbnail_url,
      curr.price,
      curr.item_url,
      curr.run_id AS current_run_id
    FROM curr_week curr
    LEFT JOIN prev_week prev ON curr.product_id = prev.product_id
    WHERE prev.product_id IS NULL
    ORDER BY curr.rank ASC
    LIMIT 20
    """.format(PROJECT_ID, DATASET, PROJECT_ID, DATASET, PROJECT_ID, DATASET)
    
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("tab_name", "STRING", tab_name),
            bigquery.ScalarQueryParameter("run_id", "STRING", run_id)
        ]
    )
    
    rows = client.query(query, job_config=job_config).result()
    return [dict(row) for row in rows]


def get_rank_drop(tab_name: str, run_id: str) -> list:
    """순위 하락 조회"""
    client = bigquery.Client(project=PROJECT_ID)
    
    query = """
    DECLARE target_tab STRING DEFAULT @tab_name;
    DECLARE target_run_id STRING DEFAULT @run_id;
    
    WITH all_weeks AS (
      SELECT DISTINCT run_id 
      FROM `{}.{}.platform_29cm_best`
      WHERE period_type = 'WEEKLY'
      ORDER BY run_id DESC
    ),
    target_week_idx AS (
      SELECT 
        run_id,
        ROW_NUMBER() OVER (ORDER BY run_id DESC) as week_idx
      FROM all_weeks
    ),
    target_week_info AS (
      SELECT week_idx
      FROM target_week_idx
      WHERE run_id = target_run_id
    ),
    weeks AS (
      SELECT t1.run_id
      FROM target_week_idx t1
      CROSS JOIN target_week_info t2
      WHERE t1.week_idx IN (t2.week_idx, t2.week_idx + 1)
      ORDER BY t1.run_id DESC
      LIMIT 2
    ),
    base_data AS (
      SELECT *,
        DENSE_RANK() OVER (ORDER BY run_id DESC) as week_idx,
        REGEXP_EXTRACT(item_url, r'catalog/([0-9]+)') as product_id
      FROM `{}.{}.platform_29cm_best`
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
    WHERE prev.rank < curr.rank
    ORDER BY Rank_Change ASC
    LIMIT 20
    """.format(PROJECT_ID, DATASET, PROJECT_ID, DATASET, PROJECT_ID, DATASET)
    
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("tab_name", "STRING", tab_name),
            bigquery.ScalarQueryParameter("run_id", "STRING", run_id)
        ]
    )
    
    rows = client.query(query, job_config=job_config).result()
    return [dict(row) for row in rows]


def get_snapshot_path(run_id: str) -> str:
    """스냅샷 파일 경로 생성"""
    match = re.match(r'(\d{4})W(\d{2})', run_id)
    if not match:
        raise ValueError(f"Invalid run_id format: {run_id}")
    
    year = match.group(1)  # 문자열로 유지
    week = match.group(2)  # 문자열로 유지 (이미 2자리)
    
    # ISO 주차를 사용하여 월 계산
    jan4 = datetime(int(year), 1, 4)
    jan4_day = jan4.weekday()
    days_to_thursday = (3 - jan4_day + 7) % 7
    first_thursday = datetime(int(year), 1, 4 + days_to_thursday)
    week_start = first_thursday + timedelta(days=-3 + (int(week) - 1) * 7)
    month = week_start.month
    
    return f"ai-reports/trend/29cm/{year}-{month:02d}-{week}/snapshot.json.gz"


def save_snapshot_to_gcs(run_id: str, tabs_data: dict) -> bool:
    """스냅샷을 GCS에 저장"""
    try:
        blob_path = get_snapshot_path(run_id)
        
        snapshot_data = {
            "run_id": run_id,
            "current_week": run_id,
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
        
        print(f"✅ 스냅샷 저장 완료: gs://{GCS_BUCKET}/{blob_path}")
        return True
        
    except Exception as e:
        print(f"❌ 스냅샷 저장 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_snapshot_exists(run_id: str) -> bool:
    """스냅샷 존재 여부 확인"""
    try:
        blob_path = get_snapshot_path(run_id)
        client = storage.Client(project=PROJECT_ID)
        bucket = client.bucket(GCS_BUCKET)
        blob = bucket.blob(blob_path)
        return blob.exists()
    except Exception as e:
        print(f"⚠️ 스냅샷 확인 실패: {e}")
        return False


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='29CM 트렌드 스냅샷 생성')
    parser.add_argument('--run-id', type=str, help='특정 run_id로 스냅샷 생성 (기본값: 최신 주차)')
    parser.add_argument('--force', action='store_true', help='기존 스냅샷이 있어도 재생성')
    
    args = parser.parse_args()
    
    # run_id 결정
    if args.run_id:
        run_id = args.run_id
        print(f"📅 지정된 run_id 사용: {run_id}")
    else:
        run_id = get_current_week_run_id()
        print(f"📅 최신 주차 사용: {run_id}")
    
    # 기존 스냅샷 확인
    if not args.force and check_snapshot_exists(run_id):
        print(f"⚠️ 스냅샷이 이미 존재합니다: {run_id}")
        print("   재생성하려면 --force 옵션을 사용하세요.")
        sys.exit(1)
    
    # 탭 목록 조회
    print(f"📂 탭 목록 조회 중...")
    tabs = get_available_tabs(run_id)
    print(f"   찾은 탭: {', '.join(tabs)}")
    
    # 각 탭별 데이터 조회
    print(f"\n📊 데이터 조회 중...")
    tabs_data = {}
    
    for tab in tabs:
        print(f"   [{tab}] 조회 중...")
        tabs_data[tab] = {
            "rising_star": get_rising_star(tab, run_id),
            "new_entry": get_new_entry(tab, run_id),
            "rank_drop": get_rank_drop(tab, run_id)
        }
        print(f"      - 급상승: {len(tabs_data[tab]['rising_star'])}개")
        print(f"      - 신규진입: {len(tabs_data[tab]['new_entry'])}개")
        print(f"      - 순위하락: {len(tabs_data[tab]['rank_drop'])}개")
    
    # 스냅샷 저장
    print(f"\n💾 스냅샷 저장 중...")
    success = save_snapshot_to_gcs(run_id, tabs_data)
    
    if not success:
        print(f"\n❌ 스냅샷 생성 실패")
        sys.exit(1)
    
    snapshot_path = f"gs://{GCS_BUCKET}/{get_snapshot_path(run_id)}"
    print(f"\n✅ 스냅샷 생성 완료!")
    print(f"   Run ID: {run_id}")
    print(f"   탭 개수: {len(tabs)}")
    print(f"   경로: {snapshot_path}")
    
    # AI 분석 자동 추가 (월간 리포트 방식)
    print(f"\n🤖 AI 분석 리포트 생성 중...")
    try:
        # 프로젝트 루트를 Python 경로에 추가
        # tools/trend_29cm_snapshot.py -> tools/ -> 프로젝트 루트 (ngn_board)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)  # tools/ -> 프로젝트 루트
        tools_path = os.path.join(project_root, 'tools', 'ai_report_test')
        if tools_path not in sys.path:
            sys.path.insert(0, tools_path)
        
        print(f"[DEBUG] 프로젝트 루트: {project_root}", file=sys.stderr)
        print(f"[DEBUG] tools 경로: {tools_path}", file=sys.stderr)
        
        from trend_29cm_ai_analyst import generate_ai_analysis_from_file
        
        # GCS 스냅샷에 AI 분석 추가 (같은 파일에 덮어쓰기)
        generate_ai_analysis_from_file(
            snapshot_file=snapshot_path,
            output_file=None,  # 입력 파일에 덮어쓰기
            api_key=None  # 환경변수에서 로드 (.env 파일 자동 찾기)
        )
        
        print(f"✅ AI 분석 리포트 추가 완료!")
    except Exception as e:
        print(f"⚠️ AI 분석 리포트 생성 실패 (스냅샷은 정상 저장됨): {e}")
        import traceback
        traceback.print_exc()
        # AI 분석 실패해도 스냅샷은 정상적으로 저장되었으므로 계속 진행


if __name__ == "__main__":
    main()

