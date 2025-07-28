# File: ngn_wep/dashboard/handlers/mobile_handler.py
import time
import datetime
from flask import Blueprint, render_template, session, redirect, url_for, jsonify, request
from functools import wraps
from google.cloud import bigquery

# 📦 기존 서비스 함수 임포트 (재사용)
from ..services.performance_summary import get_performance_summary
from ..services.cafe24_service import get_cafe24_product_sales
from ..services.ga4_source_summary import get_ga4_source_summary
from ..services.meta_ads_service import get_meta_ads_data
from ..services.meta_ads_insight import get_meta_account_list_filtered

# ─────────────────────────────────────────────
# 1) 모바일 블루프린트 생성
# ─────────────────────────────────────────────
mobile_blueprint = Blueprint("mobile", __name__)

# ─────────────────────────────────────────────
# 2) 로그인 체크 데코레이터 (기존과 동일)
# ─────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function

# ─────────────────────────────────────────────
# 3) 기존 필터 함수 재사용
# ─────────────────────────────────────────────
def get_start_end_dates(period, start_date=None, end_date=None):
    """ ✅ 필터링 기간을 결정하는 함수 (KST 기준 적용) - 기존과 동일 """
    now_utc = datetime.datetime.utcnow()
    now_kst = now_utc + datetime.timedelta(hours=9)

    date_map = {
        "today": (now_kst.strftime("%Y-%m-%d"), now_kst.strftime("%Y-%m-%d")),
        "yesterday": (
            (now_kst - datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
            (now_kst - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        ),
        "last7days": (
            (now_kst - datetime.timedelta(days=7)).strftime("%Y-%m-%d"),
            (now_kst - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        ),
        "current_month": (
            now_kst.replace(day=1).strftime("%Y-%m-%d"),
            now_kst.strftime("%Y-%m-%d")
        ),
        "last_month": (
            (now_kst.replace(day=1) - datetime.timedelta(days=1)).replace(day=1).strftime("%Y-%m-%d"),
            (now_kst.replace(day=1) - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        ),
        "last30days": (
            (now_kst - datetime.timedelta(days=30)).strftime("%Y-%m-%d"),
            (now_kst - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        ),
        "last90days": (
            (now_kst - datetime.timedelta(days=90)).strftime("%Y-%m-%d"),
            (now_kst - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        ),
        "custom": (start_date, end_date) if start_date and end_date else (now_kst.strftime("%Y-%m-%d"), now_kst.strftime("%Y-%m-%d"))
    }

    return date_map.get(period, date_map["today"])

# ─────────────────────────────────────────────
# 4) 모바일 대시보드 라우트
# ─────────────────────────────────────────────
@mobile_blueprint.route("/dashboard")
@login_required
def dashboard():
    """모바일 대시보드 메인 페이지"""
    return render_template("mobile/dashboard.html",
                         company_names=session.get("company_names", []))

# ─────────────────────────────────────────────
# 5) 모바일 데이터 API (기존 서비스 함수 재사용)
# ─────────────────────────────────────────────
@mobile_blueprint.route("/get_data", methods=["POST"])
@login_required
def get_data():
    """모바일 전용 경량 데이터 API - 기존 서비스 함수 재사용"""
    t0 = time.time()
    try:
        data = request.get_json() or {}
        user_id = session.get("user_id")
        
        # ✅ 기존과 동일한 company_name 처리
        raw_company_name = data.get("company_name", "all")
        if raw_company_name == "all":
            company_name = ["demo"] if user_id == "demo" else [
                name for name in session.get("company_names", []) if name.lower() != "demo"
            ]
        elif isinstance(raw_company_name, list):
            company_name = ["demo"] if user_id == "demo" else [
                name.lower() for name in raw_company_name if name.lower() != "demo"
            ]
        else:
            name = str(raw_company_name).strip().lower()
            if name == "demo" and user_id != "demo":
                return jsonify({"status": "error", "message": "demo 업체 접근 불가"}), 403
            company_name = name

        # ✅ 기존과 동일한 기간 필터 처리
        period = str(data.get("period", "last7days")).strip()  # 모바일 기본값: 최근 7일
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        start_date, end_date = get_start_end_dates(period, start_date, end_date)

        print(f"[MOBILE] 요청 필터 - company_name={company_name}, period={period}, "
              f"start_date={start_date}, end_date={end_date}")

        # ✅ 기존 서비스 함수 호출하여 데이터 수집
        response_data = {
            "status": "success",
            "last_updated": datetime.datetime.now().isoformat()
        }

        # 1. KPI 데이터 (Performance Summary에서 추출)
        try:
            performance_data = get_performance_summary(
                company_name=company_name,
                start_date=start_date,
                end_date=end_date,
                user_id=user_id
            )
            
            # KPI 데이터 추출 (첫 번째 행 기준)
            if performance_data:
                first_row = performance_data[0]
                response_data["kpi"] = {
                    "revenue": float(first_row.get("site_revenue", 0)),
                    "visitors": int(first_row.get("total_visitors", 0)),
                    "ad_spend": float(first_row.get("ad_spend", 0)),
                    "purchases": int(first_row.get("total_purchases", 0)),
                    "roas": float(first_row.get("roas_percentage", 0))
                }
            else:
                response_data["kpi"] = {"revenue": 0, "visitors": 0, "ad_spend": 0, "purchases": 0, "roas": 0}
        except Exception as e:
            print(f"[MOBILE] KPI 데이터 오류: {e}")
            response_data["kpi"] = {"revenue": 0, "visitors": 0, "ad_spend": 0, "purchases": 0, "roas": 0}

        # 2. 사이트 성과 (Performance Summary에서 추출)
        try:
            if performance_data:
                first_row = performance_data[0]
                response_data["site_perf"] = {
                    "orders": int(first_row.get("total_purchases", 0)),
                    "product_sales": float(first_row.get("site_revenue", 0))
                }
            else:
                response_data["site_perf"] = {"orders": 0, "product_sales": 0}
        except Exception as e:
            print(f"[MOBILE] 사이트 성과 데이터 오류: {e}")
            response_data["site_perf"] = {"orders": 0, "product_sales": 0}

        # 3. 상위 상품 (Cafe24 Product Sales)
        try:
            product_data = get_cafe24_product_sales(
                company_name, period, start_date, end_date, 
                "summary", "desc", 10, 1, user_id  # 상위 10개만
            )
            response_data["top_products"] = [
                {"name": row.get("item_product_name", ""), "qty": int(row.get("item_qty", 0))}
                for row in product_data.get("rows", [])[:10]  # 최대 10개
            ]
        except Exception as e:
            print(f"[MOBILE] 상위 상품 데이터 오류: {e}")
            response_data["top_products"] = []

        # 4. 상위 소스 (GA4 Source Summary)
        try:
            ga4_data = get_ga4_source_summary(company_name, start_date, end_date, user_id)
            # not set 제외하고 상위 5개만
            filtered_sources = [row for row in ga4_data if row.get("source", "").lower() != "not set"][:5]
            response_data["top_sources"] = [
                {"source": row.get("source", ""), "visits": int(row.get("visits", 0))}
                for row in filtered_sources
            ]
        except Exception as e:
            print(f"[MOBILE] 상위 소스 데이터 오류: {e}")
            response_data["top_sources"] = []

        # 5. 메타 광고 성과
        try:
            meta_data = get_meta_ads_data(company_name, period, start_date, end_date, "summary", "desc")
            # 필요한 필드만 추출
            response_data["meta_ads"] = {
                "rows": [
                    {
                        "campaign": row.get("company_name", ""),
                        "ad": row.get("company_name", ""),  # 임시로 company_name 사용
                        "spend": float(row.get("total_spend", 0)),
                        "cpc": float(row.get("cpc", 0)),
                        "purchases": int(row.get("total_purchases", 0)),
                        "roas": float(row.get("roas", 0))
                    }
                    for row in meta_data[:20]  # 최대 20개
                ],
                "total": {
                    "spend": sum(float(row.get("total_spend", 0)) for row in meta_data),
                    "purchases": sum(int(row.get("total_purchases", 0)) for row in meta_data),
                    "roas": sum(float(row.get("roas", 0)) for row in meta_data) / len(meta_data) if meta_data else 0
                }
            }
        except Exception as e:
            print(f"[MOBILE] 메타 광고 데이터 오류: {e}")
            response_data["meta_ads"] = {"rows": [], "total": {"spend": 0, "purchases": 0, "roas": 0}}

        # 6. LIVE 광고 미리보기 (1단계에서는 빈 배열)
        response_data["live_ads"] = []

        print(f"[MOBILE] 응답 완료 - 소요시간: {time.time() - t0:.3f}초")
        return jsonify(response_data)

    except Exception as e:
        print(f"[MOBILE] 전체 API 오류: {e}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "last_updated": datetime.datetime.now().isoformat()
        }), 500 