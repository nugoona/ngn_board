# File: services/data_service.py
import os   
import sys
import datetime
import json
import gzip
import io
import re
from flask import Blueprint, request, jsonify, session, Response
from google.cloud import bigquery
from google.cloud import storage
import time
from concurrent.futures import ThreadPoolExecutor
import requests
from urllib.parse import quote, unquote

# 프로젝트 루트 경로 추가 (company_mapping 모듈 임포트용)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
tools_path = os.path.join(project_root, "tools")
if tools_path not in sys.path:
    sys.path.insert(0, tools_path)

# 자사몰 매핑 임포트
try:
    from config.company_mapping import get_company_korean_name, get_company_brands, COMPANY_MAPPING
    COMPANY_MAPPING_AVAILABLE = True
except (ImportError, ModuleNotFoundError) as e:
    print(f"[WARN] company_mapping 모듈 로드 실패: {e}")
    COMPANY_MAPPING_AVAILABLE = False
    def get_company_korean_name(name): return None
    def get_company_brands(name): return []
    COMPANY_MAPPING = {}

# 캐시 유틸리티 임포트
from ..utils.cache_utils import get_cache_stats, invalidate_cache_by_pattern

# 📦 서비스 함수 임포트 (기능별 정리)
from ..services.cafe24_service import (
    get_cafe24_sales_data,
    get_cafe24_product_sales,
)
from ..services.catalog_sidebar_service import create_or_update_product_set, get_product_sets
from ..services.ga4_source_summary import get_ga4_source_summary
from ..services.meta_ads_insight import get_meta_account_list_filtered
from ..services.meta_ads_service import get_meta_ads_data
from ..services.performance_summary_new import get_performance_summary_new
from ..services.platform_sales_summary import get_monthly_platform_sales
from ..services.Fetch_Adset_Summary import get_meta_ads_adset_summary_by_type
from ..services.viewitem_summary import get_viewitem_summary
from ..services.monthly_net_sales_visitors import get_monthly_net_sales_visitors
from ..services.trend_29cm_service import (
    get_rising_star,
    get_new_entry,
    get_rank_drop,
    get_current_week_info,
    get_available_tabs,
    load_trend_snapshot_from_gcs,
    save_trend_snapshot_to_gcs,
    get_all_tabs_data_from_bigquery
)
from ..services.trend_ably_service import (
    get_rising_star as get_ably_rising_star,
    get_new_entry as get_ably_new_entry,
    get_rank_drop as get_ably_rank_drop,
    get_current_week_info as get_ably_current_week_info,
    get_available_tabs as get_ably_available_tabs,
    load_trend_snapshot_from_gcs as load_ably_trend_snapshot_from_gcs,
    save_trend_snapshot_to_gcs as save_ably_trend_snapshot_to_gcs,
    get_all_tabs_data_from_bigquery as get_ably_all_tabs_data_from_bq
)
from ..services.compare_29cm_service import (
    get_competitor_keywords,
    get_competitor_brands,
    get_own_brand_id,
    fetch_product_reviews,
    load_search_results_from_gcs,
)



data_blueprint = Blueprint("data", __name__, url_prefix="/dashboard")


def filter_ai_report_by_company(analysis_report: str, company_name: str) -> str:
    """
    AI 리포트에서 현재 업체에 맞게 Section 1의 자사몰 브랜드명을 동적으로 변경
    
    Args:
        analysis_report: 원본 AI 리포트 (마크다운 형식)
        company_name: 현재 로그인한 업체명 (예: "piscess")
    
    Returns:
        필터링된 AI 리포트 (Section 1의 자사몰 브랜드명이 현재 업체에 맞게 변경됨)
    """
    if not analysis_report or not company_name or not COMPANY_MAPPING_AVAILABLE:
        return analysis_report
    
    # demo 계정인 경우 piscess로 매핑 (인사이트 리포트 표시를 위해)
    filter_company_name = "piscess" if company_name.lower() == "demo" else company_name
    
    company_ko = get_company_korean_name(filter_company_name)
    if not company_ko:
        # 매핑되지 않은 업체인 경우, Section 1에서 자사몰 섹션 제거 또는 기본 메시지로 변경
        # Section 1의 자사몰 부분을 "자사몰 상품이 포함되지 않았습니다"로 변경
        section1_pattern = r'##\s*Section\s*1[^#]*?(?=##|$)'
        section1_match = re.search(section1_pattern, analysis_report, flags=re.IGNORECASE | re.DOTALL)
        if section1_match:
            section1_text = section1_match.group(0)
            # 자사몰 관련 내용을 제거하고 기본 메시지로 교체
            updated_section1 = re.sub(
                r'자사몰\([^)]+\)[^#]*',
                '자사몰 성과 분석\n\n금주 랭킹 데이터에 자사몰 상품이 포함되지 않았습니다.',
                section1_text,
                flags=re.DOTALL
            )
            analysis_report = analysis_report.replace(section1_text, updated_section1)
        return analysis_report.strip()
    
    # Section 1의 자사몰 브랜드명을 현재 업체의 한글명으로 변경
    # 패턴: "## Section 1. 자사몰({브랜드명}) 성과 분석"
    section1_pattern = r'(##\s*Section\s*1[^#]*?(?=##|$))'
    section1_match = re.search(section1_pattern, analysis_report, flags=re.IGNORECASE | re.DOTALL)
    
    if section1_match:
        section1_text = section1_match.group(1)
        
        # 기존 브랜드명 패턴 찾기 및 교체
        # 패턴 1: "자사몰({브랜드명})" 또는 "자사몰 ({브랜드명})"
        updated_section1 = re.sub(
            r'자사몰\s*\([^)]+\)',
            f'자사몰({company_ko})',
            section1_text,
            flags=re.IGNORECASE
        )
        
        # 패턴 2: Section 1 텍스트 내의 모든 브랜드명 인스턴스 교체
        # 일반적인 브랜드명 패턴 교체 (따옴표 안의 브랜드명 포함)
        brand_patterns = [
            r"'썸웨어버터'",
            r'"썸웨어버터"',
            r'썸웨어버터',
            r"'파이시스'",
            r'"파이시스"',
            r'파이시스',
            r"'Somewhere Butter'",
            r'"Somewhere Butter"',
            r'Somewhere Butter',
            r"'somewhere butter'",
            r"'PISCESS'",
            r'"PISCESS"',
            r'PISCESS',
            r"'piscess'",
        ]
        
        for pattern in brand_patterns:
            updated_section1 = re.sub(
                pattern,
                company_ko,
                updated_section1,
                flags=re.IGNORECASE
            )
        
        # 패턴 3: "{target_brand}" 또는 다른 변수명 교체
        updated_section1 = re.sub(
            r"\{target_brand\}|\{TARGET_BRAND\}|\{brand\}|\{BRAND\}",
            company_ko,
            updated_section1,
            flags=re.IGNORECASE
        )
        
        analysis_report = analysis_report.replace(section1_text, updated_section1)
    
    return analysis_report.strip()

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
            else:
                # 기존 형식 (페이지네이션 없음)
                response_data["meta_ads_insight_table"] = rows

            # ✅ Meta Ads 수집시간 사용 (meta_ads_ad_level 테이블에서 조회)
            try:
                from google.cloud import bigquery as bq_client
                client = bq_client.Client()
                meta_query = """
                    SELECT MAX(updated_at) AS updated_at
                    FROM `winged-precept-443218-v8.ngn_dataset.meta_ads_ad_level`
                    WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
                """
                result = client.query(meta_query).result()
                for row in result:
                    if row.updated_at:
                        response_data["updated_at"] = row.updated_at.isoformat() if hasattr(row.updated_at, 'isoformat') else str(row.updated_at)
                        break
            except Exception as e:
                print(f"[WARN] Meta Ads updated_at 조회 실패: {e}")

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
# 📌 카탈로그 제품세트 목록 조회
#     POST  /dashboard/catalog_sets
# ─────────────────────────────────────────────────────────────

@data_blueprint.route("/catalog_sets", methods=["POST"])
def catalog_sets_route():
    """카탈로그의 제품세트 목록 조회"""
    try:
        data = request.get_json(silent=True) or {}
        catalog_id = str(data.get("catalog_id", "")).strip()

        if not catalog_id:
            return jsonify({
                "status": "error",
                "message": "catalog_id 누락"
            }), 400

        sets, err = get_product_sets(catalog_id)

        if err:
            return jsonify({"status": "error", "message": err}), 500

        return jsonify({
            "status": "success",
            "product_sets": sets
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ─────────────────────────────────────────────────────────────
# 📌 이미지 프록시 엔드포인트 (CORS 문제 해결)
#     GET  /dashboard/proxy_image?url=<encoded_image_url>
# ─────────────────────────────────────────────────────────────

@data_blueprint.route("/test", methods=["GET"])
def test():
    return "Hello World"


@data_blueprint.route("/monthly_report", methods=["POST"])
def get_monthly_report():
    """월간 리포트 스냅샷 데이터 조회 (GCS 버킷에서)"""
    try:
        data = request.get_json()
        company_name = data.get("company_name")
        year = int(data.get("year"))
        month = int(data.get("month"))
        
        if not company_name or company_name == "all":
            return jsonify({"status": "error", "message": "업체를 선택해주세요"}), 400
        
        # GCS 버킷에서 스냅샷 파일 읽기
        PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "winged-precept-443218-v8")
        GCS_BUCKET = os.environ.get("GCS_BUCKET", "winged-precept-443218-v8.appspot.com")
        
        # 경로 형식: ai-reports/monthly/{company}/{YYYY-MM}/snapshot.json[.gz] (실제 저장 경로)
        month_str = f"{year}-{month:02d}"
        
        # 여러 경로 시도 (압축 파일 우선, 그 다음 압축 없는 파일)
        blob_paths = [
            f"ai-reports/monthly/{company_name}/{month_str}/snapshot.json.gz",  # 압축 파일 (원본)
            f"ai-reports/monthly/{company_name.lower()}/{month_str}/snapshot.json.gz",  # 압축 파일 (소문자)
            f"ai-reports/monthly/{company_name}/{month_str}/snapshot.json",  # 압축 없는 파일 (원본, 하위 호환)
            f"ai-reports/monthly/{company_name.lower()}/{month_str}/snapshot.json",  # 압축 없는 파일 (소문자)
            f"ai-reports/{company_name}/{month_str}.json",  # 대체 경로 (원본)
            f"ai-reports/{company_name.lower()}/{month_str}.json"  # 대체 경로 (소문자)
        ]
        
        try:
            client = storage.Client(project=PROJECT_ID)
            bucket = client.bucket(GCS_BUCKET)
            
            # 여러 경로 시도
            blob = None
            found_path = None
            for blob_path in blob_paths:
                test_blob = bucket.blob(blob_path)
                if test_blob.exists():
                    blob = test_blob
                    found_path = blob_path
                    break
            
            if not blob:
                return jsonify({
                    "status": "error",
                    "message": f"{year}년 {month}월 리포트가 아직 생성되지 않았습니다."
                }), 404
            
            # 하이브리드 읽기 로직: Gzip 압축 여부와 관계없이 바이트로 다운로드 후 자동 판별
            snapshot_bytes = blob.download_as_bytes()
            
            # Gzip 압축 해제 시도 (성공하면 압축된 파일, 실패하면 압축되지 않은 파일)
            try:
                # Python 버전 호환성을 위해 gzip.GzipFile 사용 (max_length 파라미터 문제 회피)
                with gzip.GzipFile(fileobj=io.BytesIO(snapshot_bytes)) as gz_file:
                    snapshot_json_str = gz_file.read().decode('utf-8')
                print(f"✅ GCS에서 스냅샷을 불러왔습니다: {found_path} (Gzip 압축 해제됨)", file=sys.stderr)
            except (gzip.BadGzipFile, OSError, Exception) as e:
                # Gzip 압축 해제 실패 → 압축되지 않은 JSON 파일로 처리 (하위 호환)
                snapshot_json_str = snapshot_bytes.decode('utf-8')
                print(f"✅ GCS에서 스냅샷을 불러왔습니다: {found_path} (압축 없음, 하위 호환)", file=sys.stderr)
            
            snapshot_data = json.loads(snapshot_json_str)
            
            return jsonify({
                "status": "success",
                "data": snapshot_data
            }), 200
            
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"스냅샷 파일을 읽는 중 오류가 발생했습니다: {str(e)}"
            }), 500
            
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@data_blueprint.route("/monthly_report/check_new", methods=["POST"])
def check_new_monthly_report():
    """GCS 파일 수정 시간만 확인 (파일 다운로드 안 함, 비용 최소화)"""
    try:
        data = request.get_json()
        company_name = data.get("company_name")
        year = int(data.get("year"))
        month = int(data.get("month"))
        
        if not company_name or company_name == "all":
            return jsonify({"status": "error", "message": "업체를 선택해주세요"}), 400
        
        # GCS 버킷에서 스냅샷 파일 메타데이터만 확인 (파일 다운로드 안 함)
        PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "winged-precept-443218-v8")
        GCS_BUCKET = os.environ.get("GCS_BUCKET", "winged-precept-443218-v8.appspot.com")
        
        month_str = f"{year}-{month:02d}"
        
        # 여러 경로 시도
        blob_paths = [
            f"ai-reports/monthly/{company_name}/{month_str}/snapshot.json.gz",
            f"ai-reports/monthly/{company_name.lower()}/{month_str}/snapshot.json.gz",
            f"ai-reports/monthly/{company_name}/{month_str}/snapshot.json",
            f"ai-reports/monthly/{company_name.lower()}/{month_str}/snapshot.json",
        ]
        
        try:
            client = storage.Client(project=PROJECT_ID)
            bucket = client.bucket(GCS_BUCKET)
            
            # 여러 경로 시도 (메타데이터만 확인, 파일 다운로드 안 함)
            blob = None
            for blob_path in blob_paths:
                test_blob = bucket.blob(blob_path)
                if test_blob.exists():
                    blob = test_blob
                    # 메타데이터만 가져오기 (파일 다운로드 안 함)
                    blob.reload()
                    break
            
            if not blob:
                return jsonify({
                    "status": "error",
                    "message": f"{year}년 {month}월 리포트가 아직 생성되지 않았습니다."
                }), 404
            
            # 파일 수정 시간만 반환 (ISO 형식)
            return jsonify({
                "status": "success",
                "snapshot_updated": blob.updated.isoformat() if blob.updated else None,
                "snapshot_created": blob.time_created.isoformat() if blob.time_created else None
            }), 200
            
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"스냅샷 파일 확인 중 오류가 발생했습니다: {str(e)}"
            }), 500
            
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

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


# ─────────────────────────────────────────────────────────────
# 📌 Batch Dashboard Data API (Single Request)
#     POST  /dashboard/get_batch_dashboard_data
# ─────────────────────────────────────────────────────────────

