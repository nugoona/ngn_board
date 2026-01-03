#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import json
import random
import csv
import re
import requests
from datetime import datetime, timezone, timedelta
from google.cloud import bigquery
from google.cloud import storage
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# =============================================================================
# 1. 설정값 (환경변수 또는 기본값)
# =============================================================================
PROJECT_ID = os.environ.get("GCP_PROJECT", "winged-precept-443218-v8")
DATASET_ID = os.environ.get("BQ_DATASET", "ngn_dataset")
TABLE_ID = os.environ.get("BQ_TABLE", "platform_ably_best")
GCS_BUCKET = os.environ.get("GCS_BUCKET", "ngn-homepage-static")
GCS_PREFIX = os.environ.get("GCS_PREFIX", "ably_best")

# KST 시간대 설정
KST = timezone(timedelta(hours=9))

# =============================================================================
# 2. 유틸리티 함수
# =============================================================================
def clean_product_name(name):
    """
    상품명 정제 로직:
    1. 앞부분의 [ ... ] 패턴 제거
    2. 앞부분의 특수문자(🤍, 🚀 등) 제거
    3. 괄호(...) 안의 내용 제거 (옵션)
    4. 길이 제한 (너무 길면 자름)
    """
    if not name:
        return ""
    
    # 1. 대괄호 [ ... ] 및 그 앞의 특수문자 제거
    # 예: "🤍[유사품주의] 상품명" -> " 상품명"
    # 예: "[MD추천] 상품명" -> " 상품명"
    name = re.sub(r'^[\W_]*(\[.*?\]\s*)+', '', name)
    
    # 2. ( ... ) 괄호 내용 제거 (선택사항, 필요 없으면 주석 처리)
    # 예: "자켓(빅사이즈...)" -> "자켓"
    name = re.sub(r'\(.*?\)', '', name)
    
    # 3. 앞뒤 공백 제거
    name = name.strip()
    
    # 4. 그래도 남아있는 앞쪽 특수문자 제거
    name = re.sub(r'^[\W_]+', '', name)
    
    # 5. 길이 제한 (예: 50자)
    if len(name) > 50:
        name = name[:50] + "..."
        
    return name

def bq_table_fqn():
    return f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"

