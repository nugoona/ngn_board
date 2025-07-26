# File: services/data_service.py
import os   
import datetime
from flask import Blueprint, request, jsonify, session
from google.cloud import bigquery
import time
from concurrent.futures import ThreadPoolExecutor

# 캐시 유틸리티 임포트
from ..utils.cache_utils import get_cache_stats, invalidate_cache_by_pattern

# 📦 서비스 함수 임포트 (기능별 정리)
from ..services.cafe24_service import (
    get_cafe24_sales_data,
    get_cafe24_product_sales,
)
from ..services.catalog_sidebar_service import create_or_update_product_set
from ..services.ga4_source_summary import get_ga4_source_summary
from ..services.meta_ads_insight import get_meta_account_list_filtered
from ..services.meta_ads_service import get_meta_ads_data
from ..services.performance_summary import get_performance_summary
from ..services.platform_sales_summary import get_monthly_platform_sales
from ..services.Fetch_Adset_Summary import get_meta_ads_adset_summary_by_type
from ..services.viewitem_summary import get_viewitem_summary
from ..services.monthly_net_sales_visitors import get_monthly_net_sales_visitors



data_blueprint = Blueprint("data", __name__, url_prefix="/dashboard")

# ─────────────────────────────────────────────────────────────
# 📌 캐시 관리 엔드포인트
# ─────────────────────────────────────────────────────────────

