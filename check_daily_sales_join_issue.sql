-- ✅ 1단계: daily_cafe24_sales에 2026-01-02 데이터가 있는지 확인
SELECT 
    payment_date,
    company_name,
    total_orders,
    total_payment,
    total_refund_amount,
    net_sales
FROM `winged-precept-443218-v8.ngn_dataset.daily_cafe24_sales`
WHERE payment_date = '2026-01-02'
  AND LOWER(company_name) = 'piscess';

-- ✅ 2단계: order_agg와 refund_summary를 JOIN해서 최종 결과 확인
-- (daily_cafe24_sales_handler.py의 최종 SELECT 로직 테스트)
WITH company_mall_ids AS (
    SELECT mall_id, company_name
    FROM `winged-precept-443218-v8.ngn_dataset.company_info`
),
refund_summary AS (
    SELECT
        refund_with_payment.mall_id,
        refund_with_payment.company_name,
        refund_with_payment.payment_date,
        SUM(refund_with_payment.total_refund_amount) AS total_refund_amount
    FROM (
        SELECT
            r.mall_id,
            c.company_name,
            DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) AS payment_date,
            r.order_id,
            SUM(r.total_refund_amount) AS total_refund_amount
        FROM `winged-precept-443218-v8.ngn_dataset.cafe24_refunds_table` r
        JOIN `winged-precept-443218-v8.ngn_dataset.cafe24_orders` o
            ON r.order_id = o.order_id AND r.mall_id = o.mall_id
        JOIN company_mall_ids c
            ON r.mall_id = c.mall_id
        WHERE DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) = '2026-01-02'
          AND r.mall_id = 'piscess1'
        GROUP BY r.mall_id, c.company_name, payment_date, r.order_id
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
        MAX(o.naverpay_point) AS naverpay_point
    FROM `winged-precept-443218-v8.ngn_dataset.cafe24_orders` AS o
    WHERE DATE(DATETIME(TIMESTAMP(o.payment_date), 'Asia/Seoul')) = '2026-01-02'
      AND o.mall_id = 'piscess1'
    GROUP BY o.mall_id, o.order_id, payment_date
),
order_agg AS (
    SELECT
        os.payment_date,
        os.mall_id,
        c.company_name,
        COUNT(DISTINCT os.order_id) AS total_orders,
        SUM(os.item_product_price) AS item_product_price,
        SUM(os.shipping_fee) AS total_shipping_fee,
        SUM(os.coupon_discount_price) AS total_coupon_discount,
        SUM(os.payment_amount) + SUM(os.points_spent_amount) + SUM(os.naverpay_point) AS total_payment
    FROM order_summary AS os
    JOIN `winged-precept-443218-v8.ngn_dataset.company_info` AS c
    ON os.mall_id = c.mall_id  
    GROUP BY os.payment_date, os.mall_id, c.company_name
)
SELECT
    oa.payment_date,
    oa.company_name,
    oa.total_orders,
    oa.total_payment,
    COALESCE(r.total_refund_amount, 0) AS total_refund_amount,
    (oa.total_payment - COALESCE(r.total_refund_amount, 0)) AS net_sales
FROM order_agg AS oa
LEFT JOIN refund_summary AS r
ON oa.mall_id = r.mall_id
AND oa.payment_date = r.payment_date;

