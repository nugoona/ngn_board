# File: ngn_wep/dashboard/app.py
import time, logging
_boot = time.time()                               # ─────────── 부팅 시간 측정 시작

import os
from pathlib import Path
from datetime import timedelta
from flask import Flask, render_template, session, redirect, url_for
from dotenv import load_dotenv

# ─────────────────────────────────────────────
# 1) 환경변수(.env) 로딩  ─ 절대경로 자동 계산
# ─────────────────────────────────────────────
BASE_DIR  = Path(__file__).resolve().parents[2]   # ~/ngn_board
ENV_PATH  = BASE_DIR / "config" / "ngn.env"       # ~/ngn_board/config/ngn.env

if ENV_PATH.exists():
    load_dotenv(ENV_PATH)                         # ✅ 실제 파일 경로로 로드
    print(f"[ENV] .env 로드 완료: {ENV_PATH}")
else:
    print(f"[ENV] ⚠️ .env 파일이 없습니다: {ENV_PATH}")

# 시스템 토큰 존재 여부를 미리 로그
TOKEN_LEN = len(os.getenv("META_SYSTEM_USER_TOKEN") or "")
print(f"[ENV] META_SYSTEM_USER_TOKEN length: {TOKEN_LEN}")

# ─────────────────────────────────────────────
# 2) 로깅 설정 (INFO 이상)
# ─────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 3) 블루프린트 임포트
# ─────────────────────────────────────────────
from .handlers.accounts_handler   import accounts_blueprint
from .handlers.data_handler       import data_blueprint
from .handlers.auth_handler       import auth_blueprint
from .services.meta_demo_handler  import meta_demo_blueprint

# ─────────────────────────────────────────────
# 4) Flask 앱 생성 & 기본 설정
# ─────────────────────────────────────────────
import os
static_folder_path = os.path.join(os.path.dirname(__file__), 'static')
app = Flask(__name__, 
           static_folder=static_folder_path,
           static_url_path='/static')
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret")
app.permanent_session_lifetime = timedelta(hours=8)
app.config["SESSION_PERMANENT"] = True

# 정적 파일 경로 디버깅
print(f"[DEBUG] Flask static folder: {static_folder_path}")
print(f"[DEBUG] Static folder exists: {os.path.exists(static_folder_path)}")
print(f"[DEBUG] x.png exists: {os.path.exists(os.path.join(static_folder_path, 'img', 'x.png'))}")
print(f"[DEBUG] favicon.ico exists: {os.path.exists(os.path.join(static_folder_path, 'img', 'favicon.ico'))}")

# 캐시 헤더 제거 - 버전 파라미터로 대체

# ─────────────────────────────────────────────
# 5) Google Cloud 인증 경로 확인
# ─────────────────────────────────────────────
gcp_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
if gcp_path and os.path.exists(gcp_path):
    LOG.info("GCP 인증 경로 적용됨: %s", gcp_path)
else:
    LOG.error("GCP 인증 파일이 존재하지 않거나 설정되지 않음: %s", gcp_path)

# ─────────────────────────────────────────────
# 6) 라우트 정의
# ─────────────────────────────────────────────
@app.route("/")
def index():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    return render_template("index.html",
                           company_names=session.get("company_names", []))

@app.route("/ads")
def ads_page():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    return render_template("ads_page.html",
                           company_names=session.get("company_names", []))

@app.route("/privacy")
def privacy():
    return render_template("privacy.html")

@app.route("/delete-info")
def delete_info():
    return render_template("delete_info.html")

@app.route("/terms")
def terms():
    return render_template("terms.html")

# 정적 파일 테스트 라우트
@app.route("/test-static")
def test_static():
    return """
    <h1>정적 파일 테스트</h1>
    <p>favicon.ico: <img src="/static/img/favicon.ico" width="32" height="32"></p>
    <p>x.png: <img src="/static/img/x.png" width="32" height="32"></p>
    <p>favicon.ico 직접 링크: <a href="/static/img/favicon.ico">favicon.ico</a></p>
    <p>x.png 직접 링크: <a href="/static/img/x.png">x.png</a></p>
    """

# /login, /logout → auth 블루프린트로 리디렉트
@app.route("/login")
def login_redirect():
    return redirect(url_for("auth.login"))

@app.route("/logout")
def logout_redirect():
    return redirect(url_for("auth.logout"))

# ─────────────────────────────────────────────
# 7) 블루프린트 등록
# ─────────────────────────────────────────────
app.register_blueprint(accounts_blueprint,  url_prefix="/accounts")
app.register_blueprint(data_blueprint,      url_prefix="/dashboard")
app.register_blueprint(auth_blueprint,      url_prefix="/auth")
app.register_blueprint(meta_demo_blueprint, url_prefix="/meta-api")

# ─────────────────────────────────────────────
# 8) 부팅 완료 로그
# ─────────────────────────────────────────────
LOG.info("⭐ app import done in %.1fs", time.time() - _boot)

# ─────────────────────────────────────────────
# 9) 개발 모드 직접 실행 (로컬)
# ─────────────────────────────────────────────
if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_ENV", "production") == "development"
    LOG.info("Flask 실행 - 디버그 모드: %s", debug_mode)
    app.run(host="0.0.0.0", port=8080, debug=debug_mode)
