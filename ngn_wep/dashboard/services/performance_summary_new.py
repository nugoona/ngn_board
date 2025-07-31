import concurrent.futures
from google.cloud import bigquery
from ..utils.cache_utils import cached_query
from .cafe24_service import get_cafe24_sales_data
from .meta_ads_insight import get_meta_ads_insight_table

def get_bigquery_client():
    return bigquery.Client()

# @cached_query(func_name="performance_summary_new", ttl=600)  # 10분 캐싱
def get_performance_summary_new(company_name, start_date: str, end_date: str, user_id: str = None):
    """
    ✅ 새로운 통합 성과 요약 API (최적화됨)
    - 사이트 성과: 카페24 매출 데이터에서 직접 조회
    - 광고 성과: 메타 광고 계정 단위 성과에서 직접 조회
    - 계산: 매출 대비 광고비 실시간 계산
    """
    print(f"[DEBUG] get_performance_summary_new 호출 - company_name: {company_name}, start_date: {start_date}, end_date: {end_date}, user_id: {user_id}")
    
    # 🔥 캐시 완전 비활성화
    print("[DEBUG] 캐시 완전 비활성화 - 새로운 데이터 조회")
    
    if not start_date or not end_date:
        raise ValueError("start_date / end_date가 없습니다.")

    try:
        # 🔥 병렬 처리로 변경 (3개 쿼리를 동시에 실행)
        import time
        start_time = time.time()
        print("[DEBUG] 병렬 처리로 데이터 조회 시작")
        
        # 기본값 설정
        default_cafe24 = {"total_revenue": 0, "total_orders": 0}
        default_meta = {"total_spend": 0, "total_clicks": 0, "total_purchases": 0, "total_purchase_value": 0, "updated_at": None}
        default_ga4 = 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            # 3개 작업을 동시에 실행
            future_cafe24 = executor.submit(get_cafe24_summary_simple, company_name, start_date, end_date, user_id)
            future_meta = executor.submit(get_meta_ads_summary_simple, company_name, start_date, end_date)
            future_ga4 = executor.submit(get_ga4_visitors_simple, company_name, start_date, end_date, user_id)
            
            # 결과 수집 (개별 오류 처리)
            try:
                cafe24_data = future_cafe24.result(timeout=30)
            except Exception as e:
                print(f"[ERROR] 카페24 데이터 조회 실패: {e}")
                cafe24_data = default_cafe24
                
            try:
                meta_ads_data = future_meta.result(timeout=30)
            except Exception as e:
                print(f"[ERROR] 메타 광고 데이터 조회 실패: {e}")
                meta_ads_data = default_meta
                
            try:
                total_visitors = future_ga4.result(timeout=30)
            except Exception as e:
                print(f"[ERROR] GA4 방문자 데이터 조회 실패: {e}")
                total_visitors = default_ga4
        
        end_time = time.time()
        print(f"[DEBUG] 병렬 처리 완료 ({end_time - start_time:.2f}초) - 카페24: {cafe24_data}, 메타: {meta_ads_data}, GA4: {total_visitors}")
        
        # 4. 데이터 조합 및 계산
        result = combine_performance_data_parallel(cafe24_data, meta_ads_data, total_visitors, start_date, end_date)
        
        print(f"[DEBUG] performance_summary_new 결과: {len(result)}개")
        if result:
            print(f"[DEBUG] 최종 결과 - 날짜범위: {result[0].get('date_range')}, 광고비: {result[0].get('ad_spend')}, 매출: {result[0].get('site_revenue')}")
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
        LIMIT 1
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
    ✅ 메타 광고 요약 (성과 요약용 최적화) - meta_ads_insight.py와 동일한 로직 사용
    """
    print(f"[DEBUG] get_meta_ads_summary_simple 호출 - company_name: {company_name}, start_date: {start_date}, end_date: {end_date}")
    
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
    
    # 🔥 meta_ads_insight.py와 동일한 로직 사용
    query = f"""
        WITH latest_accounts AS (
          SELECT * EXCEPT(rn) FROM (
            SELECT account_id,
                   account_name,
                   company_name,
                   ROW_NUMBER() OVER (PARTITION BY account_id ORDER BY updated_at DESC) AS rn
            FROM `winged-precept-443218-v8.ngn_dataset.meta_ads_account_summary`
          )
          WHERE rn = 1
        )
        
        SELECT 
            COALESCE(SUM(A.spend), 0) AS total_spend,
            COALESCE(SUM(A.clicks), 0) AS total_clicks,
            COALESCE(SUM(A.purchases), 0) AS total_purchases,
            COALESCE(SUM(A.purchase_value), 0) AS total_purchase_value,
            MAX(A.updated_at) AS updated_at
        FROM `winged-precept-443218-v8.ngn_dataset.meta_ads_account_summary` A
        LEFT JOIN latest_accounts L ON A.account_id = L.account_id
        WHERE A.date BETWEEN @start_date AND @end_date
          AND LOWER(L.company_name) = LOWER(@company_name)
        GROUP BY L.company_name
        HAVING SUM(A.spend) > 0
        LIMIT 1
    """
    
    print(f"[DEBUG] 메타 광고 쿼리 파라미터: {query_params}")
    print(f"[DEBUG] 메타 광고 쿼리: {query}")
    
    try:
        client = get_bigquery_client()
        result = client.query(query, job_config=bigquery.QueryJobConfig(query_parameters=query_params)).result()
        rows = list(result)
        
        print(f"[DEBUG] 메타 광고 쿼리 결과: {len(rows)}행")
        
        if rows:
            row = rows[0]
            result_data = {
                "total_spend": row.total_spend or 0,
                "total_clicks": row.total_clicks or 0,
                "total_purchases": row.total_purchases or 0,
                "total_purchase_value": row.total_purchase_value or 0,
                "updated_at": row.updated_at
            }
            print(f"[DEBUG] 메타 광고 결과 데이터: {result_data}")
        else:
            # 데이터가 없으면 기본값 반환
            result_data = {
                "total_spend": 0,
                "total_clicks": 0,
                "total_purchases": 0,
                "total_purchase_value": 0,
                "updated_at": None
            }
            print(f"[DEBUG] 메타 광고 데이터 없음 - 기본값 반환: {result_data}")
        
        return result_data
        
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
        LIMIT 1
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
    try:
        # 카페24 데이터 집계 (안전한 타입 변환)
        site_revenue = float(cafe24_data.get('total_revenue', 0) or 0)
        total_orders = int(cafe24_data.get('total_orders', 0) or 0)
        
        # 메타 광고 데이터 집계 (안전한 타입 변환)
        ad_spend = float(meta_ads_data.get('total_spend', 0) or 0)
        total_purchases = int(meta_ads_data.get('total_purchases', 0) or 0)
        total_purchase_value = float(meta_ads_data.get('total_purchase_value', 0) or 0)
        total_clicks = int(meta_ads_data.get('total_clicks', 0) or 0)
        updated_at = meta_ads_data.get('updated_at')
        
        # 계산된 값들 (0으로 나누기 방지)
        roas_percentage = (total_purchase_value / ad_spend * 100) if ad_spend > 0 else 0
        avg_cpc = (ad_spend / total_clicks) if total_clicks > 0 else 0
        ad_spend_ratio = (ad_spend / site_revenue * 100) if site_revenue > 0 else 0
        
        # 🔥 진행중인 광고 판단 로직 개선
        # 광고비가 0보다 크면 'meta', 0이거나 null이면 '없음'
        ad_media = "meta" if ad_spend > 0 else "없음"
        
        print(f"[DEBUG] 진행중인 광고 판단 - 광고비: {ad_spend}, 결과: {ad_media}")
        print(f"[DEBUG] ad_spend 타입: {type(ad_spend)}, 값: {ad_spend}")
        print(f"[DEBUG] ad_spend > 0 조건: {ad_spend > 0}")
        
        # 결과 구성
        result = {
            "date_range": f"{start_date} ~ {end_date}",
            "ad_media": ad_media,  # ← 조건부 진행중인 광고 정보
            "ad_spend": round(ad_spend, 2),
            "total_clicks": total_clicks,
            "total_purchases": total_purchases,
            "total_purchase_value": round(total_purchase_value, 2),
            "roas_percentage": round(roas_percentage, 2),
            "avg_cpc": round(avg_cpc, 2),
            "site_revenue": round(site_revenue, 2),
            "total_orders": total_orders,  # 카페24에서 가져온 주문수
            "total_visitors": int(total_visitors or 0),
            "ad_spend_ratio": round(ad_spend_ratio, 2),
            "updated_at": updated_at  # ← 업데이트 시간 정보
        }
        
        return [result]
        
    except Exception as e:
        print(f"[ERROR] 데이터 조합 중 오류 발생: {e}")
        # 오류 발생 시 기본값으로 반환
        return [{
            "date_range": f"{start_date} ~ {end_date}",
            "ad_media": "없음",
            "ad_spend": 0,
            "total_clicks": 0,
            "total_purchases": 0,
            "total_purchase_value": 0,
            "roas_percentage": 0,
            "avg_cpc": 0,
            "site_revenue": 0,
            "total_orders": 0,
            "total_visitors": 0,
            "ad_spend_ratio": 0,
            "updated_at": None
        }] 