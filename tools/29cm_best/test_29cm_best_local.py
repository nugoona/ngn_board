# test_29cm_best_local.py  (Cloud Run Job에서도 그대로 실행 가능)
# - 29CM BEST: 전체 + 중분류 탭별 1~100위 수집 (WEEKLY/MONTHLY 스냅샷)
# - 핵심: facets.categoryFacetInputs 에 largeId + middleId 를 넣어야 탭별 랭킹이 실제로 적용됨
# - run_id 형식:
#   * 주간: {year}W{week:02d}_WEEKLY_{RANKING_TYPE}_{GENDER}_{AGE} (같은 주에는 1회만 적재)
#   * 월간: {year}-{month:02d}_MONTHLY_{RANKING_TYPE}_{GENDER}_{AGE} (전월 데이터, 매월 1일 수집)
# - run_id 중복이면 스킵(Streaming Buffer 이슈 때문에 DELETE/UPDATE는 Job에서 하지 않음)

import os
import json
import time
import random
import csv
import re
from datetime import datetime, timezone, timedelta
import urllib.request
from urllib.error import HTTPError, URLError

from google.cloud import bigquery
from google.cloud import storage


# =========================
# 1) 설정값
# =========================
API_URL = "https://display-bff-api.29cm.co.kr/api/v1/plp/best/items"
CATEGORY_TREE_URL = "https://display-bff-api.29cm.co.kr/api/v1/category-groups/tree?categoryGroupNo=1"

# BEST 대분류(여성의류)
BEST_LARGE_ID = int(os.environ.get("BEST_LARGE_ID", "268100100"))

# GCP 리소스
PROJECT_ID = (
    os.environ.get("GCP_PROJECT")
    or os.environ.get("GOOGLE_CLOUD_PROJECT")
    or "winged-precept-443218-v8"
)
DATASET_ID = os.environ.get("BQ_DATASET", "ngn_dataset")
TABLE_ID = os.environ.get("BQ_TABLE", "platform_29cm_best")

# 원본 저장 GCS
GCS_BUCKET = os.environ.get("GCS_BUCKET", "ngn-homepage-static")
GCS_PREFIX = os.environ.get("GCS_PREFIX", "29cm_best")

# 수집 파라미터 (주간 스냅샷 기본)
PERIOD_TYPE = os.environ.get("PERIOD_TYPE", "WEEKLY")        # WEEKLY 고정 권장
RANKING_TYPE = os.environ.get("RANKING_TYPE", "POPULARITY")  # POPULARITY 등
GENDER = os.environ.get("GENDER", "F")                       # F / M
AGE = os.environ.get("AGE", "THIRTIES")                      # THIRTIES 등 (API payload 값)

# Politeness
SLEEP_MIN = float(os.environ.get("SLEEP_MIN", "1.0"))
SLEEP_MAX = float(os.environ.get("SLEEP_MAX", "2.0"))

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
# 2) 공통 유틸
# =========================
def get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers=HEADERS, method="GET")
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    return json.loads(raw)


def post_json(payload: dict) -> dict:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(API_URL, data=body, headers=HEADERS, method="POST")
    with urllib.request.urlopen(req, timeout=40) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    return json.loads(raw)


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


def clean_product_name(name):
    """
    상품명 앞 prefix 제거:
    - [ ... ] / ( ... ) 가 연속으로 붙은 경우 전부 제거
    """
    if not name:
        return name
    return re.sub(r'^(?:\s*[\[\(][^\]\)]*[\]\)]\s*)+', '', str(name)).strip()


def bq_table_fqn() -> str:
    return f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"


def upload_to_gcs(local_path: str, bucket_name: str, blob_path: str):
    client = storage.Client(project=PROJECT_ID)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)
    blob.upload_from_filename(local_path)
    return f"gs://{bucket_name}/{blob_path}"


def bq_run_already_loaded(bq: bigquery.Client, run_id: str, period_type: str) -> bool:
    """
    중복 체크: LIMIT 1 사용으로 스캔 최소화
    - COUNT 대신 LIMIT 1 사용 (첫 번째 행만 찾으면 중단)
    - 클러스터링과 함께 사용하면 효과 극대화
    """
    sql = f"""
    SELECT 1
    FROM `{bq_table_fqn()}`
    WHERE run_id = @run_id
      AND period_type = @period_type
    LIMIT 1
    """
    job = bq.query(
        sql,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("run_id", "STRING", run_id),
                bigquery.ScalarQueryParameter("period_type", "STRING", period_type)
            ]
        ),
    )
    rows = list(job.result())
    return len(rows) > 0


