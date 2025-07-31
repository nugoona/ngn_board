import concurrent.futures
from google.cloud import bigquery
from ..utils.cache_utils import cached_query
from .cafe24_service import get_cafe24_sales_data
from .meta_ads_insight import get_meta_ads_insight_table

def get_bigquery_client():
    return bigquery.Client()

@cached_query(func_name="performance_summary_new", ttl=300)  # 5분 캐싱
def get_performance_summary_new(company_name, start_date: str, end_date: str, user_id: str = None):
    """
    ✅ 새로운 통합 성과 요약 API (최적화됨)
    - 사이트 성과: 카페24 매출 데이터에서 직접 조회
    - 광고 성과: 메타 광고 계정 단위 성과에서 직접 조회
    - 계산: 매출 대비 광고비 실시간 계산
    """
    print(f"[DEBUG] get_performance_summary_new 호출 - company_name: {company_name}, start_date: {start_date}, end_date: {end_date}, user_id: {user_id}")
    
    if not start_date or not end_date:
        raise ValueError("start_date / end_date가 없습니다.")

    try:
        # 🔥 순차 처리로 변경 (병렬 처리 오버헤드 제거)
        print("[DEBUG] 순차 처리로 데이터 조회 시작")
        
        # 1. 카페24 매출 데이터 조회
        cafe24_data = get_cafe24_summary_simple(company_name, start_date, end_date, user_id)
        print(f"[DEBUG] 카페24 데이터 조회 완료: {cafe24_data}")
        
        # 2. 메타 광고 계정 단위 성과 조회
        meta_ads_data = get_meta_ads_summary_simple(company_name, start_date, end_date)
        print(f"[DEBUG] 메타 광고 데이터 조회 완료: {meta_ads_data}")
        
        # 3. GA4 방문자 데이터 조회
        total_visitors = get_ga4_visitors_simple(company_name, start_date, end_date, user_id)
        print(f"[DEBUG] GA4 방문자 데이터 조회 완료: {total_visitors}")
        
        # 4. 데이터 조합 및 계산
        result = combine_performance_data_parallel(cafe24_data, meta_ads_data, total_visitors, start_date, end_date)
        
        print(f"[DEBUG] performance_summary_new 결과: {len(result)}개")
        return result
        
    except Exception as e:
        print("[ERROR] performance_summary_new 오류:", e)
        return []

def get_cafe24_summary_simple(company_name, start_date: str, end_date: str, user_id: str = None):
    """
    ✅ 카페24 매출 요약 (성과 요약용 최적화)
    """
    query_params = []
    
    # 업체 필터 처리
    if isinstance(company_name, list):
        filtered_companies = [name.lower() for name in company_name]
        filtered_companies = (
            ["demo"] if user_id == "demo"
            else [name for name in filtered_companies if name != "demo"]
        )
        if not filtered_companies:
            return {"total_revenue": 0, "total_orders": 0}
        company_filter = "LOWER(company_name) IN UNNEST(@company_name_list)"
        query_params.append(bigquery.ArrayQueryParameter("company_name_list", "STRING", filtered_companies))
    else:
        company_name = company_name.lower()
        if company_name == "demo" and user_id != "demo":
            return {"total_revenue": 0, "total_orders": 0}
        company_filter = "LOWER(company_name) = @company_name"
        query_params.append(bigquery.ScalarQueryParameter("company_name", "STRING", company_name))
    
    # 날짜 파라미터
    query_params.extend([
        bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
        bigquery.ScalarQueryParameter("end_date", "DATE", end_date)
    ])
    
    # 🔥 더 간단한 쿼리로 최적화
    query = f"""
        SELECT 
            COALESCE(SUM(total_payment - total_refund_amount), 0) AS total_revenue,
            COALESCE(SUM(total_orders), 0) AS total_orders
        FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
        WHERE payment_date BETWEEN @start_date AND @end_date
          AND {company_filter}
          AND total_payment > 0
    """
    
    try:
        client = get_bigquery_client()
        result = client.query(query, job_config=bigquery.QueryJobConfig(query_parameters=query_params)).result()
        row = list(result)[0]
        return {
            "total_revenue": row.total_revenue or 0,
            "total_orders": row.total_orders or 0
        }
    except Exception as e:
        print(f"[ERROR] 카페24 요약 조회 오류: {e}")
        return {"total_revenue": 0, "total_orders": 0}

