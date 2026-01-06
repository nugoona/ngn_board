#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
29CM 경쟁사 비교 스냅샷 생성 스크립트
매주 화요일/금요일 오후 9시에 실행되어 경쟁사 검색 결과를 수집하고 스냅샷 생성
"""
import os
import sys
import json
import gzip
import re
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.cloud import bigquery
from google.cloud import storage

# 서비스 모듈 임포트
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ngn_wep'))
from dashboard.services.compare_29cm_service import (
    get_competitor_keywords,
    load_best_ranking_dict,
    collect_and_save_search_results,
)

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "winged-precept-443218-v8")
DATASET = "ngn_dataset"
GCS_BUCKET = os.environ.get("GCS_BUCKET", "winged-precept-443218-v8.appspot.com")


def get_current_week_run_id() -> str:
    """최신 주차 run_id 조회"""
    client = bigquery.Client(project=PROJECT_ID)
    
    query = f"""
    SELECT DISTINCT run_id
    FROM `{PROJECT_ID}.{DATASET}.platform_29cm_best`
    WHERE period_type = 'WEEKLY'
    ORDER BY run_id DESC
    LIMIT 1
    """
    
    rows = list(client.query(query).result())
    if not rows:
        raise RuntimeError("주차 데이터를 찾을 수 없습니다.")
    
    return rows[0].run_id


def get_all_companies() -> List[str]:
    """모든 자사몰 목록 조회"""
    client = bigquery.Client(project=PROJECT_ID)
    
    query = f"""
    SELECT DISTINCT company_name
    FROM `{PROJECT_ID}.{DATASET}.company_competitor_keywords`
    WHERE is_active = TRUE
    ORDER BY company_name
    """
    
    try:
        rows = client.query(query).result()
        return [row.company_name for row in rows]
    except Exception as e:
        print(f"[ERROR] get_all_companies 실패: {e}")
        return []


def load_search_results_from_bq(company_name: str, run_id: str) -> Dict[str, List[Dict]]:
    """BigQuery에서 검색 결과 로드"""
    client = bigquery.Client(project=PROJECT_ID)
    
    query = f"""
    SELECT 
      search_keyword,
      item_id,
      rank,
      brand_name,
      product_name,
      price,
      discount_rate,
      like_count,
      review_count,
      review_score,
      thumbnail_url,
      item_url,
      best_rank,
      best_category,
      reviews
    FROM `{PROJECT_ID}.{DATASET}.platform_29cm_search_results`
    WHERE company_name = @company_name
      AND run_id = @run_id
    ORDER BY search_keyword, rank
    """
    
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("company_name", "STRING", company_name),
            bigquery.ScalarQueryParameter("run_id", "STRING", run_id),
        ]
    )
    
    results = {}
    try:
        rows = client.query(query, job_config=job_config).result()
        for row in rows:
            keyword = row.search_keyword
            if keyword not in results:
                results[keyword] = []
            
            # JSON 파싱
            reviews = []
            if row.reviews:
                try:
                    reviews = json.loads(row.reviews) if isinstance(row.reviews, str) else row.reviews
                except:
                    reviews = []
            
            results[keyword].append({
                "item_id": row.item_id,
                "rank": row.rank,
                "brand_name": row.brand_name,
                "product_name": row.product_name,
                "price": row.price,
                "discount_rate": row.discount_rate,
                "like_count": row.like_count,
                "review_count": row.review_count,
                "review_score": row.review_score,
                "thumbnail_url": row.thumbnail_url,
                "item_url": row.item_url,
                "best_rank": row.best_rank,
                "best_category": row.best_category,
                "reviews": reviews,
            })
    except Exception as e:
        print(f"[ERROR] load_search_results_from_bq 실패: {e}")
    
    return results


def save_snapshot_to_gcs(run_id: str, snapshot_data: Dict[str, Any]) -> bool:
    """스냅샷을 GCS에 저장"""
    try:
        # run_id에서 날짜 추출
        # 형식: {year}W{week:02d}_WEEKLY_...
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
        
        # GCS 경로
        blob_path = f"ai-reports/compare/29cm/{year}-{month:02d}-{week}/search_results.json.gz"
        
        # JSON 직렬화 및 Gzip 압축
        json_str = json.dumps(snapshot_data, ensure_ascii=False, indent=2)
        json_bytes = json_str.encode('utf-8')
        compressed_bytes = gzip.compress(json_bytes)
        
        # GCS에 업로드
        client = storage.Client(project=PROJECT_ID)
        bucket = client.bucket(GCS_BUCKET)
        blob = bucket.blob(blob_path)
        blob.upload_from_string(compressed_bytes, content_type='application/gzip')
        
        print(f"[INFO] 스냅샷 저장 완료: {blob_path}")
        return True
        
    except Exception as e:
        print(f"[ERROR] save_snapshot_to_gcs 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """메인 실행 함수"""
    try:
        # 1. 최신 주차 run_id 조회
        run_id = get_current_week_run_id()
        print(f"[INFO] 최신 주차 사용: {run_id}")
        
        # 2. 베스트 목록 로드
        print(f"[INFO] 베스트 목록 로드 중...")
        best_dict = load_best_ranking_dict(run_id)
        print(f"[INFO] 베스트 목록 {len(best_dict)}개 로드 완료")
        
        # 3. 모든 자사몰 조회
        companies = get_all_companies()
        print(f"[INFO] 자사몰 {len(companies)}개 발견")
        
        # 4. 각 자사몰별로 경쟁사 검색 결과 수집
        all_results = {}
        
        for company_name in companies:
            print(f"\n[INFO] === {company_name} 처리 시작 ===")
            
            # 경쟁사 검색어 조회
            competitor_keywords = get_competitor_keywords(company_name)
            if not competitor_keywords:
                print(f"[WARN] {company_name}의 경쟁사 검색어 없음")
                continue
            
            print(f"[INFO] 경쟁사 {len(competitor_keywords)}개 발견")
            
            company_results = {}
            
            for comp_info in competitor_keywords:
                keyword = comp_info["competitor_keyword"]
                display_name = comp_info.get("display_name", keyword)
                
                # 검색 결과 수집 및 저장
                success = collect_and_save_search_results(
                    company_name=company_name,
                    search_keyword=keyword,
                    run_id=run_id,
                    best_dict=best_dict
                )
                
                if success:
                    # BigQuery에서 로드하여 스냅샷 데이터에 추가
                    keyword_results = load_search_results_from_bq(company_name, run_id)
                    if keyword in keyword_results:
                        company_results[display_name] = keyword_results[keyword]
            
            if company_results:
                all_results[company_name] = company_results
        
        # 5. 스냅샷 생성
        if all_results:
            snapshot_data = {
                "run_id": run_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "search_results": all_results
            }
            
            success = save_snapshot_to_gcs(run_id, snapshot_data)
            if success:
                print(f"\n[INFO] ✅ 스냅샷 생성 완료")
            else:
                print(f"\n[ERROR] ❌ 스냅샷 생성 실패")
        else:
            print(f"\n[WARN] 수집된 데이터 없음")
        
    except Exception as e:
        print(f"[ERROR] 메인 실행 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