def bq_insert_rows(bq: bigquery.Client, rows: list[dict]):
    table_ref = bq.dataset(DATASET_ID).table(TABLE_ID)
    errors = bq.insert_rows_json(table_ref, rows)
    if errors:
        raise RuntimeError(f"BigQuery insert_rows_json errors: {errors}")


# =========================
# 3) 카테고리/탭 생성
# =========================
def extract_medium_categories(tree_json: dict, target_large_id: int) -> list[dict]:
    """
    return:
      [
        {"categoryName": "니트웨어", "categoryCode": 268105100, "parentCategoryCode": 268100100},
        ...
      ]
    """
    out = []
    groups = (tree_json.get("data", {}) or {}).get("categoryGroups", []) or []
    for g in groups:
        for large in g.get("largeCategories", []) or []:
            if int(large.get("categoryCode", -1)) != int(target_large_id):
                continue
            for medium in large.get("mediumCategories", []) or []:
                try:
                    out.append({
                        "categoryName": medium.get("categoryName"),
                        "categoryCode": int(medium.get("categoryCode")),
                        "parentCategoryName": large.get("categoryName"),
                        "parentCategoryCode": int(large.get("categoryCode")),
                    })
                except Exception:
                    continue
    return out


def build_category_map_from_medium_list(medium_list: list[dict]) -> dict:
    # categoryCode -> categoryName
    m = {}
    for it in medium_list:
        code = it.get("categoryCode")
        name = it.get("categoryName")
        if code is not None and name:
            m[int(code)] = name
    return m


def build_payload(large_id: int, middle_id: int | None = None) -> dict:
    """
    29CM BEST 탭별 필터링용 payload
    - 전체: largeId만
    - 탭별: largeId + middleId (✅ 프론트/HAR 검증)
    """
    cat = {"largeId": int(large_id)}
    if middle_id is not None:
        cat["middleId"] = int(middle_id)

    return {
        "pageRequest": {"page": 1, "size": 100},
        "userSegment": {
            "gender": GENDER,
            "age": AGE,
        },
        "facets": {
            "categoryFacetInputs": [cat],
            "periodFacetInput": {
                "type": PERIOD_TYPE,
                "order": "DESC",
            },
            "rankingFacetInput": {
                "type": RANKING_TYPE,
            },
        },
    }


def resolve_best_page_name(payload: dict, category_map: dict) -> str:
    """
    - middleId가 있으면 medium 이름
    - largeId만 있으면 '전체'
    """
    facets = payload.get("facets", {}) or {}
    cats = facets.get("categoryFacetInputs", []) or []
    if not cats:
        return "전체"

    c0 = cats[0] or {}
    mid = c0.get("middleId")
    if mid is not None:
        return category_map.get(int(mid), f"MIDDLE_{mid}")

    lid = c0.get("largeId")
    if lid is not None:
        return "전체"

    return "전체"


