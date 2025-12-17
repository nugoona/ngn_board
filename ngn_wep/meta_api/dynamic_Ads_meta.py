"""
모든 업체 카탈로그에
  • [자동세트] 최근28일 베스트 60
  • [자동세트] 최근7일  베스트 20
두 세트를 자동 생성·업데이트한다.
"""

# ───── 표준 라이브러리 ───────────────────────────────
import os
import json
import logging
from itertools import islice
from typing import Iterable, List, Sequence, Tuple, Dict, Optional

# ───── 외부 패키지 ───────────────────────────────────
import requests
from dotenv import load_dotenv
from google.cloud import bigquery

# ───────── 환경 변수 로드 ─────────
# ① 컨테이너 내 경로(/app/.env)를 우선 로드
if os.path.exists("/app/.env"):
    load_dotenv(dotenv_path="/app/.env", override=True)


# ───────── Meta / BigQuery 공통 ─────────
FB_VER   = os.getenv("FB_GRAPH_VERSION", "v24.0")
FB_HOST  = f"https://graph.facebook.com/{FB_VER}"
FB_TOKEN = (
    os.getenv("META_SYSTEM_TOKEN")          # System Token 1순위
    or os.getenv("META_SYSTEM_USER_TOKEN")  # (fallback)
)
TIMEOUT  = int(os.getenv("META_API_TIMEOUT", 30))
BQ       = bigquery.Client()
LOG      = logging.getLogger("auto-sets")

# ───────── 세트 규격 ─────────
SET_SPECS = [
    ("[자동세트] 최근28일 베스트 60", 28, 60),
    ("[자동세트] 최근7일 베스트 20",  7, 20),
]

# ───────── 유틸 ─────────
def chunks(lst, size):
    for i in range(0, len(lst), size):
        yield lst[i:i+size]

def fetch_catalog_ids(catalog_id) -> List[str]:
    ids, after = [], None
    while True:
        p = {"fields":"retailer_id","limit":500,"access_token":FB_TOKEN}
        if after: p["after"] = after
        data = requests.get(f"{FB_HOST}/{catalog_id}/products",
                            params=p, timeout=TIMEOUT).json()
        ids += [d["retailer_id"] for d in data.get("data", [])]
        after = data.get("paging", {}).get("cursors", {}).get("after")
        if not after: break
    return ids

def map_short(full_list, short_list):
    return [f for s in short_list for f in full_list if f.startswith(f"{s}.")]

def get_set_id(catalog_id, name):
    after = None
    while True:
        p = {"fields":"id,name","limit":200,"access_token":FB_TOKEN}
        if after: p["after"] = after
        data = requests.get(f"{FB_HOST}/{catalog_id}/product_sets",
                            params=p, timeout=TIMEOUT).json()
        for s in data.get("data", []):
            if s["name"] == name: return s["id"]
        after = data.get("paging", {}).get("cursors", {}).get("after")
        if not after: break
    return None

def replace_filter(set_id, ids):
    payload = {
        "filter": json.dumps({"retailer_id":{"is_any":ids}},
                             ensure_ascii=False, separators=(",",":")),
        "access_token": FB_TOKEN,
    }
    r = requests.post(f"{FB_HOST}/{set_id}", data=payload, timeout=TIMEOUT).json()
    if "error" in r: raise RuntimeError(r["error"]["message"])

def create_set(catalog_id, name, ids):
    body = {
        "name": name,
        "filter": json.dumps({"retailer_id":{"is_any":ids}},
                             ensure_ascii=False, separators=(",",":")),
        "access_token": FB_TOKEN,
    }
    r = requests.post(f"{FB_HOST}/{catalog_id}/product_sets",
                      data=body, timeout=TIMEOUT).json()
    if "id" not in r: raise RuntimeError(r.get("error",{}).get("message","create fail"))
    return r["id"]

# ───────── 핵심 로직 ─────────
def best_products(company, days, limit):
    """
    company     : 업체명
    days, limit : 28·60 / 7·20 등 호출부에서 전달
    returns     : retailer_id 목록 (숫자형 or 전체 ID X → 후처리로 매핑)
    """
    q = f"""
        SELECT
          CAST(product_no AS STRING)            AS retailer_id,
          SUM(item_product_sales)               AS total_sales
        FROM  `winged-precept-443218-v8.ngn_dataset.daily_cafe24_items`
        WHERE company_name = @c
          AND payment_date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL @d DAY)
                               AND CURRENT_DATE()
        GROUP BY retailer_id
        ORDER BY total_sales DESC
        LIMIT  @l
    """
    job = BQ.query(
        q,
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("c", "STRING", company),
            bigquery.ScalarQueryParameter("d", "INT64",  days),
            bigquery.ScalarQueryParameter("l", "INT64",  limit),
        ]),
    )
    return [r.retailer_id for r in job]

def run_for_company(company, catalog_id):
    LOG.info("▶ %s / catalog %s", company, catalog_id)
    catalog_ids = fetch_catalog_ids(catalog_id)

    for title, days, limit in SET_SPECS:
        short = best_products(company, days, limit)
        full  = map_short(catalog_ids, short)
        if not full:
            LOG.warning("  • %s: 매칭된 상품 없음", title); continue

        set_id = get_set_id(catalog_id, title)
        if set_id:
            replace_filter(set_id, full)
            LOG.info("  • %s → filter 교체 (%d)", title, len(full))
        else:
            new_id = create_set(catalog_id, title, full[:500])
            for rest in chunks(full[500:], 500):
                requests.post(f"{FB_HOST}/{new_id}/products", data={
                    "retailer_id": ",".join(rest),
                    "method": "POST", "allow_upsert":"true",
                    "access_token": FB_TOKEN}, timeout=TIMEOUT)
            LOG.info("  • %s → 새로 생성 (%d)", title, len(full))

def main():
    rows = BQ.query("""
        SELECT company_name, catalog_id
        FROM `winged-precept-443218-v8.ngn_dataset.metaAds_acc`
        WHERE catalog_id IS NOT NULL
        GROUP BY company_name, catalog_id
    """)
    for r in rows:
        try:
            run_for_company(r.company_name, r.catalog_id)
        except Exception as e:
            LOG.error("❌ %s 실패: %s", r.company_name, e)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if not FB_TOKEN:
        raise SystemExit("❌ META_SYSTEM_TOKEN 환경변수가 없습니다.")
    main()
