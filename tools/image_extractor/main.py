"""
이미지 추출 API 서비스
- 상품 상세페이지에서 이미지를 크롤링하고 YOLO로 크롭
- Cloud Run 서비스로 배포 (min-instances=0)
"""
import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from google.cloud import bigquery
from extractor import extract_images_from_url

app = Flask(__name__)
CORS(app)  # 모든 도메인에서 접근 허용

# BigQuery 클라이언트
bq_client = bigquery.Client()

# 기본 선택자 (폴백용)
DEFAULT_SELECTORS = [
    ".cont img", "#prdDetail img", "#prdDetailContent img", "#prdDetailContentLazy img",
    "#goods_description img", ".goods_description img",
    ".product-detail img", "#detail img"
]


def get_selectors_for_account(account_id: str) -> list:
    """BigQuery에서 계정별 CSS 선택자 조회"""
    query = """
        SELECT detail_img_selectors
        FROM `ngn_dataset.meta_account_mapping`
        WHERE account_id = @account_id
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("account_id", "STRING", account_id)
        ]
    )

    try:
        result = list(bq_client.query(query, job_config=job_config).result())
        if result and result[0].detail_img_selectors:
            return json.loads(result[0].detail_img_selectors)
    except Exception as e:
        print(f"[WARN] 선택자 조회 실패: {e}")

    return DEFAULT_SELECTORS


@app.route("/health", methods=["GET"])
def health():
    """헬스 체크"""
    return {"status": "ok"}


@app.route("/extract", methods=["POST"])
def extract():
    """
    상품 상세페이지에서 이미지 추출

    Request Body:
    {
        "url": "https://example.com/product/123",
        "account_id": "1289149138367044"  (optional)
    }

    Response:
    {
        "success": true,
        "product_name": "상품명",
        "images": ["data:image/jpeg;base64,...", ...],
        "count": 5
    }
    """
    data = request.get_json()

    if not data or not data.get("url"):
        return jsonify({"success": False, "error": "URL이 필요합니다."}), 400

    url = data["url"]
    account_id = data.get("account_id")

    # 계정별 선택자 조회
    selectors = DEFAULT_SELECTORS
    if account_id:
        selectors = get_selectors_for_account(account_id)

    print(f"[INFO] 이미지 추출 시작: {url}")
    print(f"[INFO] 사용 선택자: {selectors}")

    try:
        result = extract_images_from_url(url, selectors)

        return jsonify({
            "success": True,
            "product_name": result["product_name"],
            "images": result["images"],
            "count": len(result["images"])
        })

    except Exception as e:
        print(f"[ERROR] 이미지 추출 실패: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
