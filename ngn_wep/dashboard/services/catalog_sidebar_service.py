"""
META Catalog – Sidebar service layer
────────────────────────────────────────────────────────────────────────────
● 1) get_catalog_sidebar_data           : 자동 세트(28일·7일) + catalog_id 조회
● 2) get_manual_product_list            : 자사몰 카테고리 URL → 상품번호 + 이름
● 3) search_products_for_manual_set     : 키워드(상품명·번호) 검색
● 4) create_or_update_product_set       : 동일 세트명 있으면 ‘업데이트’, 없으면 ‘생성’
   └ 내부적으로 _get_existing_set_id() 로 기존 세트 탐색
────────────────────────────────────────────────────────────────────────────
Graph API 버전·토큰·타임아웃 모두 환경변수로 주입 가능
"""

# ───── 표준 라이브러리 ───────────────────────────────
import os
import json
import logging
from itertools import islice
from typing import Iterable, List, Sequence, Tuple, Dict, Optional
from urllib.parse import urlparse   # host 추출에만 사용

# ───── 외부 패키지 ───────────────────────────────────
import requests
from google.cloud import bigquery


# ─ Logger & BigQuery ────────────────────────────────────────────────────
LOG       = logging.getLogger(__name__)
bq_client = bigquery.Client()

# ─ Meta Graph API 공통 설정 ───────────────────────────
FB_VER   = os.getenv("FB_GRAPH_VERSION", "v24.0")
FB_HOST  = f"https://graph.facebook.com/{FB_VER}"

# ✅ ① System Token 우선
FB_TOKEN = (
    os.getenv("META_SYSTEM_TOKEN")            # ← 반드시 여기를 먼저!
    or os.getenv("META_SYSTEM_USER_TOKEN")    #    없으면 사용자 장기 토큰
)
TIMEOUT  = int(os.getenv("META_API_TIMEOUT", 30))



# ======================================================================
# 1) 자동 세트 (최근 28일 / 7일 베스트) + catalog_id
# ======================================================================
def get_catalog_sidebar_data(account_id: str):
    """
    • account_id(광고 계정) → company_name, catalog_id
    • 최근 28일 Top 60, 최근 7일 Top 20
    """
    sql_cmp = """
        SELECT company_name, catalog_id
        FROM `winged-precept-443218-v8.ngn_dataset.metaAds_acc`
        WHERE meta_acc_id = @acc_id
        LIMIT 1
    """
    row = next(
        bq_client.query(
            sql_cmp,
            job_config=bigquery.QueryJobConfig(
                query_parameters=[bigquery.ScalarQueryParameter("acc_id", "STRING", account_id)]
            ),
        ).result(),
        None,
    )
    if not row:
        return None, "해당 account_id 의 회사 정보를 찾을 수 없습니다."

    company_name, catalog_id = row["company_name"], row["catalog_id"]

    def _top_query(days: int, limit: int) -> str:
        return f"""
            SELECT product_name,
                   product_no,
                   SUM(total_quantity) AS total_quantity
            FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_items`
            WHERE company_name = @cmp
              AND payment_date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL {days} DAY)
                                   AND CURRENT_DATE()
              AND total_quantity > 0
            GROUP BY product_name, product_no
            ORDER BY total_quantity DESC
            LIMIT {limit}
        """

    param = [bigquery.ScalarQueryParameter("cmp", "STRING", company_name)]
    best_28 = [
        dict(r) for r in bq_client.query(
            _top_query(28, 60),
            job_config=bigquery.QueryJobConfig(query_parameters=param)
        ).result()
    ]
    best_7 = [
        dict(r) for r in bq_client.query(
            _top_query(7, 20),
            job_config=bigquery.QueryJobConfig(query_parameters=param)
        ).result()
    ]

    return {
        "company_name": company_name,
        "catalog_id"  : catalog_id,
        "best_28"     : best_28,
        "best_7"      : best_7,
    }, None


# ======================================================================
# 2) 수동 세트 – 카테고리 URL → product_no 크롤링 → 상품정보 조회
# ======================================================================

