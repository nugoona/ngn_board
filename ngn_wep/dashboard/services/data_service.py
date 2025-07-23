# File: services/data_service.py

import datetime
from flask import Blueprint, request, jsonify

# ✅ 서비스 함수 임포트
from services.cafe24_service import get_cafe24_sales_data, get_cafe24_product_sales
from services.meta_ads_service import get_meta_ads_data
from services.performance_summary import get_performance_summary
from services.viewitem_summary import get_viewitem_summary
from services.monthly_net_sales_visitors import get_monthly_net_sales_visitors  # ✅ NEW
from services.ga4_source_summary import get_ga4_source_summary

data_blueprint = Blueprint("data", __name__, url_prefix="/dashboard")

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
    try:
        data = request.get_json()

        raw_company_name = data.get("company_name", "all")
        user_id = session.get("user_id", "").lower() 

        if user_id == "demo":
            company_name = "demo"

        elif isinstance(raw_company_name, list):
            # demo 들어있으면 백엔드에서도 제거 안전하게
            company_name = [name.lower() for name in raw_company_name if name.lower() != "demo"]
        else:
            company_name = str(raw_company_name).strip().lower()
      
        period = str(data.get("period", "today")).strip()
        start_date = data.get("start_date", None)
        end_date = data.get("end_date", None)
        page = int(data.get("page", 1))
        limit = int(data.get("limit", 15))
        data_type = data.get("data_type", "all")

        start_date, end_date = get_start_end_dates(period, start_date, end_date)
        offset = (page - 1) * limit

        date_type = str(data.get("date_type", "summary")).strip()
        date_sort = str(data.get("date_sort", "desc")).strip()

        print(f"[DEBUG] 요청 필터 - company_name={company_name}, period={period}, "
              f"start_date={start_date}, end_date={end_date}, page={page}, limit={limit}, data_type={data_type}")
        print(f"[DEBUG] date_type={date_type}, date_sort={date_sort}")

        response_data = {"status": "success"}

        # ✅ 1) Performance Summary
        if data_type in ["performance_summary", "all"]:
            performance_data = get_performance_summary(
                company_name=company_name,
                start_date=start_date,
                end_date=end_date
            )
            performance_total_count = len(performance_data)
            response_data["performance_summary"] = performance_data[offset : offset + limit]
            response_data["performance_summary_total_count"] = performance_total_count
            print(f"[DEBUG] Performance Summary total: {performance_total_count}")

        # ✅ 2) Meta Ads
        if data_type in ["meta_ads", "all"]:
            meta_ads_data = get_meta_ads_data(
                company_name, period, start_date, end_date, date_type, date_sort
            )
            meta_ads_total_count = len(meta_ads_data)
            response_data["meta_ads"] = meta_ads_data[offset : offset + limit]
            response_data["meta_ads_total_count"] = meta_ads_total_count
            print(f"[DEBUG] Meta Ads total: {meta_ads_total_count}")

        # ✅ 3) Cafe24 Sales
        if data_type in ["cafe24_sales", "all"]:
            cafe24_sales_data = get_cafe24_sales_data(
                company_name, period, start_date, end_date, date_type, date_sort
            )
            cafe24_sales_total_count = len(cafe24_sales_data)
            response_data["cafe24_sales"] = cafe24_sales_data[offset : offset + limit]
            response_data["cafe24_sales_total_count"] = cafe24_sales_total_count
            print(f"[DEBUG] Cafe24 Sales total: {cafe24_sales_total_count}")

        # ✅ 4) Cafe24 Product Sales
        if data_type in ["cafe24_product_sales", "all"]:
            cafe24_product_sales_data = get_cafe24_product_sales(
                company_name, period, start_date, end_date
            )
            cafe24_product_sales_total_count = len(cafe24_product_sales_data)
            response_data["cafe24_product_sales"] = cafe24_product_sales_data[offset : offset + limit]
            response_data["cafe24_product_sales_total_count"] = cafe24_product_sales_total_count
            print(f"[DEBUG] Cafe24 Product Sales total: {cafe24_product_sales_total_count}")

        # ✅ 5) ViewItem Summary (✳ 전체 데이터 전송)
        if data_type in ["viewitem_summary", "all"]:
            viewitem_summary_data = get_viewitem_summary(
                company_name=company_name,
                start_date=start_date,
                end_date=end_date
            )
            viewitem_summary_total_count = len(viewitem_summary_data)
            response_data["viewitem_summary"] = viewitem_summary_data
            response_data["viewitem_summary_total_count"] = viewitem_summary_total_count
            print(f"[DEBUG] ViewItem Summary total: {viewitem_summary_total_count}")

        # ✅ 6) GA4 Source Summary
        if data_type in ["ga4_source_summary", "all"]:
            ga4_source_data = get_ga4_source_summary(
                company_name=company_name,
                start_date=start_date,
                end_date=end_date
            )
            ga4_source_summary_total_count = len(ga4_source_data)
            response_data["ga4_source_summary"] = ga4_source_data[offset : offset + limit]
            response_data["ga4_source_summary_total_count"] = ga4_source_summary_total_count
            print(f"[DEBUG] GA4 Source Summary total: {ga4_source_summary_total_count}")

        # ✅ 7) Monthly Net Sales & Visitors Chart (✳ 전체 전송, 기간 필터 무시)
        if data_type == "monthly_net_sales_visitors":
            monthly_data = get_monthly_net_sales_visitors(company_name)
            response_data["monthly_net_sales_visitors"] = monthly_data
            response_data["monthly_net_sales_visitors_total_count"] = len(monthly_data)
            print(f"[DEBUG] Monthly Net Sales & Visitors total: {len(monthly_data)}")

        return jsonify(response_data), 200

    except TypeError as te:
        print(f"[ERROR] 요청 데이터 타입 오류: {te}")
        return jsonify({"status": "error", "message": f"잘못된 요청 형식: {str(te)}"}), 400

    except Exception as e:
        print(f"[ERROR] 데이터 조회 중 오류 발생: {e}")
        return jsonify({"status": "error", "message": f"데이터 조회 중 오류 발생: {str(e)}"}), 500