def get_meta_ads_summary_simple(company_name, start_date: str, end_date: str):
    """
    ✅ 메타 광고 요약 (성과 요약용 최적화)
    """
    query_params = []
    
    # 업체 필터 처리
    if isinstance(company_name, list):
        filtered_companies = [name.lower() for name in company_name]
        company_filter = "LOWER(company_name) IN UNNEST(@company_name_list)"
        query_params.append(bigquery.ArrayQueryParameter("company_name_list", "STRING", filtered_companies))
    else:
        company_name = company_name.lower()
        company_filter = "LOWER(company_name) = @company_name"
        query_params.append(bigquery.ScalarQueryParameter("company_name", "STRING", company_name))
    
    # 날짜 파라미터
    query_params.extend([
        bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
        bigquery.ScalarQueryParameter("end_date", "DATE", end_date)
    ])
    
    # 🔥 더 간단한 쿼리로 최적화
    query = f"""
        SELECT 
            COALESCE(SUM(spend), 0) AS total_spend,
            COALESCE(SUM(clicks), 0) AS total_clicks,
            COALESCE(SUM(purchases), 0) AS total_purchases,
            COALESCE(SUM(purchase_value), 0) AS total_purchase_value,
            MAX(updated_at) AS updated_at
        FROM `winged-precept-443218-v8.ngn_dataset.meta_ads_account_summary`
        WHERE date BETWEEN @start_date AND @end_date
          AND {company_filter}
          AND spend > 0
    """
    
    try:
        client = get_bigquery_client()
        result = client.query(query, job_config=bigquery.QueryJobConfig(query_parameters=query_params)).result()
        row = list(result)[0]
        return {
            "total_spend": row.total_spend or 0,
            "total_clicks": row.total_clicks or 0,
            "total_purchases": row.total_purchases or 0,
            "total_purchase_value": row.total_purchase_value or 0,
            "updated_at": row.updated_at
        }
    except Exception as e:
        print(f"[ERROR] 메타 광고 요약 조회 오류: {e}")
        return {
            "total_spend": 0,
            "total_clicks": 0,
            "total_purchases": 0,
            "total_purchase_value": 0,
            "updated_at": None
        }

def get_ga4_visitors_simple(company_name, start_date: str, end_date: str, user_id: str = None):
    """
    ✅ GA4 방문자 수 조회 (성과 요약용 최적화)
    """
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
    
    # 🔥 더 간단한 쿼리로 최적화
    query = f"""
        SELECT COALESCE(SUM(total_users), 0) AS total_visitors
        FROM `winged-precept-443218-v8.ngn_dataset.ga4_traffic_ngn`
        WHERE {company_filter}
          AND event_date BETWEEN @start_date AND @end_date
          AND total_users > 0
    """
    
    try:
        client = get_bigquery_client()
        result = client.query(query, job_config=bigquery.QueryJobConfig(query_parameters=query_params)).result()
        row = list(result)[0]
        return row.total_visitors or 0
    except Exception as e:
        print(f"[ERROR] GA4 방문자 조회 오류: {e}")
        return 0

def combine_performance_data_parallel(cafe24_data, meta_ads_data, total_visitors, start_date, end_date):
    """
    카페24 매출과 메타 광고 데이터를 조합하여 성과 요약 생성
    """
    # 카페24 데이터 집계
    site_revenue = cafe24_data.get('total_revenue', 0)
    total_orders = cafe24_data.get('total_orders', 0)
    
    # 메타 광고 데이터 집계
    ad_spend = meta_ads_data.get('total_spend', 0)
    total_purchases = meta_ads_data.get('total_purchases', 0)
    total_purchase_value = meta_ads_data.get('total_purchase_value', 0)
    total_clicks = meta_ads_data.get('total_clicks', 0)
    updated_at = meta_ads_data.get('updated_at')
    
    # 계산된 값들
    roas_percentage = (total_purchase_value / ad_spend * 100) if ad_spend > 0 else 0
    avg_cpc = (ad_spend / total_clicks) if total_clicks > 0 else 0
    ad_spend_ratio = (ad_spend / site_revenue * 100) if site_revenue > 0 else 0
    
    # 결과 구성
    result = {
        "date_range": f"{start_date} ~ {end_date}",
        "ad_media": "meta",  # ← 진행중인 광고 정보
        "ad_spend": round(ad_spend, 2),
        "total_clicks": total_clicks,
        "total_purchases": total_purchases,
        "total_purchase_value": round(total_purchase_value, 2),
        "roas_percentage": round(roas_percentage, 2),
        "avg_cpc": round(avg_cpc, 2),
        "site_revenue": round(site_revenue, 2),
        "total_orders": total_orders,  # 카페24에서 가져온 주문수
        "total_visitors": total_visitors,
        "ad_spend_ratio": round(ad_spend_ratio, 2),
        "updated_at": updated_at  # ← 업데이트 시간 정보
    }
    
    return [result] 