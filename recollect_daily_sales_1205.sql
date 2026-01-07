-- ✅ 12/5 daily_cafe24_sales 재수집 (refund_code별 집계로 중복 방지)
MERGE `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales` AS target
USING (
  WITH company_mall_ids AS (
      SELECT mall_id, company_name
      FROM `winged-precept-443218-v8.ngn_dataset.company_info`
  ),
  refund_summary AS (
      -- ⚠️ 중요: refund_code별로 먼저 집계하여 중복 방지 (하나의 refund_code는 한 번만 집계)
      SELECT
          refund_with_payment.mall_id,
          refund_with_payment.company_name,
          refund_with_payment.payment_date,
          SUM(refund_with_payment.total_refund_amount) AS total_refund_amount
      FROM (
          -- refund_code별로 먼저 집계 (같은 refund_code는 한 번만 집계)
          SELECT
              r.mall_id,
              c.company_name,
              DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) AS payment_date,
              r.refund_code,
              MAX(r.total_refund_amount) AS total_refund_amount
          FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
          JOIN `winged-precept-443218-v8.ngn_dataset.cafe24_orders` o
              ON r.order_id = o.order_id AND r.mall_id = o.mall_id
          JOIN company_mall_ids c
              ON r.mall_id = c.mall_id
          WHERE DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) = '2025-12-05'
          GROUP BY r.mall_id, c.company_name, payment_date, r.refund_code
      ) refund_with_payment
      GROUP BY refund_with_payment.mall_id, refund_with_payment.company_name, refund_with_payment.payment_date
  ),
  order_summary AS (
      SELECT
          o.mall_id,
          o.order_id,
          DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) AS payment_date,
          MAX(
              CASE 
                  WHEN o.order_price_amount = 0 THEN o.payment_amount + o.naverpay_point
                  ELSE o.order_price_amount
              END
          ) AS item_product_price,
          MAX(o.shipping_fee) AS shipping_fee,
          MAX(o.coupon_discount_price) AS coupon_discount_price,
          MAX(o.payment_amount) AS payment_amount,
          MAX(o.points_spent_amount) AS points_spent_amount,
          MAX(o.naverpay_point) AS naverpay_point,
          MAX(CASE WHEN LOWER(o.payment_method) LIKE '%선불금%' THEN 1 ELSE 0 END) AS is_prepayment,
          MAX(CASE WHEN o.first_order = TRUE THEN 1 ELSE 0 END) AS is_first_order,
          MAX(CASE WHEN o.canceled = TRUE THEN 1 ELSE 0 END) AS is_canceled,
          MAX(CASE WHEN o.naverpay_payment_information = 'N' THEN 1 ELSE 0 END) AS is_naverpay_payment_info
      FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders` AS o
      WHERE DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) = '2025-12-05'
      GROUP BY o.mall_id, o.order_id, payment_date
  ),
  order_agg AS (
      SELECT
          os.payment_date,
          os.mall_id,
          c.company_name,
          COUNT(DISTINCT os.order_id) AS total_orders,
          0 AS item_orders,
          SUM(os.item_product_price) AS item_product_price,
          SUM(os.shipping_fee) AS total_shipping_fee,
          SUM(os.coupon_discount_price) AS total_coupon_discount,
          SUM(os.payment_amount) + SUM(os.points_spent_amount) + SUM(os.naverpay_point) AS total_payment,
          SUM(os.naverpay_point) AS total_naverpay_point,
          SUM(os.is_prepayment) AS total_prepayment,
          SUM(os.is_first_order) AS total_first_order,
          SUM(os.is_canceled) AS total_canceled,
          SUM(os.is_naverpay_payment_info) AS total_naverpay_payment_info
      FROM order_summary AS os
      JOIN `winged-precept-443218-v8.ngn_dataset.company_info` AS c
      ON os.mall_id = c.mall_id  
      GROUP BY os.payment_date, os.mall_id, c.company_name
  )
  SELECT
      oa.payment_date,
      oa.mall_id,
      oa.company_name,
      oa.total_orders,
      oa.item_orders,
      oa.item_product_price,
      oa.total_shipping_fee,
      oa.total_coupon_discount,
      oa.total_payment,
      COALESCE(r.total_refund_amount, 0) AS total_refund_amount,
      (oa.total_payment - COALESCE(r.total_refund_amount, 0)) AS net_sales,
      oa.total_naverpay_point,
      oa.total_prepayment,
      oa.total_first_order,
      oa.total_canceled,
      oa.total_naverpay_payment_info,
      CURRENT_TIMESTAMP() AS updated_at
  FROM order_agg AS oa
  LEFT JOIN refund_summary AS r
  ON oa.mall_id = r.mall_id
  AND oa.payment_date = r.payment_date
) AS source
ON target.payment_date = source.payment_date
   AND target.company_name = source.company_name
WHEN MATCHED THEN
UPDATE SET
    total_orders = source.total_orders,
    item_orders = source.item_orders,
    item_product_price = source.item_product_price,
    total_shipping_fee = source.total_shipping_fee,
    total_coupon_discount = source.total_coupon_discount,
    total_payment = source.total_payment,
    total_refund_amount = source.total_refund_amount,
    net_sales = source.net_sales,
    total_naverpay_point = source.total_naverpay_point,
    total_prepayment = source.total_prepayment,
    total_first_order = source.total_first_order,
    total_canceled = source.total_canceled,
    total_naverpay_payment_info = source.total_naverpay_payment_info,
    updated_at = CURRENT_TIMESTAMP()
WHEN NOT MATCHED THEN
INSERT (
    payment_date, mall_id, company_name, total_orders, item_orders,
    item_product_price, total_shipping_fee, total_coupon_discount,
    total_payment, total_refund_amount, net_sales, total_naverpay_point,
    total_prepayment, total_first_order, total_canceled,
    total_naverpay_payment_info, updated_at
)
VALUES (
    source.payment_date, source.mall_id, source.company_name,
    source.total_orders, source.item_orders, source.item_product_price,
    source.total_shipping_fee, source.total_coupon_discount,
    source.total_payment, source.total_refund_amount, source.net_sales,
    source.total_naverpay_point, source.total_prepayment,
    source.total_first_order, source.total_canceled,
    source.total_naverpay_payment_info, CURRENT_TIMESTAMP()
);

