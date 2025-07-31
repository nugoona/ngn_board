
# File: ngn_wep/dashboard/handlers/mobile_handler.py
import time
import datetime
import re
from flask import Blueprint, render_template, session, redirect, url_for, jsonify, request
from functools import wraps
from google.cloud import bigquery
from concurrent.futures import ThreadPoolExecutor

# 📦 웹버전과 동일한 서비스 함수 임포트
from ..services.performance_summary_new import get_performance_summary_new
from ..services.cafe24_service import get_cafe24_product_sales, get_cafe24_sales_data
from ..services.ga4_source_summary import get_ga4_source_summary
from ..services.meta_ads_service import get_meta_ads_data
from ..services.meta_ads_insight import get_meta_account_list_filtered, get_meta_ads_insight_table
from ..services.meta_ads_preview import get_meta_ads_preview_list

# 모바일 전용 함수 제거 - performance_summary_new.py에서 통합으로 가져옴

# ─────────────────────────────────────────────
# 1) 모바일 블루프린트 생성
# ─────────────────────────────────────────────
mobile_blueprint = Blueprint("mobile", __name__)

# ─────────────────────────────────────────────
# 2) 로그인 체크 데코레이터 (웹버전과 동일)
# ─────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function

# ─────────────────────────────────────────────
# 3) 웹버전과 동일한 필터 함수
# ─────────────────────────────────────────────
def get_start_end_dates(period, start_date=None, end_date=None):
    """ ✅ 필터링 기간을 결정하는 함수 (KST 기준 적용) - 웹버전과 동일 """
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
        "manual": (start_date, end_date) if start_date and end_date else (now_kst.strftime("%Y-%m-%d"), now_kst.strftime("%Y-%m-%d"))
    }

    return date_map.get(period, date_map["today"])

# ─────────────────────────────────────────────
# 4) 메타 광고 데이터 처리 함수 (모바일 전용)
# ─────────────────────────────────────────────
def process_meta_ads_for_mobile(meta_ads_data):
    """메타 광고 데이터를 모바일용으로 처리"""
    processed_data = []
    
    for row in meta_ads_data:
        processed_row = row.copy()
        
        # 캠페인명 처리: "전환", "도달", "유입" 키워드만 추출
        campaign_name = row.get('campaign_name', '')
        if campaign_name:
            if '전환' in campaign_name:
                processed_row['campaign_name'] = '전환'
            elif '도달' in campaign_name:
                processed_row['campaign_name'] = '도달'
            elif '유입' in campaign_name:
                processed_row['campaign_name'] = '유입'
            else:
                processed_row['campaign_name'] = campaign_name
        
        # 광고명 처리: [ ] 부분 제거
        ad_name = row.get('ad_name', '')
        if ad_name:
            # [ ] 패턴을 모두 제거
            cleaned_ad_name = re.sub(r'\[[^\]]*\]', '', ad_name).strip()
            processed_row['ad_name'] = cleaned_ad_name
        
        processed_data.append(processed_row)
    
    return processed_data

# ─────────────────────────────────────────────
# 5) 모바일 대시보드 라우트
# ─────────────────────────────────────────────
@mobile_blueprint.route("/dashboard")
@login_required
def dashboard():
    """모바일 대시보드 메인 페이지"""
    print(f"[MOBILE] 대시보드 페이지 접근 - user_id: {session.get('user_id')}")
    return render_template("mobile/dashboard.html",
                         company_names=session.get("company_names", []),
                         now=datetime.datetime.now())

