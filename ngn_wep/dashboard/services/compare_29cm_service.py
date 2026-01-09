"""
29CM 경쟁사 비교 서비스
검색 API를 통해 경쟁사 상품 정보를 수집하고 베스트 목록과 매칭
"""
import os
import json
import re
import time
import random
import gzip
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from google.cloud import bigquery
from google.cloud import storage

# 캐싱 유틸리티 임포트
try:
    from ..utils.cache_utils import cached_query
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False
    def cached_query(func_name=None, ttl=None):
        def decorator(func):
            return func
        return decorator

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "winged-precept-443218-v8")
DATASET_ID = os.environ.get("BQ_DATASET", "ngn_dataset")
GCS_BUCKET = os.environ.get("GCS_BUCKET", "winged-precept-443218-v8.appspot.com")
SEARCH_RESULTS_TABLE = "platform_29cm_search_results"
COMPETITOR_BRANDS_TABLE = "company_competitor_brands"  # brandId 기반 테이블
BEST_TABLE = "platform_29cm_best"

# 29CM API 설정
SEARCH_API_URL = "https://display-bff-api.29cm.co.kr/api/v1/listing/items?colorchipVariant=treatment"
REVIEW_API_URL = "https://review-api.29cm.co.kr/api/v4/reviews"

SEARCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "Origin": "https://shop.29cm.co.kr",
    "Referer": "https://shop.29cm.co.kr/",
}

REVIEW_HEADERS_BASE = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "*/*",
}

REVIEW_SORT_CANDIDATES = ["RECENT", "BEST"]


def get_bigquery_client():
    """BigQuery Client 생성"""
    return bigquery.Client(project=PROJECT_ID)


def safe_int(v):
    """안전한 int 변환"""
    try:
        return int(v) if v is not None else None
    except Exception:
        return None


def safe_float(v):
    """안전한 float 변환"""
    try:
        return float(v) if v is not None else None
    except Exception:
        return None


def post_json(url: str, headers: dict, payload: dict) -> dict:
    """POST JSON 요청"""
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = Request(url, data=body, headers=headers, method="POST")
    with urlopen(req, timeout=40) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def get_json(url: str, headers: dict) -> dict:
    """GET JSON 요청"""
    req = Request(url, headers=headers, method="GET")
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def get_competitor_brands(company_name: str) -> List[Dict[str, Any]]:
    """경쟁사 브랜드 ID 조회 (brandId 기반)"""
    client = get_bigquery_client()

    query = f"""
    SELECT
      brand_id,
      brand_name,
      display_name,
      sort_order
    FROM `{PROJECT_ID}.{DATASET_ID}.{COMPETITOR_BRANDS_TABLE}`
    WHERE company_name = @company_name
      AND is_active = TRUE
    ORDER BY sort_order ASC
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("company_name", "STRING", company_name)
        ]
    )

    try:
        rows = client.query(query, job_config=job_config).result()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"[ERROR] get_competitor_brands 실패: {e}")
        return []


def get_own_brand_id(company_name: str) -> Optional[int]:
    """자사몰 브랜드 ID 조회 (company_info.brand_id_29cm)"""
    client = get_bigquery_client()

    query = f"""
    SELECT brand_id_29cm
    FROM `{PROJECT_ID}.{DATASET_ID}.company_info`
    WHERE company_name = @company_name
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("company_name", "STRING", company_name)
        ]
    )

    try:
        rows = list(client.query(query, job_config=job_config).result())
        if rows and rows[0].brand_id_29cm:
            return int(rows[0].brand_id_29cm)
        return None
    except Exception as e:
        print(f"[ERROR] get_own_brand_id 실패: {e}")
        return None


