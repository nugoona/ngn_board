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

# ✅ Cloud Run에서는 키 파일 대신 런타임 서비스계정(ADC)을 사용
# GOOGLE_APPLICATION_CREDENTIALS 환경변수가 설정되어 있으면 제거하여 ADC 사용
creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
if creds_path and not os.path.exists(creds_path):
    os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)

# ───────────────────────────────────────────────
#  서비스 모듈
# ───────────────────────────────────────────────
from ..services.meta_demo_service import (
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
    # 모바일 디바이스 감지
    def is_mobile_device():
        user_agent = request.headers.get('User-Agent', '').lower()
        mobile_keywords = ['mobile', 'android', 'iphone', 'ipad', 'blackberry', 'windows phone']

        # 화면 크기 기반 추가 감지 (쿼리 파라미터로)
        screen_width = request.args.get('screen_width')
        if screen_width:
            try:
                width = int(screen_width)
                if width <= 768:  # 모바일 기준 너비
                    return True
            except ValueError:
                pass

        # User-Agent 기반 감지
        return any(keyword in user_agent for keyword in mobile_keywords)

    if request.method == "POST":
        user_id   = request.form["user_id"]
        password  = request.form["password"]
        login_mode = request.form.get("login_mode", "dashboard")  # 'dashboard' 또는 'adcanvas'
        client    = bigquery.Client()

        # 1) 사용자 인증
        try:
            query = """
                SELECT *
                FROM `ngn_dataset.user_accounts`
                WHERE user_id = @user_id
                  AND password = @password
                  AND status IN ('approved', 'admin')
            """
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("user_id", "STRING", user_id),
                    bigquery.ScalarQueryParameter("password", "STRING", password),
                ]
            )
            result = list(client.query(query, job_config=job_config).result())
        except Exception as e:
            print(f"[ERROR] 유저 쿼리 실패: {e}")
            # 모바일인 경우 모바일 로그인 페이지로 에러 표시
            if is_mobile_device():
                return render_template("mobile/login.html",
                                       error="내부 오류가 발생했습니다.")
            return render_template("login.html",
                                   error="내부 오류가 발생했습니다.",
                                   active_tab=login_mode)

        if not result:
            # 모바일인 경우 모바일 로그인 페이지로 에러 표시
            if is_mobile_device():
                return render_template("mobile/login.html",
                                       error="아이디 또는 비밀번호가 올바르지 않습니다.")
            return render_template("login.html",
                                   error="아이디 또는 비밀번호가 올바르지 않습니다.",
                                   active_tab=login_mode)

        # 2) 세션 저장
        session["user_id"]      = user_id
        session["is_demo_user"] = (user_id.lower() == "guest")

        # 3) 회사 목록
        company_names: list[str] = []
        try:
            if session["is_demo_user"]:
                company_names = ["demo"]
            else:
                company_query = """
                    SELECT company_name
                    FROM `ngn_dataset.user_company_map`
                    WHERE user_id = @user_id
                """
                company_job_config = bigquery.QueryJobConfig(
                    query_parameters=[
                        bigquery.ScalarQueryParameter("user_id", "STRING", user_id),
                    ]
                )
                rows = client.query(company_query, job_config=company_job_config).result()
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
            # 모바일인 경우 모바일 로그인 페이지로 에러 표시
            if is_mobile_device():
                return render_template("mobile/login.html",
                                       error="회사 목록을 불러올 수 없습니다.")
            return render_template("login.html",
                                   error="회사 목록을 불러올 수 없습니다.",
                                   active_tab=login_mode)

        session["company_names"] = company_names
        print(f"[INFO] 로그인 성공: {user_id} / 업체 수: {len(company_names)} / 모드: {login_mode}")

        # AdCanvas 모드인 경우 계정 선택 처리
        if login_mode == "adcanvas":
            return handle_adcanvas_login(user_id, client)

        return redirect("/")

    # GET - 모바일인 경우에만 모바일 로그인 페이지 렌더링
    if is_mobile_device():
        return render_template("mobile/login.html")

    # 웹은 원래 로그인 페이지 사용
    return render_template("login.html")


# ───────────────────────────────────────────────
#  AdCanvas 로그인 처리
# ───────────────────────────────────────────────
def handle_adcanvas_login(user_id: str, client: bigquery.Client):
    """AdCanvas 로그인 후 계정 선택 처리"""

    # 사용자의 Meta 계정 목록 조회 (account_name 컬럼이 없으므로 company_name 사용)
    try:
        query = """
            SELECT DISTINCT
                m.account_id,
                m.company_name AS account_name
            FROM `ngn_dataset.user_company_map` ucm
            JOIN `ngn_dataset.meta_account_mapping` m
                ON ucm.company_name = m.company_name
            WHERE ucm.user_id = @user_id
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("user_id", "STRING", user_id)
            ]
        )
        result = list(client.query(query, job_config=job_config).result())

        print(f"[AdCanvas] 사용자 {user_id}의 Meta 계정 수: {len(result)}")

        if len(result) == 0:
            # 계정이 없는 경우
            return render_template("login.html",
                                   error="연결된 광고 계정이 없습니다.",
                                   active_tab="adcanvas")
        elif len(result) == 1:
            # 단일 계정: 브릿지 페이지로 이동
            account_id = result[0].account_id
            print(f"[AdCanvas] 단일 계정 - 브릿지 페이지로 이동: {account_id}")
            return redirect(f"/admake?account_id={account_id}")
        else:
            # 다중 계정: 계정 선택 페이지로 이동
            session["adcanvas_accounts"] = [
                {"id": row.account_id, "name": row.account_name or f"계정 {row.account_id}"}
                for row in result
            ]
            print(f"[AdCanvas] 다중 계정 - 선택 페이지로 이동")
            return redirect("/adcanvas/select-account")

    except Exception as e:
        print(f"[ERROR] AdCanvas 계정 조회 실패: {e}")
        return render_template("login.html",
                               error="광고 계정 정보를 불러올 수 없습니다.",
                               active_tab="adcanvas")


# ───────────────────────────────────────────────
#  마지막 계정 저장 API
# ───────────────────────────────────────────────
@auth_blueprint.route("/save_last_account", methods=["POST"])
def save_last_account():
    """사용자의 마지막 선택 계정 저장"""
    account_id = (request.json or {}).get("account_id")
    user_id = session.get("user_id")

    if not user_id or not account_id:
        return {"status": "error", "message": "Missing user_id or account_id"}, 400

    session["last_adcanvas_account"] = account_id
    print(f"[AdCanvas] 마지막 계정 저장: user={user_id}, account={account_id}")
    return {"status": "ok"}

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
    token_url = "https://graph.facebook.com/v24.0/oauth/access_token"
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
        url    = "https://graph.facebook.com/v24.0/me/businesses"
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
        url    = f"https://graph.facebook.com/v24.0/{catalog_id}/permissions"
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
