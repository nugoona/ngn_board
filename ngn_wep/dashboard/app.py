# File: ngn_wep/dashboard/app.py
import time, logging
_boot = time.time()                               # ─────────── 부팅 시간 측정 시작

import os
from pathlib import Path
from datetime import timedelta
from flask import Flask, render_template, session, redirect, url_for, request, flash
from dotenv import load_dotenv

# ─────────────────────────────────────────────
# 1) 환경변수(.env) 로딩 (로컬 개발용, Cloud Run에서는 환경변수 사용)
# ─────────────────────────────────────────────
from dotenv import find_dotenv
env_file = find_dotenv()
if env_file:
    load_dotenv(env_file, override=False)
    print(f"[ENV] .env 로드 완료: {env_file}")
else:
    print(f"[ENV] .env 파일 없음 (Cloud Run 환경변수 사용)")

# 시스템 토큰 존재 여부를 미리 로그
TOKEN_LEN = len(os.getenv("META_SYSTEM_USER_TOKEN") or "")
print(f"[ENV] META_SYSTEM_USER_TOKEN length: {TOKEN_LEN}")

# ─────────────────────────────────────────────
# 2) 로깅 설정 (INFO 이상)
# ─────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 3) Cloud Run 환경변수 처리 (블루프린트 임포트 전)
# ─────────────────────────────────────────────
# ✅ Cloud Run에서는 키 파일 대신 런타임 서비스계정(ADC)을 사용
# GOOGLE_APPLICATION_CREDENTIALS 환경변수가 설정되어 있으면 제거하여 ADC 사용
if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
    # 키 파일 경로로 보이는 경우 제거하여 ADC 사용
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_path and not os.path.exists(creds_path):
        os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
        print("[ENV] Cloud Run 환경 감지 - GOOGLE_APPLICATION_CREDENTIALS 제거, ADC 사용")

# ─────────────────────────────────────────────
# 4) 블루프린트 임포트
# ─────────────────────────────────────────────
from .handlers.accounts_handler   import accounts_blueprint
from .handlers.data_handler       import data_blueprint
from .handlers.auth_handler       import auth_blueprint
from .services.meta_demo_handler  import meta_demo_blueprint
from .handlers.mobile_handler     import mobile_blueprint

# ─────────────────────────────────────────────
# 5) Flask 앱 생성 & 기본 설정
# ─────────────────────────────────────────────

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
# 6) Google Cloud 인증 확인 (ADC 사용)
# ─────────────────────────────────────────────
# Cloud Run에서는 ADC(Application Default Credentials) 사용
LOG.info("GCP 인증: ADC(Application Default Credentials) 사용")

# ─────────────────────────────────────────────
# 6) 모바일 디바이스 감지 함수
# ─────────────────────────────────────────────
def is_mobile_device():
    """모바일 디바이스인지 확인 - 개선된 버전"""
    user_agent = request.headers.get('User-Agent', '').lower()
    
    # 확장된 모바일 키워드 목록
    mobile_keywords = [
        'mobile', 'android', 'iphone', 'ipad', 'blackberry', 'windows phone',
        'opera mini', 'opera mobi', 'mobile safari', 'mobile chrome',
        'samsung', 'lg', 'huawei', 'xiaomi', 'oneplus', 'motorola',
        'nexus', 'pixel', 'galaxy', 'note', 'edge', 'plus',
        'kindle', 'nook', 'tablet', 'phone', 'smartphone',
        'chrome mobile', 'firefox mobile', 'safari mobile'
    ]
    
    # 디버깅을 위한 로그 추가
    print(f"[MOBILE DETECTION] User-Agent: {user_agent}")
    print(f"[MOBILE DETECTION] Mobile keywords found: {[kw for kw in mobile_keywords if kw in user_agent]}")
    
    # 1. 화면 크기 기반 감지 (쿼리 파라미터로)
    screen_width = request.args.get('screen_width')
    if screen_width:
        try:
            width = int(screen_width)
            if width <= 768:  # 모바일 기준 너비
                print(f"[MOBILE DETECTION] Screen width detected: {width}px (mobile)")
                return True
        except ValueError:
            pass
    
    # 2. User-Agent 기반 감지 (개선된 키워드)
    is_mobile_ua = any(keyword in user_agent for keyword in mobile_keywords)
    
    # 3. 추가 모바일 감지: Accept 헤더 확인
    accept_header = request.headers.get('Accept', '').lower()
    is_mobile_accept = 'application/vnd.wap.xhtml+xml' in accept_header or 'text/vnd.wap.wml' in accept_header
    
    # 4. 추가 모바일 감지: 특정 모바일 브라우저 패턴
    mobile_patterns = [
        r'mozilla/.*mobile',
        r'mozilla/.*android.*mobile',
        r'mozilla/.*iphone.*mobile',
        r'mozilla/.*ipad.*mobile',
        r'chrome/.*mobile',
        r'firefox/.*mobile',
        r'safari/.*mobile',
        r'android.*mobile',
        r'iphone.*mobile',
        r'ipad.*mobile'
    ]
    
    import re
    is_mobile_pattern = any(re.search(pattern, user_agent, re.IGNORECASE) for pattern in mobile_patterns)
    
    # 5. 추가 모바일 감지: Viewport 확인 (클라이언트 사이드에서 전송된 경우)
    viewport_width = request.args.get('viewport_width')
    if viewport_width:
        try:
            width = int(viewport_width)
            if width <= 768:
                print(f"[MOBILE DETECTION] Viewport width detected: {width}px (mobile)")
                return True
        except ValueError:
            pass
    
    # 6. 최종 모바일 판단
    is_mobile = is_mobile_ua or is_mobile_accept or is_mobile_pattern
    
    print(f"[MOBILE DETECTION] UA-based: {is_mobile_ua}, Accept-based: {is_mobile_accept}, Pattern-based: {is_mobile_pattern}")
    print(f"[MOBILE DETECTION] Final Result: {is_mobile}")
    
    return is_mobile

