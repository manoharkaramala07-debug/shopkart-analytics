"""
Generates a realistic, intentionally messy dataset for "ShopKart India" —
a mid-size online retailer — covering Jan 2023 to Dec 2024.
Run once: python generate_data.py
"""
import numpy as np, pandas as pd
from datetime import datetime, timedelta

rng = np.random.default_rng(42)
OUT = "data/raw/"

# ---------------- Customers ----------------
cities = {  # city: (state, region, weight, tier)
    "Mumbai": ("Maharashtra", "West", 14, 1), "Delhi": ("Delhi", "North", 14, 1),
    "Bengaluru": ("Karnataka", "South", 13, 1), "Hyderabad": ("Telangana", "South", 9, 1),
    "Chennai": ("Tamil Nadu", "South", 8, 1), "Kolkata": ("West Bengal", "East", 7, 1),
    "Pune": ("Maharashtra", "West", 7, 1), "Ahmedabad": ("Gujarat", "West", 6, 1),
    "Jaipur": ("Rajasthan", "North", 4, 2), "Lucknow": ("Uttar Pradesh", "North", 4, 2),
    "Chandigarh": ("Chandigarh", "North", 3, 2), "Jalandhar": ("Punjab", "North", 2, 2),
    "Indore": ("Madhya Pradesh", "Central", 3, 2), "Bhopal": ("Madhya Pradesh", "Central", 2, 2),
    "Patna": ("Bihar", "East", 2, 2), "Kochi": ("Kerala", "South", 2, 2),
    "Coimbatore": ("Tamil Nadu", "South", 2, 2), "Guwahati": ("Assam", "East", 1, 3),
    "Nagpur": ("Maharashtra", "Central", 2, 2), "Surat": ("Gujarat", "West", 3, 2),
}
city_names = list(cities)
w = np.array([cities[c][2] for c in city_names], float); w /= w.sum()

N_CUST = 12000
start, end = datetime(2023, 1, 1), datetime(2024, 12, 31)
signup_days = rng.integers(0, (end - start).days - 30, N_CUST)
signup_days = np.sort(signup_days)
cust = pd.DataFrame({
    "customer_id": [f"C{100000+i}" for i in range(N_CUST)],
    "signup_date": [start + timedelta(days=int(d)) for d in signup_days],
    "city": rng.choice(city_names, N_CUST, p=w),
    "gender": rng.choice(["M", "F", "Other"], N_CUST, p=[.54, .44, .02]),
    "age": np.clip(rng.normal(31, 8, N_CUST).round(), 18, 70).astype(int),
    "acquisition_channel": rng.choice(
        ["Organic Search", "Paid Social", "Google Ads", "Referral", "Influencer", "Email"],
        N_CUST, p=[.28, .22, .20, .12, .10, .08]),
})
cust["state"] = cust.city.map(lambda c: cities[c][0])
cust["region"] = cust.city.map(lambda c: cities[c][1])
cust["city_tier"] = cust.city.map(lambda c: cities[c][3])

# ---------------- Products ----------------
cats = {  # category: (subcats, price range, margin, return rate)
    "Electronics": (["Mobiles", "Earbuds", "Smartwatches", "Chargers", "Laptops"], (499, 65000), .12, .09),
    "Fashion": (["Men Topwear", "Women Ethnic", "Footwear", "Accessories", "Kids Wear"], (299, 4999), .38, .22),
    "Home & Kitchen": (["Cookware", "Bedsheets", "Decor", "Storage", "Appliances"], (199, 12000), .28, .07),
    "Beauty": (["Skincare", "Haircare", "Makeup", "Fragrance"], (149, 2999), .42, .05),
    "Grocery": (["Staples", "Snacks", "Beverages", "Dry Fruits"], (49, 1499), .14, .02),
    "Sports & Fitness": (["Gym Equipment", "Yoga", "Cycling", "Sportswear"], (299, 15000), .30, .08),
    "Books": (["Fiction", "Self-Help", "Exam Prep", "Kids Books"], (99, 999), .25, .03),
}
brands = ["Zentra", "Kalpa", "UrbanLoom", "Nivara", "Boltix", "Swadesh", "Aarna", "Fitora", "Mithas", "Pustak", "Veda", "Trendz"]
prows = []
pid = 1000
for cat, (subs, (lo, hi), m, rr) in cats.items():
    for s in subs:
        for _ in range(rng.integers(12, 25)):
            price = float(np.exp(rng.uniform(np.log(lo), np.log(hi))))
            price = round(price / 10) * 10 - 1
            b = rng.choice(brands)
            prows.append([f"P{pid}", f"{b} {s} {rng.integers(100,999)}", cat, s,
                          b, max(price, 49), round(price * 0.83 * (1 - m * rng.uniform(.8, 1.2)), 2), rr])
            pid += 1