def get_manual_product_list(
    category_url: str,
    max_pages: int = 10,
    crawl_func_url: str = os.getenv(
        "CRAWL_FUNCTION_URL",
        "https://asia-northeast3-winged-precept-443218-v8.cloudfunctions.net/crawl_catalog",
    ),
    crawl_timeout: int = 120,   # Cloud Function 최대 대기(초)
):
    """
    1) Cloud Function(crawl_catalog)에 category_url 전달 → 즉시 크롤링 & BigQuery 적재
    2) 적재가 끝나면 url_product 테이블을 조회해 상품목록 반환
    """
    import logging, requests
    from urllib.parse import urlparse
    from google.cloud import bigquery

    LOG = logging.getLogger("catalog")

    # ────────────────── 1️⃣ Cloud Function 호출 ──────────────────
    payload = {"category_url": category_url, "max_pages": max_pages}
    try:
        LOG.info("[crawl_catalog 호출] %s", crawl_func_url)
        cf_res = requests.post(
            crawl_func_url,
            json=payload,
            timeout=crawl_timeout,
            headers={"Content-Type": "application/json"},
        )
        cf_res.raise_for_status()
        cf_json = cf_res.json()
        LOG.info("[crawl_catalog 응답] %s", cf_json)
        if cf_json.get("status") != "success":
            return None, f"Cloud Function 실패: {cf_json}"
    except Exception as e:
        LOG.error("[Cloud Function 호출 오류] %s", e)
        return None, f"Cloud Function 호출 오류: {e}"

    # ────────────────── 2️⃣ company_name 매핑 ──────────────────
    host = urlparse(category_url).netloc.replace("www.", "")
    sql_cmp = """
        SELECT company_name
        FROM `winged-precept-443218-v8.ngn_dataset.company_info`
        WHERE @url LIKE CONCAT('%', main_url, '%')
        LIMIT 1
    """
    row = next(
        bq_client.query(
            sql_cmp,
            job_config=bigquery.QueryJobConfig(
                query_parameters=[bigquery.ScalarQueryParameter("url", "STRING", host)]
            ),
        ).result(),
        None,
    )
    if not row:
        msg = f"해당 URL({host}) 과 매칭되는 회사 정보를 찾을 수 없습니다."
        LOG.error("[도메인 매핑 실패] " + msg)
        return None, msg

    company_name = row["company_name"]
    LOG.info("[업체 매핑] %s → %s", host, company_name)

    # ────────────────── 3️⃣ url_product 테이블 조회 ──────────────────
    sql_prod = """
        SELECT DISTINCT product_name, CAST(product_no AS INT64) AS product_no
        FROM `winged-precept-443218-v8.ngn_dataset.url_product`
        WHERE company_name = @cmp
        ORDER BY product_name
    """
    rows = bq_client.query(
        sql_prod,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("cmp", "STRING", company_name)]
        ),
    ).result()
    result = [dict(r) for r in rows]
    LOG.info("[url_product] %d개 반환", len(result))
    return result, None



# ======================================================================
# 3) 수동 세트 – 키워드 검색
# ======================================================================
def search_products_for_manual_set(
    account_id: str,
    keyword: str,
    search_type: str = "product_name",
    limit: int = 100,
):
    """JS (data_type: catalog_manual_search) 에서 호출"""
    # 3-1) account_id → company_name
    sql_cmp = """
        SELECT company_name
        FROM `winged-precept-443218-v8.ngn_dataset.metaAds_acc`
        WHERE meta_acc_id = @acc
        LIMIT 1
    """
    row = next(
        bq_client.query(
            sql_cmp,
            job_config=bigquery.QueryJobConfig(
                query_parameters=[bigquery.ScalarQueryParameter("acc", "STRING", account_id)]
            ),
        ).result(),
        None,
    )
    if not row:
        return None, "해당 account_id 의 회사 정보를 찾을 수 없습니다."
    company_name = row["company_name"]

    # 3-2) 검색 조건
    if search_type == "product_no":
        where_clause = "CAST(product_no AS STRING) LIKE CONCAT('%', @kw, '%')"
    else:  # product_name
        where_clause = "LOWER(product_name) LIKE CONCAT('%', LOWER(@kw), '%')"

    sql_search = f"""
        SELECT DISTINCT company_name, product_name, product_no
        FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_items`
        WHERE company_name = @cmp
          AND {where_clause}
        ORDER BY product_name
        LIMIT {limit}
    """
    rows = bq_client.query(
        sql_search,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("cmp", "STRING", company_name),
                bigquery.ScalarQueryParameter("kw",  "STRING", keyword),
            ]
        ),
    ).result()
    return [dict(r) for r in rows], None


# ──────────────────────────────────────────────────────────────
# 4) 세트 생성 / 업데이트  (Graph API v24.0)   ★ REWORKED v2 ★
# ──────────────────────────────────────────────────────────────

# ── 내부 유틸 ────────────────────────────────────────────────
def _chunks(it: Iterable, size: int):
    it = iter(it)
    while chunk := list(islice(it, size)):
        yield chunk

