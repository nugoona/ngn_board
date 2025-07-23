# File: ngn_wep/dashboard/handlers/auth_handler.py
# pylint: disable=too-many-lines
import os
import json
import requests
from flask import (
    Blueprint, request, render_template, redirect,
    session, url_for, jsonify
)
from google.cloud import bigquery

# ───────────────────────────────────────────────
#  서비스 모듈
# ───────────────────────────────────────────────
from services.meta_demo_service import (
    get_ad_accounts,
    get_businesses,
    get_pages,
    get_campaigns,
    get_posts,
    get_engagement,
)

# ───────────────────────────────────────────────
#  기본 설정
# ───────────────────────────────────────────────
template_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "templates")
)
auth_blueprint = Blueprint("auth", __name__, template_folder=template_dir)

# ───────────────────────────────────────────────
#  로그인
# ───────────────────────────────────────────────
@auth_blueprint.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user_id   = request.form["user_id"]
        password  = request.form["password"]
        client    = bigquery.Client()

        # 1) 사용자 인증
        try:
            query = f"""
                SELECT *
                FROM `ngn_dataset.user_accounts`
                WHERE user_id   = '{user_id}'
                  AND password   = '{password}'
                  AND status    IN ('approved', 'admin')
            """
            result = list(client.query(query).result())
        except Exception as e:
            print(f"[ERROR] 유저 쿼리 실패: {e}")
            return render_template("login.html",
                                   error="내부 오류가 발생했습니다.")

        if not result:
            return render_template("login.html",
                                   error="아이디 또는 비밀번호가 올바르지 않습니다.")

        # 2) 세션 저장
        session["user_id"]      = user_id
        session["is_demo_user"] = (user_id.lower() == "guest")

        # 3) 회사 목록
        company_names: list[str] = []
        try:
            if session["is_demo_user"]:
                company_names = ["demo"]
            else:
                company_query = f"""
                    SELECT company_name
                    FROM `ngn_dataset.user_company_map`
                    WHERE user_id = '{user_id}'
                """
                rows = client.query(company_query).result()
                company_names = [
                    row.company_name
                    for row in rows
                    if row.company_name.lower() != "demo"
                ]
                company_names = list(set(company_names))

                # 관리자는 모든 업체 접근
                if not company_names and result[0].status.lower() == "admin":
                    all_company_query = """
                        SELECT DISTINCT company_name
                        FROM `ngn_dataset.user_company_map`
                        WHERE LOWER(company_name) != 'demo'
                    """
                    rows = client.query(all_company_query).result()
                    company_names = [row.company_name for row in rows]

        except Exception as e:
            print(f"[ERROR] 회사 목록 쿼리 실패: {e}")
            return render_template("login.html",
                                   error="회사 목록을 불러올 수 없습니다.")

        session["company_names"] = company_names
        print(f"[INFO] 로그인 성공: {user_id} / 업체 수: {len(company_names)}")
        return redirect("/")

    # GET
    return render_template("login.html")

# ───────────────────────────────────────────────
#  로그아웃
# ───────────────────────────────────────────────
@auth_blueprint.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))

# ───────────────────────────────────────────────
#  Facebook OAuth 콜백
# ───────────────────────────────────────────────
@auth_blueprint.route("/facebook/callback")
def facebook_callback():
    code = request.args.get("code")
    if not code:
        return "⚠️ 인증 코드가 없습니다.", 400

    client_id     = os.getenv("META_APP_ID")
    client_secret = os.getenv("META_APP_SECRET")
    redirect_uri  = "https://board.nugoona.co.kr/facebook/callback"

    # 1) Short-Lived Token
    token_url = "https://graph.facebook.com/v18.0/oauth/access_token"
    params    = {
        "client_id"    : client_id,
        "client_secret": client_secret,
        "redirect_uri" : redirect_uri,
        "code"         : code,
    }
    short_tok = requests.get(token_url, params=params).json()
    if "access_token" not in short_tok:
        return f"❌ 액세스 토큰 요청 실패: {short_tok}", 400

    # 2) Long-Lived Token
    long_params = {
        "grant_type"      : "fb_exchange_token",
        "client_id"       : client_id,
        "client_secret"   : client_secret,
        "fb_exchange_token": short_tok["access_token"],
    }
    long_tok = requests.get(token_url, params=long_params).json()
    if "access_token" not in long_tok:
        return f"❌ 장기 토큰 요청 실패: {long_tok}", 400

    # 3) 세션 저장
    session["meta_token"] = long_tok["access_token"]
    print(f"[META] 🎫 토큰 저장 완료: expires_in={long_tok.get('expires_in')}")
    return redirect("/")

