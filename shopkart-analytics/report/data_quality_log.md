# Data Quality Log

| Table | Issue | Rows affected |
|---|---|---|
| customers | Exact duplicate rows removed | 53 |
| customers | Duplicate customer_id removed | 2 |
| customers | City names standardised (case/whitespace/old names) | 100 |
| customers | Invalid ages (<18 or >80) set to NULL | 40 |
| customers | Gender values standardised / missing -> 'Unknown' | 40 |
| customers | Signup dates in DD/MM/YYYY converted to ISO | 300 |
| products | Missing unit_cost imputed with category median cost ratio | 8 |
| orders | Duplicate order rows removed | 120 |
| orders | Payment method labels standardised | 260 |
| orders | Missing coupon_code filled with 'NONE' | 70 |
| orders | Missing delivery_days (kept NULL; not imputed) | 70 |
| orders | Orphan orders (unknown customer) removed | 0 |
| order_items | Rows with quantity <= 0 removed | 80 |
| order_items | discount_pct stored as % (e.g. 15) converted to fraction (0.15) | 70 |

**Final row counts:** customers 12,000 · products 587 · orders 52,039 · order_items 81,127
