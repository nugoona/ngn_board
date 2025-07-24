from google.cloud import bigquery
import time
from ..utils.cache_utils import cached_query


def get_bigquery_client():
    """ ✅ BigQuery Client 생성 """
    return bigquery.Client()


@cached_query(func_name="cafe24_sales", ttl=180)  # 3분 캐싱
def get_cafe24_sales_data(company_name, period, start_date, end_date,
                           date_type="summary", date_sort="desc",
                           limit=1000, page=1, user_id=None):
    """ ✅ Cafe24 매출 데이터 조회 (페이징 + 전체 개수 반환 포함) """
    if not start_date or not end_date:
        raise ValueError("[ERROR] get_cafe24_sales_data() - start_date 또는 end_date가 누락됨")

    offset = (page - 1) * limit
    client = get_bigquery_client()

    query_params_base = []

    # ✅ 업체 필터 처리 (user_id 기반 demo 필터 적용)
    if company_name == "all":
        if user_id == "demo":
            company_filter = "LOWER(company_name) = 'demo'"
        else:
            company_filter = "LOWER(company_name) != 'demo'"
    elif isinstance(company_name, list):
        filtered_companies = [name.lower() for name in company_name]

        if user_id == "demo":
            filtered_companies = ["demo"]
        else:
            filtered_companies = [name for name in filtered_companies if name != "demo"]

        if not filtered_companies:
            print("[DEBUG] 필터링된 company_name 리스트 없음 → 빈 결과 반환")
            return {"rows": [], "total_count": 0}

        company_filter = "LOWER(company_name) IN UNNEST(@company_name_list)"
        query_params_base.append(
            bigquery.ArrayQueryParameter("company_name_list", "STRING", filtered_companies)
        )
    else:
        company_name = company_name.lower()
        if company_name == "demo" and user_id != "demo":
            print("[DEBUG] demo 계정 아님 + demo 요청 → 빈 결과 반환")
            return {"rows": [], "total_count": 0}

        company_filter = "LOWER(company_name) = LOWER(@company_name)"
        query_params_base.append(
            bigquery.ScalarQueryParameter("company_name", "STRING", company_name)
        )

    # ✅ 날짜 및 페이징 파라미터
    query_params_common = [
        bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
        bigquery.ScalarQueryParameter("end_date", "DATE", end_date)
    ]
    query_params_main = query_params_base + query_params_common + [
        bigquery.ScalarQueryParameter("limit", "INT64", limit),
        bigquery.ScalarQueryParameter("offset", "INT64", offset),
    ]

    report_date_expr = (
        "FORMAT_DATE('%Y-%m-%d', payment_date)"
        if date_type == "daily"
        else "@start_date || ' ~ ' || @end_date"
    )
    group_by_expr = (
        f"{report_date_expr}, company_name"
        if date_type == "daily"
        else "company_name"
    )
    order_by_clause = (
        f"ORDER BY {report_date_expr} {date_sort.upper()}, company_name"
        if date_type == "daily"
        else "ORDER BY company_name"
    )

    main_query = f"""
        SELECT
            {report_date_expr} AS report_date,
            company_name,
            SUM(total_orders) AS total_orders,
            SUM(item_orders) AS item_orders,
            SUM(item_product_price) AS item_product_price,
            SUM(total_shipping_fee) AS total_shipping_fee,
            SUM(item_product_price + total_shipping_fee - total_payment - total_coupon_discount) AS total_discount,
            SUM(total_coupon_discount) AS total_coupon_discount,
            SUM(total_payment) AS total_payment,
            SUM(total_refund_amount) AS total_refund_amount,
            SUM(total_payment - total_refund_amount) AS net_sales
        FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
        WHERE payment_date BETWEEN @start_date AND @end_date
          AND {company_filter}
        GROUP BY {group_by_expr}
        {order_by_clause}
        LIMIT @limit OFFSET @offset
    """

    count_query = f"""
        SELECT COUNT(*) AS total_count
        FROM (
            SELECT 1
            FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
            WHERE payment_date BETWEEN @start_date AND @end_date
              AND {company_filter}
            GROUP BY {group_by_expr}
        )
    """

    try:
        t1 = time.time()
        rows = client.query(main_query, job_config=bigquery.QueryJobConfig(query_parameters=query_params_main)).result()
        data = [dict(row) for row in rows]
        t2 = time.time()

        count_rows = client.query(count_query, job_config=bigquery.QueryJobConfig(query_parameters=query_params_base + query_params_common)).result()
        total_count = next(count_rows).get("total_count", 0)

        print(f"[DEBUG] Cafe24 매출 데이터 쿼리 완료 - 데이터 {len(data)}개, 전체 {total_count}개")
        print(f"[DEBUG] ⏱ 실행 시간: {t2 - t1:.2f}초")

        return {
            "rows": data,
            "total_count": total_count
        }

    except Exception as e:
        print(f"[ERROR] Cafe24 매출 쿼리 실패: {e}")
        return {
            "rows": [],
            "total_count": 0
        }



