from flask import Blueprint, jsonify
from google.cloud import bigquery

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
