# File: services/data_service.py
import os   
import datetime
from flask import Blueprint, request, jsonify, session, Response
from google.cloud import bigquery
import time
from concurrent.futures import ThreadPoolExecutor
import requests
from urllib.parse import quote, unquote
import requests
from urllib.parse import quote, unquote

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
from ..services.performance_summary_new import get_performance_summary_new
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

    # 🔥 '직접 선택' 모드에서는 날짜가 비어있으면 오류 발생
    if period == "manual":
        if not start_date or not end_date:
            raise ValueError("직접 선택 모드에서는 시작일과 종료일이 모두 필요합니다.")
    
    # 🔥 미리 정의된 기간의 경우에만 기본값 설정
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

        # 안전한 int 변환
        try:
            page = int(data.get("page", 1)) if isinstance(data.get("page"), (int, str)) else 1
        except (ValueError, TypeError):
            page = 1
            
        try:
            limit = int(data.get("limit", 15)) if isinstance(data.get("limit"), (int, str)) else 15
        except (ValueError, TypeError):
            limit = 15
        offset = (page - 1) * limit

        # ✅ 기간 필터 필요 없는 테이블 예외 처리
        if data_type not in ["monthly_net_sales_visitors", "platform_sales_monthly"]:
            # 🔥 period가 없으면 "manual"로 처리 (직접 선택 모드)
            if not period:
                period = "manual"
            start_date, end_date = get_start_end_dates(period, start_date, end_date)

        print(f"[DEBUG] 요청 필터 - company_name={company_name}, period={period}, "
              f"start_date={start_date}, end_date={end_date}, page={page}, limit={limit}, data_type={data_type}")
        print(f"[DEBUG] date_type={date_type}, date_sort={date_sort}, sort_by={sort_by}")
        print(f"[DEBUG] 정규화된 data_type: '{data_type}'")
        print(f"[DEBUG] performance_summary 조건 확인: data_type in ['performance_summary', 'all'] = {data_type in ['performance_summary', 'all']}")

        response_data = {"status": "success"}
        timing_log = {}
        fetch_tasks = []
        results_map = {}
        with ThreadPoolExecutor() as executor:
            # Performance Summary
            if data_type in ["performance_summary", "all"]:
                def fetch_performance():
                    t1 = time.time()
                    performance_data = get_performance_summary_new(
                        company_name=company_name,
                        start_date=start_date,
                        end_date=end_date,
                        user_id=user_id
                    )
                    t2 = time.time()
                    timing_log["performance_summary"] = round(t2-t1, 3)
                    
                    # 🔥 ISO 형식으로 날짜 변환 (JavaScript에서 파싱 가능)
                    latest_update = None
                    if performance_data:
                        for row in performance_data:
                            if row.get("updated_at"):
                                # datetime 객체를 ISO 형식 문자열로 변환
                                if hasattr(row["updated_at"], 'isoformat'):
                                    latest_update = row["updated_at"].isoformat()
                                else:
                                    latest_update = str(row["updated_at"])
                                break
                    
                    return ("performance_summary", performance_data[offset:offset + limit], len(performance_data), latest_update)
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
                    try:
                        # 캐시 무효화 파라미터 추출
                        cache_buster = data.get('_cache_buster')
                        print(f"[DEBUG] GA4 Source Summary 호출 - company: {company_name}, start: {start_date}, end: {end_date}")
                        print(f"[DEBUG] GA4 Source Summary 파라미터 타입 - company: {type(company_name)}, start: {type(start_date)}, end: {type(end_date)}")
                        print(f"[DEBUG] GA4 Source Summary 전체 data: {data}")
                        
                        if not start_date or not end_date:
                            print(f"[ERROR] GA4 Source Summary - start_date 또는 end_date가 없습니다!")
                            return ("ga4_source_summary", [], 0)
                        
                        data_rows = get_ga4_source_summary(company_name, start_date, end_date, limit=100, _cache_buster=cache_buster)
                        t2 = time.time()
                        timing_log["ga4_source_summary"] = round(t2-t1, 3)
                        return ("ga4_source_summary", data_rows[offset:offset + limit], len(data_rows))
                    except Exception as e:
                        print(f"[ERROR] GA4 Source Summary 오류: {type(e).__name__}: {str(e)}")
                        return ("ga4_source_summary", [], 0)
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
            # 페이지네이션 파라미터 (웹 UI에 영향 없도록 기본값 유지)
            limit = data.get("limit", None)
            page = data.get("page", 1)

            rows = get_meta_ads_insight_table(
                level=level,
                company_name=company_name,
                start_date=start_date,
                end_date=end_date,
                account_id=account_id,
                campaign_id=campaign_id,
                adset_id=adset_id,
                date_type=date_type,
                limit=limit,
                page=page
            )
            t2 = time.time()
            timing_log["meta_ads_insight_table"] = round(t2-t1, 3)
            
            # 페이지네이션된 결과 처리
            if isinstance(rows, dict) and "rows" in rows:
                # 페이지네이션된 결과 (전체 개수 포함)
                response_data["meta_ads_insight_table"] = rows["rows"]
                response_data["meta_ads_insight_table_total_count"] = rows["total_count"]
                if rows["rows"]:
                    response_data["updated_at"] = rows["rows"][0].get("updated_at")
            else:
                # 기존 형식 (페이지네이션 없음)
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

            response_data["data"] = {
                "type_summary": type_summary,
                "total_spend_sum": total_spend_sum
            }

        # Meta Ads 광고 미리보기 - 단일 (캐시 제거 버전)
        if data_type == "meta_ads_preview_list":
            from ..services.meta_ads_preview import get_meta_ads_preview_list
            import logging
            handler_logger = logging.getLogger(__name__)

            account_id = data.get("account_id")
            
            # ✅ [NO_CACHE] 캐시 완전 제거 - 항상 직접 호출
            handler_logger.warning(f"[META_API][NO_CACHE] live preview - cache bypassed, account_id={account_id}")
            handler_logger.warning(f"[META_API][ENTER] get_meta_ads_preview_list account_id={account_id}")
            
            start_time = time.time()
            ad_list = get_meta_ads_preview_list(account_id)
            processing_time = time.time() - start_time
            
            handler_logger.warning(f"[META_API][RESULT] 결과: {len(ad_list) if ad_list else 0}개, {processing_time:.2f}초")
            
            response_data["meta_ads_preview_list"] = ad_list
            response_data["cached"] = False
            response_data["processing_time"] = round(processing_time, 2)

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