# ─────────────────────────────────────────────
# 6) 모바일 데이터 API (웹버전과 동일한 병렬 처리)
# ─────────────────────────────────────────────
@mobile_blueprint.route("/get_data", methods=["POST"])
@login_required
def get_data():
    """모바일 대시보드 데이터 조회 - 웹버전과 동일한 병렬 처리"""
    t0 = time.time()
    try:
        data = request.get_json()
        user_id = session.get("user_id")
        raw_company_name = data.get("company_name", "all")
        data_type = (data.get("data_type", "all") or "").strip().lower()
        data_type = data_type.replace("-", "_")
        data_type = data_type.replace(" ", "_")

        # ✅ company_name 처리 (웹버전과 동일)
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
                return jsonify({
                    "status": "success",
                    "message": "demo 업체 접근 불가",
                    "performance_summary": [],
                    "cafe24_product_sales": [],
                    "ga4_source_summary": []
                }), 200
            company_name = name

        # ✅ 공통 파라미터 처리 (웹버전과 동일)
        period = str(data.get("period", "today")).strip()
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        
        # 안전한 int 변환
        try:
            page = int(data.get("page", 1)) if isinstance(data.get("page"), (int, str)) else 1
        except (ValueError, TypeError):
            page = 1
            
        try:
            limit = int(data.get("limit", 5)) if isinstance(data.get("limit"), (int, str)) else 5
        except (ValueError, TypeError):
            limit = 5

        # ✅ 기간 필터 처리 (웹버전과 동일)
        if data_type not in ["monthly_net_sales_visitors", "platform_sales_monthly"]:
            if not period:
                period = "manual"
            start_date, end_date = get_start_end_dates(period, start_date, end_date)

        print(f"[MOBILE] 🔄 데이터 요청 시작 - company_name={company_name}, period={period}, "
              f"start_date={start_date}, end_date={end_date}, data_type={data_type}")

        response_data = {"status": "success"}
        timing_log = {}
        fetch_tasks = []
        results_map = {}

        # 🚀 웹버전과 동일한 ThreadPoolExecutor 사용
        with ThreadPoolExecutor() as executor:
            # 1. Performance Summary (모바일 최우선)
            if data_type in ["performance_summary", "all"]:
                def fetch_performance():
                    t1 = time.time()
                    # 🚀 캐시 무효화 파라미터 처리
                    cache_buster = data.get('_cache_buster')
                    performance_data = get_performance_summary_new(
                        company_name=company_name,
                        start_date=start_date,
                        end_date=end_date,
                        user_id=user_id
                    )
                    t2 = time.time()
                    timing_log["performance_summary"] = round(t2-t1, 3)
                    return ("performance_summary", performance_data)
                fetch_tasks.append(executor.submit(fetch_performance))

            # 2. Cafe24 Product Sales (모바일용 상위 5개)
            if data_type in ["cafe24_product_sales", "all"]:
                def fetch_cafe24_products():
                    t1 = time.time()
                    result = get_cafe24_product_sales(
                        company_name, period, start_date, end_date,
                        sort_by="item_product_sales", limit=5, page=1, user_id=user_id
                    )
                    t2 = time.time()
                    timing_log["cafe24_product_sales"] = round(t2-t1, 3)
                    return ("cafe24_product_sales", result)
                fetch_tasks.append(executor.submit(fetch_cafe24_products))

            # 3. GA4 Source Summary (모바일용 상위 5개)
            if data_type in ["ga4_source_summary", "all"]:
                def fetch_ga4_sources():
                    t1 = time.time()
                    cache_buster = data.get('_cache_buster')
                    ga4_data = get_ga4_source_summary(company_name, start_date, end_date, limit=100, _cache_buster=cache_buster)
                    # not set 제외하고 상위 5개만
                    filtered_sources = [row for row in ga4_data if row.get("source", "").lower() != "not set" and row.get("source", "").lower() != "(not set)"][:5]
                    t2 = time.time()
                    timing_log["ga4_source_summary"] = round(t2-t1, 3)
                    return ("ga4_source_summary", filtered_sources)
                fetch_tasks.append(executor.submit(fetch_ga4_sources))



            # 🚀 모든 작업이 완료될 때까지 대기
            for future in fetch_tasks:
                try:
                    result_type, result_data = future.result()
                    results_map[result_type] = result_data
                except Exception as e:
                    print(f"[MOBILE] ❌ {result_type} 데이터 로딩 실패: {e}")
                    results_map[result_type] = []

        # 📊 결과 데이터 정리
        if "performance_summary" in results_map:
            performance_data = results_map["performance_summary"]
            if performance_data and len(performance_data) > 0:
                response_data["performance_summary"] = performance_data
                print(f"[MOBILE] ✅ Performance Summary 성공: {len(performance_data)}개")
                print(f"[MOBILE] 📊 Performance Summary 첫 번째 행: {performance_data[0] if performance_data else 'None'}")
            else:
                response_data["performance_summary"] = []
                print(f"[MOBILE] ⚠️ Performance Summary 데이터 없음")
        else:
            response_data["performance_summary"] = []

        if "cafe24_product_sales" in results_map:
            cafe24_result = results_map["cafe24_product_sales"]
            if cafe24_result and "rows" in cafe24_result:
                response_data["cafe24_product_sales"] = cafe24_result.get("rows", [])[:5]
                response_data["cafe24_product_sales_total_count"] = cafe24_result.get("total_count", 0)
                print(f"[MOBILE] ✅ Cafe24 Product Sales 성공: {len(response_data['cafe24_product_sales'])}개")
            else:
                response_data["cafe24_product_sales"] = []
                response_data["cafe24_product_sales_total_count"] = 0
                print(f"[MOBILE] ⚠️ Cafe24 Product Sales 데이터 없음")

        if "ga4_source_summary" in results_map:
            response_data["ga4_source_summary"] = results_map["ga4_source_summary"]
            print(f"[MOBILE] ✅ GA4 Source Summary 성공: {len(response_data['ga4_source_summary'])}개")



        # 🚀 Meta Ads 데이터 처리 (웹버전과 동일한 별도 조건문)
        if data_type in ["meta_ads", "all"]:
            t1 = time.time()
            meta_data = get_meta_ads_data(company_name, period, start_date, end_date, "summary", "desc")
            # 모바일용 데이터 처리
            processed_meta_data = process_meta_ads_for_mobile(meta_data[:10])
            response_data["meta_ads"] = processed_meta_data
            t2 = time.time()
            timing_log["meta_ads"] = round(t2-t1, 3)
            print(f"[MOBILE] ✅ Meta Ads 성공: {len(processed_meta_data)}개")

        # 🚀 성능 정보 추가
        response_data["performance"] = {
            "total_execution_time": round(time.time() - t0, 3),
            "individual_times": timing_log,
            "optimization_version": "mobile_web_aligned_v2"
        }

        print(f"[MOBILE] ✅ 응답 완료 - 소요시간: {time.time() - t0:.3f}초")
        print(f"[MOBILE] 📊 최종 응답 데이터: {response_data}")
        return jsonify(response_data)

    except Exception as e:
        print(f"[MOBILE] ❌ 전체 API 오류: {e}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "last_updated": datetime.datetime.now().isoformat()
        }), 500

