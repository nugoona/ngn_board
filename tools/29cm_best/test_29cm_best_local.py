import os
import json
import time
import random
import csv
import re
from datetime import datetime, timezone, timedelta
import urllib.request
from urllib.error import HTTPError, URLError

# BigQuery / GCS (GCP 기본 라이브러리)
from google.cloud import bigquery
from google.cloud import storage


# =========================
# 1) 설정값
# =========================
API_URL = "https://display-bff-api.29cm.co.kr/api/v1/plp/best/items"
CATEGORY_TREE_URL = "https://display-bff-api.29cm.co.kr/api/v1/category-groups/tree?categoryGroupNo=1"

# ✅ BEST 대분류(largeId) - 기본: 여성 BEST(268100100)
BEST_LARGE_ID = int(os.environ.get("BEST_LARGE_ID", "268100100"))

# ✅ 강제 재적재 옵션 (부분 적재/구버전 적재가 남아있을 때 복구용)
# - FORCE_RELOAD=1 이면 동일 run_id 데이터가 있어도 삭제 후 재적재
FORCE_RELOAD = os.environ.get("FORCE_RELOAD", "0") == "1"

# GCP 리소스
PROJECT_ID = os.environ.get("GCP_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT") or "winged-precept-443218-v8"
DATASET_ID = os.environ.get("BQ_DATASET", "ngn_dataset")
TABLE_ID = os.environ.get("BQ_TABLE", "platform_29cm_best")

# 원본 저장 GCS
GCS_BUCKET = os.environ.get("GCS_BUCKET", "ngn-homepage-static")
GCS_PREFIX = os.environ.get("GCS_PREFIX", "29cm_best")  # gs://bucket/29cm_best/YYYY-MM-DD/...

# 수집 파라미터 (원하는 값으로 바꿔도 됨)
PERIOD_TYPE = os.environ.get("PERIOD_TYPE", "WEEKLY")        # WEEKLY / DAILY 등
RANKING_TYPE = os.environ.get("RANKING_TYPE", "POPULARITY")  # POPULARITY 등
GENDER = os.environ.get("GENDER", "F")                       # F / M
AGE = os.environ.get("AGE", "THIRTIES")                      # THIRTIES 등 (API payload 값)

# ✅ 중복 적재 방지용 run_id
KST = timezone(timedelta(hours=9))


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "Origin": "https://home.29cm.co.kr",
    "Referer": "https://home.29cm.co.kr/",
}


# =========================
# 2) 수집 대상 탭 목록
# =========================
TEST_PAGES = []


# =========================
# 3) 공통 유틸
# =========================
def get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers=HEADERS, method="GET")
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    if raw.lstrip()[:1] not in ("{", "["):
        raise RuntimeError("응답이 JSON이 아님")
    return json.loads(raw)


