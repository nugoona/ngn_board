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
# Docker 환경에서는 /app이 루트이므로 PYTHONPATH로 설정됨
# 로컬 환경에서는 프로젝트 루트를 경로에 추가
if not os.environ.get('PYTHONPATH'):
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)
    ngn_wep_path = os.path.join(project_root, 'ngn_wep')
    if os.path.exists(ngn_wep_path):
        sys.path.insert(0, ngn_wep_path)

from google.cloud import bigquery
from google.cloud import storage

# 서비스 모듈 임포트
from dashboard.services.compare_29cm_service import (
    get_competitor_brands,
    get_own_brand_id,
    load_best_ranking_dict,
    collect_and_save_brand_results,
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
    """모든 자사몰 목록 조회 (brandId 기반 테이블에서)"""
    client = bigquery.Client(project=PROJECT_ID)

    query = f"""
    SELECT DISTINCT company_name
    FROM `{PROJECT_ID}.{DATASET}.company_competitor_brands`
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
    """메인 실행 함수 (brandId 기반)"""
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

        # 4. 각 자사몰별로 브랜드 데이터 수집 (자사몰 + 경쟁사)
        all_results = {}

        for company_name in companies:
            print(f"\n[INFO] === {company_name} 처리 시작 ===")

            collected_brands = []

            # 1. 자사몰 브랜드 ID 조회 및 수집
            own_brand_id = get_own_brand_id(company_name)
            if own_brand_id:
                print(f"[INFO] 자사몰 브랜드 ID: {own_brand_id}")

                brand_name = collect_and_save_brand_results(
                    company_name=company_name,
                    brand_id=own_brand_id,
                    run_id=run_id,
                    best_dict=best_dict,
                    is_own_mall=True
                )

                if brand_name:
                    collected_brands.append({
                        "brand_id": own_brand_id,
                        "brand_name": brand_name,
                        "is_own_mall": True
                    })
            else:
                print(f"[WARN] {company_name}의 자사몰 브랜드 ID 없음")

            # 2. 경쟁사 브랜드 조회 및 수집
            competitor_brands = get_competitor_brands(company_name)
            if not competitor_brands:
                print(f"[WARN] {company_name}의 경쟁사 브랜드 없음")
            else:
                print(f"[INFO] 경쟁사 브랜드 {len(competitor_brands)}개 발견")

                for brand_info in competitor_brands:
                    brand_id = brand_info["brand_id"]
                    display_name = brand_info.get("display_name") or brand_info.get("brand_name")

                    print(f"[INFO] 경쟁사 수집: brand_id={brand_id}")

                    # 브랜드 ID로 상품 수집 및 저장
                    brand_name = collect_and_save_brand_results(
                        company_name=company_name,
                        brand_id=brand_id,
                        run_id=run_id,
                        best_dict=best_dict,
                        is_own_mall=False
                    )

                    if brand_name:
                        collected_brands.append({
                            "brand_id": brand_id,
                            "brand_name": brand_name,
                            "is_own_mall": False
                        })

            if collected_brands:
                all_results[company_name] = collected_brands

        # 5. 완료 메시지
        if all_results:
            print(f"\n[INFO] ✅ 전체 수집 완료 ({len(all_results)}개 자사몰)")
            for company_name, brands in all_results.items():
                own_count = sum(1 for b in brands if b["is_own_mall"])
                comp_count = len(brands) - own_count
                print(f"  - {company_name}: 자사몰 {own_count}개, 경쟁사 {comp_count}개")
        else:
            print(f"\n[WARN] 수집된 데이터 없음")

    except Exception as e:
        print(f"[ERROR] 메인 실행 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

