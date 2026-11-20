"""
Step 1 — Data cleaning & validation.
Reads data/raw/*.csv, fixes quality issues, writes data/clean/*.csv and
loads everything into a SQLite warehouse (data/shopkart.db).
A data-quality log is written to report/data_quality_log.md.
"""
import pandas as pd, numpy as np, sqlite3

RAW, CLEAN = "data/raw/", "data/clean/"
log = []
def note(table, issue, n): log.append(f"| {table} | {issue} | {n:,} |")

# ---------- customers ----------
c = pd.read_csv(RAW + "customers.csv")
n = len(c); c = c.drop_duplicates(); note("customers", "Exact duplicate rows removed", n - len(c))
n = len(c); c = c.drop_duplicates("customer_id"); note("customers", "Duplicate customer_id removed", n - len(c))

city_map = {"Bangalore": "Bengaluru", "Bombay": "Mumbai", "New Delhi": "Delhi", "Madras": "Chennai"}
before = c.city.copy()
c["city"] = c.city.str.strip().str.title().replace(city_map)
note("customers", "City names standardised (case/whitespace/old names)", (before != c.city).sum())

bad_age = ~c.age.between(18, 80)
note("customers", "Invalid ages (<18 or >80) set to NULL", bad_age.sum())
c.loc[bad_age, "age"] = np.nan

g = c.gender.fillna("").str.strip().str.lower().map({"m": "M", "male": "M", "f": "F", "female": "F", "other": "Other"})
note("customers", "Gender values standardised / missing -> 'Unknown'", (g.isna() | (g != c.gender)).sum())
c["gender"] = g.fillna("Unknown")

d1 = pd.to_datetime(c.signup_date, format="%Y-%m-%d", errors="coerce")
d2 = pd.to_datetime(c.signup_date, format="%d/%m/%Y", errors="coerce")
note("customers", "Signup dates in DD/MM/YYYY converted to ISO", d1.isna().sum())
c["signup_date"] = d1.fillna(d2).dt.date

# ---------- products ----------
p = pd.read_csv(RAW + "products.csv")
miss = p.unit_cost.isna()
cat_ratio = (p.unit_cost / p.mrp).groupby(p.category).median()
p.loc[miss, "unit_cost"] = (p.loc[miss, "mrp"] * p.loc[miss, "category"].map(cat_ratio)).round(2)
note("products", "Missing unit_cost imputed with category median cost ratio", miss.sum())

# ---------- orders ----------
o = pd.read_csv(RAW + "orders.csv")
n = len(o); o = o.drop_duplicates("order_id"); note("orders", "Duplicate order rows removed", n - len(o))
pm = {"upi": "UPI", "cod": "COD", "credit card": "Credit Card", "debit card": "Debit Card",
      "wallet": "Wallet", "net banking": "Net Banking", "emi": "EMI"}
before = o.payment_method.copy()
o["payment_method"] = o.payment_method.str.strip().str.lower().map(pm)
note("orders", "Payment method labels standardised", (before != o.payment_method).sum())
note("orders", "Missing coupon_code filled with 'NONE'", o.coupon_code.isna().sum())
o["coupon_code"] = o.coupon_code.fillna("NONE")
note("orders", "Missing delivery_days (kept NULL; not imputed)", o.delivery_days.isna().sum())
o["order_datetime"] = pd.to_datetime(o.order_datetime)
o.loc[o.order_status.isin(["Cancelled", "RTO"]), "delivery_days"] = np.nan  # never delivered
orphan = ~o.customer_id.isin(c.customer_id)
note("orders", "Orphan orders (unknown customer) removed", orphan.sum()); o = o[~orphan]

# ---------- order items ----------
it = pd.read_csv(RAW + "order_items.csv")
bad_q = it.quantity <= 0
note("order_items", "Rows with quantity <= 0 removed", bad_q.sum()); it = it[~bad_q]
pct = it.discount_pct > 1
note("order_items", "discount_pct stored as % (e.g. 15) converted to fraction (0.15)", pct.sum())
it.loc[pct, "discount_pct"] = it.loc[pct, "discount_pct"] / 100
it["is_returned"] = it.is_returned.eq("Y").astype(int)
it = it[it.order_id.isin(o.order_id)]

# derived financial columns
it = it.merge(p[["product_id", "unit_cost"]], on="product_id", how="left")
it["selling_price"] = (it.mrp * (1 - it.discount_pct)).round(2)
it["gross_revenue"] = (it.selling_price * it.quantity).round(2)
it["cogs"] = (it.unit_cost * it.quantity).round(2)
it = it.drop(columns="unit_cost")

# ---------- save ----------
c.to_csv(CLEAN + "customers.csv", index=False); p.to_csv(CLEAN + "products.csv", index=False)
o.to_csv(CLEAN + "orders.csv", index=False); it.to_csv(CLEAN + "order_items.csv", index=False)

con = sqlite3.connect("data/shopkart.db")
for name, df in [("customers", c), ("products", p), ("orders", o), ("order_items", it)]:
    df.to_sql(name, con, if_exists="replace", index=False)
con.executescript("""
CREATE INDEX IF NOT EXISTS ix_o_c ON orders(customer_id);
CREATE INDEX IF NOT EXISTS ix_i_o ON order_items(order_id);
CREATE INDEX IF NOT EXISTS ix_i_p ON order_items(product_id);
""")
con.close()

with open("report/data_quality_log.md", "w") as f:
    f.write("# Data Quality Log\n\n| Table | Issue | Rows affected |\n|---|---|---|\n" + "\n".join(log) + "\n")
    f.write(f"\n**Final row counts:** customers {len(c):,} · products {len(p):,} · orders {len(o):,} · order_items {len(it):,}\n")
print("\n".join(log)); print(len(c), len(p), len(o), len(it))
