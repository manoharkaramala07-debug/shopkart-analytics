# ShopKart India: E-commerce Sales & Customer Analytics

An end-to-end data analytics project for a fictional Indian online retailer. It covers **messy raw data → cleaning → SQL warehouse → business analysis → insights and recommendations**.

**Tools:** Python (pandas, NumPy, Matplotlib) · SQL (SQLite) · Jupyter
**Skills shown:** data cleaning, data modelling, SQL (CTEs, window functions), cohort analysis, RFM segmentation, KPI design, data storytelling

## Business problem
ShopKart grew revenue 52% in 2024, but leadership wants answers to four questions:
1. Is the growth profitable? What do festive sales actually earn?
2. Which categories, customers, and channels create the most value?
3. Why do customers stop buying?
4. Where is money leaking in operations (payments, delivery, returns)?

## Headline results
- ₹6.3 Cr net revenue over 2 years, **+52.5% YoY**, at a 25% gross margin
- Festive sales: **+33% revenue/day, but margin drops from 27.9% to 10.5%**. Electronics and Grocery lose money during the sale.
- **25% of customers ("Champions") = 50% of revenue**. 897 high-value customers are at risk (₹93 L in historic revenue).
- COD **RTO rate is 6.9% vs ~2% for prepaid**
- First delivery in 7+ days → **40% repeat rate vs 63%** for delivery in 1–2 days
- Referral customers are worth **55% more** than influencer-acquired customers

Full report: [`report/business_report.md`](report/business_report.md)

## Project structure
```
├── generate_data.py              # builds the realistic, intentionally messy raw data
├── 01_clean_data.py              # cleaning + validation + loads SQLite warehouse
├── 02_analysis.py                # full Python analysis (same code as notebook)
├── notebooks/shopkart_analysis.ipynb
├── sql/business_questions.sql    # 10 business questions in SQL
├── sql/query_results.txt         # output of the SQL file
├── data/raw/                     # messy source CSVs (customers, products, orders, order_items)
├── data/clean/                   # cleaned CSVs + RFM scores
├── data/shopkart.db              # SQLite database (star schema)
├── charts/                       # 6 report-ready charts
└── report/                       # business report, data-quality log, KPI/RFM tables
```

## Data model (star schema)
| Table | Grain | Key columns |
|---|---|---|
| `orders` (fact) | 1 row per order | order_id, customer_id, order_datetime, payment_method, order_status, coupon_code, delivery_days, platform |
| `order_items` (fact) | 1 row per product in an order | item_id, order_id, product_id, quantity, mrp, discount_pct, selling_price, gross_revenue, cogs, is_returned |
| `customers` (dim) | 1 row per customer | customer_id, signup_date, city, state, region, city_tier, gender, age, acquisition_channel |
| `products` (dim) | 1 row per SKU | product_id, category, sub_category, brand, mrp, unit_cost |

## Data quality issues found and fixed
Duplicates (175 records), inconsistent city names (`BANGALORE`, `Bombay `), mixed date formats (`2024-03-01` vs `01/03/2024`), invalid ages (0, 150, 999), messy payment labels (`upi `, `cod`), discounts stored as `15` instead of `0.15`, zero or negative quantities, and missing product costs. See [`report/data_quality_log.md`](report/data_quality_log.md).

## How to run
```bash
pip install pandas numpy matplotlib
python generate_data.py      # optional: regenerates data/raw (seeded, reproducible)
python 01_clean_data.py
sqlite3 data/shopkart.db < sql/business_questions.sql
python 02_analysis.py        # or open notebooks/shopkart_analysis.ipynb
```

## Extend it (next steps)
- Build a Power BI / Tableau dashboard on `data/clean/*.csv`
- Churn prediction model (logistic regression on RFM + delivery features)
- Market-basket analysis (which products are bought together)

## Resume bullets
- Built an end-to-end analytics pipeline on 52K orders / 81K line items: cleaned 8 categories of data-quality issues and modelled a SQLite star schema
- Wrote 10 SQL analyses using CTEs and window functions (LAG, RANK, ROW_NUMBER) covering growth, profitability, payment risk, and retention
- Ran cohort retention and RFM segmentation and identified 897 at-risk high-value customers (₹93 L historic revenue) for a win-back campaign
- Found that festive discounts cut gross margin from 27.9% to 10.5% and that COD orders fail 3.5x more often; recommended a pricing cap and prepaid incentives

## Live interactive dashboard

`dashboard/` is a fully static, interactive dashboard (HTML + Chart.js). It has three tabs (Overview, Customers, Operations), filters for Year, Region, Category, Payment and Channel, a click-to-filter category table, and a dark mode.

**Run locally**
```bash
python 03_build_dashboard_data.py      # regenerates dashboard/data.js from data/clean
cd dashboard && python -m http.server 8000
# open http://localhost:8000
```

**Host for free:** push the repo to GitHub, then go to Settings → Pages and serve the `/dashboard` folder (or copy it into `docs/`). Put the link at the top of this README and on your resume.

**Resume bullet:** Built an interactive sales dashboard (HTML/JS, Chart.js) with 15+ KPIs, cross-filters and cohort/RFM views over 52K orders. It showed that festive sales cut margin from 27.9% to 10.5% and that COD orders have 3x higher RTO.