# ───────────────────────────────────────────────
#  NEW ⭐  카탈로그 ID 단일 조회
# ───────────────────────────────────────────────
@auth_blueprint.route("/my_catalog_id")
def my_catalog_id():
    """
    세션에 저장된 meta_token을 이용해
    사용자가 접근 가능한 '첫 번째' 카탈로그 ID를 반환한다.
    JS (fetchCatalogId) 에서 사용.
    """
    access_token = session.get("meta_token")
    if not access_token:
        return jsonify({"catalog_id": None}), 401

    try:
        url    = "https://graph.facebook.com/v22.0/me/businesses"
        params = {"fields": "catalogs{id}", "access_token": access_token}
        data   = requests.get(url, params=params, timeout=10).json()

        for biz in data.get("data", []):
            catalogs = biz.get("catalogs", {}).get("data", [])
            if catalogs:
                return jsonify({"catalog_id": catalogs[0]["id"]})

        return jsonify({"catalog_id": None}), 404
    except Exception as e:
        print("[ERROR] /my_catalog_id 실패:", e)
        return jsonify({"catalog_id": None}), 500

# ───────────────────────────────────────────────
#  카탈로그 권한 중복 확인
# ───────────────────────────────────────────────
@auth_blueprint.route("/check_catalog_permission")
def check_catalog_permission():
    catalog_id   = request.args.get("catalog_id")
    access_token = request.args.get("access_token") or session.get("meta_token")

    if not catalog_id or not access_token:
        return jsonify({
            "allowed": False,
            "error"  : "Missing catalog_id or token",
        }), 400

    try:
        url    = f"https://graph.facebook.com/v22.0/{catalog_id}/permissions"
        params = {"access_token": access_token}
        data   = requests.get(url, params=params, timeout=10).json()

        for item in data.get("data", []):
            if item.get("user") and item.get("role") in (
                "MANAGER", "PRODUCT_CATALOG_ADMIN"
            ):
                return jsonify({"allowed": True})

    except Exception as e:
        print("[ERROR] catalog permission check failed:", e)

    return jsonify({"allowed": False})

# ───────────────────────────────────────────────
#  Meta Deauthorize / Delete Callback
# ───────────────────────────────────────────────
@auth_blueprint.route("/meta/deauthorize", methods=["POST"])
def meta_deauthorize():
    user_id = request.form.get("user_id")
    print(f"[META] ⚠️ 권한 해제됨 - user_id: {user_id}")
    return "✅ 권한 해제 수신 완료", 200

@auth_blueprint.route("/meta/delete-info", methods=["POST"])
def meta_delete_info():
    user_id = request.form.get("user_id")
    print(f"[META] ⚠️ 데이터 삭제 요청 - user_id: {user_id}")
    confirmation_code = f"delete_{user_id}_confirmed"
    return {
        "url": "https://board.nugoona.co.kr/delete-info",
        "confirmation_code": confirmation_code,
    }, 200

# ───────────────────────────────────────────────
#  데모 페이지
# ───────────────────────────────────────────────
@auth_blueprint.route("/meta-demo")
def meta_demo():
    return render_template("meta_demo.html")

# ───────────────────────────────────────────────
#  JS-SDK access_token → 세션 저장
# ───────────────────────────────────────────────
@auth_blueprint.route("/store_meta_token", methods=["POST"])
def store_meta_token():
    tok = (request.json or {}).get("access_token")
    if not tok:
        return {"status": "error", "msg": "no token"}, 400
    session["meta_token"] = tok
    return {"status": "ok"}