def bq_run_already_loaded(bq, run_id):
    """
    BigQuery에 이미 같은 run_id가 있는지 확인 (중복 적재 방지)
    """
    sql = f"""
    SELECT 1
    FROM `{bq_table_fqn()}`
    WHERE run_id = @run_id
    LIMIT 1
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("run_id", "STRING", run_id)]
    )
    job = bq.query(sql, job_config=job_config)
    return len(list(job.result())) > 0

def upload_to_gcs(local_path, bucket_name, blob_path):
    client = storage.Client(project=PROJECT_ID)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)
    blob.upload_from_filename(local_path)
    return f"gs://{bucket_name}/{blob_path}"

def bq_insert_rows(bq, rows):
    table_ref = bq.dataset(DATASET_ID).table(TABLE_ID)
    errors = bq.insert_rows_json(table_ref, rows)
    if errors:
        raise RuntimeError(f"BigQuery insert errors: {errors}")

# =============================================================================
# 3. [보안 우회] 브라우저 네트워크 감청으로 '진짜 토큰' 획득
# =============================================================================
def get_real_token_from_browser():
    print("🕵️‍♂️ [1단계] 보안 우회를 위해 브라우저(Headless)를 실행합니다...")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

    driver = None
    try:
        driver = webdriver.Chrome(options=chrome_options)
    except Exception as e:
        print(f"❌ 크롬 드라이버 초기화 실패: {e}")
        return None
    
    target_token = None
    try:
        target_url = "https://m.a-bly.com/screens?screen_name=CATEGORY_DEPARTMENT&next_token=eyJsIjogIkRlcGFydG1lbnRDYXRlZ29yeVJlYWx0aW1lUmFua0dlbmVyYXRvciIsICJwIjogeyJkZXBhcnRtZW50X3R5cGUiOiAiQ0FURUdPUlkiLCAiY2F0ZWdvcnlfc25vIjogMTc0fSwgImQiOiAiQ0FURUdPUlkiLCAicHJldmlvdXNfc2NyZWVuX25hbWUiOiAiQ0xPVEhJTkdfQ0FURUdPUllfREVQQVJUTUVOVCIsICJjYXRlZ29yeV9zbm8iOiAxNzR9&category_sno=&category_list%5B%5D=174&sorting_type=POPULAR"
        
        print("   -> 에이블리 접속 및 통신 대기 중...")
        driver.get(target_url)
        time.sleep(5) 

        print("   -> 네트워크 패킷에서 토큰 추출 중...")
        logs = driver.get_log('performance')
        
        for entry in logs:
            try:
                log_json = json.loads(entry['message'])
                message = log_json.get('message', {})
                if message.get('method') == 'Network.requestWillBeSent':
                    headers = message.get('params', {}).get('request', {}).get('headers', {})
                    token = headers.get('x-anonymous-token') or headers.get('X-Anonymous-Token')
                    if token:
                        target_token = token
                        print(f"✅ [성공] 인증 토큰 확보 완료!")
                        break
            except: continue
            if target_token: break
    except Exception as e:
        print(f"⚠️ 브라우저 에러: {e}")
    finally:
        if driver: driver.quit()
    return target_token

# =============================================================================
# 4. [데이터 파싱]
# =============================================================================
def parse_two_col_list(json_data, category_name, collected_at, run_id, period_type):
    items = []
    components = json_data.get('components', [])
    for comp in components:
        if comp.get('type', {}).get('item_list') == "TWO_COL_CARD_LIST":
            item_list = comp.get('entity', {}).get('item_list', [])
            for wrapper in item_list:
                item_entity = wrapper.get('item_entity', {})
                basic_info = item_entity.get('item', {})
                analytics = item_entity.get('logging', {}).get('analytics', {})
                render_data = item_entity.get('render', {}).get('data', {})

                if 'sno' in basic_info:
                    # 구매현황 숫자 추출
                    raw_nudge = render_data.get('nudging_text', '')
                    nudge_num = re.sub(r'[^0-9]', '', str(raw_nudge))
                    sales_count = int(nudge_num) if nudge_num else 0

                    # 상품명 정제
                    raw_name = basic_info.get('name', '')
                    clean_name = clean_product_name(raw_name)

                    items.append({
                        "platform": "ably",
                        # rank는 수집 순서대로 나중에 부여
                        "brand_name": basic_info.get('market_name'),
                        "product_name": clean_name,
                        "category_medium": category_name,
                        "price": basic_info.get('price'),
                        "discount_rate": basic_info.get('discount_rate', 0),
                        "like_count": analytics.get('LIKES_COUNT', 0),
                        "sales_count": sales_count,
                        "item_url": f"https://m.a-bly.com/goods/{basic_info.get('sno')}",
                        "thumbnail_url": basic_info.get('image'),
                        "collected_at": collected_at,
                        "run_id": run_id,
                        "period_type": period_type
                    })
    return items

# =============================================================================
# 5. [메인 로직]
# =============================================================================
def main():
    # 1. 실행 ID 생성 (주간 기준)
    now = datetime.now(KST)
    iso = now.isocalendar()
    period_type = "WEEKLY"
    run_id = f"{iso.year}W{iso.week:02d}_WEEKLY_POPULARITY"
    collected_at = now.strftime("%Y-%m-%d %H:%M:%S")

    print(f"[INFO] run_id: {run_id}")
    print(f"[INFO] collected_at: {collected_at}")

    # 2. BigQuery 중복 체크
    bq = bigquery.Client(project=PROJECT_ID)
    if bq_run_already_loaded(bq, run_id):
        print(f"⏭️ [SKIP] 이미 적재된 run_id 입니다: {run_id}")
        return

    # 3. 토큰 획득
    auth_token = get_real_token_from_browser()
    if not auth_token:
        print("❌ 토큰을 찾지 못해 종료합니다.")
        return

    # 4. 데이터 수집
    categories = [
        {"name": "팬츠", "id": "174", "sort_param": "eyJsIjogIkRlcGFydG1lbnRDYXRlZ29yeVJlYWx0aW1lUmFua0dlbmVyYXRvciIsICJwIjogeyJkZXBhcnRtZW50X3R5cGUiOiAiQ0FURUdPUlkiLCAiY2F0ZWdvcnlfc25vIjogMTc0fSwgImQiOiAiQ0FURUdPUlkiLCAicHJldmlvdXNfc2NyZWVuX25hbWUiOiAiQ0xPVEhJTkdfQ0FURUdPUllfREVQQVJUTUVOVCIsICJjYXRlZ29yeV9zbm8iOiAxNzR9"},
        {"name": "원피스/세트", "id": "10", "sort_param": "eyJsIjogIkRlcGFydG1lbnRDYXRlZ29yeVJlYWx0aW1lUmFua0dlbmVyYXRvciIsICJwIjogeyJkZXBhcnRtZW50X3R5cGUiOiAiQ0FURUdPUlkiLCAiY2F0ZWdvcnlfc25vIjogMTB9LCAiZCI6ICJDQVRFR09SWSIsICJwcmV2aW91c19zY3JlZW5fbmFtZSI6ICJDTE9USElOR19DQVRFR09SWV9ERVBBUlRNRU5UIiwgImNhdGVnb3J5X3NubyI6IDEwfQ=="},
        {"name": "스커트", "id": "203", "sort_param": "eyJsIjogIkRlcGFydG1lbnRDYXRlZ29yeVJlYWx0aW1lUmFua0dlbmVyYXRvciIsICJwIjogeyJkZXBhcnRtZW50X3R5cGUiOiAiQ0FURUdPUlkiLCAiY2F0ZWdvcnlfc25vIjogMjAzfSwgImQiOiAiQ0FURUdPUlkiLCAicHJldmlvdXNfc2NyZWVuX25hbWUiOiAiQ0xPVEhJTkdfQ0FURUdPUllfREVQQVJUTUVOVCIsICJjYXRlZ29yeV9zbm8iOiAyMDN9"},
        {"name": "상의", "id": "8", "sort_param": "eyJsIjogIkRlcGFydG1lbnRDYXRlZ29yeVJlYWx0aW1lUmFua0dlbmVyYXRvciIsICJwIjogeyJkZXBhcnRtZW50X3R5cGUiOiAiQ0FURUdPUlkiLCAiY2F0ZWdvcnlfc25vIjogOH0sICJkIjogIkNBVEVHT1JZIiwgInByZXZpb3VzX3NjcmVlbl9uYW1lIjogIkNMT1RISU5HX0NBVEVHT1JZX0RFUEFSVE1FTlQiLCAiY2F0ZWdvcnlfc25vIjogOH0="},
        {"name": "트레이닝", "id": "517", "sort_param": "eyJsIjogIkRlcGFydG1lbnRDYXRlZ29yeVJlYWx0aW1lUmFua0dlbmVyYXRvciIsICJwIjogeyJkZXBhcnRtZW50X3R5cGUiOiAiQ0FURUdPUlkiLCAiY2F0ZWdvcnlfc25vIjogNTE3fSwgImQiOiAiQ0FURUdPUlkiLCAicHJldmlvdXNfc2NyZWVuX25hbWUiOiAiQ0xPVEhJTkdfQ0FURUdPUllfREVQQVJUTUVOVCIsICJjYXRlZ29yeV9zbm8iOiA1MTd9"},
        {"name": "비치웨어", "id": "467", "sort_param": "eyJsIjogIkRlcGFydG1lbnRDYXRlZ29yeVJlYWx0aW1lUmFua0dlbmVyYXRvciIsICJwIjogeyJkZXBhcnRtZW50X3R5cGUiOiAiQ0FURUdPUlkiLCAiY2F0ZWdvcnlfc25vIjogNDY3fSwgImQiOiAiQ0FURUdPUlkiLCAicHJldmlvdXNfc2NyZWVuX25hbWUiOiAiQ0xPVEhJTkdfQ0FURUdPUllfREVQQVJUTUVOVCIsICJjYXRlZ29yeV9zbm8iOiA0Njd9"},
        {"name": "아우터", "id": "7", "sort_param": "eyJsIjogIkRlcGFydG1lbnRDYXRlZ29yeVJlYWx0aW1lUmFua0dlbmVyYXRvciIsICJwIjogeyJkZXBhcnRtZW50X3R5cGUiOiAiQ0FURUdPUlkiLCAiY2F0ZWdvcnlfc25vIjogN30sICJkIjogIkNBVEVHT1JZIiwgInByZXZpb3VzX3NjcmVlbl9uYW1lIjogIkNMT1RISU5HX0NBVEVHT1JZX0RFUEFSVE1FTlQiLCAiY2F0ZWdvcnlfc25vIjogN30="},
    ]

    headers = {
        'accept': 'application/json, text/plain, */*',
        'x-anonymous-token': auth_token,
        'x-device-type': 'PCWeb',
        'x-web-type': 'Web',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
        'referer': 'https://m.a-bly.com/',
        'origin': 'https://m.a-bly.com'
    }

    all_results = []
    
    print("\n🚀 [2단계] 고속 데이터 수집 시작...")

    for cat in categories:
        print(f"\n📂 [{cat['name']}] 카테고리 수집 중...")
        cat_items = []
        params = {'next_token': cat['sort_param'], 'category_list[]': cat['id'], 'sorting_type': 'POPULAR'}

        while len(cat_items) < 100:
            try:
                url = 'https://api.a-bly.com/api/v2/screens/CATEGORY_DEPARTMENT/'
                response = requests.get(url, params=params, headers=headers, timeout=10)
                if response.status_code != 200:
                    print(f"   ❌ 요청 실패 (Code: {response.status_code})")
                    break
                data = response.json()
                new_items = parse_two_col_list(data, cat['name'], collected_at, run_id, period_type)
                
                for item in new_items:
                    if len(cat_items) < 100:
                        item['rank'] = len(cat_items) + 1 # 순위 부여
                        cat_items.append(item)
                
                next_tk = data.get('next_token')
                if next_tk and len(cat_items) < 100:
                    params['next_token'] = next_tk
                    time.sleep(random.uniform(0.5, 1))
                else: break
            except Exception as e:
                print(f"   ⚠️ 에러: {e}")
                break
        
        all_results.extend(cat_items)
        time.sleep(1)

    if not all_results:
        print("❌ 수집된 데이터가 없습니다.")
        return

    # 5. 로컬 저장 (CSV/JSON)
    out_dir = os.path.join("/tmp", "ably_best_output")
    os.makedirs(out_dir, exist_ok=True)
    ts = now.strftime("%Y%m%d_%H%M%S")
    json_path = os.path.join(out_dir, f"ably_best_{ts}.json")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print(f"✅ 로컬 JSON 저장 완료: {json_path}")
    print(f"   총 수집 건수: {len(all_results)}")

    # 6. GCS 업로드
    try:
        gcs_path = f"{GCS_PREFIX}/{now.strftime('%Y-%m-%d')}/{os.path.basename(json_path)}"
        upload_to_gcs(json_path, GCS_BUCKET, gcs_path)
        print(f"✅ GCS 업로드 완료: gs://{GCS_BUCKET}/{gcs_path}")
    except Exception as e:
        print(f"⚠️ GCS 업로드 실패: {e}")

    # 7. BigQuery 적재
    try:
        bq_insert_rows(bq, all_results)
        print(f"✅ BigQuery 적재 완료: {len(all_results)}건")
    except Exception as e:
        print(f"❌ BigQuery 적재 실패: {e}")

if __name__ == "__main__":
    main()
