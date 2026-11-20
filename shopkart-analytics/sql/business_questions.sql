-- ============================================================
-- ShopKart India — Business Questions in SQL (SQLite dialect)
-- Run:  sqlite3 data/shopkart.db < sql/business_questions.sql
-- Revenue definition: Net Revenue = gross revenue of items in
-- Delivered orders that were NOT returned.
-- ============================================================
.headers on
.mode column

-- Reusable view: one row per sold line item with order + product context
DROP VIEW IF EXISTS v_sales;
CREATE VIEW v_sales AS
SELECT i.*, o.customer_id, o.order_datetime, o.order_status, o.payment_method,
       o.coupon_code, o.platform, o.delivery_days,
       p.category, p.sub_category, p.brand,
       CASE WHEN o.order_status = 'Delivered' AND i.is_returned = 0 THEN 1 ELSE 0 END AS is_net_sale
FROM order_items i
JOIN orders   o ON o.order_id  = i.order_id
JOIN products p ON p.product_id = i.product_id;

-- Q1. Headline KPIs by year
SELECT strftime('%Y', order_datetime)                         AS year,
       COUNT(DISTINCT order_id)                               AS orders,
       COUNT(DISTINCT customer_id)                            AS customers,
       ROUND(SUM(gross_revenue * is_net_sale) / 1e7, 2)       AS net_revenue_cr,
       ROUND(SUM((gross_revenue - cogs) * is_net_sale) / 1e7, 2) AS gross_profit_cr,
       ROUND(SUM(gross_revenue * is_net_sale) /
             COUNT(DISTINCT CASE WHEN is_net_sale = 1 THEN order_id END), 0) AS aov_inr
FROM v_sales GROUP BY 1;

-- Q2. Month-over-month net revenue growth (window function)
WITH m AS (
  SELECT strftime('%Y-%m', order_datetime) AS month,
         SUM(gross_revenue * is_net_sale)  AS rev
  FROM v_sales GROUP BY 1)
SELECT month, ROUND(rev/1e5, 1) AS net_rev_lakh,
       ROUND(100.0 * (rev - LAG(rev) OVER (ORDER BY month)) / LAG(rev) OVER (ORDER BY month), 1) AS mom_growth_pct
FROM m ORDER BY month;

-- Q3. Category profitability and return rate
SELECT category,
       ROUND(SUM(gross_revenue * is_net_sale)/1e5, 1)                    AS net_rev_lakh,
       ROUND(100.0 * SUM((gross_revenue - cogs) * is_net_sale)
                   / SUM(gross_revenue * is_net_sale), 1)               AS gross_margin_pct,
       ROUND(100.0 * SUM(is_returned) / COUNT(*), 1)                     AS return_rate_pct,
       ROUND(AVG(discount_pct) * 100, 1)                                 AS avg_discount_pct
FROM v_sales GROUP BY 1 ORDER BY net_rev_lakh DESC;

-- Q4. Top 10 products by net revenue, ranked within category
SELECT * FROM (
  SELECT category, product_id, ROUND(SUM(gross_revenue * is_net_sale)) AS net_rev,
         RANK() OVER (PARTITION BY category ORDER BY SUM(gross_revenue * is_net_sale) DESC) AS rnk
  FROM v_sales GROUP BY category, product_id)
WHERE rnk <= 2 ORDER BY net_rev DESC LIMIT 10;

-- Q5. Payment method risk: cancellation + RTO (return-to-origin) rates
SELECT payment_method,
       COUNT(*) AS orders,
       ROUND(100.0 * SUM(order_status = 'Cancelled') / COUNT(*), 1) AS cancel_pct,
       ROUND(100.0 * SUM(order_status = 'RTO') / COUNT(*), 1)       AS rto_pct
FROM orders GROUP BY 1 ORDER BY rto_pct DESC;

-- Q6. Region x city tier performance
SELECT c.region, c.city_tier,
       COUNT(DISTINCT c.customer_id) AS customers,
       ROUND(SUM(s.gross_revenue * s.is_net_sale) / COUNT(DISTINCT c.customer_id)) AS rev_per_customer,
       ROUND(AVG(s.delivery_days), 1) AS avg_delivery_days
FROM customers c JOIN v_sales s ON s.customer_id = c.customer_id
GROUP BY 1, 2 ORDER BY 1, 2;

-- Q7. Repeat purchase rate and customer value by acquisition channel
WITH cust AS (
  SELECT c.customer_id, c.acquisition_channel,
         COUNT(DISTINCT o.order_id) AS n_orders,
         SUM(CASE WHEN o.order_status='Delivered' THEN 1 ELSE 0 END) AS delivered
  FROM customers c LEFT JOIN orders o ON o.customer_id = c.customer_id
  GROUP BY 1, 2),
val AS (
  SELECT customer_id, SUM(gross_revenue * is_net_sale) AS ltv FROM v_sales GROUP BY 1)
SELECT acquisition_channel,
       COUNT(*) AS customers,
       ROUND(100.0 * SUM(n_orders >= 2) / COUNT(*), 1) AS repeat_rate_pct,
       ROUND(AVG(n_orders), 2) AS avg_orders,
       ROUND(AVG(COALESCE(ltv, 0))) AS avg_ltv_inr
FROM cust LEFT JOIN val USING (customer_id)
GROUP BY 1 ORDER BY avg_ltv_inr DESC;

-- Q8. Does slow delivery hurt repeat purchase? (first-order delivery time)
WITH firsts AS (
  SELECT customer_id, order_id, delivery_days,
         ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_datetime) AS rn,
         COUNT(*)     OVER (PARTITION BY customer_id) AS total_orders
  FROM orders)
SELECT CASE WHEN delivery_days <= 2 THEN '1-2 days'
            WHEN delivery_days <= 4 THEN '3-4 days'
            WHEN delivery_days <= 6 THEN '5-6 days' ELSE '7+ days' END AS first_delivery,
       COUNT(*) AS customers,
       ROUND(100.0 * SUM(total_orders >= 2) / COUNT(*), 1) AS repeat_rate_pct
FROM firsts WHERE rn = 1 AND delivery_days IS NOT NULL
GROUP BY 1 ORDER BY 1;

-- Q9. Coupon effectiveness: AOV and margin by coupon
SELECT coupon_code,
       COUNT(DISTINCT order_id) AS orders,
       ROUND(SUM(gross_revenue * is_net_sale) / COUNT(DISTINCT CASE WHEN is_net_sale=1 THEN order_id END)) AS aov,
       ROUND(100.0 * SUM((gross_revenue - cogs) * is_net_sale) / SUM(gross_revenue * is_net_sale), 1) AS margin_pct
FROM v_sales GROUP BY 1 ORDER BY orders DESC;

-- Q10. Festive sale (Oct 1 – Nov 15) vs rest of year
SELECT CASE WHEN strftime('%m-%d', order_datetime) BETWEEN '10-01' AND '11-15'
            THEN 'Festive sale' ELSE 'Rest of year' END AS period,
       ROUND(SUM(gross_revenue * is_net_sale) / COUNT(DISTINCT date(order_datetime)) / 1e5, 2) AS net_rev_per_day_lakh,
       ROUND(100.0 * SUM((gross_revenue - cogs) * is_net_sale) / SUM(gross_revenue * is_net_sale), 1) AS margin_pct,
       ROUND(AVG(discount_pct) * 100, 1) AS avg_discount_pct
FROM v_sales GROUP BY 1;