@data_blueprint.route("/get_batch_dashboard_data", methods=["POST"])
def get_batch_dashboard_data_route():
    """
    대시보드 초기 로딩을 위한 통합 API
    모든 위젯 데이터를 한 번의 요청으로 병렬 처리하여 반환
    """
    t0 = time.time()
    try:
        data = request.get_json()
        user_id = session.get("user_id")
        raw_company_name = data.get("company_name", "all")

        # ✅ company_name 처리 (기존 로직과 동일)
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
                    "cafe24_sales": [],
                    "cafe24_product_sales": [],
                    "ga4_source_summary": [],
                    "viewitem_summary": [],
                    "monthly_net_sales_visitors": [],
                    "platform_sales_summary": [],
                    "platform_sales_ratio": [],
                    "product_sales_ratio": []
                }), 200
            company_name = name

        # ✅ 공통 파라미터 처리
        period = str(data.get("period", "today")).strip()
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        
        # ✅ 추가 파라미터 (기본값 적용)
        date_type = str(data.get("date_type", "summary")).strip()
        date_sort = str(data.get("date_sort", "desc")).strip()
        sort_by = str(data.get("sort_by", "sales")).strip()
        platform_date_type = str(data.get("platform_date_type", "summary")).strip()
        platform_date_sort = str(data.get("platform_date_sort", "desc")).strip()

        # ✅ 기간 필터 처리
        if period and period not in ["monthly_net_sales_visitors", "platform_sales_monthly"]:
            if not period:
                period = "manual"
            try:
                start_date, end_date = get_start_end_dates(period, start_date, end_date)
            except ValueError as ve:
                return jsonify({"status": "error", "message": str(ve)}), 400

        print(f"[BATCH_API] 요청 - company_name={company_name}, period={period}, "
              f"start_date={start_date}, end_date={end_date}")

        # ✅ 응답 데이터 초기화
        response_data = {
            "status": "success",
            "performance_summary": [],
            "performance_summary_total_count": 0,
            "latest_update": None,
            "cafe24_sales": [],
            "cafe24_sales_total_count": 0,
            "cafe24_product_sales": [],
            "cafe24_product_sales_total_count": 0,
            "ga4_source_summary": [],
            "ga4_source_summary_total_count": 0,
            "viewitem_summary": [],
            "viewitem_summary_total_count": 0,
            "monthly_net_sales_visitors": [],
            "monthly_net_sales_visitors_total_count": 0,
            "platform_sales_summary": [],
            "platform_sales_summary_total_count": 0,
            "platform_sales_ratio": [],
            "product_sales_ratio": []
        }
        
        timing_log = {}
        fetch_tasks = []

        # ✅ ThreadPoolExecutor로 병렬 처리
        with ThreadPoolExecutor() as executor:
            # 1. Performance Summary
            def fetch_performance():
                try:
                    t1 = time.time()
                    performance_data = get_performance_summary_new(
                        company_name=company_name,
                        start_date=start_date,
                        end_date=end_date,
                        user_id=user_id
                    )
                    t2 = time.time()
                    timing_log["performance_summary"] = round(t2-t1, 3)
                    
                    latest_update = None
                    if performance_data:
                        for row in performance_data:
                            if row.get("updated_at"):
                                if hasattr(row["updated_at"], 'isoformat'):
                                    latest_update = row["updated_at"].isoformat()
                                else:
                                    latest_update = str(row["updated_at"])
                                break
                    
                    return ("performance_summary", performance_data[:100], len(performance_data), latest_update)
                except Exception as e:
                    print(f"[ERROR] Performance Summary 오류: {type(e).__name__}: {str(e)}")
                    return ("performance_summary", [], 0, None)
            
            fetch_tasks.append(executor.submit(fetch_performance))
            
            # 2. Cafe24 Sales
            def fetch_cafe24_sales():
                try:
                    t1 = time.time()
                    result = get_cafe24_sales_data(
                        company_name, period, start_date, end_date,
                        date_type, date_sort, limit=30, page=1, user_id=user_id
                    )
                    t2 = time.time()
                    timing_log["cafe24_sales"] = round(t2-t1, 3)
                    return ("cafe24_sales", result.get("rows", []), result.get("total_count", 0))
                except Exception as e:
                    print(f"[ERROR] Cafe24 Sales 오류: {type(e).__name__}: {str(e)}")
                    return ("cafe24_sales", [], 0)
            
            fetch_tasks.append(executor.submit(fetch_cafe24_sales))
            
            # 3. Cafe24 Product Sales
            def fetch_cafe24_product_sales():
                try:
                    t1 = time.time()
                    result = get_cafe24_product_sales(
                        company_name, period, start_date, end_date,
                        sort_by=sort_by, limit=13, page=1, user_id=user_id
                    )
                    t2 = time.time()
                    timing_log["cafe24_product_sales"] = round(t2-t1, 3)
                    return ("cafe24_product_sales", result.get("rows", []), result.get("total_count", 0))
                except Exception as e:
                    print(f"[ERROR] Cafe24 Product Sales 오류: {type(e).__name__}: {str(e)}")
                    return ("cafe24_product_sales", [], 0)
            
            fetch_tasks.append(executor.submit(fetch_cafe24_product_sales))
            
            # 4. GA4 Source Summary
            def fetch_ga4_source_summary():
                try:
                    t1 = time.time()
                    if not start_date or not end_date:
                        print(f"[ERROR] GA4 Source Summary - start_date 또는 end_date가 없습니다!")
                        return ("ga4_source_summary", [], 0)
                    
                    cache_buster = data.get('_cache_buster')
                    data_rows = get_ga4_source_summary(company_name, start_date, end_date, limit=100, _cache_buster=cache_buster)
                    t2 = time.time()
                    timing_log["ga4_source_summary"] = round(t2-t1, 3)
                    return ("ga4_source_summary", data_rows[:100], len(data_rows))
                except Exception as e:
                    print(f"[ERROR] GA4 Source Summary 오류: {type(e).__name__}: {str(e)}")
                    return ("ga4_source_summary", [], 0)
            
            fetch_tasks.append(executor.submit(fetch_ga4_source_summary))
            
            # 5. ViewItem Summary
            def fetch_viewitem_summary():
                try:
                    t1 = time.time()
                    if not start_date or not end_date:
                        print(f"[ERROR] ViewItem Summary - start_date 또는 end_date가 없습니다!")
                        return ("viewitem_summary", [], 0)
                    
                    data_rows = get_viewitem_summary(company_name, start_date, end_date, limit=500)
                    t2 = time.time()
                    timing_log["viewitem_summary"] = round(t2-t1, 3)
                    return ("viewitem_summary", data_rows, len(data_rows))
                except Exception as e:
                    print(f"[ERROR] ViewItem Summary 오류: {type(e).__name__}: {str(e)}")
                    return ("viewitem_summary", [], 0)
            
            fetch_tasks.append(executor.submit(fetch_viewitem_summary))
            
            # 6. Monthly Net Sales & Visitors
            def fetch_monthly_net_sales_visitors():
                try:
                    t1 = time.time()
                    data_rows = get_monthly_net_sales_visitors(company_name)
                    t2 = time.time()
                    timing_log["monthly_net_sales_visitors"] = round(t2-t1, 3)
                    return ("monthly_net_sales_visitors", data_rows, len(data_rows))
                except Exception as e:
                    print(f"[ERROR] Monthly Net Sales Visitors 오류: {type(e).__name__}: {str(e)}")
                    return ("monthly_net_sales_visitors", [], 0)
            
            fetch_tasks.append(executor.submit(fetch_monthly_net_sales_visitors))
            
            # 7. Platform Sales Summary
            def fetch_platform_sales_summary():
                try:
                    t1 = time.time()
                    from ..services.platform_sales_summary import get_platform_sales_by_day
                    _company_names = company_name if isinstance(company_name, list) else [company_name]
                    
                    if not start_date or not end_date:
                        print(f"[ERROR] Platform Sales Summary - start_date 또는 end_date가 없습니다!")
                        return ("platform_sales_summary", [], 0)
                    
                    data_rows = get_platform_sales_by_day(
                        company_names=_company_names,
                        start_date=start_date,
                        end_date=end_date,
                        date_type=platform_date_type,
                        date_sort=platform_date_sort
                    )
                    t2 = time.time()
                    timing_log["platform_sales_summary"] = round(t2-t1, 3)
                    return ("platform_sales_summary", data_rows, len(data_rows))
                except Exception as e:
                    print(f"[ERROR] Platform Sales Summary 오류: {type(e).__name__}: {str(e)}")
                    return ("platform_sales_summary", [], 0)
            
            fetch_tasks.append(executor.submit(fetch_platform_sales_summary))
            
            # 8. Platform Sales Ratio
            def fetch_platform_sales_ratio():
                try:
                    t1 = time.time()
                    from ..services.platform_sales_summary import get_platform_sales_ratio
                    _company_names = company_name if isinstance(company_name, list) else [company_name]
                    
                    if not start_date or not end_date:
                        print(f"[ERROR] Platform Sales Ratio - start_date 또는 end_date가 없습니다!")
                        return ("platform_sales_ratio", [])
                    
                    data_rows = get_platform_sales_ratio(
                        company_names=_company_names,
                        start_date=start_date,
                        end_date=end_date
                    )
                    t2 = time.time()
                    timing_log["platform_sales_ratio"] = round(t2-t1, 3)
                    return ("platform_sales_ratio", data_rows)
                except Exception as e:
                    print(f"[ERROR] Platform Sales Ratio 오류: {type(e).__name__}: {str(e)}")
                    return ("platform_sales_ratio", [])
            
            fetch_tasks.append(executor.submit(fetch_platform_sales_ratio))
            
            # 9. Product Sales Ratio
            def fetch_product_sales_ratio():
                try:
                    t1 = time.time()
                    from ..services.product_sales_ratio import get_product_sales_ratio
                    _company_names = company_name if isinstance(company_name, list) else [company_name]
                    
                    if not start_date or not end_date:
                        print(f"[ERROR] Product Sales Ratio - start_date 또는 end_date가 없습니다!")
                        return ("product_sales_ratio", [])
                    
                    data_rows = get_product_sales_ratio(
                        _company_names, start_date, end_date, limit=50, user_id=user_id
                    )
                    t2 = time.time()
                    timing_log["product_sales_ratio"] = round(t2-t1, 3)
                    return ("product_sales_ratio", data_rows)
                except Exception as e:
                    print(f"[ERROR] Product Sales Ratio 오류: {type(e).__name__}: {str(e)}")
                    return ("product_sales_ratio", [])
            
            fetch_tasks.append(executor.submit(fetch_product_sales_ratio))

        # ✅ 결과 수집
        for future in fetch_tasks:
            try:
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
                elif result[0] == "ga4_source_summary":
                    response_data["ga4_source_summary"] = result[1]
                    response_data["ga4_source_summary_total_count"] = result[2]
                elif result[0] == "viewitem_summary":
                    response_data["viewitem_summary"] = result[1]
                    response_data["viewitem_summary_total_count"] = result[2]
                elif result[0] == "monthly_net_sales_visitors":
                    response_data["monthly_net_sales_visitors"] = result[1]
                    response_data["monthly_net_sales_visitors_total_count"] = result[2]
                elif result[0] == "platform_sales_summary":
                    response_data["platform_sales_summary"] = result[1]
                    response_data["platform_sales_summary_total_count"] = result[2]
                elif result[0] == "platform_sales_ratio":
                    response_data["platform_sales_ratio"] = result[1]
                elif result[0] == "product_sales_ratio":
                    response_data["product_sales_ratio"] = result[1]
            except Exception as e:
                print(f"[ERROR] Future 결과 처리 오류: {type(e).__name__}: {str(e)}")
                # 개별 실패는 무시하고 계속 진행

        t_end = time.time()
        print("[BATCH_API] /dashboard/get_batch_dashboard_data timing:", timing_log, "total:", round(t_end-t0, 3), "s")
        return jsonify(response_data), 200

    except TypeError as te:
        print(f"[ERROR] Batch API 요청 데이터 타입 오류: {te}")
        return jsonify({"status": "error", "message": f"잘못된 요청 형식: {str(te)}"}), 400

    except Exception as e:
        print(f"[ERROR] Batch API 데이터 조회 중 오류 발생: {e}")
        return jsonify({"status": "error", "message": f"데이터 조회 중 오류 발생: {str(e)}"}), 500


# ─────────────────────────────────────────────────────────────
# 📌 29CM 트렌드 API
# ─────────────────────────────────────────────────────────────