# =========================
# 4) 메인
# =========================
def main():
    now = datetime.now(KST)
    collected_at = now.strftime("%Y-%m-%d %H:%M:%S")
    
    # period_type은 환경변수에서 직접 가져오기
    period_type = PERIOD_TYPE.upper()  # "WEEKLY" 또는 "MONTHLY"

    # ✅ run_id 생성 (주간/월간 구분)
    if period_type == "MONTHLY":
        # 월간: 전월 데이터 수집 (매월 1일 새벽 3시 실행 시 전월)
        if now.month == 1:
            target_year = now.year - 1
            target_month = 12
        else:
            target_year = now.year
            target_month = now.month - 1
        run_id = f"{target_year}-{target_month:02d}_{PERIOD_TYPE}_{RANKING_TYPE}_{GENDER}_{AGE}"
    else:
        # 주간: ISO 주차 기반
        iso = now.isocalendar()  # (year, week, weekday)
        run_id = f"{iso.year}W{iso.week:02d}_{PERIOD_TYPE}_{RANKING_TYPE}_{GENDER}_{AGE}"

    print("[INFO] PROJECT_ID:", PROJECT_ID)
    print("[INFO] BQ TABLE:", bq_table_fqn())
    print("[INFO] GCS BUCKET:", GCS_BUCKET)
    print("[INFO] run_id:", run_id)
    print("[INFO] period_type:", period_type)
    print("[INFO] collected_at:", collected_at)
    print("[INFO] BEST_LARGE_ID:", BEST_LARGE_ID)
    print("[INFO] PERIOD_TYPE:", PERIOD_TYPE)

    # 0) BigQuery 중복 체크 (먼저 해서 불필요한 크롤링/비용 방지)
    bq = bigquery.Client(project=PROJECT_ID)
    if bq_run_already_loaded(bq, run_id, period_type):
        print(f"⏭️ 이미 적재된 run_id라서 스킵: {run_id} (period_type: {period_type})")
        return

    # 1) 카테고리 트리 로드 → medium 탭 생성
    try:
        tree_json = get_json(CATEGORY_TREE_URL)
        medium_list = extract_medium_categories(tree_json, BEST_LARGE_ID)
        category_map = build_category_map_from_medium_list(medium_list)
    except Exception as e:
        raise SystemExit(f"[ERROR] category tree fetch failed: {e}")

    # 전체 + medium 탭 payload 생성
    test_pages = [{"payload": build_payload(BEST_LARGE_ID)}]  # 전체

    for m in medium_list:
        # categoryCode == middleId 로 사용 (✅ 검증된 키)
        test_pages.append({"payload": build_payload(BEST_LARGE_ID, m["categoryCode"])})

    print(
        f"[INFO] 탭 자동 생성 완료: 전체 포함 {len(test_pages)}개 "
        f"(middle {len(medium_list)}개)"
    )

    # 2) 수집
    results = []

    for i, page in enumerate(test_pages, start=1):
        payload = page["payload"]
        best_page_name = resolve_best_page_name(payload, category_map)

        print(f"[CRAWL] {best_page_name} 수집 시작 ({i}/{len(test_pages)})")
        time.sleep(random.uniform(SLEEP_MIN, SLEEP_MAX))

        try:
            resp = post_json(payload)
        except HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            print(f"[WARN] HTTPError {e.code} on {best_page_name}\n{body[:1200]}")
            continue
        except URLError as e:
            print(f"[WARN] URLError on {best_page_name}: {e}")
            continue
        except Exception as e:
            print(f"[WARN] ERROR on {best_page_name}: {e}")
            continue

        items = (resp.get("data", {}) or {}).get("list", []) or []
        print("items:", len(items))

        for idx, it in enumerate(items):
            ev = it.get("itemEvent", {}).get("eventProperties", {}) or {}
            info = it.get("itemInfo", {}) or {}
            url = it.get("itemUrl", {}) or {}

            results.append({
                "platform": "29CM",
                "best_page_name": best_page_name,
                "rank": idx + 1,
                "brand_name": info.get("brandName") or ev.get("brandName"),
                "product_name": clean_product_name(info.get("productName") or ev.get("itemName")),
                "category_large": ev.get("largeCategoryName"),
                "category_medium": ev.get("middleCategoryName"),
                "category_small": ev.get("smallCategoryName"),
                "category_path": " > ".join([p for p in [
                    ev.get("largeCategoryName"),
                    ev.get("middleCategoryName"),
                    ev.get("smallCategoryName"),
                ] if p]) or None,
                "price": safe_int(info.get("displayPrice") or ev.get("price")),
                "discount_rate": safe_int(info.get("saleRate") or ev.get("discountRate")),
                "like_count": safe_int(info.get("likeCount")),
                "review_count": safe_int(info.get("reviewCount")),
                "review_score": safe_float(info.get("reviewScore")),
                "item_url": (url.get("webLink") if isinstance(url, dict) else None),
                "thumbnail_url": info.get("thumbnailUrl"),
                "collected_at": collected_at,
                "run_id": run_id,
                "period_type": period_type,
            })

    if not results:
        raise SystemExit("[ERROR] results is empty")

    # 3) 로컬 저장 (/tmp)
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

    print(f"✅ CSV 저장 완료: {csv_path}")
    print(f"✅ JSON 저장 완료: {json_path}")
    print(f"총 행 수: {len(results)}")

    # 4) GCS 업로드
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

    # 5) BigQuery 적재
    # (크롤링 전에 이미 중복 체크했으므로 여기서는 재확인 생략 - 비용 절감)
    bq_insert_rows(bq, results)
    print(f"✅ BigQuery 적재 완료: {bq_table_fqn()} (rows={len(results)})")


if __name__ == "__main__":
    main()
