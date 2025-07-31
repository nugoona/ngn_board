from google.cloud import bigquery

def get_daily_summary_query(start_date, end_date, company_name):
    """
    동적 쿼리를 생성하여 Google BigQuery에서 데이터 조회
    """
    query = f"""
    WITH prepayment_excluded AS (
      SELECT o.order_id
      FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders_table` o
      WHERE o.payment_method_name LIKE '%선불금%'
        OR o.naverpay_payment_information = 'N'
    ),
    distinct_orders AS (
      SELECT DISTINCT o.mall_id, o.order_id, o.payment_amount, o.first_order
      FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders_table` o
      WHERE o.mall_id IN (SELECT mall_id FROM `winged-precept-443218-v8.ngn_dataset.company_info`
                          WHERE company_name = '{company_name}')
        AND FORMAT_TIMESTAMP("%Y-%m-%d", TIMESTAMP(o.payment_date), "Asia/Seoul") 
        BETWEEN '{start_date}' AND '{end_date}'
    ),
    distinct_items AS (
      SELECT DISTINCT i.mall_id, i.order_id, i.product_no, i.product_name, i.product_price, 
        i.quantity, p.category_no,
        CASE WHEN o.canceled = TRUE THEN i.quantity ELSE 0 END AS canceled_quantity
      FROM `winged-precept-443218-v8.ngn_dataset.cafe24_order_items_table` i
      JOIN `winged-precept-443218-v8.ngn_dataset.cafe24_orders_table` o
        ON i.mall_id = o.mall_id AND i.order_id = o.order_id
      LEFT JOIN `winged-precept-443218-v8.ngn_dataset.cafe24_products_table` p
        ON i.product_no = p.product_no AND i.mall_id = p.mall_id
      WHERE i.mall_id IN (SELECT mall_id FROM `winged-precept-443218-v8.ngn_dataset.company_info`
                          WHERE company_name = '{company_name}')
        AND i.ordered_date BETWEEN '{start_date}' AND '{end_date}'
    ),
    item_aggregates AS (
      SELECT di.mall_id, di.product_no, di.product_name, di.product_price, di.category_no,
        SUM(di.quantity) AS total_quantity, SUM(di.canceled_quantity) AS total_canceled_quantity
      FROM distinct_items di
      GROUP BY di.mall_id, di.product_no, di.product_name, di.product_price, di.category_no
    ),
    first_order_aggregates AS (
      SELECT o.mall_id, di.product_no, di.product_name,
        SUM(CASE WHEN o.first_order = TRUE THEN 1 ELSE 0 END) AS first_order_count
      FROM distinct_orders o
      JOIN distinct_items di ON o.mall_id = di.mall_id AND o.order_id = di.order_id
      GROUP BY o.mall_id, di.product_no, di.product_name
    ),
    final_aggregates AS (
      SELECT '{start_date} ~ {end_date}' AS payment_date_range, ci.company_name, ia.product_name,
        ia.product_price, ia.total_quantity, ia.total_canceled_quantity,
        ia.total_quantity - ia.total_canceled_quantity AS sale_quantity,
        CASE WHEN ia.total_quantity - ia.total_canceled_quantity = 0 THEN 0
          ELSE ia.product_price * (ia.total_quantity - ia.total_canceled_quantity) END AS sale,
        foa.first_order_count,
        CONCAT('https://', ci.main_url, '/product/',
               REPLACE(LOWER(REGEXP_REPLACE(ia.product_name, r'[^\w]+', '-')), '--', '-'),
               '/category/', ia.category_no, '/display/1/') AS product_url
      FROM item_aggregates ia
      LEFT JOIN first_order_aggregates foa
        ON ia.mall_id = foa.mall_id AND ia.product_no = foa.product_no
      LEFT JOIN `winged-precept-443218-v8.ngn_dataset.company_info` ci
        ON ia.mall_id = ci.mall_id
    )
    SELECT payment_date_range AS payment_date, company_name, product_name, product_price,
      total_quantity, total_canceled_quantity, sale_quantity, sale,
      first_order_count AS total_first_order_count, product_url
    FROM final_aggregates
    ORDER BY sale_quantity DESC;
    """
    return query
