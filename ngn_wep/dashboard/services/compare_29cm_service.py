"""
29CM 경쟁사 비교 서비스
검색 API를 통해 경쟁사 상품 정보를 수집하고 베스트 목록과 매칭
"""
import os
import json
import re
import time
import random
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from google.cloud import bigquery

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "winged-precept-443218-v8")
DATASET_ID = os.environ.get("BQ_DATASET", "ngn_dataset")
SEARCH_RESULTS_TABLE = "platform_29cm_search_results"
COMPETITOR_KEYWORDS_TABLE = "company_competitor_keywords"
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


def get_competitor_keywords(company_name: str) -> List[Dict[str, Any]]:
    """경쟁사 검색어 조회"""
    client = get_bigquery_client()
    
    query = f"""
    SELECT 
      competitor_keyword,
      display_name,
      sort_order
    FROM `{PROJECT_ID}.{DATASET_ID}.{COMPETITOR_KEYWORDS_TABLE}`
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
        print(f"[ERROR] get_competitor_keywords 실패: {e}")
        return []


def build_search_payload(keyword: str) -> dict:
    """검색 API payload 생성"""
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
    """29CM 검색 API 호출"""
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


def save_search_results_to_bq(
    company_name: str,
    search_keyword: str,
    run_id: str,
    search_results: List[Dict],
    search_date: datetime
) -> bool:
    """
    검색 결과를 BigQuery에 저장 (MERGE 문 사용)
    스트리밍 버퍼 문제를 피하기 위해 DELETE 대신 MERGE 사용
    """
    if not search_results:
        return False
    
    client = get_bigquery_client()
    
    # 새 데이터 준비
    rows = []
    for result in search_results:
        item_id = result.get("item_id")
        if not item_id:
            continue
        
        reviews = result.get("reviews", [])
        reviews_json = json.dumps(reviews, ensure_ascii=False) if reviews else None
        
        # 날짜를 문자열로 변환 (BigQuery insert_rows_json은 DATE를 문자열로 받음)
        search_date_str = search_date.date().isoformat()  # 'YYYY-MM-DD' 형식
        created_at_str = search_date.isoformat()  # ISO 형식 문자열
        
        row = {
            "search_keyword": search_keyword,
            "company_name": company_name,
            "run_id": run_id,
            "item_id": item_id,
            "rank": result.get("rank"),
            "brand_name": result.get("brand_name"),
            "product_name": result.get("product_name"),
            "price": result.get("price"),
            "discount_rate": result.get("discount_rate"),
            "like_count": result.get("like_count"),
            "review_count": result.get("review_count"),
            "review_score": result.get("review_score"),
            "thumbnail_url": result.get("thumbnail_url"),
            "item_url": result.get("item_url"),
            "best_rank": result.get("best_rank"),
            "best_category": result.get("best_category"),
            "search_date": search_date_str,  # 문자열로 변환
            "created_at": created_at_str,  # 문자열로 변환
            "updated_at": created_at_str,  # 문자열로 변환
            "reviews": reviews_json,
        }
        rows.append(row)
    
    if not rows:
        return False
    
    # 임시 테이블에 데이터 로드
    temp_table_id = f"{SEARCH_RESULTS_TABLE}_temp_{run_id}_{company_name}_{search_keyword}".replace("-", "_").replace(".", "_").replace(" ", "_")
    temp_table_ref = client.dataset(DATASET_ID).table(temp_table_id)
    
    try:
        # 기존 임시 테이블 삭제 (있다면)
        client.delete_table(temp_table_ref, not_found_ok=True)
        
        # 기존 테이블의 스키마 가져오기
        main_table_ref = client.dataset(DATASET_ID).table(SEARCH_RESULTS_TABLE)
        main_table = client.get_table(main_table_ref)
        
        # 임시 테이블 생성 (같은 스키마 사용)
        temp_table = bigquery.Table(temp_table_ref, schema=main_table.schema)
        client.create_table(temp_table)
        
        # 임시 테이블에 데이터 로드 (스트리밍 버퍼 문제를 피하기 위해 load_table_from_json 사용)
        job_config = bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            schema=main_table.schema,
            autodetect=False
        )
        
        # JSON 문자열로 변환
        json_rows = [json.dumps(row, ensure_ascii=False) for row in rows]
        json_content = "\n".join(json_rows)
        
        # 임시 테이블에 로드
        from io import BytesIO
        job = client.load_table_from_file(
            BytesIO(json_content.encode('utf-8')),
            temp_table_ref,
            job_config=job_config
        )
        job.result()  # 완료 대기
        
        print(f"[INFO] 임시 테이블에 {len(rows)}개 행 로드 완료: {temp_table_id}")
        
        # MERGE 문 실행 (덮어쓰기)
        merge_query = f"""
        MERGE `{PROJECT_ID}.{DATASET_ID}.{SEARCH_RESULTS_TABLE}` AS target
        USING `{PROJECT_ID}.{DATASET_ID}.{temp_table_id}` AS source
        ON target.company_name = source.company_name
           AND target.search_keyword = source.search_keyword
           AND target.run_id = source.run_id
           AND target.item_id = source.item_id
        WHEN MATCHED THEN
          UPDATE SET
            rank = source.rank,
            brand_name = source.brand_name,
            product_name = source.product_name,
            price = source.price,
            discount_rate = source.discount_rate,
            like_count = source.like_count,
            review_count = source.review_count,
            review_score = source.review_score,
            thumbnail_url = source.thumbnail_url,
            item_url = source.item_url,
            best_rank = source.best_rank,
            best_category = source.best_category,
            search_date = source.search_date,
            updated_at = source.updated_at,
            reviews = source.reviews
        WHEN NOT MATCHED THEN
          INSERT (
            search_keyword, company_name, run_id, item_id, rank,
            brand_name, product_name, price, discount_rate,
            like_count, review_count, review_score,
            thumbnail_url, item_url, best_rank, best_category,
            search_date, created_at, updated_at, reviews
          )
          VALUES (
            source.search_keyword, source.company_name, source.run_id, source.item_id, source.rank,
            source.brand_name, source.product_name, source.price, source.discount_rate,
            source.like_count, source.review_count, source.review_score,
            source.thumbnail_url, source.item_url, source.best_rank, source.best_category,
            source.search_date, source.created_at, source.updated_at, source.reviews
          )
        """
        
        merge_job = client.query(merge_query)
        merge_job.result()  # 완료 대기
        
        print(f"[INFO] MERGE 완료: {len(rows)}개 행 처리됨")
        
        # 임시 테이블 삭제
        client.delete_table(temp_table_ref, not_found_ok=True)
        
        # 같은 run_id의 기존 데이터 중 MERGE되지 않은 데이터 삭제 (선택적)
        # 주의: 스트리밍 버퍼 문제가 있을 수 있으므로 주석 처리
        # delete_old_query = f"""
        # DELETE FROM `{PROJECT_ID}.{DATASET_ID}.{SEARCH_RESULTS_TABLE}`
        # WHERE company_name = @company_name
        #   AND search_keyword = @search_keyword
        #   AND run_id = @run_id
        #   AND item_id NOT IN (
        #     SELECT item_id FROM `{PROJECT_ID}.{DATASET_ID}.{temp_table_id}`
        #   )
        # """
        
        return True
        
    except Exception as e:
        print(f"[ERROR] save_search_results_to_bq 실패: {e}")
        import traceback
        traceback.print_exc()
        
        # 임시 테이블 정리
        try:
            client.delete_table(temp_table_ref, not_found_ok=True)
        except:
            pass
        
        return False