prod = pd.DataFrame(prows, columns=["product_id", "product_name", "category", "sub_category", "brand",
                                    "mrp", "unit_cost", "_rr"])
cat_pop = {"Electronics": 1.0, "Fashion": 2.2, "Home & Kitchen": 1.3, "Beauty": 1.4, "Grocery": 1.8,
           "Sports & Fitness": .6, "Books": .5}
pw = prod.category.map(cat_pop) / np.sqrt(prod.mrp)  # cheaper items sell more
pw = (pw / pw.sum()).values

# ---------------- Orders ----------------
def season(d):
    m, day = d.month, d.day
    f = 1.0
    if m == 10 or (m == 11 and day <= 15): f = 2.1          # Diwali / Big Billion style sale
    elif m == 1 and 15 <= day <= 26: f = 1.5                 # Republic Day sale
    elif m == 8 and 5 <= day <= 15: f = 1.6                  # Independence Day sale
    elif m in (3, 4): f = 0.85
    elif m == 12: f = 1.2
    return f * (1.0 if d.weekday() < 5 else 1.15)

orders, items = [], []
oid = 500000
cust_arr = cust.to_dict("records")
# each customer gets a loyalty propensity
propensity = rng.gamma(0.9, 1.4, N_CUST)
channel_boost = {"Referral": 1.35, "Email": 1.25, "Organic Search": 1.1, "Google Ads": .95, "Paid Social": .8, "Influencer": .75}
for i, c in enumerate(cust_arr):
    p = propensity[i] * channel_boost[c["acquisition_channel"]] * (1.1 if c["city_tier"] == 1 else .9)
    d = c["signup_date"] + timedelta(days=int(rng.integers(0, 5)))
    first = True
    while d <= end:
        n_items = rng.choice([1, 2, 3, 4], p=[.62, .24, .10, .04])
        status = rng.choice(["Delivered", "Cancelled", "Returned", "RTO"], p=[.86, .07, .05, .02])
        payment = rng.choice(["UPI", "COD", "Credit Card", "Debit Card", "Wallet", "Net Banking", "EMI"],
                             p=[.46, .22, .11, .07, .06, .04, .04])
        if c["city_tier"] >= 2 and rng.random() < .15: payment = "COD"
        if payment == "COD" and status == "Delivered" and rng.random() < .06: status = "RTO"
        sale = season(d) > 1.4
        oid += 1
        o_id = f"ORD{oid}"
        ship_days = int(np.clip(rng.normal(3.2 + (c["city_tier"] - 1) * 1.3, 1.2), 1, 12))
        coupon = rng.choice(["NONE", "WELCOME10", "FEST20", "FLAT150", "LOYAL5"],
                            p=[.6, .1, .1, .1, .1]) if not first else rng.choice(["WELCOME10", "NONE"], p=[.7, .3])
        if sale and coupon == "NONE" and rng.random() < .5: coupon = "FEST20"
        orders.append([o_id, c["customer_id"], d + timedelta(hours=int(rng.integers(7, 24)), minutes=int(rng.integers(0, 60))),
                       payment, status, coupon, ship_days, rng.choice(["App", "Web", "mWeb"], p=[.68, .2, .12])])
        for pi in rng.choice(len(prod), n_items, p=pw, replace=False):
            pr = prod.iloc[pi]
            disc = rng.uniform(.05, .25) + (rng.uniform(.10, .25) if sale else 0)
            qty = 1 if pr.mrp > 2000 else rng.choice([1, 2, 3], p=[.8, .15, .05])
            ret = status == "Returned" or (status == "Delivered" and rng.random() < pr._rr * .4)
            items.append([o_id, pr.product_id, qty, pr.mrp, round(min(disc, .7), 3), ret])
        # churn: first experience matters a lot (slow delivery / failed order => less likely to return)
        if first:
            churn = 0.40 + 0.05 * max(ship_days - 3, 0) + (0.18 if status != "Delivered" else 0) - 0.08 * min(p, 2)
            first = False
            if rng.random() < churn: break
        elif rng.random() < 0.30 / (1 + p): break
        gap = rng.exponential(75 / (0.4 + p)) / season(d)
        d = d + timedelta(days=int(gap) + 1)