@data_blueprint.route("/cache/stats", methods=["GET"])
def cache_stats():
    """캐시 상태 정보 조회"""
    try:
        stats = get_cache_stats()
        return jsonify({"status": "success", "cache_stats": stats}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@data_blueprint.route("/cache/invalidate", methods=["POST"])
def cache_invalidate():
    """캐시 무효화 (패턴 기반)"""
    try:
        data = request.get_json() or {}
        pattern = data.get("pattern", "")
        
        if not pattern:
            return jsonify({"status": "error", "message": "pattern 파라미터 필요"}), 400
        
        deleted_count = invalidate_cache_by_pattern(pattern)
        return jsonify({
            "status": "success", 
            "message": f"{pattern} 패턴으로 {deleted_count}개 캐시 삭제됨"
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@data_blueprint.route("/cache/invalidate/ga4_source", methods=["POST"])
def cache_invalidate_ga4_source():
    """GA4 소스 요약 캐시 무효화 엔드포인트"""
    try:
        from ..utils.cache_utils import invalidate_cache_by_pattern
        deleted_count = invalidate_cache_by_pattern("ga4_source_summary")
        
        return jsonify({
            "status": "success",
            "message": f"GA4 소스 요약 캐시 무효화 완료: {deleted_count}개 키 삭제",
            "deleted_count": deleted_count
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"GA4 소스 요약 캐시 무효화 실패: {str(e)}"
        }), 500

# ─────────────────────────────────────────────────────────────

def get_start_end_dates(period, start_date=None, end_date=None):
    """ ✅ 필터링 기간을 결정하는 함수 (KST 기준 적용) """
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
        )
    }

    if start_date == "":
        start_date = None
    if end_date == "":
        end_date = None

    if period in date_map:
        start_date, end_date = date_map[period]

    if not start_date:
        start_date = now_kst.strftime("%Y-%m-%d")
    if not end_date:
        end_date = now_kst.strftime("%Y-%m-%d")

    print(f"[DEBUG] 변환된 날짜 값 - start_date: {start_date}, end_date: {end_date}")
    return start_date, end_date

@data_blueprint.route("/get_data", methods=["POST"])
def get_dashboard_data_route():
    t0 = time.time()
    try:
        data = request.get_json()
        user_id = session.get("user_id")
        raw_company_name = data.get("company_name", "all")

        # ✅ company_name 처리
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
                    "cafe24_sales": [],
                    "cafe24_sales_total_count": 0
                }), 200
            company_name = name

        # ✅ 공통 파라미터 처리
        period = str(data.get("period", "today")).strip()
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        data_type = (data.get("data_type", "all") or "").strip().lower()
        data_type = data_type.replace("-", "_")  # kebab-case -> snake_case
        data_type = data_type.replace(" ", "_")  # spaces -> underscores
        date_type = str(data.get("date_type", "summary")).strip()
        date_sort = str(data.get("date_sort", "desc")).strip()
        sort_by = str(data.get("sort_by", "item_product_sales")).strip()

        page = int(data.get("page", 1))
        limit = int(data.get("limit", 15))
        offset = (page - 1) * limit

        # ✅ 기간 필터 필요 없는 테이블 예외 처리
        if data_type not in ["monthly_net_sales_visitors", "platform_sales_monthly"]:
            start_date, end_date = get_start_end_dates(period, start_date, end_date)

        print(f"[DEBUG] 요청 필터 - company_name={company_name}, period={period}, "
              f"start_date={start_date}, end_date={end_date}, page={page}, limit={limit}, data_type={data_type}")
        print(f"[DEBUG] date_type={date_type}, date_sort={date_sort}, sort_by={sort_by}")
        print(f"[DEBUG] 정규화된 data_type: '{data_type}'")

        response_data = {"status": "success"}
        timing_log = {}
        fetch_tasks = []
        results_map = {}
        with ThreadPoolExecutor() as executor:
            # Performance Summary
            if data_type in ["performance_summary", "all"]:
                def fetch_performance():
                    t1 = time.time()
                    performance_data = get_performance_summary(
                        company_name=company_name,
                        start_date=start_date,
                        end_date=end_date,
                        user_id=user_id
                    )
                    t2 = time.time()
                    timing_log["performance_summary"] = round(t2-t1, 3)
                    return ("performance_summary", performance_data[offset:offset + limit], len(performance_data), max([
                        str(row.get("updated_at"))[:16].replace(" ", "-").replace(":", "-")
                        for row in performance_data if row.get("updated_at")
                    ], default=None))
                fetch_tasks.append(executor.submit(fetch_performance))
            
            # Cafe24 Sales
            if data_type in ["cafe24_sales", "all"]:
                def fetch_cafe24_sales():
                    t1 = time.time()
                    result = get_cafe24_sales_data(
                        company_name, period, start_date, end_date,
                        date_type, date_sort, limit, page, user_id
                    )
                    t2 = time.time()
                    timing_log["cafe24_sales"] = round(t2-t1, 3)
                    return ("cafe24_sales", result["rows"], result["total_count"])
                fetch_tasks.append(executor.submit(fetch_cafe24_sales))
            
            # Cafe24 Product Sales
            if data_type in ["cafe24_product_sales", "all"]:
                def fetch_cafe24_product_sales():
                    t1 = time.time()
                    result = get_cafe24_product_sales(
                        company_name, period, start_date, end_date,
                        sort_by=sort_by, limit=limit, page=page, user_id=user_id
                    )
                    t2 = time.time()
                    timing_log["cafe24_product_sales"] = round(t2-t1, 3)
                    return ("cafe24_product_sales", result["rows"], result["total_count"])
                fetch_tasks.append(executor.submit(fetch_cafe24_product_sales))
            
            # ViewItem Summary
            if data_type in ["viewitem_summary", "all"]:
                def fetch_viewitem_summary():
                    t1 = time.time()
                    data_rows = get_viewitem_summary(company_name, start_date, end_date, limit=500)
                    t2 = time.time()
                    timing_log["viewitem_summary"] = round(t2-t1, 3)
                    return ("viewitem_summary", data_rows, len(data_rows))
                fetch_tasks.append(executor.submit(fetch_viewitem_summary))
            
            # GA4 Source Summary
            if data_type in ["ga4_source_summary", "all"]:
                def fetch_ga4_source_summary():
                    t1 = time.time()
                    data_rows = get_ga4_source_summary(company_name, start_date, end_date, limit=100)
                    t2 = time.time()
                    timing_log["ga4_source_summary"] = round(t2-t1, 3)
                    return ("ga4_source_summary", data_rows[offset:offset + limit], len(data_rows))
                fetch_tasks.append(executor.submit(fetch_ga4_source_summary))
            
            # Monthly Net Sales & Visitors Chart
            if data_type == "monthly_net_sales_visitors":
                def fetch_monthly_net_sales_visitors():
                    t1 = time.time()
                    data_rows = get_monthly_net_sales_visitors(company_name)
                    t2 = time.time()
                    timing_log["monthly_net_sales_visitors"] = round(t2-t1, 3)
                    return ("monthly_net_sales_visitors", data_rows, len(data_rows))
                fetch_tasks.append(executor.submit(fetch_monthly_net_sales_visitors))
            
            # Product Sales Ratio
            if data_type == "product_sales_ratio":
                def fetch_product_sales_ratio():
                    t1 = time.time()
                    from ..services.product_sales_ratio import get_product_sales_ratio
                    # ⬇️ 서비스 함수는 리스트 파라미터를 기대하므로 문자열이면 리스트로 래핑
                    _company_names = company_name if isinstance(company_name, list) else [company_name]
                    data_rows = get_product_sales_ratio(_company_names, start_date, end_date, limit=50, user_id=user_id)
                    t2 = time.time()
                    timing_log["product_sales_ratio"] = round(t2-t1, 3)
                    return ("product_sales_ratio", data_rows)
                fetch_tasks.append(executor.submit(fetch_product_sales_ratio))
            
            # Platform Sales Summary
            if data_type == "platform_sales_summary":
                def fetch_platform_sales_summary():
                    t1 = time.time()
                    from ..services.platform_sales_summary import get_platform_sales_by_day
                    # ⬇️ 서비스 함수는 리스트 파라미터를 기대하므로 문자열이면 리스트로 래핑
                    _company_names = company_name if isinstance(company_name, list) else [company_name]

                    data_rows = get_platform_sales_by_day(
                        company_names=_company_names,
                        start_date=start_date,
                        end_date=end_date,
                        date_type=date_type,
                        date_sort=date_sort
                    )
                    t2 = time.time()
                    timing_log["platform_sales_summary"] = round(t2-t1, 3)
                    return ("platform_sales_summary", data_rows, len(data_rows))
                fetch_tasks.append(executor.submit(fetch_platform_sales_summary))
            
            # Platform Sales Ratio (파이차트용)
            if data_type == "platform_sales_ratio":
                def fetch_platform_sales_ratio():
                    t1 = time.time()
                    from ..services.platform_sales_summary import get_platform_sales_ratio
                    _company_names = company_name if isinstance(company_name, list) else [company_name]

                    data_rows = get_platform_sales_ratio(
                        company_names=_company_names,
                        start_date=start_date,
                        end_date=end_date
                    )
                    t2 = time.time()
                    timing_log["platform_sales_ratio"] = round(t2-t1, 3)
                    return ("platform_sales_ratio", data_rows)
                fetch_tasks.append(executor.submit(fetch_platform_sales_ratio))
            
            # Platform Sales Monthly
            if data_type == "platform_sales_monthly":
                def fetch_monthly_platform_sales():
                    t1 = time.time()
                    from ..services.platform_sales_summary import get_monthly_platform_sales
                    _company_names = company_name if isinstance(company_name, list) else [company_name]
                    data_rows = get_monthly_platform_sales(_company_names)
                    t2 = time.time()
                    timing_log["platform_sales_monthly"] = round(t2-t1, 3)
                    return ("platform_sales_monthly", data_rows, len(data_rows))
                fetch_tasks.append(executor.submit(fetch_monthly_platform_sales))

        # Collect results
        for future in fetch_tasks:
            result = future.result()
            if result[0] == "performance_summary":
                response_data["performance_summary"] = result[1]
                response_data["performance_summary_total_count"] = result[2]
                response_data["latest_update"] = result[3]
            elif result[0] == "cafe24_sales":
                response_data["cafe24_sales"] = result[1]
                response_data["cafe24_sales_total_count"] = result[2]
            elif result[0] == "cafe24_product_sales":
                response_data["cafe24_product_sales"] = result[1]
                response_data["cafe24_product_sales_total_count"] = result[2]
            elif result[0] == "viewitem_summary":
                response_data["viewitem_summary"] = result[1]
                response_data["viewitem_summary_total_count"] = result[2]
            elif result[0] == "ga4_source_summary":
                response_data["ga4_source_summary"] = result[1]
                response_data["ga4_source_summary_total_count"] = result[2]
            elif result[0] == "monthly_net_sales_visitors":
                response_data["monthly_net_sales_visitors"] = result[1]
                response_data["monthly_net_sales_visitors_total_count"] = result[2]
            elif result[0] == "product_sales_ratio":
                response_data["product_sales_ratio"] = result[1]
            elif result[0] == "platform_sales_summary":
                response_data["platform_sales_summary"] = result[1]
                response_data["platform_sales_summary_total_count"] = result[2]
            elif result[0] == "platform_sales_ratio":
                response_data["platform_sales_ratio"] = result[1]
            elif result[0] == "platform_sales_monthly":
                response_data["platform_sales_monthly"] = result[1]
                response_data["platform_sales_monthly_total_count"] = result[2]

        # Meta 광고 관련 데이터 요청 처리
        if data_type == "meta_ads_insight_table":
            t1 = time.time()
            from ..services.meta_ads_insight import get_meta_ads_insight_table

            level = data.get("level", "account")
            account_id = data.get("account_id")
            campaign_id = data.get("campaign_id")
            adset_id = data.get("adset_id")
            date_type = data.get("date_type", "summary")

            rows = get_meta_ads_insight_table(
                level=level,
                company_name=company_name,
                start_date=start_date,
                end_date=end_date,
                account_id=account_id,
                campaign_id=campaign_id,
                adset_id=adset_id,
                date_type=date_type
            )
            t2 = time.time()
            timing_log["meta_ads_insight_table"] = round(t2-t1, 3)
            response_data["meta_ads_insight_table"] = rows
            if rows:
                response_data["updated_at"] = rows[0].get("updated_at")

        # Meta Ads 계정 목록 요청 처리
        if data_type == "meta_account_list":
            if user_id == "demo":
                session["company_names"] = ["demo"]

            from ..services.meta_ads_insight import get_meta_account_list_filtered
            rows = get_meta_account_list_filtered(company_name)
            response_data["meta_accounts"] = rows

        # Meta Ads 캠페인 목표별 성과 요약
        if data_type == "meta_ads_adset_summary_by_type":
            account_id = data.get("account_id")
            period = data.get("period")
            start_date = data.get("start_date")
            end_date = data.get("end_date")

            type_summary, total_spend_sum = get_meta_ads_adset_summary_by_type(
                account_id=account_id,
                period=period,
                start_date=start_date,
                end_date=end_date
            )

            response_data["meta_ads_adset_summary_by_type"] = type_summary

        # Meta Ads 광고 미리보기 - 단일
        if data_type == "meta_ads_preview_list":
            from ..services.meta_ads_preview import get_meta_ads_preview_list

            account_id = data.get("account_id")
            ad_list = get_meta_ads_preview_list(account_id)

            response_data["meta_ads_preview_list"] = ad_list

        # Meta Ads 광고 미리보기 - 콜렉션/슬라이드드
        if data_type == "slide_collection_ads":
            from ..services.meta_ads_slide_collection import get_slide_collection_ads

            account_id = data.get("account_id")
            ad_list = get_slide_collection_ads(account_id)

            response_data["slide_collection_ads"] = ad_list

        # catalog_sidebar
        if data_type == "catalog_sidebar":
            from ..services.catalog_sidebar_service import get_catalog_sidebar_data

            account_id = data.get("account_id")
            if not account_id:
                return jsonify({"status": "error", "message": "account_id 누락"}), 400

            result, error = get_catalog_sidebar_data(account_id)
            if error:
                return jsonify({"status": "error", "message": error}), 404

            response_data["catalog_sidebar"] = result

        # catalog_manual  ─ 자사몰 URL 수집
        if data_type == "catalog_manual":
            from ..services.catalog_sidebar_service import get_manual_product_list

            category_url = data.get("category_url")
            if not category_url:
                return jsonify({"status": "error", "message": "category_url 누락"}), 400

            result, error = get_manual_product_list(category_url)
            if error:
                return jsonify({"status": "error", "message": error}), 404

            response_data["products"] = result

        # catalog_manual_search  ─ 수동 세트 키워드 검색
        if data_type == "catalog_manual_search":
            from ..services.catalog_sidebar_service import search_products_for_manual_set

            account_id = data.get("account_id")
            keyword = (data.get("keyword") or "").strip()
            search_type = data.get("search_type")   # 'product_name' | 'product_no'

            # ── 파라미터 검증 ─────────────────────────────
            if not account_id:
                return jsonify({"status": "error", "message": "account_id 누락"}), 400
            if not keyword:
                return jsonify({"status": "error", "message": "keyword 누락"}), 400
            if search_type not in ("product_name", "product_no"):
                return jsonify({"status": "error", "message": "search_type 누락 또는 잘못됨"}), 400

            # ── 서비스 호출 ─────────────────────────────
            result, error = search_products_for_manual_set(
                account_id=account_id,
                keyword=keyword,
                search_type=search_type
            )
            if error:
                return jsonify({"status": "error", "message": error}), 404

            response_data["results"] = result

        t_end = time.time()
        print("[TIMING_LOG] /dashboard/get_data timing:", timing_log, "total:", round(t_end-t0, 3), "s")
        return jsonify(response_data), 200

    except TypeError as te:
        print(f"[ERROR] 요청 데이터 타입 오류: {te}")
        return jsonify({"status": "error", "message": f"잘못된 요청 형식: {str(te)}"}), 400

    except Exception as e:
        print(f"[ERROR] 데이터 조회 중 오류 발생: {e}")
        return jsonify({"status": "error", "message": f"데이터 조회 중 오류 발생: {str(e)}"}), 500


