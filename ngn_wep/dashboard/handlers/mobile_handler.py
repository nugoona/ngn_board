# File: ngn_wep/dashboard/handlers/mobile_handler.py
import time
import datetime
import re
from flask import Blueprint, render_template, session, redirect, url_for, jsonify, request
from functools import wraps
from google.cloud import bigquery

# 📦 웹버전과 동일한 서비스 함수 임포트
from ..services.performance_summary import get_performance_summary
from ..services.cafe24_service import get_cafe24_product_sales, get_cafe24_sales_data
from ..services.ga4_source_summary import get_ga4_source_summary
from ..services.meta_ads_service import get_meta_ads_data
from ..services.meta_ads_insight import get_meta_account_list_filtered, get_meta_ads_insight_table
from ..services.meta_ads_preview import get_meta_ads_preview_list

# 모바일 전용 함수 추가
def get_total_orders_from_cafe24(company_name, start_date, end_date, user_id=None):
    """모바일 전용: daily_cafe24_sales에서 total_orders 가져오기"""
    from google.cloud import bigquery
    
    client = bigquery.Client()
    query_params = []
    
    # 업체 필터 처리
    if isinstance(company_name, list):
        filtered_companies = [name.lower() for name in company_name]
        filtered_companies = (
            ["demo"] if user_id == "demo"
            else [name for name in filtered_companies if name != "demo"]
        )
        if not filtered_companies:
            return 0
        company_filter = "LOWER(company_name) IN UNNEST(@company_name_list)"
        query_params.append(bigquery.ArrayQueryParameter("company_name_list", "STRING", filtered_companies))
    else:
        company_name = company_name.lower()
        if company_name == "demo" and user_id != "demo":
            return 0
        company_filter = "LOWER(company_name) = @company_name"
        query_params.append(bigquery.ScalarQueryParameter("company_name", "STRING", company_name))
    
    # 날짜 파라미터
    query_params.extend([
        bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
        bigquery.ScalarQueryParameter("end_date", "DATE", end_date)
    ])
    
    query = f"""
        SELECT SUM(total_orders) AS total_orders
        FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
        WHERE payment_date BETWEEN @start_date AND @end_date
          AND {company_filter}
    """
    
    try:
        result = client.query(query, job_config=bigquery.QueryJobConfig(query_parameters=query_params)).result()
        row = next(result)
        return row.get("total_orders", 0) or 0
    except Exception as e:
        print(f"[MOBILE] ❌ total_orders 조회 실패: {e}")
        return 0

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
# 6) 모바일 데이터 API (웹버전과 동일한 구조, 데이터만 축소)
# ─────────────────────────────────────────────
@mobile_blueprint.route("/get_data", methods=["POST"])
@login_required
def get_data():
    """모바일 전용 데이터 API - 웹버전과 동일한 구조, 데이터만 축소"""
    t0 = time.time()
    try:
        data = request.get_json() or {}
        user_id = session.get("user_id")
        
        print(f"[MOBILE] 🔍 API 호출 시작 - user_id: {user_id}")
        print(f"[MOBILE] 📊 요청 데이터: {data}")
        
        # ✅ 웹버전과 동일한 company_name 처리
        raw_company_name = data.get("company_name", "all")
        print(f"[MOBILE] 🏢 raw_company_name: {raw_company_name}")
        
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
        
        print(f"[MOBILE] 🏢 처리된 company_name: {company_name}")

        # ✅ 웹버전과 동일한 기간 필터 처리
        period = str(data.get("period", "today")).strip()
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        start_date, end_date = get_start_end_dates(period, start_date, end_date)

        print(f"[MOBILE] 📅 필터 값 - period: {period}, start_date: {start_date}, end_date: {end_date}")

        # ✅ 웹버전과 동일한 서비스 함수 호출, 데이터만 축소
        response_data = {
            "status": "success",
            "last_updated": datetime.datetime.now().isoformat()
        }

        # 1. Performance Summary (웹버전과 동일)
        try:
            print(f"[MOBILE] 🔄 Performance Summary 호출 시작...")
            performance_data = get_performance_summary(
                company_name=company_name,
                start_date=start_date,
                end_date=end_date,
                user_id=user_id
            )
            
            print(f"[MOBILE] 📊 Performance Summary 결과: {len(performance_data) if performance_data else 0}개")
            
            if performance_data:
                first_row = performance_data[0]
                
                # 모바일 전용: 추가 데이터 조회하여 보완
                try:
                    print(f"[MOBILE] 🔄 추가 데이터 조회 시작...")
                    
                    # 사이트 성과 요약 관련 데이터만 조회
                    # 사이트 매출 조회
                    from ..services.platform_sales_summary import get_platform_sales_by_day
                    platform_sales = get_platform_sales_by_day(
                        company_names=company_name if isinstance(company_name, list) else [company_name],
                        start_date=start_date,
                        end_date=end_date,
                        date_type="summary"
                    )
                    
                    site_revenue = 0
                    if platform_sales and len(platform_sales) > 0:
                        site_revenue = platform_sales[0].get('site_official', 0)
                    
                    # 방문자 수 조회
                    from ..services.ga4_source_summary import get_ga4_traffic_summary
                    ga4_traffic = get_ga4_traffic_summary(company_name, start_date, end_date, user_id=user_id)
                    total_visitors = sum(row.get('visitors', 0) for row in ga4_traffic) if ga4_traffic else 0
                    
                    # 광고비 비율 계산 (사이트 성과 요약용)
                    ad_spend = first_row.get('ad_spend', 0)
                    ad_spend_ratio = round((ad_spend / site_revenue * 100), 2) if site_revenue > 0 else 0
                    
                    # 사이트 성과 요약 관련 필드만 업데이트 (총 광고 성과는 건드리지 않음)
                    first_row['site_revenue'] = site_revenue
                    first_row['total_visitors'] = total_visitors
                    first_row['ad_spend_ratio'] = ad_spend_ratio
                    
                    print(f"[MOBILE] ✅ 사이트 성과 요약 데이터 보완 완료 - 사이트 매출: {site_revenue}, 방문자: {total_visitors}, 광고비 비율: {ad_spend_ratio}%")
                except Exception as e:
                    print(f"[MOBILE] ❌ 추가 데이터 조회 오류: {e}")
                    # 오류가 발생해도 기존 데이터는 유지
                
                response_data["performance_summary"] = [first_row]  # 첫 번째 행만
                # 웹버전과 동일한 형식으로 latest_update 설정
                latest_update = max([
                    row.get("updated_at")
                    for row in performance_data if row.get("updated_at")
                ], default=None)
                
                # 디버깅: 실제 updated_at 값들 출력
                print(f"[MOBILE] 🔍 Performance Data의 updated_at 값들:")
                for i, row in enumerate(performance_data):
                    print(f"  Row {i}: updated_at = {row.get('updated_at')} (type: {type(row.get('updated_at'))})")
                
                response_data["latest_update"] = latest_update
                print(f"[MOBILE] ✅ Performance Summary 성공 - latest_update: {response_data['latest_update']} (type: {type(response_data['latest_update'])})")
                
                # 디버깅: 실제 데이터 값들 출력
                print(f"[MOBILE] 🔍 Performance Summary 데이터 값들:")
                print(f"  site_revenue: {first_row.get('site_revenue')}")
                print(f"  total_visitors: {first_row.get('total_visitors')}")
                print(f"  ad_spend_ratio: {first_row.get('ad_spend_ratio')}")
                print(f"  product_views: {first_row.get('product_views')}")
                print(f"  views_per_visit: {first_row.get('views_per_visit')}")
            else:
                response_data["performance_summary"] = []
                print(f"[MOBILE] ⚠️ Performance Summary 데이터 없음")
        except Exception as e:
            print(f"[MOBILE] ❌ Performance Summary 오류: {e}")
            response_data["performance_summary"] = []

        # 1-1. 모바일 전용: total_orders 가져오기
        try:
            print(f"[MOBILE] 🔄 Total Orders 호출 시작...")
            total_orders = get_total_orders_from_cafe24(
                company_name=company_name,
                start_date=start_date,
                end_date=end_date,
                user_id=user_id
            )
            response_data["total_orders"] = total_orders
            print(f"[MOBILE] ✅ Total Orders 성공: {total_orders}")
        except Exception as e:
            print(f"[MOBILE] ❌ Total Orders 오류: {e}")
            response_data["total_orders"] = 0

        # 1-2. Performance Summary에서 추가 데이터 조회 완료

        # 2. Cafe24 Product Sales (웹버전과 동일한 호출 방식)
        try:
            print(f"[MOBILE] 🔄 Cafe24 Product Sales 호출 시작...")
            print(f"[MOBILE] 📊 Cafe24 Product Sales 파라미터: company_name={company_name}, period={period}, start_date={start_date}, end_date={end_date}")
            
            # 웹버전과 동일한 파라미터 순서: company_name, period, start_date, end_date, sort_by, limit, page, user_id
            result = get_cafe24_product_sales(
                company_name, period, start_date, end_date,
                sort_by="item_product_sales", limit=5, page=1, user_id=user_id
            )
            
            print(f"[MOBILE] 📊 Cafe24 Product Sales 서비스 결과: {result}")
            
            if result and "rows" in result:
                response_data["cafe24_product_sales"] = result.get("rows", [])[:5]
                response_data["cafe24_product_sales_total_count"] = result.get("total_count", 0)
                print(f"[MOBILE] 📊 Cafe24 Product Sales 결과: {len(response_data['cafe24_product_sales'])}개 / 전체: {response_data['cafe24_product_sales_total_count']}개")
            else:
                print(f"[MOBILE] ⚠️ Cafe24 Product Sales 결과가 비어있음")
                response_data["cafe24_product_sales"] = []
                response_data["cafe24_product_sales_total_count"] = 0
        except Exception as e:
            print(f"[MOBILE] ❌ Cafe24 Product Sales 오류: {e}")
            response_data["cafe24_product_sales"] = []

        # 3. GA4 Source Summary (웹버전과 동일한 호출 방식)
        try:
            print(f"[MOBILE] 🔄 GA4 Source Summary 호출 시작...")
            # 웹버전과 동일한 파라미터: company_name, start_date, end_date, limit, _cache_buster
            cache_buster = data.get('_cache_buster')
            ga4_data = get_ga4_source_summary(company_name, start_date, end_date, limit=100, _cache_buster=cache_buster)
            # not set 제외하고 상위 5개만
            filtered_sources = [row for row in ga4_data if row.get("source", "").lower() != "not set" and row.get("source", "").lower() != "(not set)"][:5]
            response_data["ga4_source_summary"] = filtered_sources
            print(f"[MOBILE] 📊 GA4 Source Summary 결과: {len(response_data['ga4_source_summary'])}개")
        except Exception as e:
            print(f"[MOBILE] ❌ GA4 Source Summary 오류: {e}")
            response_data["ga4_source_summary"] = []

        # 4. Meta Ads (상위 10개만, 모바일용 처리)
        try:
            print(f"[MOBILE] 🔄 Meta Ads 호출 시작...")
            meta_data = get_meta_ads_data(company_name, period, start_date, end_date, "summary", "desc")
            # 모바일용 데이터 처리
            processed_meta_data = process_meta_ads_for_mobile(meta_data[:10])
            response_data["meta_ads"] = processed_meta_data
            print(f"[MOBILE] 📊 Meta Ads 결과: {len(response_data['meta_ads'])}개")
        except Exception as e:
            print(f"[MOBILE] ❌ Meta Ads 오류: {e}")
            response_data["meta_ads"] = []

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