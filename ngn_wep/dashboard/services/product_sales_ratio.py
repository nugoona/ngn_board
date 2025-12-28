from google.cloud import bigquery
from ..utils.cache_utils import cached_query


def get_bigquery_client():
    return bigquery.Client()


@cached_query(func_name="product_sales_ratio", ttl=900)  # 캐싱 활성화 (15분)
def get_product_sales_ratio(
    company_name,
    start_date: str,
    end_date: str,
    limit: int = 50,
    user_id=None,
):
    '''
    ✅ 상품별 매출 비율 조회 (2025-07-25 전면 개편)
      • LIMIT 파라미터 제거 → 문자열 삽입(정수 검증)
      • 중첩 집계 → WITH base / total 로 분리
      • BigQuery용 정규식에서 r'' 접두사 제거
    '''
    print(
        f"[DEBUG] product_sales_ratio 호출: "
        f"company_name={company_name}, start_date={start_date}, "
        f"end_date={end_date}, limit={limit}"
    )

    # ---------- 기본 검증 ----------
    if not start_date or not end_date:
        print('[WARN] start_date 또는 end_date가 없습니다.')
        return []
        
    if not isinstance(limit, int) or limit <= 0:
        print('[WARN] limit 값이 유효하지 않습니다.')
        return []

    # ---------- 업체 필터 ----------
    query_params_base = []

    if company_name == 'all':
        company_filter = (
            "LOWER(company_name) = 'demo'"
            if user_id == 'demo'
            else "LOWER(company_name) != 'demo'"
        )

    elif isinstance(company_name, list):
        filtered = [n.lower() for n in company_name]
        filtered = ['demo'] if user_id == 'demo' else [n for n in filtered if n != 'demo']
        if not filtered:
            print('[DEBUG] 필터링된 company_name 리스트 없음 → 빈 결과 반환')
            return []

        company_filter = 'LOWER(company_name) IN UNNEST(@company_name_list)'
        query_params_base.append(
            bigquery.ArrayQueryParameter('company_name_list', 'STRING', filtered)
        )
        print(f'[DEBUG] company_name 리스트: {filtered}')

    else:
        company_name = company_name.lower()
        if company_name == 'demo' and user_id != 'demo':
            print('[DEBUG] demo 계정 아님 + demo 요청 → 빈 결과 반환')
            return []

        company_filter = 'LOWER(company_name) = LOWER(@company_name)'
        query_params_base.append(
            bigquery.ScalarQueryParameter('company_name', 'STRING', company_name)
        )
        print(f'[DEBUG] company_name 단일 값: {company_name}')

    # ---------- 공통 파라미터 ----------
    query_params_common = [
        bigquery.ScalarQueryParameter('start_date', 'DATE', start_date),
        bigquery.ScalarQueryParameter('end_date', 'DATE', end_date),
        bigquery.ScalarQueryParameter('limit', 'INT64', limit),
    ]
    query_params = query_params_base + query_params_common
    print(f'[DEBUG] 최종 company_filter: {company_filter}')
    print(f'[DEBUG] query_params: {len(query_params)}개')

    # ---------- 쿼리 ----------
    query = f"""
    WITH base AS (
        SELECT
            company_name,
            REGEXP_REPLACE(
                REGEXP_REPLACE(
                    product_name,
                    r'\[(?i)(?!set\])[^\]]+\]',         -- [SET]/[set] 제외하고 [브랜드] 등 제거
                    ''
                ),
                r'_.*$',                              -- _컬러 제거
                ''
            ) AS cleaned_product_name,
            SUM(item_quantity)      AS item_quantity,
            SUM(item_product_sales) AS item_product_sales
        FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_items`
        WHERE payment_date BETWEEN @start_date AND @end_date
          AND {company_filter}
          AND item_product_sales > 0
          AND product_name IS NOT NULL
        GROUP BY company_name, cleaned_product_name
    ),
    total AS (
        SELECT SUM(item_product_sales) AS total_sales FROM base
    )
    SELECT
        FORMAT_DATE('%Y-%m-%d', @start_date) || ' ~ ' ||
        FORMAT_DATE('%Y-%m-%d', @end_date)               AS report_period,
        b.company_name,
        b.cleaned_product_name,
        b.item_quantity,
        b.item_product_sales,
        ROUND(b.item_product_sales * 100.0 / t.total_sales, 1)
            AS sales_ratio_percent
    FROM base b
    CROSS JOIN total t
    ORDER BY b.item_product_sales DESC
    LIMIT @limit
    """

    # ---------- 실행 ----------
    try:
        client = get_bigquery_client()

        print('[DEBUG] 쿼리 파라미터:')
        for i, p in enumerate(query_params):
            val = getattr(p, "value", getattr(p, "values", None))
            print(f'  {i}: {p.name} = {val}')

        rows = client.query(
            query,
            job_config=bigquery.QueryJobConfig(query_parameters=query_params),
        ).result()
        data = [dict(r) for r in rows]
        print(f'[DEBUG] 결과 건수: {len(data)}')
        
        if len(data) > 0:
            print(f'[DEBUG] 첫 번째 결과: {data[0]}')
        else:
            print('[DEBUG] ⚠️ 결과가 없음 (비용 절감을 위해 디버깅 쿼리 제거됨)')

        return data

    except Exception as ex:
        print('[ERROR] get_product_sales_ratio 실패:', ex)
        return []