def post_json(payload: dict) -> dict:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(API_URL, data=body, headers=HEADERS, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    if raw.lstrip()[:1] not in ("{", "["):
        raise RuntimeError("응답이 JSON이 아님")
    return json.loads(raw)


def extract_items(resp: dict) -> list:
    data = resp.get("data", {}) or {}
    return data.get("list", []) or []


def build_category_map(tree_json: dict) -> dict:
    """
    categoryCode(int) -> categoryName(str)
    large/medium/small 모두 맵에 포함
    """
    out = {}
    groups = (tree_json.get("data", {}) or {}).get("categoryGroups", []) or []
    for g in groups:
        for large in g.get("largeCategories", []) or []:
            if "categoryCode" in large and "categoryName" in large:
                out[int(large["categoryCode"])] = large.get("categoryName")
            for medium in large.get("mediumCategories", []) or []:
                if "categoryCode" in medium and "categoryName" in medium:
                    out[int(medium["categoryCode"])] = medium.get("categoryName")
                for small in medium.get("smallCategories", []) or []:
                    if "categoryCode" in small and "categoryName" in small:
                        out[int(small["categoryCode"])] = small.get("categoryName")
    return out


def resolve_best_page_name(payload: dict, category_map: dict) -> str:
    """
    payload의 facets.categoryFacetInputs[0] 기준으로 탭명을 결정
    """
    facets = payload.get("facets", {}) or {}
    cats = facets.get("categoryFacetInputs", []) or []
    if not cats:
        return "전체"

    c0 = cats[0] or {}

    mid = c0.get("mediumId")
    if mid is not None:
        return category_map.get(int(mid), f"MEDIUM_{mid}")

    sid = c0.get("smallId")
    if sid is not None:
        return category_map.get(int(sid), f"SMALL_{sid}")

    lid = c0.get("largeId")
    if lid is not None:
        return "전체"

    return "전체"


def split_category(ev: dict):
    """
    반환:
      - category_large, category_medium, category_small, category_path
    """
    large = ev.get("largeCategoryName")
    medium = ev.get("middleCategoryName")
    small = ev.get("smallCategoryName")

    parts = [p for p in [large, medium, small] if p]
    path = " > ".join(parts) if parts else None
    return large, medium, small, path


def safe_int(v):
    try:
        return int(v) if v is not None else None
    except Exception:
        return None


def safe_float(v):
    try:
        return float(v) if v is not None else None
    except Exception:
        return None


def bq_table_fqn() -> str:
    return f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"


def clean_product_name(name):
    """
    상품명 앞에 붙은 [ ... ], ( ... ) 블록들을 모두 제거
    """
    if not name:
        return name
    return re.sub(
        r'^(?:\s*[\[\(][^\]\)]*[\]\)]\s*)+',
        '',
        str(name)
    ).strip()


def extract_medium_ids_from_tree(tree_json: dict, large_id: int) -> list[int]:
    """
    category tree에서 large_id 아래 mediumCategories의 categoryCode(=mediumId) 목록을 추출
    """
    data = tree_json.get("data", {}) or {}
    groups = data.get("categoryGroups", []) or []
    medium_ids = []

    for g in groups:
        for large in g.get("largeCategories", []) or []:
            if int(large.get("categoryCode", -1)) != int(large_id):
                continue

            for medium in large.get("mediumCategories", []) or []:
                code = medium.get("categoryCode")
                if code is None:
                    continue
                medium_ids.append(int(code))

            return medium_ids

    return medium_ids


def build_payload(large_id: int, medium_id=None) -> dict:
    """
    기존 payload 구조 유지. medium_id가 있으면 탭 수집, 없으면 전체 수집.
    """
    cat = {"largeId": int(large_id)}
    if medium_id is not None:
        cat["mediumId"] = int(medium_id)

    return {
        "pageRequest": {"page": 1, "size": 100},
        "userSegment": {"gender": GENDER, "age": AGE},
        "facets": {
            "categoryFacetInputs": [cat],
            "periodFacetInput": {"type": PERIOD_TYPE, "order": "DESC"},
            "rankingFacetInput": {"type": RANKING_TYPE},
        },
    }


def build_test_pages(tree_json: dict, large_id: int) -> list[dict]:
    """
    전체 + medium 탭들을 자동으로 TEST_PAGES 형태로 생성
    """
    pages = []

    # 1) 전체
    pages.append({"payload": build_payload(large_id=large_id, medium_id=None)})

    # 2) medium 탭들
    medium_ids = extract_medium_ids_from_tree(tree_json, large_id=large_id)

    # 중복 제거(순서 유지)
    seen = set()
    uniq = []
    for mid in medium_ids:
        if mid not in seen:
            seen.add(mid)
            uniq.append(mid)

    for mid in uniq:
        pages.append({"payload": build_payload(large_id=large_id, medium_id=mid)})

    return pages


# =========================
# 4) GCS 업로드
# =========================
def upload_to_gcs(local_path: str, bucket_name: str, blob_path: str):
    client = storage.Client(project=PROJECT_ID)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)
    blob.upload_from_filename(local_path)
    return f"gs://{bucket_name}/{blob_path}"


# =========================
# 5) BigQuery 적재(중복 방지 포함)
# =========================
def bq_run_already_loaded(bq: bigquery.Client, run_id: str) -> bool:
    sql = f"""
    SELECT COUNT(1) AS cnt
    FROM `{bq_table_fqn()}`
    WHERE run_id = @run_id
    """
    job = bq.query(
        sql,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("run_id", "STRING", run_id)]
        ),
    )
    rows = list(job.result())
    return (rows[0]["cnt"] or 0) > 0


def bq_delete_run_id(bq: bigquery.Client, run_id: str):
    """
    FORCE_RELOAD=1 일 때: 동일 run_id 데이터가 이미 있으면 삭제 후 재적재
    """
    sql = f"""
    DELETE FROM `{bq_table_fqn()}`
    WHERE run_id = @run_id
    """
    bq.query(
        sql,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("run_id", "STRING", run_id)]
        ),
    ).result()


def bq_insert_rows(bq: bigquery.Client, rows: list[dict]):
    table_ref = bq.dataset(DATASET_ID).table(TABLE_ID)
    errors = bq.insert_rows_json(table_ref, rows)
    if errors:
        raise RuntimeError(f"BigQuery insert_rows_json errors: {errors}")


