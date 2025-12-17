# File: services/meta_demo_handler.py

import os
import requests
from flask import Blueprint, request, jsonify

meta_demo_blueprint = Blueprint("meta_demo", __name__)

def load_access_token():
    # 환경변수에서 직접 토큰 가져오기 (Cloud Run 환경변수 사용)
    token = os.getenv("META_LONG_TOKEN")
    if token:
        return token
    # 로컬 개발용 fallback (선택사항)
    return None

@meta_demo_blueprint.route("/get_data", methods=["POST"])
def get_meta_demo_data():
    data = request.get_json()
    type_param = data.get("type")
    access_token = load_access_token()
    if not access_token:
        return jsonify({"error": "Access token not found"}), 401

    def make_request(url, params):
        try:
            response = requests.get(url, params=params, timeout=10)
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    if type_param == "adaccounts":
        url = "https://graph.facebook.com/v24.0/me/adaccounts"
        params = {"access_token": access_token, "fields": "id,name"}
        return jsonify(make_request(url, params))

    elif type_param == "businesses":
        url = "https://graph.facebook.com/v24.0/me/businesses"
        params = {"access_token": access_token, "fields": "id,name"}
        return jsonify(make_request(url, params))

    elif type_param == "pages":
        url = "https://graph.facebook.com/v24.0/me/accounts"
        params = {"access_token": access_token, "fields": "id,name"}
        return jsonify(make_request(url, params))

    elif type_param and type_param.startswith("campaigns:"):
        ad_account_id = type_param.split(":", 1)[1]
        url = f"https://graph.facebook.com/v24.0/{ad_account_id}/campaigns"
        params = {"access_token": access_token, "fields": "id,name"}
        return jsonify(make_request(url, params))

    elif type_param and type_param.startswith("posts:"):
        page_id = type_param.split(":", 1)[1]
        url = f"https://graph.facebook.com/v24.0/{page_id}/posts"
        params = {"access_token": access_token, "fields": "id,message,created_time"}
        return jsonify(make_request(url, params))

    elif type_param and type_param.startswith("engagement:"):
        page_id = type_param.split(":", 1)[1]
        url = f"https://graph.facebook.com/v24.0/{page_id}/insights/page_impressions,page_engaged_users"
        params = {"access_token": access_token}
        return jsonify(make_request(url, params))

    return jsonify({"error": "올바르지 않은 type 값입니다."}), 400