def _fetch_catalog_retailer_ids(catalog_id: str) -> List[str]:
    """해당 카탈로그에 등록된 모든 retailer_id 리스트"""
    ids, after = [], None
    while True:
        params = {
            "fields"      : "retailer_id",
            "limit"       : 500,
            "access_token": FB_TOKEN,
            **({"after": after} if after else {}),
        }
        res = requests.get(f"{FB_HOST}/{catalog_id}/products",
                           params=params, timeout=TIMEOUT).json()
        ids += [p["retailer_id"] for p in res.get("data", [])]
        after = res.get("paging", {}).get("cursors", {}).get("after")
        if not after:
            break
    return ids

def _map_short_to_full(short_ids: Sequence[str], catalog_ids: List[str]) -> List[str]:
    """‘679’ → ‘679.P000…’ 식으로 full retailer_id 매핑"""
    full: List[str] = []
    for sid in short_ids:
        full += [rid for rid in catalog_ids if rid.startswith(f"{sid}.")]
    return full

def _get_existing_set_id(catalog_id: str, set_name: str) -> Optional[str]:
    """세트명이 동일한 product_set ID(있으면)"""
    after = None
    while True:
        params = {
            "fields"      : "id,name",
            "limit"       : 200,
            "access_token": FB_TOKEN,
            **({"after": after} if after else {}),
        }
        res = requests.get(f"{FB_HOST}/{catalog_id}/product_sets",
                           params=params, timeout=TIMEOUT).json()
        for s in res.get("data", []):
            if s["name"] == set_name:
                return s["id"]
        after = res.get("paging", {}).get("cursors", {}).get("after")
        if not after:
            break
    return None

def _replace_set_filter(set_id: str, ids: List[str]) -> Tuple[bool, str]:
    """filter 전체 덮어쓰기"""
    payload = {
        "filter"      : json.dumps({"retailer_id": {"is_any": ids}},
                                   ensure_ascii=False, separators=(",", ":")),
        "access_token": FB_TOKEN,
    }
    res = requests.post(f"{FB_HOST}/{set_id}", data=payload, timeout=TIMEOUT).json()
    if "error" in res:
        return False, res["error"].get("message", "filter 갱신 실패")
    return True, ""

# ── PUBLIC 함수 ─────────────────────────────────────────────
def create_or_update_product_set(
    catalog_id  : str,
    set_name    : str,
    retailer_ids: Sequence[str],
):
    """
    • retailer_ids 에 ‘679’, ‘680.P0…’ 등 혼합 가능
    • 500개 초과 시 자동 batch 업로드
    • 기존 세트가 있으면 filter 를 **완전히 교체**하여 수량 감소도 반영
    """
    if not FB_TOKEN:
        return {}, "META_SYSTEM_TOKEN 누락"

    # 1️⃣ 매핑
    catalog_ids = _fetch_catalog_retailer_ids(catalog_id)
    full_ids    = _map_short_to_full(retailer_ids, catalog_ids)
    if not full_ids:
        return {}, "카탈로그에서 매칭된 retailer_id 가 없습니다."

    # 2️⃣ 동일 세트 여부
    existing_id = _get_existing_set_id(catalog_id, set_name)
    MAX_FILTER  = 4_500                # 약 64 kB(여유)

    if existing_id:
        # 2-a) filter 덮어쓰기 시도
        if len(full_ids) <= MAX_FILTER:
            ok, msg = _replace_set_filter(existing_id, full_ids)
            if not ok:
                return {}, msg
            return {"action": "replaced", "set_id": existing_id}, ""

        # 2-b) 너무 크면 삭제 후 재생성
        del_res = requests.delete(
            f"{FB_HOST}/{existing_id}",
            params={"access_token": FB_TOKEN},
            timeout=TIMEOUT
        ).json()
        if "error" in del_res:
            return {}, del_res["error"].get("message", "세트 삭제 실패")
        existing_id = None   # ← fall-through 로 ‘새로 생성’ 진입

    # 3️⃣ 새 세트 생성
    first, rest = full_ids[:500], full_ids[500:]
    create_body = {
        "name"        : set_name,
        "filter"      : json.dumps({"retailer_id": {"is_any": first}},
                                   ensure_ascii=False, separators=(",", ":")),
        "access_token": FB_TOKEN,
    }
    res = requests.post(f"{FB_HOST}/{catalog_id}/product_sets",
                        data=create_body, timeout=TIMEOUT).json()
    if "id" not in res:
        return {}, res.get("error", {}).get("message", "Create 실패")

    new_id = res["id"]
    for chunk in _chunks(rest, 500):
        add = requests.post(
            f"{FB_HOST}/{new_id}/products",
            data={
                "retailer_id" : ",".join(chunk),
                "method"      : "POST",
                "allow_upsert": "true",
                "access_token": FB_TOKEN,
            },
            timeout=TIMEOUT,
        ).json()
        if not add.get("success"):
            return {}, add.get("error", {}).get("message", "추가 업로드 실패")

    return {"action": "created", "set_id": new_id}, ""