# ─────────────────────────────────────────────────────────────
# 📌 이미지 프록시 엔드포인트 (CORS 문제 해결)
#     GET  /dashboard/proxy_image?url=<encoded_image_url>
# ─────────────────────────────────────────────────────────────

@data_blueprint.route("/test", methods=["GET"])
def test():
    return "Hello World"

@data_blueprint.route("/proxy_image", methods=["GET"])
def proxy_image():
    """
    외부 이미지 URL을 프록시하여 CORS 및 Mixed Content 문제를 해결합니다.
    Meta API에서 가져온 이미지 URL을 서버에서 가져와서 반환합니다.
    """
    print(f"[PROXY] proxy_image 호출됨 - args: {request.args}")
    try:
        # URL 파라미터에서 이미지 URL 가져오기
        image_url = request.args.get("url")
        
        if not image_url:
            return jsonify({"status": "error", "message": "url 파라미터가 필요합니다"}), 400
        
        # URL 디코딩
        try:
            image_url = unquote(image_url)
        except Exception:
            pass  # 이미 디코딩된 경우 그대로 사용
        
        # 보안: 허용된 도메인만 프록시 (Meta/Facebook 이미지)
        allowed_domains = [
            "fbcdn.net",
            "facebook.com",
            "scontent",
            "cdninstagram.com",
            "instagram.com"
        ]
        
        if not any(domain in image_url.lower() for domain in allowed_domains):
            # 로컬 파일 경로인 경우 허용 (예: /static/demo_ads/...)
            if not image_url.startswith("/static/"):
                return jsonify({"status": "error", "message": "허용되지 않은 도메인입니다"}), 403
        
        # 로컬 파일인 경우 직접 반환
        if image_url.startswith("/static/"):
            from flask import send_from_directory
            import os
            static_folder = os.path.join(os.path.dirname(__file__), "..", "static")
            file_path = image_url.replace("/static/", "")
            return send_from_directory(static_folder, file_path)
        
        # 외부 이미지 가져오기
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        response = requests.get(image_url, headers=headers, timeout=10, stream=True)
        response.raise_for_status()
        
        # Content-Type 확인
        content_type = response.headers.get("Content-Type", "image/jpeg")
        
        # 이미지 데이터를 스트림으로 반환
        def generate():
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    yield chunk
        
        return Response(
            generate(),
            mimetype=content_type,
            headers={
                "Cache-Control": "public, max-age=3600",  # 1시간 캐시
                "Access-Control-Allow-Origin": "*",  # CORS 허용
            }
        )
        
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] 이미지 프록시 실패: {image_url}, 오류: {str(e)}")
        return jsonify({"status": "error", "message": f"이미지를 가져올 수 없습니다: {str(e)}"}), 500
    except Exception as e:
        print(f"[ERROR] 이미지 프록시 오류: {str(e)}")
        return jsonify({"status": "error", "message": f"프록시 오류: {str(e)}"}), 500