# ─────────────────────────────────────────────
# 7) 헬스체크 엔드포인트 (Cloud Scheduler 워밍업용)
# ─────────────────────────────────────────────
@app.route("/health")
def health():
    return "ok", 200

# ─────────────────────────────────────────────
# 8) 라우트 정의
# ─────────────────────────────────────────────
@app.route("/")
def index():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    
    # 강제 모바일 버전 요청 확인
    force_mobile = request.args.get('mobile') == 'true'
    
    # 모바일 디바이스인 경우 또는 강제 모바일 요청인 경우 모바일 버전으로 리다이렉트
    if is_mobile_device() or force_mobile:
        return redirect(url_for("mobile.dashboard"))
    
    return render_template("index.html",
                           company_names=session.get("company_names", []))

@app.route("/ads")
def ads_page():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    
    # 강제 모바일 버전 요청 확인
    force_mobile = request.args.get('mobile') == 'true'
    
    # 모바일 디바이스인 경우 또는 강제 모바일 요청인 경우 모바일 버전으로 리다이렉트
    if is_mobile_device() or force_mobile:
        return redirect(url_for("mobile.dashboard"))
    
    return render_template("ads_page.html",
                           company_names=session.get("company_names", []))

@app.route("/trend/selection")
def trend_selection_page():
    """트렌드 선택 브릿지 페이지"""
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    
    company_names = session.get("company_names", [])
    return render_template("trend_selection.html",
                           company_names=company_names)

@app.route("/trend/29cm")
def trend_29cm_page():
    """29CM 트렌드 페이지"""
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    
    # 업체 선택 확인 (월간 리포트와 동일한 방식)
    # 쿼리 파라미터에서 company_name 가져오기
    company_name = request.args.get("company_name")
    
    if not company_name or company_name == "all":
        # 업체가 선택되지 않았으면 트렌드 선택 페이지로 리다이렉트
        flash("트렌드 페이지를 보려면 먼저 사이트 성과 페이지에서 업체를 선택해주세요.", "warning")
        return redirect(url_for("trend_selection_page"))
    
    # 업체가 세션의 company_names에 포함되어 있는지 확인 (보안)
    company_names = session.get("company_names", [])
    if company_name.lower() not in [name.lower() for name in company_names]:
        # 권한이 없는 업체인 경우 트렌드 선택 페이지로 리다이렉트
        flash("접근 권한이 없는 업체입니다.", "error")
        return redirect(url_for("trend_selection_page"))
    
    return render_template("trend_page.html",
                           company_names=company_names,
                           selected_company=company_name,
                           page_type="29cm")

@app.route("/trend/ably")
def trend_ably_page():
    """Ably 트렌드 페이지"""
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    
    # 업체 선택 확인 (월간 리포트와 동일한 방식)
    # 쿼리 파라미터에서 company_name 가져오기
    company_name = request.args.get("company_name")
    
    if not company_name or company_name == "all":
        # 업체가 선택되지 않았으면 트렌드 선택 페이지로 리다이렉트
        flash("트렌드 페이지를 보려면 먼저 사이트 성과 페이지에서 업체를 선택해주세요.", "warning")
        return redirect(url_for("trend_selection_page"))
    
    # 업체가 세션의 company_names에 포함되어 있는지 확인 (보안)
    company_names = session.get("company_names", [])
    if company_name.lower() not in [name.lower() for name in company_names]:
        # 권한이 없는 업체인 경우 트렌드 선택 페이지로 리다이렉트
        flash("접근 권한이 없는 업체입니다.", "error")
        return redirect(url_for("trend_selection_page"))
    
    return render_template("trend_page.html",
                           company_names=company_names,
                           selected_company=company_name,
                           page_type="ably")

# 기존 /trend 라우트는 /trend/selection으로 리다이렉트 (하위 호환성)
@app.route("/trend")
def trend_page():
    return redirect(url_for("trend_selection_page"))

@app.route("/admake")
def admake_page():
    """ADMAKE 페이지"""
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    
    return render_template("admake_page.html",
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
# 8) 블루프린트 등록
# ─────────────────────────────────────────────
app.register_blueprint(accounts_blueprint,  url_prefix="/accounts")
app.register_blueprint(data_blueprint,      url_prefix="/dashboard")
app.register_blueprint(auth_blueprint,      url_prefix="/auth")
app.register_blueprint(meta_demo_blueprint, url_prefix="/meta-api")
app.register_blueprint(mobile_blueprint,    url_prefix="/m")

# ─────────────────────────────────────────────
# 9) 부팅 완료 로그
# ─────────────────────────────────────────────
LOG.info("⭐ app import done in %.1fs", time.time() - _boot)

# ─────────────────────────────────────────────
# 10) 개발 모드 직접 실행 (로컬)
# ─────────────────────────────────────────────
if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_ENV", "production") == "development"
    LOG.info("Flask 실행 - 디버그 모드: %s", debug_mode)
    app.run(host="0.0.0.0", port=8080, debug=debug_mode)