# =========================
# 6) 메인
# =========================
def main():
    global TEST_PAGES

    # ✅ 수집 시작 기준 시간 (KST)
    now = datetime.now(KST)

    # BigQuery DATETIME 안전 포맷
    collected_at = now.strftime("%Y-%m-%d %H:%M:%S")

    # ✅ 중복 방지용 run_id (같은 날/같은 조건이면 동일)
    run_id = f"{now.strftime('%Y%m%d')}_{PERIOD_TYPE}_{RANKING_TYPE}_{GENDER}_{AGE}"

    print("[INFO] PROJECT_ID:", PROJECT_ID)
    print("[INFO] BQ TABLE:", bq_table_fqn())
    print("[INFO] GCS BUCKET:", GCS_BUCKET)
    print("[INFO] BEST_LARGE_ID:", BEST_LARGE_ID)
    print("[INFO] FORCE_RELOAD:", FORCE_RELOAD)
    print("[INFO] run_id:", run_id)
    print("[INFO] collected_at:", collected_at)

    # 0) 카테고리 트리 로드(탭명 자동화 + 탭 자동 생성)
    try:
        tree_json = get_json(CATEGORY_TREE_URL)
        category_map = build_category_map(tree_json)

        TEST_PAGES = build_test_pages(tree_json, large_id=BEST_LARGE_ID)
        print(f"[INFO] 탭 자동 생성 완료: 전체 포함 {len(TEST_PAGES)}개 (medium {len(TEST_PAGES) - 1}개)")
    except Exception as e:
        print("[WARN] category tree fetch failed:", e)
        category_map = {}

        TEST_PAGES = [{"payload": build_payload(large_id=BEST_LARGE_ID, medium_id=None)}]
        print("[WARN] 탭 자동 생성 실패 -> 전체 탭만 수집합니다 (1개)")

    # 1) 수집
    results = []

    for page in TEST_PAGES:
        payload = page["payload"]
        best_page_name = resolve_best_page_name(payload, category_map)

        print(f"\n[CRAWL] {best_page_name} 수집 시작")
        time.sleep(random.uniform(0.8, 1.5))

        try:
            resp = post_json(payload)
        except HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise SystemExit(f"[HTTPError] {e.code}\n{body[:1500]}")
        except URLError as e:
            raise SystemExit(f"[URLError] {e}")
        except Exception as e:
            raise SystemExit(f"[ERROR] {e}")

        items = extract_items(resp)
        print("items:", len(items))

        for idx, it in enumerate(items):
            ev = it.get("itemEvent", {}).get("eventProperties", {}) or {}
            info = it.get("itemInfo", {}) or {}
            url = it.get("itemUrl", {}) or {}

            category_large, category_medium, category_small, category_path = split_category(ev)

            raw_name = info.get("productName") or ev.get("itemName")
            cleaned_name = clean_product_name(raw_name)

            results.append({
                "platform": "29CM",
                "best_page_name": best_page_name,
                "rank": idx + 1,
                "brand_name": info.get("brandName") or ev.get("brandName"),
                "product_name": cleaned_name,
                "category_large": category_large,
                "category_medium": category_medium,
                "category_small": category_small,
                "category_path": category_path,
                "price": safe_int(info.get("displayPrice") or ev.get("price")),
                "discount_rate": safe_int(info.get("saleRate") or ev.get("discountRate")),
                "like_count": safe_int(info.get("likeCount")),
                "review_count": safe_int(info.get("reviewCount")),
                "review_score": safe_float(info.get("reviewScore")),
                "item_url": (url.get("webLink") if isinstance(url, dict) else None),
                "thumbnail_url": info.get("thumbnailUrl"),
                "collected_at": collected_at,
                "run_id": run_id,
            })

    if not results:
        raise SystemExit("[ERROR] results is empty")

    # 2) 로컬 파일 저장
    out_dir = os.path.join("/tmp", "29cm_best_output")
    os.makedirs(out_dir, exist_ok=True)

    ts = now.strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join(out_dir, f"29cm_best_{ts}.csv")
    json_path = os.path.join(out_dir, f"29cm_best_{ts}.json")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    fields = list(results[0].keys())
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in results:
            writer.writerow(row)

    print(f"\n✅ CSV 저장 완료: {csv_path}")
    print(f"✅ JSON 저장 완료: {json_path}")
    print(f"총 행 수: {len(results)}")

    # 3) GCS 업로드
    date_prefix = now.strftime("%Y-%m-%d")
    gcs_csv = f"{GCS_PREFIX}/{date_prefix}/{os.path.basename(csv_path)}"
    gcs_json = f"{GCS_PREFIX}/{date_prefix}/{os.path.basename(json_path)}"

    try:
        gs_csv_uri = upload_to_gcs(csv_path, GCS_BUCKET, gcs_csv)
        gs_json_uri = upload_to_gcs(json_path, GCS_BUCKET, gcs_json)
        print("✅ GCS 업로드 완료:", gs_csv_uri)
        print("✅ GCS 업로드 완료:", gs_json_uri)
    except Exception as e:
        print("[WARN] GCS upload failed:", e)

    # 4) BigQuery 적재 (중복 방지 + 강제 재적재)
    bq = bigquery.Client(project=PROJECT_ID)

    if bq_run_already_loaded(bq, run_id):
        if not FORCE_RELOAD:
            print(f"⏭️ 이미 적재된 run_id라서 스킵: {run_id}")
            return
        print(f"[INFO] FORCE_RELOAD=1 -> 기존 run_id 데이터 삭제 후 재적재: {run_id}")
        bq_delete_run_id(bq, run_id)

    bq_insert_rows(bq, results)
    print(f"✅ BigQuery 적재 완료: {bq_table_fqn()} (rows={len(results)})")


if __name__ == "__main__":
    main()
