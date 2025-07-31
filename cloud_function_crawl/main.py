# File: main.py  (Cloud Function: crawl_catalog)

import io, json, requests, re, datetime
from bs4 import BeautifulSoup
from google.cloud import bigquery
import functions_framework

# ───────────────────────── 브라우저 수준 HEADERS ─────────────────────────
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Connection": "keep-alive",
}

# ───────────────────────── 회사명 매핑 함수 ─────────────────────────
def get_company_name_by_url(cate_url: str) -> str | None:
    """
    cate_url 안에 포함된 main_url 로 company_info 테이블에서 company_name 조회
    """
    client = bigquery.Client()
    query = """
        SELECT company_name
        FROM `winged-precept-443218-v8.ngn_dataset.company_info`
        WHERE @url LIKE CONCAT('%', main_url, '%')
        LIMIT 1
    """
    job_cfg = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("url", "STRING", cate_url)]
    )
    row = next(client.query(query, job_config=job_cfg).result(), None)
    return row["company_name"] if row else None

# ───────────────────────── Cloud Function 엔트리포인트 ─────────────────────────
@functions_framework.http
def crawl_catalog(request):
    """
    Body(JSON):
      {
        "category_url": "https://piscess.shop/product/list.html?cate_no=76",
        "max_pages": 10          # (선택) 기본 10, 0이면 끝까지
      }
    """
    try:
        data      = request.get_json(silent=True) or {}
        cate_url  = data.get("category_url")
        max_pages = int(data.get("max_pages", 10))

        if not cate_url:
            return _resp({"status": "error", "msg": "category_url 누락"}, 400)

        # 1️⃣ company_name 매핑
        company = get_company_name_by_url(cate_url)
        if not company:
            return _resp({"status": "error", "msg": "company_name 조회 실패"}, 400)

        # 2️⃣ 세션 & 쿠키 확보 (timeout 20초)
        sess = requests.Session()
        sess.headers.update(HEADERS)
        base = f"https://{cate_url.split('/')[2]}"
        sess.get(base, timeout=20)   # 쿠키 사전 확보

        # 3️⃣ 카탈로그 크롤링
        rows = []
        page_idx = 1
        while True:
            if max_pages and page_idx > max_pages:
                break

            target_url = f"{cate_url}&page={page_idx}" if page_idx > 1 else cate_url
            sess.headers["Referer"] = base
            res = sess.get(target_url, timeout=20)
            res.encoding = "utf-8"

            soup = BeautifulSoup(res.text, "html.parser")
            li_tags = soup.select("li[id^=anchorBoxId_]")
            if not li_tags:      # 다음 페이지 없음
                break

            for li in li_tags:
                m = re.match(r"anchorBoxId_(\d+)", li.get("id", ""))
                if not m:
                    continue
                prod_no = m.group(1)

                spans = li.select("strong.name a span")
                prod_nm = spans[-1].get_text(strip=True) if spans else ""
                if not prod_nm:
                    continue

                rows.append(
                    {
                        "company_name": company,
                        "product_no": prod_no,
                        "product_name": prod_nm,
                        "updated_at": datetime.datetime.utcnow().isoformat(),
                    }
                )

            page_idx += 1

        if not rows:
            return _resp({"status": "empty", "msg": "크롤링된 상품이 없습니다."})

        # 4️⃣ BigQuery Load Job (WRITE_TRUNCATE: 테이블 전체 덮어쓰기)
        client   = bigquery.Client()
        table_id = "winged-precept-443218-v8.ngn_dataset.url_product"

        load_cfg = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        )
        json_data = "\n".join(json.dumps(r, ensure_ascii=False) for r in rows).encode("utf-8")
        load_job = client.load_table_from_file(
            io.BytesIO(json_data), table_id, job_config=load_cfg, rewind=True
        )
        load_job.result()  # 완료 대기

        return _resp({"status": "success", "count": len(rows)})

    except Exception as e:
        return _resp({"status": "error", "msg": str(e)}, 500)

# ───────────────────────── 공통 응답 헬퍼 ─────────────────────────
def _resp(obj: dict, code: int = 200):
    return (json.dumps(obj, ensure_ascii=False), code, {"Content-Type": "application/json"})