@cached_query(func_name="cafe24_product_sales", ttl=180)  # 3분 캐싱
def get_cafe24_product_sales(company_name, period, start_date, end_date,
                              sort_by="item_product_sales", limit=1000, page=1, user_id=None):
    from google.cloud import bigquery
    import time

    if not start_date or not end_date:
        raise ValueError("[ERROR] get_cafe24_product_sales() - start_date 또는 end_date가 누락됨")

    offset = (page - 1) * limit
    client = bigquery.Client()

    query_params_base = []

    # ✅ 업체 필터 처리
    if company_name == "all":
        if user_id == "demo":
            company_filter = "LOWER(i.company_name) = 'demo'"
        else:
            company_filter = "LOWER(i.company_name) != 'demo'"
    elif isinstance(company_name, list):
        filtered_companies = [name.lower() for name in company_name if name.lower() != "demo"]
        if user_id == "demo":
            filtered_companies = ["demo"]
        if not filtered_companies:
            return {"rows": [], "total_count": 0}
        company_filter = "LOWER(i.company_name) IN UNNEST(@company_name_list)"
        query_params_base.append(
            bigquery.ArrayQueryParameter("company_name_list", "STRING", filtered_companies)
        )
    else:
        company_name = company_name.lower()
        if company_name == "demo" and user_id != "demo":
            return {"rows": [], "total_count": 0}
        company_filter = "LOWER(i.company_name) = LOWER(@company_name)"
        query_params_base.append(
            bigquery.ScalarQueryParameter("company_name", "STRING", company_name)
        )

    query_params_common = [
        bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
        bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
    ]
    query_params_main = query_params_base + query_params_common + [
        bigquery.ScalarQueryParameter("limit", "INT64", limit),
        bigquery.ScalarQueryParameter("offset", "INT64", offset),
    ]

    valid_sort_columns = {
        "item_quantity": "item_quantity",
        "item_product_sales": "item_product_sales"
    }
    order_by_column = valid_sort_columns.get(sort_by, "item_product_sales")

    # ✅ 최적화된 쿼리: 불필요한 JOIN 제거, 복잡한 URL 생성 로직 간소화
    data_query = f"""
        SELECT
            CONCAT(@start_date, ' ~ ', @end_date) AS report_date,
            i.company_name,
            i.product_name,
            MAX(i.product_price) AS product_price,
            SUM(i.total_quantity) AS total_quantity,
            SUM(i.total_canceled) AS total_canceled,
            SUM(i.item_quantity) AS item_quantity,
            SUM(i.item_product_sales) AS item_product_sales,
            SUM(i.total_first_order) AS total_first_order,
            -- ✅ 간소화된 URL (복잡한 JOIN 제거)
            CONCAT('https://product-', CAST(i.product_no AS STRING)) AS product_url,
            MAX(i.updated_at) AS updated_at
        FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_items` AS i
        WHERE i.payment_date BETWEEN @start_date AND @end_date
          AND {company_filter}
          AND i.item_product_sales > 0
        GROUP BY i.company_name, i.product_name, i.product_no
        ORDER BY {order_by_column} DESC
        LIMIT @limit OFFSET @offset
    """

    count_query = f"""
        SELECT COUNT(*) AS total_count
        FROM (
            SELECT 1
            FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_items` AS i
            WHERE i.payment_date BETWEEN @start_date AND @end_date
              AND {company_filter}
              AND i.item_product_sales > 0
            GROUP BY i.company_name, i.product_name, i.product_no
        )
    """

    try:
        t1 = time.time()
        result = client.query(data_query, job_config=bigquery.QueryJobConfig(query_parameters=query_params_main)).result()
        rows = [dict(row) for row in result]
        t2 = time.time()

        count_result = client.query(count_query, job_config=bigquery.QueryJobConfig(query_parameters=query_params_base + query_params_common)).result()
        total_count = next(count_result)["total_count"]
        t3 = time.time()

        print(f"[DEBUG] Cafe24 상품 매출 쿼리 완료 (최적화됨) - 데이터 {len(rows)}개 / 전체 {total_count}개")
        print(f"[DEBUG] ⏱ 실행 시간: 데이터 {t2 - t1:.2f}s / 개수 {t3 - t2:.2f}s")

        return {
            "rows": rows,
            "total_count": total_count
        }

    except Exception as e:
        print(f"[ERROR] Cafe24 상품 판매 쿼리 실패: {e}")
        return {
            "rows": [],
            "total_count": 0
        }
