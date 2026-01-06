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
    load_search_results_from_gcs,
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




def save_snapshot_to_gcs(run_id: str, snapshot_data: Dict[str, Any]) -> bool:
    """
    스냅샷을 GCS에 저장
    company_name별로 별도 파일로 저장 (compare_29cm_service의 save_search_results_to_gcs와 동일한 경로 사용)
    """
    try:
        from dashboard.services.compare_29cm_service import get_compare_snapshot_path
        
        # company_name 추출
        company_name = snapshot_data.get("company_name")
        
        # 스냅샷 경로 생성 (company_name 포함)
        blob_path = get_compare_snapshot_path(run_id, company_name)
        
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
        
        # 4. 각 자사몰별로 검색 결과 수집 (자사몰 + 경쟁사)
        all_results = {}
        
        # company_mapping 임포트
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tools'))
            from config.company_mapping import get_company_brands, get_company_korean_name
            COMPANY_MAPPING_AVAILABLE = True
        except:
            COMPANY_MAPPING_AVAILABLE = False
            def get_company_brands(name): return []
            def get_company_korean_name(name): return None
        
        for company_name in companies:
            print(f"\n[INFO] === {company_name} 처리 시작 ===")
            
            company_results = {}
            
            # 1. 자사몰 검색어 수집 (company_mapping에서 브랜드명 가져오기)
            if COMPANY_MAPPING_AVAILABLE:
                brands = get_company_brands(company_name)
                if brands:
                    own_brand = brands[0]  # 첫 번째 브랜드명 사용
                    print(f"[INFO] 자사몰 검색어: {own_brand}")
                    
                    success = collect_and_save_search_results(
                        company_name=company_name,
                        search_keyword=own_brand,
                        run_id=run_id,
                        best_dict=best_dict
                    )
                    
                    if success:
                        # GCS 스냅샷에서 로드
                        keyword_results = load_search_results_from_gcs(company_name, run_id)
                        if keyword_results and own_brand in keyword_results:
                            # 자사몰 탭 표시명 결정
                            korean_name = get_company_korean_name(company_name)
                            display_name = korean_name or company_name
                            company_results[display_name] = keyword_results[own_brand]
            
            # 2. 경쟁사 검색어 조회 및 수집
            competitor_keywords = get_competitor_keywords(company_name)
            if not competitor_keywords:
                print(f"[WARN] {company_name}의 경쟁사 검색어 없음")
            else:
                print(f"[INFO] 경쟁사 {len(competitor_keywords)}개 발견")
                
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
                        # GCS 스냅샷에서 로드
                        keyword_results = load_search_results_from_gcs(company_name, run_id)
                        if keyword_results and keyword in keyword_results:
                            company_results[display_name] = keyword_results[keyword]
            
            if company_results:
                all_results[company_name] = company_results
        
        # 5. 완료 메시지
        # 주의: 각 검색어별로 collect_and_save_search_results가 호출될 때마다
        # save_search_results_to_gcs가 스냅샷을 업데이트하므로, 여기서는 별도 저장 불필요
        if all_results:
            print(f"\n[INFO] ✅ 전체 수집 완료 ({len(all_results)}개 자사몰)")
            for company_name, results in all_results.items():
                print(f"  - {company_name}: {len(results)}개 검색어")
        else:
            print(f"\n[WARN] 수집된 데이터 없음")
        
    except Exception as e:
        print(f"[ERROR] 메인 실행 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

