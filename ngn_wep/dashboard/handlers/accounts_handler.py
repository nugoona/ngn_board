import os
from flask import Blueprint, jsonify
from google.cloud import bigquery

# ✅ Cloud Run에서는 키 파일 대신 런타임 서비스계정(ADC)을 사용
# (키 파일 경로가 남아 있으면 /app/service-account.json 찾다가 부팅이 죽음)
if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") == "/app/service-account.json":
    if not os.path.exists("/app/service-account.json"):
        os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)

accounts_blueprint = Blueprint("accounts", __name__)
client = bigquery.Client()

@accounts_blueprint.route("/get_accounts", methods=["GET"])
def get_accounts():
    """
    업체 계정 목록을 BigQuery에서 조회하여 반환
    (demo 계정은 관리자 계정에서 제외)
    """
    query = """
    SELECT DISTINCT company_name
    FROM `winged-precept-443218-v8.ngn_dataset.company_info`
    WHERE LOWER(company_name) != 'demo'
    ORDER BY company_name
    """
    results = client.query(query).result()
    accounts = [row.company_name for row in results]

    return jsonify({"accounts": accounts})
