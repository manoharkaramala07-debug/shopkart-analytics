# %% [markdown]
# # ShopKart India — Sales & Customer Analytics (2023–2024)
# End-to-end analysis: KPIs, trends, category profitability, cohort retention,
# RFM segmentation, payment risk and delivery impact. Charts saved to `charts/`.

# %%
import sqlite3, pandas as pd, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mt

plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.titleweight": "bold", "axes.titlesize": 12, "font.size": 10})
BLUE, ORANGE, GREY, RED, GREEN = "#1f5f8b", "#e07b39", "#9aa5b1", "#c0392b", "#2e8b57"
con = sqlite3.connect("data/shopkart.db")

s = pd.read_sql("""
SELECT i.*, o.customer_id, o.order_datetime, o.order_status, o.payment_method, o.coupon_code,
       o.delivery_days, o.platform, p.category, p.sub_category
FROM order_items i JOIN orders o USING(order_id) JOIN products p USING(product_id)""", con,
                parse_dates=["order_datetime"])
orders = pd.read_sql("SELECT * FROM orders", con, parse_dates=["order_datetime"])
cust = pd.read_sql("SELECT * FROM customers", con, parse_dates=["signup_date"])
s["net"] = ((s.order_status == "Delivered") & (s.is_returned == 0)).astype(int)
s["net_rev"] = s.gross_revenue * s.net
s["net_profit"] = (s.gross_revenue - s.cogs) * s.net
s["month"] = s.order_datetime.dt.to_period("M")

# %% [markdown]
# ## 1. Headline KPIs

# %%
def kpis(df):
    net_orders = df.loc[df.net == 1, "order_id"].nunique()
    return pd.Series({
        "Net revenue (₹ Cr)": df.net_rev.sum() / 1e7,
        "Gross profit (₹ Cr)": df.net_profit.sum() / 1e7,
        "Gross margin %": 100 * df.net_profit.sum() / df.net_rev.sum(),
        "Orders": df.order_id.nunique(),
        "Active customers": df.customer_id.nunique(),
        "AOV (₹)": df.net_rev.sum() / net_orders,
        "Item return rate %": 100 * df.is_returned.mean(),
    })
k = s.groupby(s.order_datetime.dt.year).apply(kpis).T
k["YoY %"] = 100 * (k[2024] / k[2023] - 1)
print(k.round(2))
k.round(2).to_csv("report/kpi_summary.csv")

# %% [markdown]
# ## 2. Monthly revenue trend & seasonality

# %%
m = s.groupby("month").agg(rev=("net_rev", "sum"), profit=("net_profit", "sum"))
m["margin"] = 100 * m.profit / m.rev
fig, ax = plt.subplots(figsize=(11, 4.2))
x = m.index.to_timestamp()
ax.bar(x, m.rev / 1e5, width=20, color=BLUE, label="Net revenue")
ax.set_ylabel("Net revenue (₹ lakh)"); ax.set_ylim(0, m.rev.max() / 1e5 * 1.22)
ax2 = ax.twinx(); ax2.plot(x, m.margin, color=ORANGE, marker="o", lw=2, label="Gross margin %")
ax2.set_ylabel("Gross margin %"); ax2.spines["top"].set_visible(False)
ax2.set_ylim(0, 40)
for yr in (2023, 2024):
    ax.axvspan(pd.Timestamp(f"{yr}-10-01"), pd.Timestamp(f"{yr}-11-15"), color=ORANGE, alpha=.08)
    ax.text(pd.Timestamp(f"{yr}-10-05"), ax.get_ylim()[1] * .93, "Festive\nsale", fontsize=8, color=ORANGE)
ax.set_title("Monthly net revenue vs gross margin — festive sales drive volume but crush margin")
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, loc="upper left", frameon=False, ncol=2)
fig.tight_layout(); fig.savefig("charts/01_monthly_revenue_margin.png"); plt.close()

# %% [markdown]
# ## 3. Category profitability

# %%
c = s.groupby("category").agg(rev=("net_rev", "sum"), profit=("net_profit", "sum"),
                              ret=("is_returned", "mean")).sort_values("rev")