def update_brand_name(company_name: str, brand_id: int, brand_name: str) -> bool:
    """브랜드명 자동 업데이트 (brand_name이 NULL인 경우에만)"""
    client = get_bigquery_client()

    query = f"""
    UPDATE `{PROJECT_ID}.{DATASET_ID}.{COMPETITOR_BRANDS_TABLE}`
    SET brand_name = @brand_name,
        display_name = COALESCE(display_name, @brand_name),
        updated_at = CURRENT_TIMESTAMP()
    WHERE company_name = @company_name
      AND brand_id = @brand_id
      AND brand_name IS NULL
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("brand_name", "STRING", brand_name),
            bigquery.ScalarQueryParameter("company_name", "STRING", company_name),
            bigquery.ScalarQueryParameter("brand_id", "INT64", brand_id),
        ]
    )

    try:
        result = client.query(query, job_config=job_config).result()
        if result.num_dml_affected_rows > 0:
            print(f"[INFO] 브랜드명 업데이트: {brand_id} → {brand_name}")
        return True
    except Exception as e:
        print(f"[ERROR] update_brand_name 실패: {e}")
        return False


def build_brand_payload(brand_id: int, page: int = 1, size: int = 50) -> dict:
    """브랜드 ID 기반 API payload 생성
    - frontBrandNo를 facets.brandFacetInputs 안에 설정
    """
    return {
        "pageType": "BRAND_HOME",
        "sortType": "MOST_SOLD",  # 판매순 정렬
        "facets": {
            "brandFacetInputs": [
                {"frontBrandNo": brand_id}
            ]
        },
        "pageRequest": {"page": page, "size": size},
    }


# 하위 호환성을 위한 별칭
def get_competitor_keywords(company_name: str) -> List[Dict[str, Any]]:
    """[DEPRECATED] get_competitor_brands() 사용 권장"""
    brands = get_competitor_brands(company_name)
    # 기존 형식으로 변환
    return [
        {
            "competitor_keyword": str(b["brand_id"]),
            "display_name": b.get("display_name") or b.get("brand_name") or str(b["brand_id"]),
            "sort_order": b["sort_order"]
        }
        for b in brands
    ]


def build_search_payload(keyword: str) -> dict:
    """[DEPRECATED] build_brand_payload() 사용 권장"""
    return {
        "keyword": keyword,
        "pageType": "SRP",
        "sortType": "RECOMMENDED",
        "facets": {},
        "pageRequest": {"page": 1, "size": 50},
    }


def extract_top20(resp: dict) -> List[dict]:
    """검색 결과에서 TOP 20 추출"""
    items = (resp.get("data") or {}).get("list") or []
    result = []

    for rank, it in enumerate(items[:20], start=1):
        item_url = it.get("itemUrl") or {}
        item_event = (it.get("itemEvent") or {}).get("eventProperties") or {}
        item_info = it.get("itemInfo") or {}

        result.append({
            "rank": rank,
            "item_id": safe_int(it.get("itemId")),
            "brand_name": item_info.get("brandName") or item_event.get("brandName"),
            "product_name": item_info.get("productName") or item_event.get("itemName"),
            "price": safe_int(item_info.get("displayPrice") or item_event.get("price")),
            "discount_rate": safe_int(item_info.get("saleRate") or item_event.get("discountRate")),
            "like_count": safe_int(item_info.get("likeCount")),
            "review_count": safe_int(item_info.get("reviewCount")),
            "review_score": safe_float(item_info.get("reviewScore")),
            "thumbnail_url": item_info.get("thumbnailUrl"),
            "item_url": item_url.get("webLink") if isinstance(item_url, dict) else None,
        })

    return result


def search_29cm_products(keyword: str) -> List[Dict]:
    """[DEPRECATED] fetch_brand_products() 사용 권장"""
    try:
        payload = build_search_payload(keyword)
        resp = post_json(SEARCH_API_URL, SEARCH_HEADERS, payload)
        return extract_top20(resp)
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"[ERROR] 검색 API HTTPError {e.code}: {body[:500]}")
        return []
    except URLError as e:
        print(f"[ERROR] 검색 API URLError: {e}")
        return []
    except Exception as e:
        print(f"[ERROR] 검색 API 오류: {e}")
        return []


def fetch_brand_products(brand_id: int) -> List[Dict]:
    """브랜드 ID로 상품 목록 조회 (brandId 기반)"""
    try:
        payload = build_brand_payload(brand_id)
        resp = post_json(SEARCH_API_URL, SEARCH_HEADERS, payload)
        return extract_top20(resp)
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"[ERROR] 브랜드 API HTTPError {e.code}: {body[:500]}")
        return []
    except URLError as e:
        print(f"[ERROR] 브랜드 API URLError: {e}")
        return []
    except Exception as e:
        print(f"[ERROR] 브랜드 API 오류: {e}")
        return []


def _fetch_reviews(item_id: int, sort_value: str, limit: int, referer: str) -> dict:
    """리뷰 API 호출 (내부 함수)"""
    params = {
        "itemId": item_id,
        "page": 0,
        "size": limit,
        "sort": sort_value,
    }
    url = f"{REVIEW_API_URL}?{urlencode(params)}"

    headers = dict(REVIEW_HEADERS_BASE)
    headers["Referer"] = referer
    return get_json(url, headers)


def fetch_product_reviews(item_id: int, limit: int = 10) -> List[Dict]:
    """상품 리뷰 수집 (fallback 포함)"""
    referers = [
        f"https://www.29cm.co.kr/products/{item_id}",
        f"https://product.29cm.co.kr/catalog/{item_id}",
    ]

    for ref in referers:
        for sort_value in REVIEW_SORT_CANDIDATES:
            try:
                data = _fetch_reviews(item_id, sort_value, limit, ref)

                if isinstance(data, dict) and data.get("result") == "FAIL":
                    continue

                # 리뷰 정규화
                raw = data.get("raw") or data
                data_section = raw.get("data") or {}
                results = data_section.get("results") or []

                reviews = []
                for r in results:
                    content = (r.get("contents") or r.get("content") or "").strip()
                    content = content.replace("\r\n", "\n").replace("\r", "\n")

                    if len(content) > 200:
                        content = content[:200] + "…"

                    opt = r.get("optionValue") or []
                    if isinstance(opt, list):
                        opt_str = ", ".join([str(x) for x in opt if x is not None]) or None
                    else:
                        opt_str = str(opt)

                    created_at = (
                        r.get("insertTimestamp")
                        or r.get("createdAt")
                        or r.get("created_at")
                        or r.get("registrationDate")
                    )

                    reviews.append({
                        "rating": safe_int(r.get("point")),
                        "option": opt_str,
                        "created_at": created_at,
                        "content": content,
                    })

                return reviews

            except HTTPError as e:
                continue
            except Exception as e:
                continue

    return []  # 모든 시도 실패


def extract_item_id_from_url(item_url: str) -> Optional[int]:
    """item_url에서 item_id 추출"""
    if not item_url:
        return None
    
    match = re.search(r'catalog/(\d+)', item_url)
    if match:
        return safe_int(match.group(1))
    
    match = re.search(r'products/(\d+)', item_url)
    if match:
        return safe_int(match.group(1))
    
    return None


def load_best_ranking_dict(run_id: str) -> Dict[int, Dict]:
    """베스트 목록을 딕셔너리로 로드 (item_id -> {rank, category})"""
    client = get_bigquery_client()
    
    query = f"""
    SELECT 
      REGEXP_EXTRACT(item_url, r'catalog/([0-9]+)') as product_id,
      rank,
      best_page_name
    FROM `{PROJECT_ID}.{DATASET_ID}.{BEST_TABLE}`
    WHERE run_id = @run_id
      AND period_type = 'WEEKLY'
    QUALIFY ROW_NUMBER() OVER (PARTITION BY item_url ORDER BY collected_at DESC) = 1
    """
    
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("run_id", "STRING", run_id)
        ]
    )
    
    best_dict = {}
    try:
        rows = client.query(query, job_config=job_config).result()
        for row in rows:
            product_id = safe_int(row.product_id)
            if product_id:
                best_dict[product_id] = {
                    "rank": row.rank,
                    "category": row.best_page_name,
                }
    except Exception as e:
        print(f"[ERROR] load_best_ranking_dict 실패: {e}")
    
    return best_dict


def match_with_best_ranking(search_results: List[Dict], best_dict: Dict[int, Dict]) -> List[Dict]:
    """검색 결과와 베스트 목록 매칭"""
    for result in search_results:
        item_id = result.get("item_id")
        if item_id and item_id in best_dict:
            best_info = best_dict[item_id]
            result["best_rank"] = best_info["rank"]
            result["best_category"] = best_info["category"]
        else:
            result["best_rank"] = None
            result["best_category"] = None
    
    return search_results


def delete_existing_search_results(company_name: str, search_keyword: str, run_id: str) -> bool:
    """
    기존 검색 결과 삭제 (덮어쓰기용)
    주의: 스트리밍 버퍼 문제로 인해 DELETE가 실패할 수 있으므로,
    MERGE 문을 사용하는 것을 권장합니다.
    """
    client = get_bigquery_client()
    
    # 스트리밍 버퍼 문제를 피하기 위해 DELETE 대신 MERGE에서 처리
    # 이 함수는 더 이상 사용하지 않지만, 호환성을 위해 남겨둠
    return True


def get_compare_snapshot_path(run_id: str, company_name: Optional[str] = None) -> str:
    """
    스냅샷 GCS 경로 생성
    company_name이 있으면 경로에 포함 (같은 run_id에 여러 company가 있을 수 있으므로)
    """
    # run_id 형식: {year}W{week:02d}_WEEKLY_...
    week_match = re.match(r'(\d{4})W(\d{2})', run_id)
    if not week_match:
        raise ValueError(f"Invalid run_id format: {run_id}")
    
    year = week_match.group(1)
    week = week_match.group(2)
    
    # ISO 주차를 사용하여 월 계산
    jan4 = datetime(int(year), 1, 4)
    jan4_day = jan4.weekday()
    days_to_thursday = (3 - jan4_day + 7) % 7
    first_thursday = datetime(int(year), 1, 4 + days_to_thursday)
    week_start = first_thursday + timedelta(days=-3 + (int(week) - 1) * 7)
    month = week_start.month
    
    # company_name이 있으면 경로에 포함
    if company_name:
        return f"ai-reports/compare/29cm/{company_name}/{year}-{month:02d}-{week}/search_results.json.gz"
    else:
        return f"ai-reports/compare/29cm/{year}-{month:02d}-{week}/search_results.json.gz"


def save_search_results_to_gcs(
    company_name: str,
    search_keyword: str,
    run_id: str,
    search_results: List[Dict],
    search_date: datetime
) -> bool:
    """
    검색 결과를 GCS 스냅샷으로 저장
    BigQuery 저장은 포기하고 스냅샷만 사용
    """
    if not search_results:
        return False
    
    try:
        # 스냅샷 경로 생성 (company_name 포함)
        blob_path = get_compare_snapshot_path(run_id, company_name)
        
        # 기존 스냅샷 로드 (있다면)
        existing_snapshot = load_search_results_from_gcs(company_name, run_id)
        if existing_snapshot is None:
            existing_snapshot = {}
        
        # 현재 검색어 데이터 업데이트
        existing_snapshot[search_keyword] = search_results
        
        # 스냅샷 데이터 구성
        snapshot_data = {
            "run_id": run_id,
            "company_name": company_name,
            "created_at": search_date.isoformat(),
            "search_results": existing_snapshot
        }
        
        # JSON 직렬화 및 Gzip 압축
        json_str = json.dumps(snapshot_data, ensure_ascii=False, indent=2)
        json_bytes = json_str.encode('utf-8')
        compressed_bytes = gzip.compress(json_bytes)
        
        # GCS에 업로드 (덮어쓰기)
        client = storage.Client(project=PROJECT_ID)
        bucket = client.bucket(GCS_BUCKET)
        blob = bucket.blob(blob_path)
        
        # 기존 파일이 있으면 삭제 후 업로드 (명시적 덮어쓰기)
        if blob.exists():
            blob.delete()
            print(f"[INFO] 기존 스냅샷 삭제: {blob_path}")
        
        blob.upload_from_string(compressed_bytes, content_type='application/gzip')
        
        print(f"[INFO] 스냅샷 저장 완료: {blob_path} ({search_keyword}: {len(search_results)}개)")
        return True
        
    except Exception as e:
        print(f"[ERROR] save_search_results_to_gcs 실패: {e}")
        import traceback
        traceback.print_exc()
        return False
    


@cached_query(func_name="compare_29cm_load_search_results", ttl=300)  # 5분 캐싱
def load_search_results_from_gcs(company_name: str, run_id: str, search_keyword: Optional[str] = None) -> Optional[Dict[str, List[Dict]]]:
    """
    GCS 스냅샷에서 검색 결과 로드 (캐싱 적용)
    """
    try:
        # 스냅샷 경로 생성 (company_name 포함)
        blob_path = get_compare_snapshot_path(run_id, company_name)
        
        client = storage.Client(project=PROJECT_ID)
        bucket = client.bucket(GCS_BUCKET)
        blob = bucket.blob(blob_path)
        
        if not blob.exists():
            print(f"[WARN] 스냅샷 파일이 없습니다: {blob_path}")
            return None
        
        # 파일 읽기 및 압축 해제
        snapshot_bytes = blob.download_as_bytes(raw_download=True)
        
        try:
            snapshot_json_str = gzip.decompress(snapshot_bytes).decode('utf-8')
        except (gzip.BadGzipFile, OSError):
            snapshot_json_str = snapshot_bytes.decode('utf-8')
        
        snapshot_data = json.loads(snapshot_json_str)
        
        # company_name 확인
        if snapshot_data.get("company_name") != company_name:
            print(f"[WARN] 스냅샷의 company_name이 일치하지 않습니다: {snapshot_data.get('company_name')} != {company_name}")
            return None
        
        # search_results 추출
        search_results = snapshot_data.get("search_results", {})
        created_at = snapshot_data.get("created_at")  # 수집 시간
        
        # search_keyword가 지정된 경우 해당 키워드만 반환
        if search_keyword:
            if search_keyword in search_results:
                return {
                    "search_results": {search_keyword: search_results[search_keyword]},
                    "created_at": created_at
                }
            else:
                return {
                    "search_results": {},
                    "created_at": created_at
                }
        
        return {
            "search_results": search_results,
            "created_at": created_at
        }
        
    except Exception as e:
        print(f"[ERROR] load_search_results_from_gcs 실패: {e}")
        import traceback
        traceback.print_exc()
        return None


def collect_and_save_brand_results(
    company_name: str,
    brand_id: int,
    run_id: str,
    best_dict: Dict[int, Dict],
    is_own_mall: bool = False
) -> Optional[str]:
    """브랜드 ID 기반 상품 수집 및 저장 (전체 프로세스)

    Returns:
        brand_name: 수집된 브랜드명 (API 응답에서 추출) 또는 None
    """
    print(f"[INFO] 브랜드 수집 시작: {brand_id} (company: {company_name}, own_mall: {is_own_mall})")

    # 1. 브랜드 ID로 상품 조회
    search_results = fetch_brand_products(brand_id)
    if not search_results:
        print(f"[WARN] 검색 결과 없음: brand_id={brand_id}")
        return None

    print(f"[INFO] 검색 결과 {len(search_results)}개 수집")

    # 브랜드명 추출 (첫 번째 상품에서)
    brand_name = search_results[0].get("brand_name") if search_results else None

    # 2. 리뷰 수집
    for result in search_results:
        item_id = result.get("item_id")
        if item_id:
            time.sleep(random.uniform(0.3, 0.5))  # API 호출 간격
            reviews = fetch_product_reviews(item_id, limit=10)
            result["reviews"] = reviews

    # 3. 베스트 목록 매칭
    search_results = match_with_best_ranking(search_results, best_dict)

    # 4. 저장 (GCS 스냅샷) - brand_id를 키로 사용
    search_date = datetime.now(timezone(timedelta(hours=9)))
    success = save_brand_results_to_gcs(
        company_name=company_name,
        brand_id=brand_id,
        run_id=run_id,
        search_results=search_results,
        search_date=search_date,
        is_own_mall=is_own_mall
    )

    if success:
        print(f"[INFO] 저장 완료: brand_id={brand_id} ({len(search_results)}개)")
        # 브랜드명 자동 업데이트 (경쟁사만)
        if brand_name and not is_own_mall:
            update_brand_name(company_name, brand_id, brand_name)
    else:
        print(f"[ERROR] 저장 실패: brand_id={brand_id}")

    return brand_name


def save_brand_results_to_gcs(
    company_name: str,
    brand_id: int,
    run_id: str,
    search_results: List[Dict],
    search_date: datetime,
    is_own_mall: bool = False
) -> bool:
    """브랜드 ID 기반 검색 결과를 GCS 스냅샷으로 저장"""
    if not search_results:
        return False

    try:
        # 스냅샷 경로 생성 (company_name 포함)
        blob_path = get_compare_snapshot_path(run_id, company_name)

        # 기존 스냅샷 로드 (있다면)
        existing_data = load_search_results_from_gcs(company_name, run_id)
        existing_snapshot = {}
        if existing_data and "search_results" in existing_data:
            existing_snapshot = existing_data["search_results"]

        # brand_id를 문자열 키로 사용
        brand_key = str(brand_id)
        existing_snapshot[brand_key] = search_results

        # 스냅샷 데이터 구성
        snapshot_data = {
            "run_id": run_id,
            "company_name": company_name,
            "created_at": search_date.isoformat(),
            "search_results": existing_snapshot
        }

        # JSON 직렬화 및 Gzip 압축
        json_str = json.dumps(snapshot_data, ensure_ascii=False, indent=2)
        json_bytes = json_str.encode('utf-8')
        compressed_bytes = gzip.compress(json_bytes)

        # GCS에 업로드 (덮어쓰기)
        client = storage.Client(project=PROJECT_ID)
        bucket = client.bucket(GCS_BUCKET)
        blob = bucket.blob(blob_path)

        if blob.exists():
            blob.delete()

        blob.upload_from_string(compressed_bytes, content_type='application/gzip')

        print(f"[INFO] 스냅샷 저장 완료: {blob_path} (brand_id={brand_id}: {len(search_results)}개)")
        return True

    except Exception as e:
        print(f"[ERROR] save_brand_results_to_gcs 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


# 하위 호환성을 위한 기존 함수 유지
def collect_and_save_search_results(
    company_name: str,
    search_keyword: str,
    run_id: str,
    best_dict: Dict[int, Dict]
) -> bool:
    """[DEPRECATED] collect_and_save_brand_results() 사용 권장"""
    print(f"[INFO] 검색 시작: {search_keyword} (company: {company_name})")

    # 1. 검색
    search_results = search_29cm_products(search_keyword)
    if not search_results:
        print(f"[WARN] 검색 결과 없음: {search_keyword}")
        return False

    print(f"[INFO] 검색 결과 {len(search_results)}개 수집")

    # 2. 리뷰 수집
    for result in search_results:
        item_id = result.get("item_id")
        if item_id:
            time.sleep(random.uniform(0.3, 0.5))  # API 호출 간격
            reviews = fetch_product_reviews(item_id, limit=10)
            result["reviews"] = reviews

    # 3. 베스트 목록 매칭
    search_results = match_with_best_ranking(search_results, best_dict)

    # 4. 저장 (GCS 스냅샷)
    search_date = datetime.now(timezone(timedelta(hours=9)))
    success = save_search_results_to_gcs(
        company_name=company_name,
        search_keyword=search_keyword,
        run_id=run_id,
        search_results=search_results,
        search_date=search_date
    )

    if success:
        print(f"[INFO] 저장 완료: {search_keyword} ({len(search_results)}개)")
    else:
        print(f"[ERROR] 저장 실패: {search_keyword}")

    return success