# ─────────────────────────────────────────────
# 7) 메타 광고 계정 목록 API (웹버전과 동일)
# ─────────────────────────────────────────────
@mobile_blueprint.route("/get_meta_accounts", methods=["POST"])
@login_required
def get_meta_accounts():
    """메타 광고 계정 목록 조회 - 웹버전과 동일"""
    try:
        data = request.get_json() or {}
        user_id = session.get("user_id")
        
        raw_company_name = data.get("company_name", "all")
        if raw_company_name == "all":
            company_name = ["demo"] if user_id == "demo" else [
                name for name in session.get("company_names", []) if name.lower() != "demo"
            ]
        else:
            company_name = str(raw_company_name).strip().lower()
        
        # 메타 광고 계정 목록 조회 (웹버전과 동일)
        accounts = get_meta_account_list_filtered(company_name)
        
        return jsonify({
            "status": "success",
            "meta_accounts": accounts
        })
        
    except Exception as e:
        print(f"[MOBILE] 메타 광고 계정 목록 오류: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

# ─────────────────────────────────────────────
# 8) 메타 광고별 성과 API (광고 탭 기준)
# ─────────────────────────────────────────────
@mobile_blueprint.route("/get_meta_ads_by_account", methods=["POST"])
@login_required
def get_meta_ads_by_account():
    """특정 계정의 메타 광고별 성과 조회 - 광고 탭 기준"""
    try:
        data = request.get_json() or {}
        user_id = session.get("user_id")
        
        account_id = data.get("account_id")
        if not account_id:
            return jsonify({"status": "error", "message": "account_id 누락"}), 400
        
        period = str(data.get("period", "today")).strip()
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        start_date, end_date = get_start_end_dates(period, start_date, end_date)
        
        # company_name 설정 (웹버전과 동일한 로직)
        raw_company_name = data.get("company_name", "all")
        if raw_company_name == "all":
            company_name = ["demo"] if user_id == "demo" else [
                name for name in session.get("company_names", []) if name.lower() != "demo"
            ]
        else:
            company_name = str(raw_company_name).strip().lower()
        
        # 페이지네이션 파라미터 추출 (백엔드에서는 모든 데이터 가져오기)
        page = data.get("page", 1)
        limit = None  # 백엔드에서는 모든 데이터 가져오기 (프론트엔드에서 페이지네이션 처리)
        
        # 메타 광고별 성과 조회 (광고 탭 기준)
        print(f"[MOBILE] 📊 메타 광고별 성과 파라미터: company_name={company_name}, account_id={account_id}, start_date={start_date}, end_date={end_date}, page={page}, limit={limit}")
        
        ads_data = get_meta_ads_insight_table(
            level="ad",
            company_name=company_name,
            start_date=start_date,
            end_date=end_date,
            account_id=account_id,
            limit=limit,  # None으로 설정하여 모든 데이터 가져오기
            page=1  # 항상 첫 페이지로 가져오기 (프론트엔드에서 페이지네이션 처리)
        )
        
        # 페이지네이션된 결과 처리
        if isinstance(ads_data, dict) and "rows" in ads_data:
            # 페이지네이션된 결과 (전체 개수 포함)
            rows = ads_data.get("rows", [])
            total_count = ads_data.get("total_count", len(rows))
            print(f"[MOBILE] 📊 메타 광고별 성과 서비스 결과: {len(rows)}개 / 전체: {total_count}개")
            
            # 모바일용 데이터 처리
            processed_ads_data = process_meta_ads_for_mobile(rows)
            
            return jsonify({
                "status": "success",
                "meta_ads_by_account": processed_ads_data,
                "meta_ads_total_count": total_count
            })
        else:
            # 기존 형식 (페이지네이션 없음)
            print(f"[MOBILE] 📊 메타 광고별 성과 서비스 결과: {len(ads_data) if ads_data else 0}개")
            
            # 모바일용 데이터 처리
            processed_ads_data = process_meta_ads_for_mobile(ads_data[:10])
            
            return jsonify({
                "status": "success",
                "meta_ads_by_account": processed_ads_data
            })
        
    except Exception as e:
        print(f"[MOBILE] 메타 광고별 성과 오류: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

# ─────────────────────────────────────────────
# 9) LIVE 광고 미리보기 API (웹버전과 동일)
# ─────────────────────────────────────────────
@mobile_blueprint.route("/get_live_ads", methods=["POST"])
@login_required
def get_live_ads():
    """특정 계정의 LIVE 광고 미리보기 조회 - 웹버전과 동일"""
    try:
        data = request.get_json() or {}
        account_id = data.get("account_id")
        
        if not account_id:
            return jsonify({"status": "error", "message": "account_id 누락"}), 400
        
        # LIVE 광고 미리보기 조회 (웹버전과 동일)
        live_ads = get_meta_ads_preview_list(account_id)
        
        return jsonify({
            "status": "success",
            "live_ads": live_ads[:5]  # 상위 5개만
        })
        
    except Exception as e:
        print(f"[MOBILE] LIVE 광고 미리보기 오류: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500 