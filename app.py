"""Regional Profit Watch — Global Superstore dashboard.

Built for a regional sales manager: spot profit erosion early, see where it
comes from (deep-discount lines and loss-making sub-categories), and act by
capping discount approvals — all filtered to their own market/region.
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Regional Profit Watch", layout="wide")

TEAM_NAME = "Team ProfitWatch"  # TODO: replace with your own team name
DATA_PERIOD = "Data: Jan 2011 – Dec 2014 (Kaggle snapshot) · Production refresh: nightly from the order system"

# ---------------------------------------------------------------- load data
@st.cache_data
def load_data() -> pd.DataFrame:
    df = pd.read_csv(Path("data/superstore.csv"), parse_dates=["Order Date"])
    df["Year"] = df["Order Date"].dt.year
    return df


df = load_data()

# ---------------------------------------------------------------- sidebar
st.sidebar.header("Filters")

markets = ["All"] + sorted(df["Market"].unique())
market = st.sidebar.selectbox("Market", markets, index=0)

if market == "All":
    regions = ["All"]
else:
    regions = ["All"] + sorted(df.loc[df["Market"] == market, "Region"].unique())
region = st.sidebar.selectbox("Region", regions, index=0)

years = sorted(df["Year"].unique())
year_range = st.sidebar.select_slider(
    "Year range", options=years, value=(years[-2], years[-1])
)

# ---------------------------------------------------------------- filter
view = df
if market != "All":
    view = view[view["Market"] == market]
if region != "All":
    view = view[view["Region"] == region]
y0, y1 = year_range
view = view[view["Year"].between(y0, y1)]

# prior equal-length window, for the KPI deltas (None if outside the data)
span = y1 - y0 + 1
p0, p1 = y0 - span, y0 - 1
prior = df
if market != "All":
    prior = prior[prior["Market"] == market]
if region != "All":
    prior = prior[prior["Region"] == region]
has_prior = p0 >= years[0]
prior = prior[prior["Year"].between(p0, p1)] if has_prior else None

# ---------------------------------------------------------------- header
st.title(f"{TEAM_NAME} · Regional Profit Watch")
st.caption(
    "For the regional sales manager: if margin trends down while deep-discount sales grow, "
    "cap discount approvals and pull loss-making sub-categories into a pricing review."
)
st.caption(DATA_PERIOD)

if view.empty:
    st.warning("No orders match these filters.")
    st.stop()

# ---------------------------------------------------------------- KPIs
sales, profit = view["Sales"].sum(), view["Profit"].sum()
margin = profit / sales if sales else 0.0

d_sales = d_margin = None
if has_prior and prior["Sales"].sum() > 0:
    p_sales, p_profit = prior["Sales"].sum(), prior["Profit"].sum()
    d_sales = sales - p_sales
    d_margin = margin - p_profit / p_sales

c1, c2, c3 = st.columns(3)
with c1:
    st.metric(
        "Sales",
        f"${sales / 1e6:,.2f}M",
        delta=None if d_sales is None else f"{d_sales / 1e3:,.0f}k",
        help="Gross revenue for the selected region and years (before returns).",
    )
with c2:
    st.metric(
        "Profit",
        f"${profit / 1e3:,.0f}k",
        delta=None if d_sales is None else f"{(profit - prior['Profit'].sum()) / 1e3:,.0f}k",
        help="Reported line-item profit, gross of returns.",
    )
with c3:
    st.metric(
        "Profit margin",
        f"{margin:.1%}",
        delta=None if d_margin is None else f"{d_margin * 100:.1f} pts",
        help="Profit / Sales. Company average in this snapshot is 11.6%.",
    )

# ---------------------------------------------------------------- chart 1: trend
st.subheader("Why did the numbers move?")
st.markdown(
    "Monthly sales and profit for the current selection. "
    "Profit tracks sales with a stable gap — the leaks hide inside the totals (see below)."
)

monthly = (
    view.set_index("Order Date")
    .resample("ME")
    .agg(Sales=("Sales", "sum"), Profit=("Profit", "sum"))
    .reset_index()
)
fig1 = go.Figure()
fig1.add_trace(
    go.Scatter(x=monthly["Order Date"], y=monthly["Sales"] / 1e3, name="Sales ($k)",
               line=dict(color="#1f77b4", width=2))
)
fig1.add_trace(
    go.Scatter(x=monthly["Order Date"], y=monthly["Profit"] / 1e3, name="Profit ($k)",
               line=dict(color="#2ca02c", width=2))
)
fig1.update_layout(
    height=330,
    margin=dict(l=10, r=10, t=30, b=10),
    yaxis_title="$ thousands",
    legend=dict(orientation="h", y=1.1),
)
st.plotly_chart(fig1, width="stretch")

# ---------------------------------------------------------------- chart 2: sub-category
st.subheader("Where does profit leak?")
st.markdown(
    "Profit by sub-category, split by discount depth. Red = line items sold at a "
    "**discount of 30% or more** — in this snapshot those lines lose money on average, "
    "and they are the share the manager can control by refusing or capping deep discounts."
)

view = view.assign(deep=view["Discount"] >= 0.30)
sc = (
    view.groupby(["Sub-Category", "deep"], as_index=False)
    .agg(Profit=("Profit", "sum"))
)
totals = sc.groupby("Sub-Category")["Profit"].sum().sort_values()
order = list(totals.index)
normal = sc[~sc["deep"]].set_index("Sub-Category")["Profit"]
deep = sc[sc["deep"]].set_index("Sub-Category")["Profit"]

fig2 = go.Figure()
fig2.add_trace(
    go.Bar(
        y=order, x=[normal.get(s, 0) / 1e3 for s in order], orientation="h",
        name="Discount < 30%", marker_color="#2ca02c",
    )
)
fig2.add_trace(
    go.Bar(
        y=order, x=[deep.get(s, 0) / 1e3 for s in order], orientation="h",
        name="Discount ≥ 30%", marker_color="#d62728",
    )
)
fig2.add_vline(x=0, line_width=1)
fig2.update_layout(
    barmode="relative",
    height=520,
    margin=dict(l=10, r=10, t=30, b=10),
    xaxis_title="Profit ($ thousands)",
    legend=dict(orientation="h", y=1.06),
)
st.plotly_chart(fig2, width="stretch")

# ---------------------------------------------------------------- detail table
with st.expander(f"Loss-making line items sold at ≥30% discount ({view['deep'].sum():,} lines)"):
    st.markdown(
        "The rows a pricing review would start from — worst line items first. "
        "Sales and profit are **gross of returns**: 1,173 of 25,035 orders (4.7%) were returned "
        "and the returns table carries no amounts, so nothing can be netted down. The data is a "
        "synthetic Kaggle snapshot — treat the levels as illustrative, not audited."
    )
    worst = (
        view[view["deep"] & (view["Profit"] < 0)]
        .sort_values("Profit")
        .head(50)[["Order Date", "Order ID", "Sub-Category", "Product Name",
                   "Quantity", "Discount", "Sales", "Profit"]]
    )
    st.dataframe(worst, width="stretch", hide_index=True)