c["margin"] = 100 * c.profit / c.rev
fig, axs = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
axs[0].barh(c.index, c.rev / 1e5, color=BLUE); axs[0].set_xlabel("Net revenue (₹ lakh)")
axs[0].set_title("Revenue by category")
cols = [RED if v < 15 else GREEN for v in c.margin]
axs[1].barh(c.index, c.margin, color=cols); axs[1].set_xlabel("Gross margin %")
axs[1].set_title("Gross margin by category")
for i, (mg, r) in enumerate(zip(c.margin, c.ret)):
    axs[1].text(mg + .5, i, f"{mg:.0f}%  (returns {r*100:.0f}%)", va="center", fontsize=8)
axs[1].set_xlim(0, 55)
fig.tight_layout(); fig.savefig("charts/02_category_profitability.png"); plt.close()
print(c.round(2))

# %% [markdown]
# ## 4. Cohort retention (monthly signup cohorts)

# %%
o = orders.merge(cust[["customer_id"]], on="customer_id")
o["order_m"] = o.order_datetime.dt.to_period("M")
o["cohort"] = o.groupby("customer_id").order_m.transform("min")
o["age_m"] = (o.order_m - o.cohort).apply(lambda d: d.n)
coh = o.groupby(["cohort", "age_m"]).customer_id.nunique().unstack()
ret = coh.div(coh[0], axis=0) * 100
ret = ret.loc["2023-01":"2024-06", range(0, 13)]
fig, ax = plt.subplots(figsize=(11, 6))
im = ax.imshow(ret.values, cmap="Blues", vmin=0, vmax=40, aspect="auto")
ax.set_xticks(range(13)); ax.set_xticklabels(range(13))
ax.set_yticks(range(len(ret))); ax.set_yticklabels([str(p) for p in ret.index])
for i in range(ret.shape[0]):
    for j in range(ret.shape[1]):
        v = ret.values[i, j]
        if not np.isnan(v) and j > 0:
            ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=7,
                    color="white" if v > 25 else "black")
ax.set_xlabel("Months since first order"); ax.set_ylabel("First-order cohort")
ax.set_title("Monthly cohort retention (% of cohort ordering again)")
fig.colorbar(im, ax=ax, label="% retained", shrink=.8)
fig.tight_layout(); fig.savefig("charts/03_cohort_retention.png"); plt.close()
avg_ret = ret.mean().round(1)
print("Avg retention by month:", avg_ret.to_dict())

# %% [markdown]
# ## 5. RFM customer segmentation

# %%
snap = s.order_datetime.max() + pd.Timedelta(days=1)
net = s[s.net == 1]
rfm = net.groupby("customer_id").agg(
    recency=("order_datetime", lambda d: (snap - d.max()).days),
    frequency=("order_id", "nunique"), monetary=("net_rev", "sum"))