@data_blueprint.route("/trend", methods=["POST"])
def get_trend_data():
    """29CM 트렌드 데이터 조회 (스냅샷 우선, 없으면 BigQuery 조회)"""
    try:
        data = request.get_json() or {}
        tab_names = data.get("tab_names")  # 리스트로 받아서 여러 탭 한 번에 처리
        tab_name = data.get("tab_name")  # 단일 탭 (하위 호환)
        trend_type = data.get("trend_type", "all")  # "rising", "new_entry", "rank_drop", "all"
        company_name = data.get("company_name")  # 현재 로그인한 업체명 (자사몰 필터링용)
        
        # 주차 정보 조회 (스냅샷 경로 생성을 위해)
        current_week = get_current_week_info()
        if not current_week:
            return jsonify({"status": "error", "message": "주차 정보를 찾을 수 없습니다."}), 404
        
        # 스냅샷에서 로드 시도 (우선순위 1: GCS 버킷)
        # ✅ 업체명 폴더 구조 사용
        snapshot_data = load_trend_snapshot_from_gcs(current_week, company_name) if company_name else None
        
        if snapshot_data:
            # 스냅샷 데이터 사용 (GCS 버킷에서 로드 성공)
            print(f"[INFO] ✅ GCS 스냅샷에서 트렌드 데이터 로드 성공: {current_week}")
            
            if tab_names and isinstance(tab_names, list):
                # 여러 탭 처리
                # AI 리포트 필터링 (현재 업체에 해당하는 자사몰 섹션만 포함)
                insights = snapshot_data.get("insights", {})
                
                # ✅ 리포트가 있으면 무조건 표시 (Section 1만 필터링)
                # 브랜드 체크와 관계없이 리포트는 항상 반환
                if company_name and insights.get("analysis_report"):
                    # 리포트가 있으면 Section 1만 필터링하고 항상 반환
                    analysis_report = insights.get("analysis_report", "")
                    filtered_report = filter_ai_report_by_company(
                        analysis_report,
                        company_name.lower() if isinstance(company_name, str) else company_name
                    )
                    insights = insights.copy()
                    insights["analysis_report"] = filtered_report
                elif company_name:
                    # company_name이 있지만 insights에 analysis_report가 없는 경우
                    # insights 자체가 없으면 빈 객체 유지
                    if not insights:
                        insights = {}
                
                result = {
                    "status": "success",
                    "current_week": snapshot_data.get("current_week", current_week),
                    "tabs_data": {},
                    "insights": insights  # 필터링된 AI 분석 리포트 포함
                }
                
                for tab in tab_names:
                    tab_data = snapshot_data.get("tabs_data", {}).get(tab, {})
                    if trend_type == "all":
                        result["tabs_data"][tab] = tab_data
                    else:
                        filtered_data = {}
                        if trend_type == "rising" and "rising_star" in tab_data:
                            filtered_data["rising_star"] = tab_data["rising_star"]
                        if trend_type == "new_entry" and "new_entry" in tab_data:
                            filtered_data["new_entry"] = tab_data["new_entry"]
                        if trend_type == "rank_drop" and "rank_drop" in tab_data:
                            filtered_data["rank_drop"] = tab_data["rank_drop"]
                        result["tabs_data"][tab] = filtered_data
                
                return jsonify(result), 200
            else:
                # 단일 탭 처리 (하위 호환)
                tab_name = tab_name or "전체"
                tab_data = snapshot_data.get("tabs_data", {}).get(tab_name, {})
                
                # AI 리포트 필터링 (현재 업체에 해당하는 자사몰 섹션만 포함)
                insights = snapshot_data.get("insights", {})
                
                # ✅ 업체별로 insights가 없으면 빈 객체 반환 (버킷이 없는 업체)
                # insights의 analysis_report를 확인하여 현재 업체의 브랜드가 포함되어 있는지 확인
                if company_name and insights.get("analysis_report"):
                    # 현재 업체의 브랜드명 목록 가져오기
                    company_ko = get_company_korean_name(company_name.lower())
                    company_brands = []
                    if company_ko and COMPANY_MAPPING_AVAILABLE:
                        company_info = COMPANY_MAPPING.get(company_name.lower(), {})
                        company_brands = company_info.get("brands", [])
                    
                    # insights 리포트에 현재 업체의 브랜드가 포함되어 있는지 확인
                    analysis_report = insights.get("analysis_report", "")
                    has_company_brand = False
                    if company_ko and analysis_report:
                        # 리포트에 현재 업체의 브랜드명이 포함되어 있는지 확인
                        for brand in company_brands:
                            if brand in analysis_report:
                                has_company_brand = True
                                break
                        # 한글명도 확인
                        if company_ko in analysis_report:
                            has_company_brand = True
                    
                    if has_company_brand:
                        # 현재 업체의 브랜드가 포함되어 있으면 필터링
                        filtered_report = filter_ai_report_by_company(
                            analysis_report,
                            company_name.lower() if isinstance(company_name, str) else company_name
                        )
                        insights = insights.copy()
                        insights["analysis_report"] = filtered_report
                    else:
                        # 현재 업체의 브랜드가 포함되어 있지 않으면 빈 객체 반환
                        insights = {}
                elif company_name:
                    # 해당 업체의 insights가 없으면 빈 객체로 설정
                    insights = {}
                elif company_name:
                    # 해당 업체의 insights가 없으면 빈 객체로 설정
                    insights = {}
                
                result = {
                    "status": "success",
                    "tab_name": tab_name,
                    "current_week": snapshot_data.get("current_week", current_week),
                    "insights": insights  # 필터링된 AI 분석 리포트 포함
                }
                
                if trend_type == "all":
                    result["rising_star"] = tab_data.get("rising_star", [])
                    result["new_entry"] = tab_data.get("new_entry", [])
                    result["rank_drop"] = tab_data.get("rank_drop", [])
                else:
                    if trend_type == "rising" or trend_type == "all":
                        result["rising_star"] = tab_data.get("rising_star", [])
                    if trend_type == "new_entry" or trend_type == "all":
                        result["new_entry"] = tab_data.get("new_entry", [])
                    if trend_type == "rank_drop" or trend_type == "all":
                        result["rank_drop"] = tab_data.get("rank_drop", [])
                
                return jsonify(result), 200
        else:
            # 스냅샷이 없으면 BigQuery에서 조회 (Fallback)
            print(f"[WARN] ⚠️ GCS 스냅샷 없음, BigQuery에서 직접 조회 (비용 발생): {current_week}")
            
            if tab_names and isinstance(tab_names, list):
                # 여러 탭 데이터를 한 번에 반환
                result = {
                    "status": "success",
                    "tabs_data": {},
                    "current_week": current_week
                }
                
                # 각 탭별 데이터 조회
                for tab in tab_names:
                    tab_data = {}
                    if trend_type == "rising" or trend_type == "all":
                        tab_data["rising_star"] = get_rising_star(tab)
                    if trend_type == "new_entry" or trend_type == "all":
                        tab_data["new_entry"] = get_new_entry(tab)
                    if trend_type == "rank_drop" or trend_type == "all":
                        tab_data["rank_drop"] = get_rank_drop(tab)
                    result["tabs_data"][tab] = tab_data
                
                return jsonify(result), 200
            else:
                # 단일 탭 처리 (하위 호환)
                tab_name = tab_name or "전체"
                result = {
                    "status": "success",
                    "tab_name": tab_name,
                    "current_week": current_week
                }
                
                # 트렌드 타입별 데이터 조회
                if trend_type == "rising" or trend_type == "all":
                    result["rising_star"] = get_rising_star(tab_name)
                
                if trend_type == "new_entry" or trend_type == "all":
                    result["new_entry"] = get_new_entry(tab_name)
                
                if trend_type == "rank_drop" or trend_type == "all":
                    result["rank_drop"] = get_rank_drop(tab_name)
                
                return jsonify(result), 200
        
    except Exception as e:
        print(f"[ERROR] get_trend_data 실패: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


@data_blueprint.route("/trend/snapshot/create", methods=["POST"])
def create_trend_snapshot():
    """트렌드 스냅샷 생성 (수동 실행용, 스케줄 추가 예정)"""
    try:
        data = request.get_json() or {}
        tab_names = data.get("tab_names", [])
        
        if not tab_names:
            # 기본 탭 목록 조회
            tab_names = get_available_tabs()
        
        # 주차 정보 조회
        current_week = get_current_week_info()
        if not current_week:
            return jsonify({"status": "error", "message": "주차 정보를 찾을 수 없습니다."}), 404
        
        # 모든 탭 데이터 조회 (캐시 무시하고 직접 조회)
        print(f"[INFO] 스냅샷 생성 시작: {current_week}")
        tabs_data = get_all_tabs_data_from_bigquery(tab_names)
        
        # GCS에 저장
        success = save_trend_snapshot_to_gcs(current_week, tabs_data, current_week)
        
        if success:
            return jsonify({
                "status": "success",
                "message": f"스냅샷 생성 완료: {current_week}",
                "run_id": current_week,
                "tabs_count": len(tab_names)
            }), 200
        else:
            return jsonify({"status": "error", "message": "스냅샷 저장 실패"}), 500
        
    except Exception as e:
        print(f"[ERROR] create_trend_snapshot 실패: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


@data_blueprint.route("/get_meta_token", methods=["POST"])
def get_meta_token():
    """Meta API 액세스 토큰 반환 (클라이언트에서 직접 API 호출용)

    토큰 조회 우선순위:
    1. 환경 변수 META_SYSTEM_USER_TOKEN (마케팅 대행사 마스터 권한)
    2. 환경 변수 META_LONG_TOKEN (기존 방식)
    3. 세션에서 meta_token
    """
    try:
        # 개발 환경 체크 (FLASK_ENV=development 시 인증 스킵)
        is_dev = os.getenv("FLASK_ENV") == "development"

        # 1순위: 환경 변수 META_SYSTEM_USER_TOKEN (마케팅 대행사 마스터 권한)
        access_token = os.getenv("META_SYSTEM_USER_TOKEN")
        if access_token:
            print(f"[INFO] META_SYSTEM_USER_TOKEN 환경 변수에서 토큰 발견")
            print(f"[INFO] 토큰 반환 성공: {access_token[:10]}...")
            return jsonify({
                "status": "success",
                "access_token": access_token
            }), 200

        # 2순위: 기존 load_access_token (META_LONG_TOKEN)
        from ..services.meta_demo_service import load_access_token
        access_token = load_access_token()
        if access_token:
            print(f"[INFO] META_LONG_TOKEN 환경 변수에서 토큰 발견")
            print(f"[INFO] 토큰 반환 성공: {access_token[:10]}...")
            return jsonify({
                "status": "success",
                "access_token": access_token
            }), 200

        # 3순위: 세션에서 토큰 확인
        access_token = session.get("meta_token")
        if access_token:
            print(f"[INFO] 세션에서 토큰 발견")
            print(f"[INFO] 토큰 반환 성공: {access_token[:10]}...")
            return jsonify({
                "status": "success",
                "access_token": access_token
            }), 200

        # 토큰 없음
        print("[ERROR] Meta 액세스 토큰을 찾을 수 없습니다 (모든 소스 확인 완료)")
        return jsonify({"status": "error", "message": "Meta 액세스 토큰이 없습니다"}), 401

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


@data_blueprint.route("/generate_ad_preview", methods=["POST"])
def generate_ad_preview():
    """Meta API를 사용하여 광고 미리보기 생성

    요청 파라미터:
    - account_id: 광고 계정 ID
    - ad_format: INSTAGRAM_STANDARD, INSTAGRAM_REELS, MOBILE_FEED_STANDARD
    - media_type: image 또는 video
    - image_hash: 이미지 해시 (이미지용)
    - video_id: 비디오 ID (동영상용)
    - link: 웹사이트 URL
    - message: Primary Text
    - name: Headline
    - description: Description
    - cta_type: Call to Action 타입
    - is_carousel: 슬라이드 여부 (선택)
    - cards: 슬라이드 카드 배열 (선택)
    """
    import requests
    import json

    print("[PREVIEW] ===== 광고 미리보기 생성 시작 =====")

    try:
        data = request.get_json()
        print(f"[PREVIEW] 요청 데이터: {json.dumps(data, indent=2, ensure_ascii=False)}")

        # 필수 파라미터 확인
        account_id = data.get('account_id')
        ad_format = data.get('ad_format', 'INSTAGRAM_STANDARD')
        media_type = data.get('media_type', 'image')

        if not account_id:
            print("[PREVIEW] ERROR: account_id 누락")
            return jsonify({"status": "error", "message": "account_id가 필요합니다"}), 400

        # 액세스 토큰 가져오기
        access_token = os.getenv("META_SYSTEM_USER_TOKEN") or os.getenv("META_LONG_TOKEN")
        if not access_token:
            print("[PREVIEW] ERROR: 액세스 토큰 없음")
            return jsonify({"status": "error", "message": "Meta 액세스 토큰이 없습니다"}), 401

        print(f"[PREVIEW] 토큰 확인: {access_token[:15]}...")

        # BigQuery에서 page_id, instagram_user_id 조회
        bq_client = bigquery.Client()
        mapping_query = """
            SELECT page_id, instagram_user_id
            FROM `ngn_dataset.meta_account_mapping`
            WHERE account_id = @account_id
            LIMIT 1
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("account_id", "STRING", account_id)
            ]
        )
        mapping_result = bq_client.query(mapping_query, job_config=job_config).result()
        mapping_row = None
        for row in mapping_result:
            mapping_row = row
            break

        page_id = None
        instagram_user_id = None

        if mapping_row:
            # 값 trim 및 유효성 검사
            page_id = str(mapping_row.page_id).strip() if mapping_row.page_id else None
            instagram_user_id = str(mapping_row.instagram_user_id).strip() if mapping_row.instagram_user_id else None
            print(f"[PREVIEW] BigQuery에서 조회 - page_id: '{page_id}', instagram_user_id: '{instagram_user_id}'")
        else:
            print(f"[PREVIEW] BigQuery에 account_id={account_id} 매핑 없음, Meta API로 폴백")
            # 폴백: Meta API에서 Page ID 조회
            pages_url = "https://graph.facebook.com/v24.0/me/accounts"
            pages_response = requests.get(pages_url, params={
                "access_token": access_token,
                "fields": "id,name"
            }, timeout=10)
            pages_data = pages_response.json()
            print(f"[PREVIEW] Pages 응답: {json.dumps(pages_data, indent=2)}")

            if 'data' in pages_data and len(pages_data['data']) > 0:
                page_id = pages_data['data'][0]['id']

        if not page_id:
            print("[PREVIEW] ERROR: page_id를 찾을 수 없음")
            return jsonify({"status": "error", "message": "연결된 Facebook 페이지가 없습니다"}), 400

        # Facebook Page에서 연결된 Instagram Business Account 조회 (항상 최신 정보)
        try:
            ig_url = f"https://graph.facebook.com/v24.0/{page_id}"
            ig_response = requests.get(ig_url, params={
                "access_token": access_token,
                "fields": "instagram_business_account"
            }, timeout=10)
            ig_data = ig_response.json()
            print(f"[PREVIEW] Page Instagram 연결 조회: {json.dumps(ig_data, indent=2)}")

            if 'instagram_business_account' in ig_data:
                fetched_ig_id = ig_data['instagram_business_account'].get('id')
                if fetched_ig_id:
                    instagram_user_id = fetched_ig_id
                    print(f"[PREVIEW] Page에서 Instagram ID 가져옴: {instagram_user_id}")
        except Exception as e:
            print(f"[PREVIEW] Instagram 계정 조회 실패: {e}")

        print(f"[PREVIEW] 사용할 Page ID: {page_id}, Instagram User ID: {instagram_user_id}")

        # creative_spec 구성
        link = data.get('link', 'https://example.com')
        message = data.get('message', '')
        headline = data.get('name', '')
        description = data.get('description', '')
        cta_type = data.get('cta_type', 'SHOP_NOW')
        image_hash = data.get('image_hash')
        video_id = data.get('video_id')
        is_carousel = data.get('is_carousel', False)
        cards = data.get('cards', [])

        creative_spec = {
            "object_story_spec": {
                "page_id": page_id
            }
        }

        # Instagram 포맷인 경우 instagram_user_id 추가 (Meta API v24.0 규격)
        is_instagram_format = ad_format in ['INSTAGRAM_STANDARD', 'INSTAGRAM_REELS', 'INSTAGRAM_STORY']
        if is_instagram_format and instagram_user_id:
            creative_spec["object_story_spec"]["instagram_user_id"] = instagram_user_id
            print(f"[PREVIEW] Instagram 포맷 - instagram_user_id 추가: {instagram_user_id}")

        if is_carousel and len(cards) > 1:
            # 슬라이드 (Carousel) 광고
            print(f"[PREVIEW] 슬라이드 광고 생성: {len(cards)}개 카드")
            child_attachments = []
            for i, card in enumerate(cards):
                attachment = {
                    "link": card.get('link', link),
                    "name": card.get('name', headline),
                    "description": card.get('description', description),
                    "call_to_action": {"type": cta_type}
                }
                # video_id를 먼저 확인 (동영상 우선)
                if card.get('video_id'):
                    attachment["video_id"] = card['video_id']
                elif card.get('image_hash'):
                    attachment["image_hash"] = card['image_hash']
                child_attachments.append(attachment)
                print(f"[PREVIEW] 카드 {i+1}: {attachment}")

            creative_spec["object_story_spec"]["link_data"] = {
                "link": link,
                "message": message,
                "child_attachments": child_attachments,
                "multi_share_optimized": True
            }
        else:
            # 단일 이미지/동영상 광고
            if media_type == 'video' and video_id:
                print(f"[PREVIEW] 단일 동영상 광고: video_id={video_id}")

                # 동영상 썸네일 URL 가져오기 (Meta API 필수 요구사항)
                thumbnail_url = None
                try:
                    thumb_response = requests.get(
                        f"https://graph.facebook.com/v24.0/{video_id}",
                        params={
                            "access_token": access_token,
                            "fields": "thumbnails"
                        },
                        timeout=10
                    )
                    thumb_data = thumb_response.json()
                    print(f"[PREVIEW] 썸네일 응답: {json.dumps(thumb_data, indent=2)}")

                    if 'thumbnails' in thumb_data and 'data' in thumb_data['thumbnails']:
                        thumbnails = thumb_data['thumbnails']['data']
                        if thumbnails:
                            thumbnail_url = thumbnails[0].get('uri')
                            print(f"[PREVIEW] 썸네일 URL: {thumbnail_url}")
                except Exception as e:
                    print(f"[PREVIEW] 썸네일 조회 실패: {e}")

                video_data = {
                    "video_id": video_id,
                    "message": message,
                    "title": headline,
                    "link_description": description,
                    "call_to_action": {
                        "type": cta_type,
                        "value": {"link": link}
                    }
                }

                # 썸네일 URL 추가 (필수)
                if thumbnail_url:
                    video_data["image_url"] = thumbnail_url
                else:
                    # 폴백: 투명 1x1 픽셀 또는 기본 이미지
                    video_data["image_url"] = "https://via.placeholder.com/1080x1920/000000/000000?text=+"
                    print("[PREVIEW] 썸네일 없음, 플레이스홀더 사용")

                creative_spec["object_story_spec"]["video_data"] = video_data
            elif image_hash:
                print(f"[PREVIEW] 단일 이미지 광고: image_hash={image_hash}")
                creative_spec["object_story_spec"]["link_data"] = {
                    "image_hash": image_hash,
                    "link": link,
                    "message": message,
                    "name": headline,
                    "description": description,
                    "call_to_action": {"type": cta_type}
                }
            else:
                print("[PREVIEW] ERROR: image_hash 또는 video_id 필요")
                return jsonify({"status": "error", "message": "이미지 해시 또는 비디오 ID가 필요합니다"}), 400

        print(f"[PREVIEW] creative_spec: {json.dumps(creative_spec, indent=2)}")

        # Meta API 호출 (GET 방식 + 재시도 로직)
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry

        ad_account_id = f"act_{account_id}"
        preview_url = f"https://graph.facebook.com/v24.0/{ad_account_id}/generatepreviews"

        # GET 파라미터 구성 (JSON 압축으로 URL 길이 최소화)
        api_params = {
            "access_token": access_token,
            "creative": json.dumps(creative_spec, separators=(',', ':')),  # 공백 제거
            "ad_format": ad_format
        }

        print(f"[PREVIEW] API 호출 (GET): {preview_url}")
        print(f"[PREVIEW] ad_format: {ad_format}")

        # 재시도 전략 설정 (최대 3회, backoff factor 적용)
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session = requests.Session()
        session.mount("https://", adapter)

        response = session.get(preview_url, params=api_params, timeout=30)
        result = response.json()

        print(f"[PREVIEW] API 응답 상태: {response.status_code}")
        print(f"[PREVIEW] API 응답: {json.dumps(result, indent=2)}")

        if 'error' in result:
            error_msg = result['error'].get('message', '알 수 없는 오류')
            error_code = result['error'].get('code', '')
            print(f"[PREVIEW] ERROR: {error_code} - {error_msg}")
            return jsonify({
                "status": "error",
                "message": f"Meta API 오류: {error_msg}",
                "error_code": error_code
            }), 400

        if 'data' in result and len(result['data']) > 0:
            preview_html = result['data'][0].get('body', '')
            print(f"[PREVIEW] 미리보기 HTML 길이: {len(preview_html)}")
            print("[PREVIEW] ===== 미리보기 생성 성공 =====")
            return jsonify({
                "status": "success",
                "preview_html": preview_html
            }), 200
        else:
            print("[PREVIEW] ERROR: 미리보기 데이터 없음")
            return jsonify({
                "status": "error",
                "message": "미리보기 데이터가 없습니다"
            }), 400

    except requests.exceptions.Timeout:
        print("[PREVIEW] ERROR: API 요청 타임아웃")
        return jsonify({"status": "error", "message": "Meta API 요청 시간 초과"}), 504
    except requests.exceptions.RequestException as e:
        print(f"[PREVIEW] ERROR: 네트워크 오류 - {e}")
        return jsonify({"status": "error", "message": f"네트워크 오류: {str(e)}"}), 500
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[PREVIEW] ERROR: 예외 발생 - {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@data_blueprint.route("/trend/tabs", methods=["GET"])
def get_trend_tabs():
    """사용 가능한 탭 목록 조회"""
    try:
        tabs = get_available_tabs()
        return jsonify({"status": "success", "tabs": tabs}), 200
    except Exception as e:
        print(f"[ERROR] get_trend_tabs 실패: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# ─────────────────────────────────────────────────────────────
# 📌 Ably 트렌드 API
# ─────────────────────────────────────────────────────────────

@data_blueprint.route("/trend/ably", methods=["POST"])
def get_ably_trend_data():
    """Ably 트렌드 데이터 조회 (스냅샷 우선, 없으면 BigQuery 조회)"""
    try:
        data = request.get_json() or {}
        tab_names = data.get("tab_names")  # 리스트로 받아서 여러 탭 한 번에 처리
        tab_name = data.get("tab_name")  # 단일 탭 (하위 호환)
        trend_type = data.get("trend_type", "all")  # "rising", "new_entry", "rank_drop", "all"
        company_name = data.get("company_name")  # 현재 로그인한 업체명 (자사몰 필터링용)
        
        # 주차 정보 조회 (스냅샷 경로 생성을 위해)
        current_week = get_ably_current_week_info()
        if not current_week:
            return jsonify({"status": "error", "message": "주차 정보를 찾을 수 없습니다."}), 404
        
        # 스냅샷에서 로드 시도 (우선순위 1: GCS 버킷)
        # ✅ 업체명 폴더 구조 사용
        snapshot_data = load_ably_trend_snapshot_from_gcs(current_week, company_name) if company_name else None
        
        if snapshot_data:
            # 스냅샷 데이터 사용 (GCS 버킷에서 로드 성공)
            print(f"[INFO] ✅ GCS 스냅샷에서 Ably 트렌드 데이터 로드 성공: {current_week}")
            
            if tab_names and isinstance(tab_names, list):
                # 여러 탭 처리
                # AI 리포트 필터링 (현재 업체에 해당하는 자사몰 섹션만 포함)
                insights = snapshot_data.get("insights", {})
                
                # ✅ 리포트가 있으면 무조건 표시 (Section 1만 필터링)
                # 브랜드 체크와 관계없이 리포트는 항상 반환
                if company_name and insights.get("analysis_report"):
                    # 리포트가 있으면 Section 1만 필터링하고 항상 반환
                    analysis_report = insights.get("analysis_report", "")
                    filtered_report = filter_ai_report_by_company(
                        analysis_report,
                        company_name.lower() if isinstance(company_name, str) else company_name
                    )
                    insights = insights.copy()
                    insights["analysis_report"] = filtered_report
                elif company_name:
                    # company_name이 있지만 insights에 analysis_report가 없는 경우
                    # insights 자체가 없으면 빈 객체 유지
                    if not insights:
                        insights = {}
                
                result = {
                    "status": "success",
                    "current_week": snapshot_data.get("current_week", current_week),
                    "tabs_data": {},
                    "insights": insights  # 필터링된 AI 분석 리포트 포함
                }
                
                for tab in tab_names:
                    tab_data = snapshot_data.get("tabs_data", {}).get(tab, {})
                    if trend_type == "all":
                        result["tabs_data"][tab] = tab_data
                    else:
                        filtered_data = {}
                        if trend_type == "rising" and "rising_star" in tab_data:
                            filtered_data["rising_star"] = tab_data["rising_star"]
                        if trend_type == "new_entry" and "new_entry" in tab_data:
                            filtered_data["new_entry"] = tab_data["new_entry"]
                        if trend_type == "rank_drop" and "rank_drop" in tab_data:
                            filtered_data["rank_drop"] = tab_data["rank_drop"]
                        result["tabs_data"][tab] = filtered_data
                
                return jsonify(result), 200
            else:
                # 단일 탭 처리 (하위 호환)
                tab_name = tab_name or "상의"
                tab_data = snapshot_data.get("tabs_data", {}).get(tab_name, {})
                
                # AI 리포트 필터링 (현재 업체에 해당하는 자사몰 섹션만 포함)
                insights = snapshot_data.get("insights", {})
                
                # ✅ 업체별로 insights가 없으면 빈 객체 반환 (버킷이 없는 업체)
                # insights의 analysis_report를 확인하여 현재 업체의 브랜드가 포함되어 있는지 확인
                if company_name and insights.get("analysis_report"):
                    # 현재 업체의 브랜드명 목록 가져오기
                    company_ko = get_company_korean_name(company_name.lower())
                    company_brands = []
                    if company_ko and COMPANY_MAPPING_AVAILABLE:
                        company_info = COMPANY_MAPPING.get(company_name.lower(), {})
                        company_brands = company_info.get("brands", [])
                    
                    # insights 리포트에 현재 업체의 브랜드가 포함되어 있는지 확인
                    analysis_report = insights.get("analysis_report", "")
                    has_company_brand = False
                    if company_ko and analysis_report:
                        # 리포트에 현재 업체의 브랜드명이 포함되어 있는지 확인
                        for brand in company_brands:
                            if brand in analysis_report:
                                has_company_brand = True
                                break
                        # 한글명도 확인
                        if company_ko in analysis_report:
                            has_company_brand = True
                    
                    if has_company_brand:
                        # 현재 업체의 브랜드가 포함되어 있으면 필터링
                        filtered_report = filter_ai_report_by_company(
                            analysis_report,
                            company_name.lower() if isinstance(company_name, str) else company_name
                        )
                        insights = insights.copy()
                        insights["analysis_report"] = filtered_report
                    else:
                        # 현재 업체의 브랜드가 포함되어 있지 않으면 빈 객체 반환
                        insights = {}
                elif company_name:
                    # 해당 업체의 insights가 없으면 빈 객체로 설정
                    insights = {}
                
                result = {
                    "status": "success",
                    "tab_name": tab_name,
                    "current_week": snapshot_data.get("current_week", current_week),
                    "insights": insights  # 필터링된 AI 분석 리포트 포함
                }
                
                if trend_type == "all":
                    result["rising_star"] = tab_data.get("rising_star", [])
                    result["new_entry"] = tab_data.get("new_entry", [])
                    result["rank_drop"] = tab_data.get("rank_drop", [])
                else:
                    if trend_type == "rising" or trend_type == "all":
                        result["rising_star"] = tab_data.get("rising_star", [])
                    if trend_type == "new_entry" or trend_type == "all":
                        result["new_entry"] = tab_data.get("new_entry", [])
                    if trend_type == "rank_drop" or trend_type == "all":
                        result["rank_drop"] = tab_data.get("rank_drop", [])
                
                return jsonify(result), 200
        else:
            # 스냅샷이 없으면 BigQuery에서 조회 (Fallback)
            print(f"[WARN] ⚠️ GCS 스냅샷 없음, BigQuery에서 직접 조회 (비용 발생): {current_week}")
            
            if tab_names and isinstance(tab_names, list):
                # 여러 탭 데이터를 한 번에 반환
                result = {
                    "status": "success",
                    "tabs_data": {},
                    "current_week": current_week
                }
                
                # 각 탭별 데이터 조회
                for tab in tab_names:
                    tab_data = {}
                    if trend_type == "rising" or trend_type == "all":
                        tab_data["rising_star"] = get_ably_rising_star(tab)
                    if trend_type == "new_entry" or trend_type == "all":
                        tab_data["new_entry"] = get_ably_new_entry(tab)
                    if trend_type == "rank_drop" or trend_type == "all":
                        tab_data["rank_drop"] = get_ably_rank_drop(tab)
                    result["tabs_data"][tab] = tab_data
                
                return jsonify(result), 200
            else:
                # 단일 탭 처리 (하위 호환)
                tab_name = tab_name or "상의"
                result = {
                    "status": "success",
                    "tab_name": tab_name,
                    "current_week": current_week
                }
                
                # 트렌드 타입별 데이터 조회
                if trend_type == "rising" or trend_type == "all":
                    result["rising_star"] = get_ably_rising_star(tab_name)
                
                if trend_type == "new_entry" or trend_type == "all":
                    result["new_entry"] = get_ably_new_entry(tab_name)
                
                if trend_type == "rank_drop" or trend_type == "all":
                    result["rank_drop"] = get_ably_rank_drop(tab_name)
                
                return jsonify(result), 200
        
    except Exception as e:
        print(f"[ERROR] get_ably_trend_data 실패: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


@data_blueprint.route("/trend/ably/snapshot/create", methods=["POST"])
def create_ably_trend_snapshot():
    """Ably 트렌드 스냅샷 생성 (수동 실행용, 스케줄 추가 예정)"""
    try:
        data = request.get_json() or {}
        tab_names = data.get("tab_names", [])
        
        if not tab_names:
            # 기본 탭 목록 조회
            tab_names = get_ably_available_tabs()
        
        # 주차 정보 조회
        current_week = get_ably_current_week_info()
        if not current_week:
            return jsonify({"status": "error", "message": "주차 정보를 찾을 수 없습니다."}), 404
        
        # 모든 탭 데이터 조회 (캐시 무시하고 직접 조회)
        print(f"[INFO] Ably 스냅샷 생성 시작: {current_week}")
        tabs_data = get_ably_all_tabs_data_from_bigquery(tab_names)
        
        # GCS에 저장 (AI 분석 리포트 포함)
        success = save_ably_trend_snapshot_to_gcs(current_week, tabs_data, current_week, enable_ai_analysis=True)
        
        if success:
            return jsonify({
                "status": "success",
                "message": f"Ably 스냅샷 생성 완료: {current_week}",
                "run_id": current_week,
                "tabs_count": len(tab_names)
            }), 200
        else:
            return jsonify({"status": "error", "message": "스냅샷 저장 실패"}), 500
        
    except Exception as e:
        print(f"[ERROR] create_ably_trend_snapshot 실패: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


@data_blueprint.route("/trend/ably/tabs", methods=["GET"])
def get_ably_trend_tabs():
    """사용 가능한 Ably 탭 목록 조회"""
    try:
        tabs = get_ably_available_tabs()
        return jsonify({"status": "success", "tabs": tabs}), 200
    except Exception as e:
        print(f"[ERROR] get_ably_trend_tabs 실패: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# ─────────────────────────────────────────────────────────────
# 📌 29CM 경쟁사 비교 페이지 API
# ─────────────────────────────────────────────────────────────

@data_blueprint.route("/compare/29cm/brands", methods=["GET"])
def get_compare_brands():
    """경쟁사 브랜드 목록 조회 (brandId 기반)"""
    try:
        company_name = request.args.get("company_name")
        if not company_name:
            return jsonify({"status": "error", "message": "company_name 파라미터가 필요합니다."}), 400

        # 자사몰 브랜드 ID
        own_brand_id = get_own_brand_id(company_name)

        # 경쟁사 브랜드 목록
        competitor_brands = get_competitor_brands(company_name)

        return jsonify({
            "status": "success",
            "own_brand_id": own_brand_id,
            "brands": competitor_brands
        }), 200
    except Exception as e:
        print(f"[ERROR] get_compare_brands 실패: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@data_blueprint.route("/compare/29cm/keywords", methods=["GET"])
def get_compare_keywords_legacy():
    """[DEPRECATED] /compare/29cm/brands 사용 권장"""
    try:
        company_name = request.args.get("company_name")
        if not company_name:
            return jsonify({"status": "error", "message": "company_name 파라미터가 필요합니다."}), 400

        keywords = get_competitor_keywords(company_name)
        return jsonify({
            "status": "success",
            "keywords": keywords
        }), 200
    except Exception as e:
        print(f"[ERROR] get_compare_keywords 실패: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@data_blueprint.route("/compare/29cm/search", methods=["POST"])
def get_compare_search_results():
    """경쟁사 검색 결과 조회 (brand_id 또는 search_keyword 지원)"""
    try:
        data = request.get_json() or {}
        company_name = data.get("company_name")
        brand_id = data.get("brand_id")  # 새로운 brandId 기반
        search_keyword = data.get("search_keyword")  # 하위 호환성
        run_id = data.get("run_id")
        get_run_id_only = data.get("get_run_id_only", False)

        if not company_name:
            return jsonify({"status": "error", "message": "company_name이 필요합니다."}), 400

        # run_id만 조회하는 경우
        if get_run_id_only:
            run_id = get_current_week_info()
            if not run_id:
                return jsonify({"status": "error", "message": "주차 정보를 찾을 수 없습니다."}), 404
            return jsonify({"status": "success", "run_id": run_id}), 200

        # run_id가 없으면 최신 주차 사용
        if not run_id:
            run_id = get_current_week_info()
            if not run_id:
                return jsonify({"status": "error", "message": "주차 정보를 찾을 수 없습니다."}), 404

        # brand_id 기반 처리 (우선)
        if brand_id is not None:
            # brand_id를 문자열 키로 변환 (GCS 스냅샷 키 형식)
            brand_key = str(brand_id)

            # 자사몰 브랜드인 경우 (brand_id == 'own')
            if brand_id == 'own':
                own_brand_id = get_own_brand_id(company_name)
                if own_brand_id:
                    brand_key = str(own_brand_id)
                else:
                    return jsonify({"status": "error", "message": "자사몰 브랜드 ID를 찾을 수 없습니다."}), 404

            # GCS 스냅샷에서 검색 결과 로드
            snapshot_data = load_search_results_from_gcs(
                company_name=company_name,
                run_id=run_id,
                search_keyword=brand_key
            )

            if snapshot_data is None:
                return jsonify({"status": "error", "message": "스냅샷을 찾을 수 없습니다."}), 404

            search_results = snapshot_data.get("search_results", {})
            created_at = snapshot_data.get("created_at")

            return jsonify({
                "status": "success",
                "run_id": run_id,
                "brand_id": brand_id,
                "results": search_results.get(brand_key, []),
                "created_at": created_at
            }), 200

        # 하위 호환성: search_keyword 기반 처리
        if search_keyword == 'own':
            if COMPANY_MAPPING_AVAILABLE:
                brands = get_company_brands(company_name)
                if brands:
                    search_keyword = brands[0]
                else:
                    korean_name = get_company_korean_name(company_name)
                    if korean_name:
                        search_keyword = korean_name
                    else:
                        search_keyword = company_name
            else:
                brand_mapping = {'piscess': '파이시스'}
                search_keyword = brand_mapping.get(company_name.lower(), company_name)

        # GCS 스냅샷에서 검색 결과 로드
        snapshot_data = load_search_results_from_gcs(
            company_name=company_name,
            run_id=run_id,
            search_keyword=search_keyword if search_keyword else None
        )

        if snapshot_data is None:
            return jsonify({"status": "error", "message": "스냅샷을 찾을 수 없습니다."}), 404

        search_results = snapshot_data.get("search_results", {})
        created_at = snapshot_data.get("created_at")

        if search_keyword:
            return jsonify({
                "status": "success",
                "run_id": run_id,
                "search_keyword": search_keyword,
                "results": search_results.get(search_keyword, []),
                "created_at": created_at
            }), 200
        else:
            return jsonify({
                "status": "success",
                "run_id": run_id,
                "results": search_results,
                "created_at": created_at
            }), 200

    except Exception as e:
        print(f"[ERROR] get_compare_search_results 실패: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


@data_blueprint.route("/compare/29cm/reviews", methods=["GET"])
def get_compare_reviews():
    """상품 리뷰 조회"""
    try:
        item_id = request.args.get("item_id")
        if not item_id:
            return jsonify({"status": "error", "message": "item_id 파라미터가 필요합니다."}), 400
        
        try:
            item_id_int = int(item_id)
        except ValueError:
            return jsonify({"status": "error", "message": "item_id는 숫자여야 합니다."}), 400
        
        reviews = fetch_product_reviews(item_id_int, limit=10)
        return jsonify({
            "status": "success",
            "item_id": item_id_int,
            "reviews": reviews
        }), 200
        
    except Exception as e:
        print(f"[ERROR] get_compare_reviews 실패: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# ─────────────────────────────────────────────────────────────
# 📌 Step 4: 광고 관리 API (Ad Management)
# ─────────────────────────────────────────────────────────────

@data_blueprint.route("/get_active_ads", methods=["GET"])
def get_active_ads():
    """
    Meta API에서 활성 광고 목록 조회
    - effective_status 필터링 사용 (ACTIVE 상태)
    - 조회 순서: adset → campaign → account (폴백)
    - 썸네일 URL 포함
    """
    try:
        account_id = request.args.get("account_id")
        if not account_id:
            return jsonify({"status": "success", "ads": [], "total": 0, "message": "account_id가 필요합니다."}), 200

        # Meta API 액세스 토큰
        access_token = os.environ.get("META_SYSTEM_USER_TOKEN")
        if not access_token:
            return jsonify({"status": "success", "ads": [], "total": 0, "message": "Meta API 토큰 없음"}), 200

        # account_id 정규화 (act_ 접두사 제거)
        clean_account_id = account_id.replace("act_", "")
        ad_account_id = f"act_{clean_account_id}"
        print(f"[STEP4] 요청 account_id: {account_id}, ad_account_id: {ad_account_id}")

        # BigQuery에서 캠페인/세트 ID 조회
        mapping_row = None
        try:
            bq_client = bigquery.Client()
            mapping_query = """
                SELECT account_id, conv_campaign_id, conv_adset_id, traffic_campaign_id, traffic_adset_id
                FROM `ngn_dataset.meta_account_mapping`
                WHERE account_id = @account_id
                   OR account_id = @clean_account_id
                   OR account_id = @prefixed_account_id
                LIMIT 1
            """
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("account_id", "STRING", account_id),
                    bigquery.ScalarQueryParameter("clean_account_id", "STRING", clean_account_id),
                    bigquery.ScalarQueryParameter("prefixed_account_id", "STRING", ad_account_id)
                ]
            )
            mapping_result = bq_client.query(mapping_query, job_config=job_config).result()
            for row in mapping_result:
                mapping_row = row
                print(f"[STEP4] BigQuery 매핑: conv_campaign={row.conv_campaign_id}, conv_adset={row.conv_adset_id}")
                break
        except Exception as bq_err:
            print(f"[STEP4] BigQuery 조회 실패: {bq_err}")

        # ID 목록 수집 (캠페인 유형별로 구분)
        conv_adset_ids = set()
        traffic_adset_ids = set()
        conv_campaign_ids = set()
        traffic_campaign_ids = set()

        if mapping_row:
            if mapping_row.conv_adset_id and mapping_row.conv_adset_id.strip():
                conv_adset_ids.add(mapping_row.conv_adset_id.strip())
            if mapping_row.traffic_adset_id and mapping_row.traffic_adset_id.strip():
                traffic_adset_ids.add(mapping_row.traffic_adset_id.strip())
            if mapping_row.conv_campaign_id and mapping_row.conv_campaign_id.strip():
                conv_campaign_ids.add(mapping_row.conv_campaign_id.strip())
            if mapping_row.traffic_campaign_id and mapping_row.traffic_campaign_id.strip():
                traffic_campaign_ids.add(mapping_row.traffic_campaign_id.strip())

        # 통합 리스트 (조회용)
        adset_ids = list(conv_adset_ids | traffic_adset_ids)
        campaign_ids = list(conv_campaign_ids | traffic_campaign_ids)

        print(f"[STEP4] adset_ids: {adset_ids}, campaign_ids: {campaign_ids}")

        # Meta API 필드 정의 (썸네일 + configured_status 포함)
        fields = "id,name,status,effective_status,configured_status,preview_shareable_link,creative{id,thumbnail_url,image_url},adcreatives{image_url,thumbnail_url}"

        # Meta API는 status/effective_status 필터링 지원 안함
        # 서버에서 직접 필터링: DELETED, ARCHIVED 제외

        all_ads = []

        # 캐시 우회 헤더
        headers = {
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache"
        }
        # 타임스탬프 (캐시 무효화)
        import time
        cache_buster = int(time.time() * 1000)

        # 광고 ID → 캠페인 유형 매핑
        ad_campaign_type = {}

        # 1단계: AdSet 기준 조회
        if adset_ids:
            for adset_id in adset_ids:
                # 캠페인 유형 결정
                if adset_id in conv_adset_ids:
                    campaign_type = "전환"
                elif adset_id in traffic_adset_ids:
                    campaign_type = "유입"
                else:
                    campaign_type = "-"

                try:
                    ads_url = f"https://graph.facebook.com/v24.0/{adset_id}/ads"
                    params = {
                        "access_token": access_token,
                        "fields": fields,
                        "limit": 100,
                        "_ts": cache_buster
                    }
                    print(f"[STEP4] AdSet {adset_id} ({campaign_type}) 조회 중...")
                    response = requests.get(ads_url, params=params, headers=headers, timeout=30)
                    result = response.json()

                    if "error" not in result:
                        ads_data = result.get("data", [])
                        # 각 광고에 캠페인 유형 태깅
                        for ad in ads_data:
                            ad_campaign_type[ad.get("id")] = campaign_type
                        all_ads.extend(ads_data)
                        print(f"[STEP4] AdSet {adset_id}: {len(ads_data)}개 광고")
                        for ad in ads_data:
                            print(f"  - ID: {ad.get('id')}, Name: {ad.get('name')}, Status: {ad.get('status')}")
                    else:
                        print(f"[STEP4] AdSet {adset_id} 오류: {result.get('error', {}).get('message')}")
                except Exception as e:
                    print(f"[STEP4] AdSet {adset_id} 예외: {e}")

        # 2단계: AdSet에서 못 찾으면 Campaign 기준 조회 (폴백)
        if not all_ads and campaign_ids:
            print(f"[STEP4] AdSet 조회 결과 없음, Campaign 폴백 시도")
            for campaign_id in campaign_ids:
                # 캠페인 유형 결정
                if campaign_id in conv_campaign_ids:
                    campaign_type = "전환"
                elif campaign_id in traffic_campaign_ids:
                    campaign_type = "유입"
                else:
                    campaign_type = "-"

                try:
                    ads_url = f"https://graph.facebook.com/v24.0/{campaign_id}/ads"
                    params = {
                        "access_token": access_token,
                        "fields": fields,
                        "limit": 100,
                        "_ts": cache_buster
                    }
                    print(f"[STEP4] Campaign {campaign_id} ({campaign_type}) 조회 중...")
                    response = requests.get(ads_url, params=params, headers=headers, timeout=30)
                    result = response.json()

                    if "error" not in result:
                        ads_data = result.get("data", [])
                        # 각 광고에 캠페인 유형 태깅
                        for ad in ads_data:
                            ad_campaign_type[ad.get("id")] = campaign_type
                        all_ads.extend(ads_data)
                        print(f"[STEP4] Campaign {campaign_id}: {len(ads_data)}개 광고")
                        for ad in ads_data:
                            print(f"  - ID: {ad.get('id')}, Name: {ad.get('name')}, Status: {ad.get('status')}")
                    else:
                        print(f"[STEP4] Campaign {campaign_id} 오류: {result.get('error', {}).get('message')}")
                except Exception as e:
                    print(f"[STEP4] Campaign {campaign_id} 예외: {e}")

        # 3단계: 아직도 없으면 Account 전체 조회 (최종 폴백)
        if not all_ads:
            print(f"[STEP4] Campaign 조회 결과 없음, Account 전체 폴백")
            try:
                ads_url = f"https://graph.facebook.com/v24.0/{ad_account_id}/ads"
                params = {
                    "access_token": access_token,
                    "fields": fields,
                    "limit": 100,
                    "_ts": cache_buster
                }
                print(f"[STEP4] Account {ad_account_id} 전체 조회 중...")
                response = requests.get(ads_url, params=params, headers=headers, timeout=30)
                result = response.json()

                if "error" not in result:
                    all_ads = result.get("data", [])
                    print(f"[STEP4] Account 전체: {len(all_ads)}개 광고")
                else:
                    print(f"[STEP4] Account 전체 조회 오류: {result.get('error', {}).get('message')}")
            except Exception as e:
                print(f"[STEP4] Account 전체 조회 예외: {e}")

        # 중복 제거 + DELETED/ARCHIVED 필터링 (서버 측)
        seen_ids = set()
        unique_ads = []
        excluded_statuses = {'DELETED', 'ARCHIVED'}
        for ad in all_ads:
            ad_id = ad.get("id")
            ad_status = ad.get("status", "")
            # DELETED, ARCHIVED 제외
            if ad_status in excluded_statuses:
                continue
            if ad_id and ad_id not in seen_ids:
                seen_ids.add(ad_id)
                unique_ads.append(ad)

        print(f"[STEP4] 최종 조회 결과: {len(unique_ads)}개 광고 (DELETED/ARCHIVED 제외)")
        for ad in unique_ads:
            print(f"  [최종] ID: {ad.get('id')}, Name: {ad.get('name')}")

        # 광고 데이터 가공 (썸네일 추출)
        processed_ads = []
        for ad in unique_ads:
            # 썸네일 URL 추출 우선순위: creative.thumbnail_url → creative.image_url → adcreatives[0].image_url
            thumbnail_url = ""
            creative = ad.get("creative", {})
            if creative:
                thumbnail_url = creative.get("thumbnail_url") or creative.get("image_url") or ""

            if not thumbnail_url:
                adcreatives = ad.get("adcreatives", {}).get("data", [])
                if adcreatives and len(adcreatives) > 0:
                    thumbnail_url = adcreatives[0].get("image_url") or adcreatives[0].get("thumbnail_url") or ""

            processed_ads.append({
                "id": ad.get("id"),
                "name": ad.get("name", "이름 없음"),
                "status": ad.get("status"),
                "effective_status": ad.get("effective_status"),
                "configured_status": ad.get("configured_status"),  # 사용자 설정 상태 (ON/OFF 배지용)
                "campaign_type": ad_campaign_type.get(ad.get("id"), "-"),  # 전환/유입
                "thumbnail_url": thumbnail_url,
                "preview_link": ad.get("preview_shareable_link", "")
            })

        return jsonify({
            "status": "success",
            "ads": processed_ads,
            "total": len(processed_ads)
        }), 200

    except requests.exceptions.Timeout:
        print("[STEP4] Meta API 타임아웃")
        return jsonify({"status": "success", "ads": [], "total": 0, "message": "API 타임아웃"}), 200
    except Exception as e:
        print(f"[ERROR] get_active_ads 실패: {e}")
        import traceback
        traceback.print_exc()
        # 에러 시에도 빈 리스트 반환 (프론트엔드 에러 방지)
        return jsonify({"status": "success", "ads": [], "total": 0, "message": str(e)}), 200


@data_blueprint.route("/pause_ads", methods=["POST"])
def pause_ads():
    """선택한 광고들을 일시정지(PAUSED) 상태로 변경"""
    try:
        data = request.get_json() or {}
        ad_ids = data.get("ad_ids", [])

        if not ad_ids:
            return jsonify({"status": "error", "message": "ad_ids가 필요합니다."}), 400

        access_token = os.environ.get("META_SYSTEM_USER_TOKEN")
        if not access_token:
            return jsonify({"status": "error", "message": "Meta API 토큰이 설정되지 않았습니다."}), 500

        print(f"[STEP4] 광고 일시정지 요청: {len(ad_ids)}개")

        success_count = 0
        failed_ids = []

        for ad_id in ad_ids:
            try:
                update_url = f"https://graph.facebook.com/v24.0/{ad_id}"
                response = requests.post(
                    update_url,
                    data={
                        "access_token": access_token,
                        "status": "PAUSED"
                    },
                    timeout=15
                )
                result = response.json()

                if result.get("success") or "id" in result:
                    success_count += 1
                    print(f"[STEP4] 광고 {ad_id} 일시정지 성공")
                else:
                    failed_ids.append(ad_id)
                    print(f"[STEP4] 광고 {ad_id} 일시정지 실패: {result}")

            except Exception as e:
                failed_ids.append(ad_id)
                print(f"[STEP4] 광고 {ad_id} 일시정지 오류: {e}")

        return jsonify({
            "status": "success" if success_count > 0 else "error",
            "message": f"{success_count}개 광고 일시정지 완료",
            "success_count": success_count,
            "failed_ids": failed_ids
        }), 200

    except Exception as e:
        print(f"[ERROR] pause_ads 실패: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@data_blueprint.route("/delete_ads", methods=["POST"])
def delete_ads():
    """선택한 광고들을 삭제 (DELETED 상태로 변경)"""
    try:
        data = request.get_json() or {}
        ad_ids = data.get("ad_ids", [])

        if not ad_ids:
            return jsonify({"status": "error", "message": "ad_ids가 필요합니다."}), 400

        access_token = os.environ.get("META_SYSTEM_USER_TOKEN")
        if not access_token:
            return jsonify({"status": "error", "message": "Meta API 토큰이 설정되지 않았습니다."}), 500

        print(f"[STEP4] 광고 삭제 요청: {len(ad_ids)}개")

        success_count = 0
        failed_ids = []

        for ad_id in ad_ids:
            try:
                # Meta API에서 광고 삭제는 DELETE 메서드 또는 status=DELETED로 변경
                delete_url = f"https://graph.facebook.com/v24.0/{ad_id}"
                response = requests.delete(
                    delete_url,
                    params={"access_token": access_token},
                    timeout=15
                )
                result = response.json()

                if result.get("success"):
                    success_count += 1
                    print(f"[STEP4] 광고 {ad_id} 삭제 성공")
                else:
                    failed_ids.append(ad_id)
                    print(f"[STEP4] 광고 {ad_id} 삭제 실패: {result}")

            except Exception as e:
                failed_ids.append(ad_id)
                print(f"[STEP4] 광고 {ad_id} 삭제 오류: {e}")

        return jsonify({
            "status": "success" if success_count > 0 else "error",
            "message": f"{success_count}개 광고 삭제 완료",
            "success_count": success_count,
            "failed_ids": failed_ids
        }), 200

    except Exception as e:
        print(f"[ERROR] delete_ads 실패: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# ===== Meta API 에러 메시지 한국어 번역 =====
META_ERROR_TRANSLATIONS = {
    "(#100) Invalid parameter": "잘못된 파라미터입니다.",
    "(#100) image_hash": "이미지 해시가 유효하지 않습니다.",
    "(#100) video_id": "비디오 ID가 유효하지 않습니다.",
    "(#2) Service temporarily unavailable": "Meta 서비스가 일시적으로 불가합니다. 잠시 후 다시 시도해주세요.",
    "(#1) Please reduce the amount of data": "데이터 양이 너무 많습니다. 광고 개수를 줄여주세요.",
    "(#190) Access token has expired": "인증이 만료되었습니다. 다시 로그인해주세요.",
    "creative_spec": "광고 소재 설정에 오류가 있습니다.",
    "object_story_spec": "광고 콘텐츠 설정에 오류가 있습니다.",
    "The image hash": "이미지 해시가 올바르지 않습니다.",
    "video ID": "비디오 ID가 올바르지 않습니다.",
    "Page access token": "페이지 접근 권한이 없습니다.",
    "permission": "접근 권한이 부족합니다.",
    "rate limit": "API 호출 한도를 초과했습니다. 잠시 후 다시 시도해주세요.",
}


def translate_meta_error(error_message: str) -> str:
    """Meta API 에러 메시지를 한국어로 번역"""
    for key, translation in META_ERROR_TRANSLATIONS.items():
        if key.lower() in error_message.lower():
            return translation
    return f"알 수 없는 오류: {error_message}"


# ─────────────────────────────────────────────────────────────
# 📌 ADMAKE: Pending Ads 세션 관리 API
# ─────────────────────────────────────────────────────────────

@data_blueprint.route("/add_pending_ad", methods=["POST"])
def add_pending_ad():
    """
    Step 3에서 '광고 추가하기' 클릭 시 pending_ads 세션에 광고 데이터 추가
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "광고 데이터가 필요합니다."}), 400

        # 세션에 pending_ads 리스트 초기화
        if "pending_ads" not in session:
            session["pending_ads"] = []

        # 고유 ID 생성
        import uuid
        ad_data = {
            "id": str(uuid.uuid4()),
            "media_id": data.get("media_id"),  # IndexedDB 키 (Step 5 썸네일 로드용)
            "media_type": data.get("media_type", "image"),
            "video_id": data.get("video_id"),
            "image_hash": data.get("image_hash"),
            "thumbnail_url": data.get("thumbnail_url"),
            "message": data.get("message", ""),
            "headline": data.get("headline", ""),
            "description": data.get("description", ""),
            "link": data.get("link", ""),
            "cta_type": data.get("cta_type", "SHOP_NOW"),
            "ad_name": data.get("ad_name", f"AD_{len(session['pending_ads']) + 1}"),
            "is_carousel": data.get("is_carousel", False),
            "cards": data.get("cards", [])
        }

        session["pending_ads"].append(ad_data)
        session.modified = True

        print(f"[ADMAKE] 광고 추가됨: {ad_data['ad_name']}, 총 {len(session['pending_ads'])}개")

        return jsonify({
            "status": "success",
            "message": "광고가 추가되었습니다.",
            "ad_id": ad_data["id"],
            "total_count": len(session["pending_ads"])
        }), 200

    except Exception as e:
        print(f"[ERROR] add_pending_ad 실패: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@data_blueprint.route("/get_pending_ads", methods=["GET"])
def get_pending_ads():
    """
    세션에 저장된 pending_ads 리스트 조회
    """
    try:
        pending_ads = session.get("pending_ads", [])
        print(f"[ADMAKE] pending_ads 조회: {len(pending_ads)}개")

        return jsonify({
            "status": "success",
            "pending_ads": pending_ads,
            "total_count": len(pending_ads)
        }), 200

    except Exception as e:
        print(f"[ERROR] get_pending_ads 실패: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@data_blueprint.route("/clear_pending_ads", methods=["DELETE"])
def clear_pending_ads():
    """
    pending_ads 세션 초기화
    """
    try:
        session["pending_ads"] = []
        session.modified = True
        print("[ADMAKE] pending_ads 초기화됨")

        return jsonify({
            "status": "success",
            "message": "광고 목록이 초기화되었습니다."
        }), 200

    except Exception as e:
        print(f"[ERROR] clear_pending_ads 실패: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@data_blueprint.route("/remove_pending_ad/<ad_id>", methods=["DELETE"])
def remove_pending_ad(ad_id):
    """
    특정 pending_ad 삭제
    """
    try:
        pending_ads = session.get("pending_ads", [])
        original_count = len(pending_ads)

        session["pending_ads"] = [ad for ad in pending_ads if ad.get("id") != ad_id]
        session.modified = True

        removed = original_count - len(session["pending_ads"])
        print(f"[ADMAKE] 광고 삭제: {ad_id}, 삭제됨: {removed}개")

        return jsonify({
            "status": "success",
            "message": "광고가 삭제되었습니다.",
            "removed_count": removed,
            "total_count": len(session["pending_ads"])
        }), 200

    except Exception as e:
        print(f"[ERROR] remove_pending_ad 실패: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# ─────────────────────────────────────────────────────────────
# 📌 ADMAKE: 계정 정보 조회 API
# ─────────────────────────────────────────────────────────────

@data_blueprint.route("/get_account_info", methods=["GET"])
def get_account_info_api():
    """
    광고 계정에 연결된 페이지/Instagram/AdSet/UTM/Pixel 정보 조회 API
    """
    try:
        account_id = request.args.get("account_id")
        if not account_id:
            return jsonify({"status": "error", "message": "account_id가 필요합니다."}), 400

        access_token = os.environ.get("META_SYSTEM_USER_TOKEN")
        if not access_token:
            return jsonify({"status": "error", "message": "Meta API 토큰이 없습니다."}), 500

        # account_id 정규화 (act_ 접두사 제거)
        clean_account_id = account_id.replace("act_", "")

        # 기존 헬퍼 함수 호출
        info = get_account_info(clean_account_id, access_token)

        if not info or (not info.get("page_id") and not info.get("conv_adset_id")):
            return jsonify({
                "status": "error",
                "message": "계정 정보를 찾을 수 없습니다."
            }), 404

        print(f"[STEP4] 계정 정보 조회 완료: {json.dumps(info, ensure_ascii=False)[:300]}")

        return jsonify({
            "status": "success",
            "page_id": info.get("page_id"),
            "instagram_user_id": info.get("instagram_user_id"),
            "conv_adset_id": info.get("conv_adset_id"),
            "traffic_adset_id": info.get("traffic_adset_id"),
            "utm_params": info.get("utm_params"),
            "pixel_id": info.get("pixel_id")
        }), 200

    except Exception as e:
        print(f"[ERROR] get_account_info_api 실패: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


# ─────────────────────────────────────────────────────────────
# 📌 ADMAKE: 예산 실시간 조회/수정 API (Meta API Live)
# ─────────────────────────────────────────────────────────────

@data_blueprint.route("/get_budget_info", methods=["GET"])
def get_budget_info():
    """
    Meta API에서 캠페인/세트 예산 실시간 조회
    - CBO(캠페인 예산) vs ABO(세트 예산) 자동 판단
    """
    try:
        account_id = request.args.get("account_id")
        if not account_id:
            return jsonify({"status": "error", "message": "account_id가 필요합니다."}), 400

        access_token = os.environ.get("META_SYSTEM_USER_TOKEN")
        if not access_token:
            return jsonify({"status": "error", "message": "Meta API 토큰이 없습니다."}), 500

        # account_id 정규화
        clean_account_id = account_id.replace("act_", "")

        # BigQuery에서 캠페인/세트 ID 조회
        bq_client = bigquery.Client()
        mapping_query = """
            SELECT conv_campaign_id, conv_adset_id, traffic_campaign_id, traffic_adset_id
            FROM `ngn_dataset.meta_account_mapping`
            WHERE account_id = @account_id
            LIMIT 1
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("account_id", "STRING", clean_account_id)
            ]
        )
        mapping_result = bq_client.query(mapping_query, job_config=job_config).result()

        mapping_row = None
        for row in mapping_result:
            mapping_row = row
            break

        if not mapping_row:
            return jsonify({"status": "error", "message": "계정 매핑 정보가 없습니다."}), 404

        result = {
            "conv": None,  # 전환 캠페인 예산 정보
            "traffic": None  # 유입 캠페인 예산 정보
        }

        # 전환 캠페인 예산 조회
        if mapping_row.conv_campaign_id:
            conv_budget = get_campaign_budget_from_meta(
                mapping_row.conv_campaign_id,
                mapping_row.conv_adset_id,
                access_token
            )
            result["conv"] = conv_budget

        # 유입 캠페인 예산 조회
        if mapping_row.traffic_campaign_id:
            traffic_budget = get_campaign_budget_from_meta(
                mapping_row.traffic_campaign_id,
                mapping_row.traffic_adset_id,
                access_token
            )
            result["traffic"] = traffic_budget

        print(f"[STEP4] 예산 정보 조회 완료: {json.dumps(result, indent=2, ensure_ascii=False)[:500]}")

        return jsonify({
            "status": "success",
            "conv_campaign": result.get("conv"),
            "traffic_campaign": result.get("traffic")
        }), 200

    except Exception as e:
        print(f"[ERROR] get_budget_info 실패: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


def get_campaign_budget_from_meta(campaign_id: str, adset_id: str, access_token: str) -> dict:
    """
    Meta API에서 캠페인/세트 예산 조회 및 CBO/ABO 판단
    """
    try:
        budget_info = {
            "campaign_id": campaign_id,
            "adset_id": adset_id,
            "budget_type": None,  # "CBO" or "ABO"
            "daily_budget": None,
            "lifetime_budget": None,
            "budget_remaining": None,
            "status": None,
            "name": None
        }

        # 캠페인 정보 조회
        campaign_url = f"https://graph.facebook.com/v24.0/{campaign_id}"
        campaign_response = requests.get(campaign_url, params={
            "fields": "id,name,status,daily_budget,lifetime_budget,budget_remaining",
            "access_token": access_token
        }, timeout=15)
        campaign_data = campaign_response.json()

        print(f"[STEP4] 캠페인 {campaign_id} 조회: {json.dumps(campaign_data, indent=2)[:300]}")

        # CBO 여부 판단: 캠페인에 예산이 있으면 CBO
        if campaign_data.get("daily_budget") or campaign_data.get("lifetime_budget"):
            budget_info["budget_type"] = "CBO"
            budget_info["daily_budget"] = int(campaign_data.get("daily_budget", 0)) // 100 if campaign_data.get("daily_budget") else None
            budget_info["lifetime_budget"] = int(campaign_data.get("lifetime_budget", 0)) // 100 if campaign_data.get("lifetime_budget") else None
            budget_info["budget_remaining"] = int(campaign_data.get("budget_remaining", 0)) // 100 if campaign_data.get("budget_remaining") else None
            budget_info["status"] = campaign_data.get("status")
            budget_info["name"] = campaign_data.get("name")
        else:
            # ABO: 세트 예산 조회
            budget_info["budget_type"] = "ABO"
            budget_info["name"] = campaign_data.get("name")

            if adset_id:
                adset_url = f"https://graph.facebook.com/v24.0/{adset_id}"
                adset_response = requests.get(adset_url, params={
                    "fields": "id,name,status,daily_budget,lifetime_budget,budget_remaining",
                    "access_token": access_token
                }, timeout=15)
                adset_data = adset_response.json()

                print(f"[STEP4] 세트 {adset_id} 조회: {json.dumps(adset_data, indent=2)[:300]}")

                budget_info["daily_budget"] = int(adset_data.get("daily_budget", 0)) // 100 if adset_data.get("daily_budget") else None
                budget_info["lifetime_budget"] = int(adset_data.get("lifetime_budget", 0)) // 100 if adset_data.get("lifetime_budget") else None
                budget_info["budget_remaining"] = int(adset_data.get("budget_remaining", 0)) // 100 if adset_data.get("budget_remaining") else None
                budget_info["status"] = adset_data.get("status")

        return budget_info

    except Exception as e:
        print(f"[STEP4] 예산 조회 오류: {e}")
        return {"error": str(e)}


@data_blueprint.route("/update_budget", methods=["POST"])
def update_budget():
    """
    Meta API로 예산 업데이트 (CBO/ABO 자동 분기)
    """
    try:
        data = request.get_json()
        target_type = data.get("target_type")  # "conv" or "traffic"
        budget_type = data.get("budget_type")  # "CBO" or "ABO"
        campaign_id = data.get("campaign_id")
        adset_id = data.get("adset_id")
        daily_budget = data.get("daily_budget")  # 원화 단위 (예: 50000)
        lifetime_budget = data.get("lifetime_budget")

        access_token = os.environ.get("META_SYSTEM_USER_TOKEN")
        if not access_token:
            return jsonify({"status": "error", "message": "Meta API 토큰이 없습니다."}), 500

        # 예산을 센트 단위로 변환 (Meta API 규격)
        update_data = {}
        if daily_budget is not None:
            update_data["daily_budget"] = int(daily_budget) * 100
        if lifetime_budget is not None:
            update_data["lifetime_budget"] = int(lifetime_budget) * 100

        if not update_data:
            return jsonify({"status": "error", "message": "업데이트할 예산이 없습니다."}), 400

        # CBO면 캠페인, ABO면 세트에 업데이트
        if budget_type == "CBO":
            target_id = campaign_id
            target_url = f"https://graph.facebook.com/v24.0/{campaign_id}"
        else:
            target_id = adset_id
            target_url = f"https://graph.facebook.com/v24.0/{adset_id}"

        update_data["access_token"] = access_token

        print(f"[STEP4] 예산 업데이트: {target_url}, 데이터: {update_data}")

        response = requests.post(target_url, data=update_data, timeout=15)
        result = response.json()

        print(f"[STEP4] 예산 업데이트 응답: {json.dumps(result, indent=2)}")

        if result.get("success"):
            return jsonify({
                "status": "success",
                "message": "예산이 업데이트되었습니다.",
                "target_type": target_type,
                "target_id": target_id
            }), 200
        elif "error" in result:
            return jsonify({
                "status": "error",
                "message": result["error"].get("message", "예산 업데이트 실패")
            }), 400
        else:
            return jsonify({"status": "error", "message": "알 수 없는 오류"}), 500

    except Exception as e:
        print(f"[ERROR] update_budget 실패: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@data_blueprint.route("/update_adset_status", methods=["POST"])
def update_adset_status():
    """
    AdSet 상태(ACTIVE/PAUSED) 업데이트
    """
    try:
        data = request.get_json()
        adset_id = data.get("adset_id")
        status = data.get("status")  # "ACTIVE" or "PAUSED"

        if not adset_id or not status:
            return jsonify({"status": "error", "message": "adset_id와 status가 필요합니다."}), 400

        access_token = os.environ.get("META_SYSTEM_USER_TOKEN")
        if not access_token:
            return jsonify({"status": "error", "message": "Meta API 토큰이 없습니다."}), 500

        url = f"https://graph.facebook.com/v24.0/{adset_id}"
        response = requests.post(url, data={
            "status": status,
            "access_token": access_token
        }, timeout=15)
        result = response.json()

        print(f"[STEP4] AdSet 상태 업데이트: {adset_id} → {status}, 응답: {result}")

        if result.get("success"):
            return jsonify({
                "status": "success",
                "message": f"세트 상태가 {status}로 변경되었습니다."
            }), 200
        elif "error" in result:
            return jsonify({
                "status": "error",
                "message": result["error"].get("message", "상태 업데이트 실패")
            }), 400
        else:
            return jsonify({"status": "error", "message": "알 수 없는 오류"}), 500

    except Exception as e:
        print(f"[ERROR] update_adset_status 실패: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@data_blueprint.route("/update_adset_schedule", methods=["POST"])
def update_adset_schedule():
    """
    AdSet 노출 기간 설정 업데이트 (Meta API v24.0)
    - end_time: 종료 시간 (ISO 8601 또는 Unix timestamp)
    - 'no_end'인 경우 end_time을 0으로 설정 (종료일 없음)
    """
    try:
        data = request.get_json()
        account_id = data.get("account_id")
        end_time_setting = data.get("end_time_setting", "no_end")  # "no_end" or "set_end"
        end_time_value = data.get("end_time_value")  # ISO 8601 형식: "2024-12-31T23:59:00+09:00"

        print(f"[STEP4] ========== AdSet 스케줄 업데이트 시작 ==========")
        print(f"[STEP4] account_id: {account_id}")
        print(f"[STEP4] end_time_setting: {end_time_setting}")
        print(f"[STEP4] end_time_value: {end_time_value}")

        if not account_id:
            return jsonify({"status": "error", "message": "account_id가 필요합니다."}), 400

        access_token = os.environ.get("META_SYSTEM_USER_TOKEN")
        if not access_token:
            return jsonify({"status": "error", "message": "Meta API 토큰이 없습니다."}), 500

        # BigQuery에서 계정의 AdSet ID 조회
        raw_account_id = account_id.replace("act_", "") if account_id.startswith("act_") else account_id
        account_info = get_account_info(raw_account_id, access_token)
        conv_adset_id = account_info.get("conv_adset_id")
        traffic_adset_id = account_info.get("traffic_adset_id")

        if not conv_adset_id and not traffic_adset_id:
            return jsonify({"status": "error", "message": "업데이트할 AdSet이 없습니다."}), 400

        # 업데이트할 AdSet 목록
        adsets_to_update = []
        if conv_adset_id:
            adsets_to_update.append(("전환", conv_adset_id))
        if traffic_adset_id:
            adsets_to_update.append(("유입", traffic_adset_id))

        results = []
        for adset_name, adset_id in adsets_to_update:
            url = f"https://graph.facebook.com/v24.0/{adset_id}"

            # 페이로드 구성
            payload = {"access_token": access_token}

            if end_time_setting == "no_end":
                # 종료일 없음: end_time을 0으로 설정 (Meta API에서 종료일 제거)
                payload["end_time"] = 0
                print(f"[STEP4] {adset_name} AdSet: 종료일 없음 설정")
            elif end_time_setting == "set_end" and end_time_value:
                # 특정 종료일 설정
                payload["end_time"] = end_time_value
                print(f"[STEP4] {adset_name} AdSet: 종료일 설정 → {end_time_value}")
            else:
                print(f"[STEP4] {adset_name} AdSet: 변경 없음 (스킵)")
                continue

            response = requests.post(url, data=payload, timeout=15)
            result = response.json()

            print(f"[STEP4] {adset_name} AdSet ({adset_id}) 응답: {result}")

            if result.get("success"):
                results.append({
                    "adset_name": adset_name,
                    "adset_id": adset_id,
                    "success": True
                })
            else:
                error_msg = result.get("error", {}).get("message", "Unknown error")
                results.append({
                    "adset_name": adset_name,
                    "adset_id": adset_id,
                    "success": False,
                    "error": error_msg
                })

        # 결과 집계
        success_count = sum(1 for r in results if r["success"])
        fail_count = len(results) - success_count

        print(f"[STEP4] 스케줄 업데이트 완료: 성공 {success_count}, 실패 {fail_count}")
        print(f"[STEP4] ========== AdSet 스케줄 업데이트 종료 ==========")

        if fail_count > 0:
            failed_names = [r["adset_name"] for r in results if not r["success"]]
            return jsonify({
                "status": "partial",
                "message": f"일부 AdSet 업데이트 실패: {', '.join(failed_names)}",
                "results": results
            }), 200

        return jsonify({
            "status": "success",
            "message": "모든 AdSet 스케줄이 업데이트되었습니다.",
            "results": results
        }), 200

    except Exception as e:
        print(f"[ERROR] update_adset_schedule 실패: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


@data_blueprint.route("/publish_ads_batch", methods=["POST"])
def publish_ads_batch():
    """
    Step 5: 여러 광고를 배치로 생성
    - AdCreative 생성 → Ad 생성
    - 유입 캠페인 복사 옵션 지원
    - UTM 파라미터 및 Pixel tracking 지원
    """
    try:
        data = request.get_json()
        account_id = data.get("account_id")
        ads = data.get("ads", [])

        # Step 4 설정 추출
        copy_to_traffic = data.get("copy_to_traffic", False)
        conv_active = data.get("conv_active", True)
        traffic_active = data.get("traffic_active", False)
        end_time = data.get("end_time")  # ISO 8601 형식 (예: 2024-12-31T23:59:00+09:00)
        utm_params = data.get("utm_params", "")
        pixel_id = data.get("pixel_id", "")

        print(f"[STEP5] ========== publish_ads_batch 시작 ==========")
        print(f"[STEP5] 수신된 account_id: {account_id}")
        print(f"[STEP5] 수신된 ads 개수: {len(ads) if ads else 0}")
        print(f"[STEP5] copy_to_traffic: {copy_to_traffic}, conv_active: {conv_active}, traffic_active: {traffic_active}")
        print(f"[STEP5] end_time: {end_time}")
        print(f"[STEP5] utm_params: {utm_params[:50] if utm_params else 'None'}...")
        print(f"[STEP5] pixel_id: {pixel_id}")

        if not account_id:
            return jsonify({"status": "error", "message": "account_id가 필요합니다."}), 400

        if not ads:
            return jsonify({"status": "error", "message": "전송할 광고가 없습니다."}), 400

        # act_ 접두사 제거 (BigQuery 조회용)
        raw_account_id = account_id.replace("act_", "") if account_id.startswith("act_") else account_id
        print(f"[STEP5] BigQuery 조회용 account_id: {raw_account_id}")

        access_token = os.environ.get("META_SYSTEM_USER_TOKEN")
        if not access_token:
            return jsonify({"status": "error", "message": "Meta API 토큰이 설정되지 않았습니다."}), 500

        print(f"[STEP5] access_token 존재: True, 길이: {len(access_token)}")
        print(f"[STEP5] 광고 배치 전송 시작: {len(ads)}개")

        # 광고 계정 정보 조회 (page_id, instagram_user_id 등) - raw ID 사용
        account_info = get_account_info(raw_account_id, access_token)
        page_id = account_info.get("page_id")
        instagram_user_id = account_info.get("instagram_user_id")
        conv_adset_id = account_info.get("conv_adset_id")
        traffic_adset_id = account_info.get("traffic_adset_id")

        # 클라이언트에서 전달된 값이 없으면 계정 정보에서 가져오기
        if not utm_params:
            utm_params = account_info.get("utm_params", "")
        if not pixel_id:
            pixel_id = account_info.get("pixel_id", "")

        if not page_id:
            return jsonify({"status": "error", "message": "Facebook 페이지 정보를 찾을 수 없습니다."}), 400

        # 전송할 캠페인 결정
        # Note: PAUSED 상태의 AdSet에도 광고 생성 가능 (Meta API 허용)
        target_adsets = []

        # 전환 캠페인: adset_id가 있으면 항상 추가 (PAUSED 상태여도 광고 생성 가능)
        if conv_adset_id:
            target_adsets.append(("conv", conv_adset_id))
            print(f"[STEP5] 전환 캠페인 추가 (conv_active={conv_active})")

        # 유입 캠페인: 명시적으로 활성화하거나 복사 옵션 선택 시에만 추가
        if (traffic_active or copy_to_traffic) and traffic_adset_id:
            target_adsets.append(("traffic", traffic_adset_id))
            print(f"[STEP5] 유입 캠페인 추가 (traffic_active={traffic_active}, copy_to_traffic={copy_to_traffic})")

        if not target_adsets:
            return jsonify({"status": "error", "message": "전송할 광고 세트가 없습니다. 계정 설정을 확인해주세요."}), 400

        print(f"[STEP5] 전송할 캠페인: {target_adsets}")

        results = []
        success_count = 0
        fail_count = 0

        for idx, ad_data in enumerate(ads):
            ad_name = ad_data.get("name", f"AD_{idx + 1}")
            print(f"[STEP5] 광고 {idx + 1}/{len(ads)} 처리 중: {ad_name}")

            try:
                # 1. AdCreative 생성 (UTM 파라미터 포함)
                creative_id = create_ad_creative_internal(
                    account_id=account_id,
                    ad_data=ad_data,
                    page_id=page_id,
                    instagram_user_id=instagram_user_id,
                    access_token=access_token,
                    url_tags=utm_params  # UTM 파라미터 전달
                )

                if not creative_id:
                    raise Exception("AdCreative 생성 실패")

                print(f"[STEP5] AdCreative 생성 완료: {creative_id}")

                # 2. 각 타겟 AdSet에 Ad 생성
                ad_created = False
                for campaign_type, adset_id in target_adsets:
                    suffix = "_TRAFFIC" if campaign_type == "traffic" else ""
                    full_ad_name = f"{ad_name}{suffix}"

                    ad_result = create_ad_internal(
                        account_id=account_id,
                        adset_id=adset_id,
                        creative_id=creative_id,
                        ad_name=full_ad_name,
                        access_token=access_token,
                        status="ACTIVE",  # 광고 ON 상태로 생성
                        pixel_id=pixel_id,  # 전환 + 유입 캠페인 모두 픽셀 적용 (웹사이트 이벤트 추적)
                        end_time=end_time
                    )

                    if ad_result.get("success"):
                        results.append({
                            "name": full_ad_name,
                            "campaign_type": campaign_type,
                            "success": True,
                            "creative_id": creative_id,
                            "ad_id": ad_result.get("ad_id"),
                            "preview_link": ad_result.get("preview_link")
                        })
                        success_count += 1
                        ad_created = True
                        print(f"[STEP5] Ad 생성 완료 ({campaign_type}): {ad_result.get('ad_id')}")
                    else:
                        raise Exception(f"{campaign_type} 캠페인 Ad 생성 실패: {ad_result.get('error', 'Unknown')}")

            except Exception as e:
                error_msg = str(e)
                translated_error = translate_meta_error(error_msg)
                print(f"[STEP5] 광고 {ad_name} 전송 실패: {error_msg}")

                results.append({
                    "name": ad_name,
                    "success": False,
                    "error": translated_error
                })
                fail_count += 1

        return jsonify({
            "status": "success",
            "results": results,
            "success_count": success_count,
            "fail_count": fail_count
        }), 200

    except Exception as e:
        print(f"[ERROR] publish_ads_batch 실패: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


def get_account_info(account_id: str, access_token: str) -> dict:
    """광고 계정에 연결된 페이지/Instagram/AdSet/UTM/Pixel 정보 조회 (BigQuery 우선, Meta API 폴백)"""
    try:
        page_id = None
        instagram_user_id = None
        conv_adset_id = None
        traffic_adset_id = None
        utm_params = None
        pixel_id = None

        # 기본 UTM 템플릿 (fallback)
        DEFAULT_UTM = "utm_source=meta&utm_medium=prospecting&utm_campaign={{campaign.name}}&utm_content={{ad.name}}"

        # 1. BigQuery에서 page_id, instagram_user_id, adset_id, utm_params, pixel_id 조회
        try:
            bq_client = bigquery.Client()
            mapping_query = """
                SELECT page_id, instagram_user_id, conv_adset_id, traffic_adset_id, utm_params, pixel_id
                FROM `ngn_dataset.meta_account_mapping`
                WHERE account_id = @account_id
                LIMIT 1
            """
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("account_id", "STRING", account_id)
                ]
            )
            mapping_result = bq_client.query(mapping_query, job_config=job_config).result()

            for row in mapping_result:
                page_id = str(row.page_id).strip() if row.page_id else None
                instagram_user_id = str(row.instagram_user_id).strip() if row.instagram_user_id else None
                conv_adset_id = str(row.conv_adset_id).strip() if row.conv_adset_id else None
                traffic_adset_id = str(row.traffic_adset_id).strip() if row.traffic_adset_id else None
                utm_params = str(row.utm_params).strip() if row.utm_params else None
                pixel_id = str(row.pixel_id).strip() if row.pixel_id else None
                print(f"[STEP5] BigQuery에서 조회 - page_id: '{page_id}', instagram_user_id: '{instagram_user_id}'")
                print(f"[STEP5] BigQuery에서 조회 - conv_adset_id: '{conv_adset_id}', traffic_adset_id: '{traffic_adset_id}'")
                print(f"[STEP5] BigQuery에서 조회 - utm_params: '{utm_params}', pixel_id: '{pixel_id}'")
                break
        except Exception as bq_err:
            print(f"[STEP5] BigQuery 조회 실패: {bq_err}")

        # UTM fallback 적용
        if not utm_params:
            utm_params = DEFAULT_UTM
            print(f"[STEP5] UTM 기본값 적용: {utm_params}")

        # 2. BigQuery에 없으면 Meta API로 폴백
        if not page_id:
            print(f"[STEP5] BigQuery에 account_id={account_id} 매핑 없음, Meta API로 폴백")
            pages_url = "https://graph.facebook.com/v24.0/me/accounts"
            pages_response = requests.get(pages_url, params={
                "access_token": access_token,
                "fields": "id,name"
            }, timeout=10)
            pages_data = pages_response.json()
            print(f"[STEP5] Pages 응답: {json.dumps(pages_data, indent=2)[:500]}")

            if 'data' in pages_data and len(pages_data['data']) > 0:
                page_id = pages_data['data'][0]['id']

        # 3. Page에서 Instagram Business Account 조회
        if page_id and not instagram_user_id:
            try:
                ig_url = f"https://graph.facebook.com/v24.0/{page_id}"
                ig_response = requests.get(ig_url, params={
                    "access_token": access_token,
                    "fields": "instagram_business_account"
                }, timeout=10)
                ig_data = ig_response.json()

                if "instagram_business_account" in ig_data:
                    instagram_user_id = ig_data["instagram_business_account"].get("id")
                    print(f"[STEP5] Page에서 Instagram 계정 조회: {instagram_user_id}")
            except Exception as ig_err:
                print(f"[STEP5] Instagram 계정 조회 실패: {ig_err}")

        print(f"[STEP5] 최종 계정 정보: page_id={page_id}, instagram_user_id={instagram_user_id}")
        print(f"[STEP5] AdSet 정보: conv_adset_id={conv_adset_id}, traffic_adset_id={traffic_adset_id}")
        print(f"[STEP5] 추적 정보: utm_params={utm_params[:50] if utm_params else None}..., pixel_id={pixel_id}")
        return {
            "page_id": page_id,
            "instagram_user_id": instagram_user_id,
            "conv_adset_id": conv_adset_id,
            "traffic_adset_id": traffic_adset_id,
            "utm_params": utm_params,
            "pixel_id": pixel_id
        }

    except Exception as e:
        print(f"[STEP5] 계정 정보 조회 실패: {e}")
        return {}


def ensure_act_prefix(account_id: str) -> str:
    """광고 계정 ID에 act_ 접두사가 있는지 확인하고 없으면 추가"""
    if not account_id:
        return account_id
    account_id = str(account_id).strip()
    if not account_id.startswith("act_"):
        return f"act_{account_id}"
    return account_id


def get_video_thumbnail(video_id: str, access_token: str) -> str:
    """Meta API에서 비디오 썸네일 URL 조회"""
    try:
        url = f"https://graph.facebook.com/v24.0/{video_id}"
        params = {
            "fields": "thumbnails,picture",
            "access_token": access_token
        }
        response = requests.get(url, params=params, timeout=15)
        result = response.json()

        print(f"[STEP5] 비디오 썸네일 조회 응답: {json.dumps(result, indent=2, ensure_ascii=False)[:500]}")

        # thumbnails 배열에서 가장 큰 썸네일 선택
        if "thumbnails" in result and result["thumbnails"].get("data"):
            thumbnails = result["thumbnails"]["data"]
            # 해상도가 가장 높은 썸네일 선택
            best_thumb = max(thumbnails, key=lambda x: x.get("width", 0) * x.get("height", 0))
            thumb_url = best_thumb.get("uri") or best_thumb.get("url")
            if thumb_url:
                print(f"[STEP5] 비디오 썸네일 찾음 (thumbnails): {thumb_url}")
                return thumb_url

        # picture 필드에서 가져오기
        if "picture" in result:
            print(f"[STEP5] 비디오 썸네일 찾음 (picture): {result['picture']}")
            return result["picture"]

        print(f"[STEP5] 비디오 썸네일을 찾을 수 없음")
        return None

    except Exception as e:
        print(f"[STEP5] 비디오 썸네일 조회 오류: {e}")
        return None


def create_ad_internal(account_id: str, adset_id: str, creative_id: str, ad_name: str, access_token: str, status: str = "PAUSED", pixel_id: str = "", end_time: str = "") -> dict:
    """
    Meta API를 통해 Ad(광고) 생성
    - AdCreative를 AdSet에 연결하여 실제 광고 생성
    - pixel_id: Meta Pixel ID (tracking_specs에 사용)
    - end_time: 광고 종료 시간 (ISO 8601 형식)
    """
    try:
        formatted_account_id = ensure_act_prefix(account_id)
        url = f"https://graph.facebook.com/v24.0/{formatted_account_id}/ads"

        print(f"[STEP5] ========== Ad 생성 시작 ==========")
        print(f"[STEP5] Ad 생성 URL: {url}")
        print(f"[STEP5] adset_id: {adset_id}")
        print(f"[STEP5] creative_id: {creative_id}")
        print(f"[STEP5] ad_name: {ad_name}")
        print(f"[STEP5] status: {status}")
        print(f"[STEP5] pixel_id: {pixel_id}")
        print(f"[STEP5] end_time: {end_time}")

        payload = {
            "name": ad_name,
            "adset_id": str(adset_id),
            "creative": json.dumps({"creative_id": str(creative_id)}),
            "status": status,
            "access_token": access_token
        }

        # tracking_specs 추가 (Pixel ID가 있는 경우) - 웹사이트 이벤트 추적 활성화
        # Meta API v24.0 형식: fb_pixel 사용 (offsite_pixel 아님)
        if pixel_id:
            tracking_specs = [
                {
                    "action.type": "offsite_conversion",
                    "fb_pixel": [str(pixel_id)]
                }
            ]
            payload["tracking_specs"] = json.dumps(tracking_specs)
            print(f"[STEP5] tracking_specs 추가: {tracking_specs}")

        # end_time 추가 (종료 시간이 있는 경우)
        # Note: end_time은 Ad 레벨이 아닌 AdSet 레벨에서 설정해야 함
        # 여기서는 로그만 출력하고 실제 설정은 AdSet 업데이트 API에서 처리
        if end_time:
            print(f"[STEP5] Note: end_time은 AdSet 레벨에서 관리됨: {end_time}")

        print(f"[STEP5] Ad 생성 페이로드: name={ad_name}, adset_id={adset_id}, creative_id={creative_id}")

        response = requests.post(url, data=payload, timeout=30)
        result = response.json()

        print(f"[STEP5] Ad 생성 응답 상태: {response.status_code}")
        print(f"[STEP5] Ad 생성 응답 내용: {json.dumps(result, indent=2, ensure_ascii=False)[:500]}")

        if "id" in result:
            ad_id = result["id"]
            print(f"[STEP5] Ad 생성 성공! ID: {ad_id}")
            return {
                "success": True,
                "ad_id": ad_id,
                "preview_link": f"https://business.facebook.com/adsmanager/manage/ads?act={account_id.replace('act_', '')}&selected_ad_ids={ad_id}"
            }
        elif "error" in result:
            error_msg = result["error"].get("message", "Unknown error")
            error_code = result["error"].get("code", "N/A")
            print(f"[STEP5] Ad 생성 실패 - 코드: {error_code}, 메시지: {error_msg}")
            return {"success": False, "error": error_msg}
        else:
            return {"success": False, "error": "Ad ID를 받지 못했습니다."}

    except Exception as e:
        print(f"[STEP5] Ad 생성 오류: {e}")
        return {"success": False, "error": str(e)}


def create_ad_creative_internal(account_id: str, ad_data: dict, page_id: str, instagram_user_id: str, access_token: str, url_tags: str = "") -> str:
    """
    Meta API를 통해 AdCreative 생성 (내부 함수)
    - url_tags: UTM 파라미터 (예: utm_source=meta&utm_medium=prospecting...)
    """
    try:
        # 1. act_ 접두사 강제 적용
        formatted_account_id = ensure_act_prefix(account_id)
        url = f"https://graph.facebook.com/v24.0/{formatted_account_id}/adcreatives"

        print(f"[STEP5] ========== AdCreative 생성 시작 ==========")
        print(f"[STEP5] 원본 account_id: {account_id}")
        print(f"[STEP5] 포맷된 account_id: {formatted_account_id}")
        print(f"[STEP5] 최종 URL: {url}")
        print(f"[STEP5] page_id: {page_id}")
        print(f"[STEP5] instagram_user_id: {instagram_user_id}")
        print(f"[STEP5] access_token 존재: {bool(access_token)}, 길이: {len(access_token) if access_token else 0}")

        # 2. object_story_spec 구성 - 모든 ID는 문자열로 명시적 변환
        # v24.0 규격: instagram_user_id는 object_story_spec 최상위 레벨에 위치
        object_story_spec = {
            "page_id": str(page_id) if page_id else None
        }

        # instagram_user_id 명시적 문자열 변환 (v24.0: instagram_actor_id → instagram_user_id)
        if instagram_user_id:
            object_story_spec["instagram_user_id"] = str(instagram_user_id)
            print(f"[STEP5] instagram_user_id 설정됨: {object_story_spec['instagram_user_id']} (type: {type(object_story_spec['instagram_user_id']).__name__})")

        # 캐러셀 vs 단일 미디어 분기
        if ad_data.get("is_carousel") and ad_data.get("cards"):
            # 캐러셀 광고
            child_attachments = []
            for card in ad_data["cards"]:
                attachment = {
                    "link": card.get("link", ad_data.get("link", "")),
                    "name": card.get("name", ""),
                    "description": card.get("description", ""),
                    "call_to_action": {"type": ad_data.get("cta_type", "SHOP_NOW")}
                }
                # 미디어 타입에 따라 분기
                if card.get("video_id"):
                    video_id_str = str(card["video_id"])
                    attachment["video_id"] = video_id_str
                    # 비디오 썸네일 처리
                    thumb_url = card.get("thumbnail_url") or card.get("image_url")
                    if not thumb_url:
                        thumb_url = get_video_thumbnail(video_id_str, access_token)
                    if thumb_url:
                        attachment["picture"] = str(thumb_url)
                        print(f"[STEP5] 캐러셀 카드 썸네일: {thumb_url}")
                elif card.get("image_hash"):
                    attachment["image_hash"] = str(card["image_hash"])

                child_attachments.append(attachment)

            object_story_spec["link_data"] = {
                "message": ad_data.get("message", ""),
                "link": ad_data.get("link", ""),
                "child_attachments": child_attachments,
                "call_to_action": {"type": ad_data.get("cta_type", "SHOP_NOW")}
            }

        else:
            # 단일 미디어 광고
            media_type = ad_data.get("media_type", "image")

            if media_type == "video":
                # 비디오 광고 - image_url (썸네일) 필수
                video_id_str = str(ad_data.get("video_id")) if ad_data.get("video_id") else None

                video_data = {
                    "video_id": video_id_str,
                    "message": ad_data.get("message", ""),
                    "title": ad_data.get("headline", ""),
                    "link_description": ad_data.get("description", ""),
                    "call_to_action": {
                        "type": ad_data.get("cta_type", "SHOP_NOW"),
                        "value": {"link": ad_data.get("link", "")}
                    }
                }

                # 썸네일 URL 추가 (thumbnail_url 또는 image_url 필드에서 가져옴)
                thumbnail_url = ad_data.get("thumbnail_url") or ad_data.get("image_url")

                # blob URL은 Meta API에서 사용 불가 - 필터링
                if thumbnail_url and thumbnail_url.startswith("blob:"):
                    print(f"[STEP5] blob URL 감지, 무시: {thumbnail_url[:50]}...")
                    thumbnail_url = None

                # 썸네일이 없으면 Meta API에서 비디오 썸네일 조회
                if not thumbnail_url and video_id_str:
                    print(f"[STEP5] 썸네일 URL 없음, Meta API에서 조회 시도...")
                    thumbnail_url = get_video_thumbnail(video_id_str, access_token)

                if thumbnail_url:
                    video_data["image_url"] = str(thumbnail_url)
                    print(f"[STEP5] video_data.image_url 설정됨: {thumbnail_url}")
                else:
                    print(f"[STEP5] WARNING: 비디오 썸네일 URL을 찾을 수 없습니다!")

                object_story_spec["video_data"] = video_data
            else:
                # 이미지 광고
                object_story_spec["link_data"] = {
                    "message": ad_data.get("message", ""),
                    "link": ad_data.get("link", ""),
                    "image_hash": str(ad_data.get("image_hash")) if ad_data.get("image_hash") else None,
                    "name": ad_data.get("headline", ""),
                    "description": ad_data.get("description", ""),
                    "call_to_action": {"type": ad_data.get("cta_type", "SHOP_NOW")}
                }

        # 3. object_story_spec JSON 직렬화 (한 번만)
        object_story_spec_json = json.dumps(object_story_spec, ensure_ascii=False)
        print(f"[STEP5] object_story_spec (직렬화 전): {json.dumps(object_story_spec, indent=2, ensure_ascii=False)}")
        print(f"[STEP5] object_story_spec (직렬화 후 길이): {len(object_story_spec_json)}")

        # 4. API 요청 페이로드 - form data로 전송
        payload = {
            "name": ad_data.get("name", "AdCreative"),
            "object_story_spec": object_story_spec_json,
            "access_token": access_token
        }

        # UTM 파라미터 추가 (url_tags)
        if url_tags:
            payload["url_tags"] = url_tags
            print(f"[STEP5] url_tags 추가: {url_tags[:80]}...")

        # [v24.0] 어드밴티지+ 크리에이티브 전체 비활성화
        # creative_features_spec만 사용 (degrees_of_freedom_spec 사용 금지)
        # standard_enhancements는 v24.0에서 완전히 폐기됨
        creative_features_spec = {
            "advantage_plus_creative": {
                "enroll_status": "OPT_OUT"
            }
        }
        payload["creative_features_spec"] = json.dumps(creative_features_spec, ensure_ascii=False)
        print(f"[STEP5] creative_features_spec 추가: {creative_features_spec}")

        # [Emergency Check] standard_enhancements 필드가 페이로드에 존재하면 강제 삭제
        payload_str = json.dumps(payload, ensure_ascii=False)
        if "standard_enhancements" in payload_str:
            print(f"[STEP5] WARNING: standard_enhancements 감지됨! 강제 삭제 시도...")
            # 가능한 모든 위치에서 제거
            if "degrees_of_freedom_spec" in payload:
                del payload["degrees_of_freedom_spec"]
                print(f"[STEP5] degrees_of_freedom_spec 삭제됨")

        # 전송 직전 최종 페이로드 로깅 (access_token 마스킹)
        print(f"[STEP5] ========== 전송 직전 최종 페이로드 ==========")
        print(f"[STEP5] URL: {url}")
        print(f"[STEP5] name: {payload['name']}")
        print(f"[STEP5] object_story_spec (전체):")
        print(f"{object_story_spec_json}")
        print(f"[STEP5] creative_features_spec: {payload.get('creative_features_spec', 'N/A')}")
        # 최종 검증: standard_enhancements 문자열 포함 여부
        final_payload_str = str(payload)
        if "standard_enhancements" in final_payload_str:
            print(f"[STEP5] CRITICAL ERROR: standard_enhancements가 여전히 존재함!")
        else:
            print(f"[STEP5] OK: standard_enhancements 미포함 확인")
        print(f"[STEP5] access_token: {access_token[:20]}...{access_token[-10:] if len(access_token) > 30 else ''}")
        print(f"[STEP5] ================================================")

        # 5. API 호출
        response = requests.post(url, data=payload, timeout=30)
        result = response.json()

        print(f"[STEP5] API 응답 상태: {response.status_code}")
        print(f"[STEP5] API 응답 내용: {json.dumps(result, indent=2, ensure_ascii=False)[:1000]}")

        if "id" in result:
            print(f"[STEP5] AdCreative 생성 성공! ID: {result['id']}")
            return result["id"]
        elif "error" in result:
            error_msg = result["error"].get("message", "Unknown error")
            error_code = result["error"].get("code", "N/A")
            error_type = result["error"].get("type", "N/A")
            print(f"[STEP5] AdCreative 생성 실패 - 코드: {error_code}, 타입: {error_type}, 메시지: {error_msg}")
            raise Exception(error_msg)
        else:
            raise Exception("AdCreative ID를 받지 못했습니다.")

    except Exception as e:
        print(f"[STEP5] AdCreative 생성 오류: {e}")
        print(f"[STEP5] ========== AdCreative 생성 종료 (실패) ==========")
        raise