def load_search_results_from_bq(company_name: str, run_id: str, search_keyword: Optional[str] = None) -> Dict[str, List[Dict]]:
    """BigQuery에서 검색 결과 로드"""
    client = get_bigquery_client()
    
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
    FROM `{PROJECT_ID}.{DATASET_ID}.{SEARCH_RESULTS_TABLE}`
    WHERE company_name = @company_name
      AND run_id = @run_id
    """
    
    params = [
        bigquery.ScalarQueryParameter("company_name", "STRING", company_name),
        bigquery.ScalarQueryParameter("run_id", "STRING", run_id),
    ]
    
    if search_keyword:
        query += " AND search_keyword = @search_keyword"
        params.append(bigquery.ScalarQueryParameter("search_keyword", "STRING", search_keyword))
    
    query += " ORDER BY search_keyword, rank"
    
    job_config = bigquery.QueryJobConfig(query_parameters=params)
    
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


def collect_and_save_search_results(
    company_name: str,
    search_keyword: str,
    run_id: str,
    best_dict: Dict[int, Dict]
) -> bool:
    """검색 결과 수집 및 저장 (전체 프로세스)"""
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
    
    # 4. 저장
    search_date = datetime.now(timezone(timedelta(hours=9)))
    success = save_search_results_to_bq(
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

