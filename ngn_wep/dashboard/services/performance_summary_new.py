from google.cloud import bigquery
from ..utils.cache_utils import cached_query
from .cafe24_sales import get_cafe24_sales_data
from .meta_ads_account_summary import get_meta_ads_account_summary

def get_bigquery_client():
    return bigquery.Client()

@cached_query(func_name="performance_summary_new", ttl=300)  # 5분 캐싱
def get_performance_summary_new(company_name, start_date: str, end_date: str, user_id: str = None):
    """
    ✅ 새로운 통합 성과 요약 API
    - 사이트 성과: 카페24 매출 데이터에서 직접 조회
    - 광고 성과: 메타 광고 계정 단위 성과에서 직접 조회
    - 계산: 매출 대비 광고비 실시간 계산
    """
    print(f"[DEBUG] get_performance_summary_new 호출 - company_name: {company_name}, start_date: {start_date}, end_date: {end_date}, user_id: {user_id}")
    
    if not start_date or not end_date:
        raise ValueError("start_date / end_date가 없습니다.")

    try:
        # 1. 카페24 매출 데이터 조회 (사이트 성과)
        cafe24_data = get_cafe24_sales_data(
            company_name=company_name,
            period="manual",
            start_date=start_date,
            end_date=end_date,
            date_type="payment_date",
            date_sort="desc",
            limit=1000,
            page=1,
            user_id=user_id
        )
        
        # 2. 메타 광고 계정 단위 성과 조회
        meta_ads_data = get_meta_ads_account_summary(
            company_name=company_name,
            start_date=start_date,
            end_date=end_date,
            user_id=user_id
        )
        
        # 3. 데이터 조합 및 계산
        result = combine_performance_data(cafe24_data, meta_ads_data, start_date, end_date)
        
        print(f"[DEBUG] performance_summary_new 결과: {len(result)}개")
        return result
        
    except Exception as e:
        print("[ERROR] performance_summary_new 오류:", e)
        return []

def combine_performance_data(cafe24_data, meta_ads_data, start_date, end_date):
    """
    카페24 매출과 메타 광고 데이터를 조합하여 성과 요약 생성
    """
    # 카페24 데이터 집계
    site_revenue = sum(row.get('net_sales', 0) for row in cafe24_data.get('rows', []))
    total_orders = sum(row.get('order_count', 0) for row in cafe24_data.get('rows', []))
    
    # GA4 방문자 데이터 조회
    total_visitors = get_ga4_visitors(company_name, start_date, end_date, user_id)
    
    # 메타 광고 데이터 집계
    ad_spend = sum(row.get('spend', 0) for row in meta_ads_data)
    total_purchases = sum(row.get('purchases', 0) for row in meta_ads_data)
    total_purchase_value = sum(row.get('purchase_value', 0) for row in meta_ads_data)
    total_clicks = sum(row.get('clicks', 0) for row in meta_ads_data)
    
    # 계산된 값들
    roas_percentage = (total_purchase_value / ad_spend * 100) if ad_spend > 0 else 0
    avg_cpc = (ad_spend / total_clicks) if total_clicks > 0 else 0
    ad_spend_ratio = (ad_spend / site_revenue * 100) if site_revenue > 0 else 0
    
    # 결과 구성
    result = {
        "date_range": f"{start_date} ~ {end_date}",
        "ad_media": "meta",
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
        "updated_at": None  # 실시간 데이터이므로 None
    }
    
    return [result]

def get_ga4_visitors(company_name, start_date: str, end_date: str, user_id: str = None):
    """
    GA4에서 방문자 수 조회
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
    
    query = f"""
        SELECT SUM(total_users) AS total_visitors
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