orders = pd.DataFrame(orders, columns=["order_id", "customer_id", "order_datetime", "payment_method",
                                       "order_status", "coupon_code", "delivery_days", "platform"])
items = pd.DataFrame(items, columns=["order_id", "product_id", "quantity", "mrp", "discount_pct", "is_returned"])
items.insert(0, "item_id", [f"IT{i+1:07d}" for i in range(len(items))])

# ---------------- Inject real-world mess ----------------
cust_raw = cust.copy()
idx = rng.choice(len(cust_raw), 180, replace=False)
cust_raw.loc[idx[:60], "city"] = cust_raw.loc[idx[:60], "city"].str.upper()
cust_raw.loc[idx[60:100], "city"] = cust_raw.loc[idx[60:100], "city"].replace(
    {"Bengaluru": "Bangalore", "Mumbai": "Bombay", "Delhi": "New Delhi", "Chennai": "Madras"}) + " "
cust_raw.loc[idx[100:140], "age"] = rng.choice([0, 150, 999, -1], 40)
cust_raw.loc[idx[140:], "gender"] = rng.choice(["male", "female", "", None], 40)
cust_raw = pd.concat([cust_raw, cust_raw.sample(55, random_state=1)])  # duplicates
cust_raw["signup_date"] = cust_raw["signup_date"].dt.strftime("%Y-%m-%d")
mix = rng.choice(len(cust_raw), 300, replace=False)
cust_raw.iloc[mix, cust_raw.columns.get_loc("signup_date")] = pd.to_datetime(
    cust_raw.iloc[mix]["signup_date"]).dt.strftime("%d/%m/%Y").values
cust_raw = cust_raw.sample(frac=1, random_state=3)

orders_raw = orders.copy()
orders_raw["order_datetime"] = orders_raw.order_datetime.dt.strftime("%Y-%m-%d %H:%M:%S")
j = rng.choice(len(orders_raw), 400, replace=False)
orders_raw.loc[j[:200], "payment_method"] = orders_raw.loc[j[:200], "payment_method"].str.lower()
orders_raw.loc[j[200:260], "payment_method"] = "upi "
orders_raw.loc[j[260:330], "delivery_days"] = np.nan
orders_raw.loc[j[330:], "coupon_code"] = None
orders_raw = pd.concat([orders_raw, orders_raw.sample(120, random_state=7)])

items_raw = items.copy()
k = rng.choice(len(items_raw), 150, replace=False)
items_raw.loc[k[:50], "quantity"] = 0
items_raw.loc[k[50:80], "quantity"] = -1
items_raw.loc[k[80:], "discount_pct"] = items_raw.loc[k[80:], "discount_pct"] * 100  # % vs fraction mix-up
items_raw["is_returned"] = items_raw.is_returned.map({True: "Y", False: "N"})

prod_raw = prod.drop(columns="_rr")
prod_raw.loc[rng.choice(len(prod_raw), 8, replace=False), "unit_cost"] = np.nan

cust_raw.to_csv(OUT + "customers.csv", index=False)
prod_raw.to_csv(OUT + "products.csv", index=False)
orders_raw.to_csv(OUT + "orders.csv", index=False)
items_raw.to_csv(OUT + "order_items.csv", index=False)
print(len(cust_raw), len(prod_raw), len(orders_raw), len(items_raw))