rfm["R"] = pd.qcut(rfm.recency, 5, labels=[5, 4, 3, 2, 1]).astype(int)
rfm["F"] = pd.qcut(rfm.frequency.rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
rfm["M"] = pd.qcut(rfm.monetary, 5, labels=[1, 2, 3, 4, 5]).astype(int)

def seg(r):
    if r.R >= 4 and r.F >= 4: return "Champions"
    if r.R >= 3 and r.F >= 3: return "Loyal"
    if r.R >= 4 and r.F <= 2: return "New / Promising"
    if r.R <= 2 and r.F >= 4: return "At Risk (high value)"
    if r.R <= 2 and r.F <= 2: return "Hibernating / Lost"
    return "Needs Attention"
rfm["segment"] = rfm.apply(seg, axis=1)
sg = rfm.groupby("segment").agg(customers=("R", "size"), revenue=("monetary", "sum"),
                                avg_recency=("recency", "mean"), avg_orders=("frequency", "mean"),
                                avg_value=("monetary", "mean"))
sg["cust_%"] = 100 * sg.customers / sg.customers.sum()
sg["rev_%"] = 100 * sg.revenue / sg.revenue.sum()
sg = sg.sort_values("rev_%", ascending=False)
print(sg.round(1))
sg.round(1).to_csv("report/rfm_segments.csv")
rfm.to_csv("data/clean/rfm_scores.csv")

fig, ax = plt.subplots(figsize=(10, 4.2))
y = np.arange(len(sg))
ax.barh(y - .2, sg["cust_%"], .4, color=GREY, label="% of customers")
ax.barh(y + .2, sg["rev_%"], .4, color=BLUE, label="% of revenue")
ax.set_yticks(y); ax.set_yticklabels(sg.index); ax.invert_yaxis()
ax.xaxis.set_major_formatter(mt.PercentFormatter())
ax.set_title("RFM segments — share of customers vs share of revenue"); ax.legend(frameon=False)
fig.tight_layout(); fig.savefig("charts/04_rfm_segments.png"); plt.close()

# %% [markdown]
# ## 6. Operations: payment risk and delivery speed

# %%
pay = orders.groupby("payment_method").agg(orders=("order_id", "size"),
        rto=("order_status", lambda x: 100 * (x == "RTO").mean()),
        cancel=("order_status", lambda x: 100 * (x == "Cancelled").mean())).sort_values("rto")
first = orders.sort_values("order_datetime").groupby("customer_id").agg(
    first_dd=("delivery_days", lambda x: x.iloc[0]), n=("order_id", "size")).dropna()
first["bucket"] = pd.cut(first.first_dd, [0, 2, 4, 6, 99], labels=["1–2 days", "3–4 days", "5–6 days", "7+ days"])
dd = first.groupby("bucket", observed=True).agg(customers=("n", "size"), repeat=("n", lambda x: 100 * (x >= 2).mean()))

fig, axs = plt.subplots(1, 2, figsize=(11, 4.2))
axs[0].barh(pay.index, pay.rto, color=[RED if i == "COD" else GREY for i in pay.index])
axs[0].set_title("Return-to-origin (RTO) rate by payment method"); axs[0].set_xlabel("RTO % of orders")
for i, v in enumerate(pay.rto): axs[0].text(v + .1, i, f"{v:.1f}%", va="center", fontsize=8)
axs[1].bar(dd.index.astype(str), dd.repeat, color=[GREEN, GREEN, ORANGE, RED])
axs[1].set_title("Repeat-purchase rate by first-order delivery time"); axs[1].set_ylabel("% who ordered again")
for i, v in enumerate(dd.repeat): axs[1].text(i, v + 1, f"{v:.0f}%", ha="center", fontsize=9)
axs[1].set_ylim(0, 80)
fig.tight_layout(); fig.savefig("charts/05_payment_delivery.png"); plt.close()
print(pay.round(1)); print(dd.round(1))

# %% [markdown]
# ## 7. Acquisition channel quality (customer lifetime value)

# %%
ltv = net.groupby("customer_id").net_rev.sum()
ch = cust.assign(ltv=cust.customer_id.map(ltv).fillna(0)).groupby("acquisition_channel").agg(
    customers=("customer_id", "size"), avg_ltv=("ltv", "mean")).sort_values("avg_ltv")
fig, ax = plt.subplots(figsize=(9, 3.8))
ax.barh(ch.index, ch.avg_ltv, color=BLUE)
for i, v in enumerate(ch.avg_ltv): ax.text(v + 50, i, f"₹{v:,.0f}", va="center", fontsize=9)
ax.set_xlabel("Average 2-year net revenue per customer (₹)")
ax.set_title("Customer value by acquisition channel"); ax.set_xlim(0, ch.avg_ltv.max() * 1.18)
fig.tight_layout(); fig.savefig("charts/06_channel_ltv.png"); plt.close()
print(ch.round(0))

# %% [markdown]
# ## 8. Festive sale economics

# %%
s["festive"] = s.order_datetime.dt.strftime("%m-%d").between("10-01", "11-15")
fe = s.groupby(["festive", "category"]).apply(lambda d: 100 * d.net_profit.sum() / d.net_rev.sum()).unstack(0)
fe.columns = ["Rest of year", "Festive sale"]
print(fe.round(1))
fe.round(1).to_csv("report/festive_margin_by_category.csv")
