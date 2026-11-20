"""
Step 3 — Export compact columnar data for the interactive dashboard (dashboard/data.js).
Order-level and line-level arrays let the browser recompute every KPI under any filter.
"""
import sqlite3, json, pandas as pd, numpy as np

con = sqlite3.connect("data/shopkart.db")
o = pd.read_sql("""SELECT o.*, c.region, c.city, c.city_tier, c.acquisition_channel
                   FROM orders o JOIN customers c USING(customer_id)""", con, parse_dates=["order_datetime"])
it = pd.read_sql("""SELECT i.order_id, i.product_id, i.quantity, i.discount_pct, i.gross_revenue, i.cogs,
                    i.is_returned, p.category, p.product_name FROM order_items i JOIN products p USING(product_id)""", con)
o = o.sort_values("order_datetime").reset_index(drop=True)

def codes(series):
    cats = sorted(series.dropna().unique().tolist())
    return cats, series.map({v: i for i, v in enumerate(cats)}).astype(int).tolist()

D = {}
months = pd.period_range("2023-01", "2024-12", freq="M")
D["months"] = [str(m) for m in months]
o["m"] = o.order_datetime.dt.to_period("M").map({m: i for i, m in enumerate(months)})
D["regions"], o_reg = codes(o.region)
D["payments"], o_pay = codes(o.payment_method)
D["channels"], o_ch = codes(o.acquisition_channel)
D["statuses"], o_st = codes(o.order_status)
D["platforms"], o_pl = codes(o.platform)
D["cities"], o_city = codes(o.city)
cust_ids = {c: i for i, c in enumerate(o.customer_id.unique())}
first_order = o.groupby("customer_id").order_datetime.transform("min")
festive = o.order_datetime.dt.strftime("%m-%d").between("10-01", "11-15")

D["o"] = {
    "m": o.m.tolist(), "reg": o_reg, "pay": o_pay, "ch": o_ch, "st": o_st, "pl": o_pl, "city": o_city,
    "tier": o.city_tier.tolist(), "cust": o.customer_id.map(cust_ids).tolist(),
    "first": (o.order_datetime == first_order).astype(int).tolist(),
    "dd": o.delivery_days.fillna(-1).astype(int).tolist(),
    "fest": festive.astype(int).tolist(),
}
oidx = {k: i for i, k in enumerate(o.order_id)}
it = it[it.order_id.isin(oidx)]
D["categories"], l_cat = codes(it.category)
prod_ids = sorted(it.product_id.unique())
pmap = {p: i for i, p in enumerate(prod_ids)}
pinfo = it.drop_duplicates("product_id").set_index("product_id")
D["products"] = [[pinfo.loc[p, "product_name"], D["categories"].index(pinfo.loc[p, "category"])] for p in prod_ids]
D["l"] = {
    "o": it.order_id.map(oidx).tolist(), "cat": l_cat, "p": it.product_id.map(pmap).tolist(),
    "q": it.quantity.tolist(), "rev": it.gross_revenue.round(0).astype(int).tolist(),
    "cogs": it.cogs.round(0).astype(int).tolist(), "ret": it.is_returned.tolist(),
    "disc": (it.discount_pct * 1000).round().astype(int).tolist(),
}

# Static (whole-dataset) analyses
rfm = pd.read_csv("report/rfm_segments.csv")
D["rfm"] = rfm[["segment", "customers", "revenue", "avg_recency", "avg_orders", "avg_value", "cust_%", "rev_%"]].round(1).values.tolist()
oc = o.copy(); oc["om"] = oc.order_datetime.dt.to_period("M")
oc["cohort"] = oc.groupby("customer_id").om.transform("min")
oc["age"] = (oc.om - oc.cohort).apply(lambda d: d.n)
coh = oc.groupby(["cohort", "age"]).customer_id.nunique().unstack()
ret = (coh.div(coh[0], axis=0) * 100).loc["2023-01":"2024-06", list(range(13))]
D["cohort"] = {"rows": [str(i) for i in ret.index], "size": coh.loc["2023-01":"2024-06", 0].astype(int).tolist(),
               "vals": [[None if np.isnan(v) else round(v, 1) for v in r] for r in ret.values]}

js = "window.SHOPKART = " + json.dumps(D, separators=(",", ":")) + ";"
open("dashboard/data.js", "w").write(js)
print(f"data.js {len(js)/1e6:.2f} MB, orders {len(o)}, lines {len(it)}")