# ─────────────────────────────────────────────────────────────
# 📌 카탈로그 상품세트 생성 / 업데이트
#     POST  /dashboard/catalog_set
# ─────────────────────────────────────────────────────────────

@data_blueprint.route("/catalog_set", methods=["POST"])
def catalog_set_route():
    try:
        data = request.get_json(silent=True) or {}

        catalog_id   = str(data.get("catalog_id", "")).strip()
        set_name     = str(data.get("set_name", "")).strip()
        retailer_ids = [str(r).strip() for r in data.get("retailer_ids", [])]

        # ─── ① 필수 파라미터 확인 ──────────────────────────
        if not (catalog_id and set_name and retailer_ids):
            return jsonify({
                "status": "error",
                "message": "catalog_id / set_name / retailer_ids 누락"
            }), 400

        # ─── ② 시스템-토큰 존재 여부만 확인 ────────────────
        if not os.getenv("META_SYSTEM_TOKEN"):
            return jsonify({
                "status": "error",
                "message": "META_SYSTEM_TOKEN 이 환경변수에 없습니다."
            }), 500

        # ─── ③ 세트 생성/업데이트 호출 ─────────────────────
        result, err = create_or_update_product_set(
            catalog_id   = catalog_id,
            set_name     = set_name,
            retailer_ids = retailer_ids
        )

        if err:
            return jsonify({"status": "error", "message": err}), 500

        return jsonify({"status": "success", **result}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
