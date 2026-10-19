# Team ProfitWatch · Regional Profit Watch — Global Superstore

**Deployed app:** <https://YOUR-APP-URL.streamlit.app> · **Team:** Team ProfitWatch

A one-page Streamlit dashboard for a **regional sales manager** at a global retail chain.
It answers one question in five seconds — *is my region's profit healthy, and if not, where is it leaking?* —
and it is deliberately built around a single controllable lever: **deep discounts**.

- **Dataset:** [Global Superstore (Kaggle)](https://www.kaggle.com/datasets/shekpaul/global-superstore) — 51,290 order line items, 25,035 orders, 1,590 customers, Jan 2011 – Dec 2014. One row = one product line on one order. It is the well-known Tableau "Global Superstore" sample, i.e. **synthetic/illustrative** data structured like a real retailer's order extract. The original `.xls` was converted to `data/superstore.csv` (12.5 MB, under the 25 MB limit — no sampling needed); the small `Returns` sheet was exported to `data/returns.csv`.
- **Decision-maker:** a **regional sales manager** responsible for one Market/Region (e.g. APAC / Oceania), who owns discount approvals and category performance in their region.

## Answers at a glance

| Question | Answer |
|---|---|
| **Who is it for?** | The regional sales manager — one role, one market/region each, not "everyone". |
| **What decision does it support?** | *"If my region's margin is falling while sales at ≥30% discount grow, I will cap deep-discount approvals and put the loss-making sub-categories into a pricing review."* |
| **What did we show?** | 3 headline metrics (Sales, Profit, Profit margin) → 2 charts (monthly trend; sub-category profit split by discount depth) → 1 collapsed table of the worst deep-discount line items. |
| **What did we cut?** | Shipping cost / ship-mode analysis, and customer/segment leaderboards — neither changes a decision this manager can make on a monthly cadence. |
| **How often is it refreshed?** | Data nightly from the order system; reviewed weekly and monthly. One exception — the deep-discount share — becomes a same-day **alert**, not a dashboard check. |

---

## Step 1 — Dataset and decision-maker

We wanted a dataset with a believable operations story: orders, revenue, discounts, returns.
Global Superstore is a retail fact table (who bought what, where, at which discount, at what profit)
across 7 markets and 17 sub-categories — the well-known Tableau "Global Superstore" sample,
released on Kaggle by Chandra Shekhar (license: Other; single file `Global Superstore.xls`,
18.2 MB, three sheets: Orders / Returns / People). We read the dataset page and verified in the
EDA (`eda.ipynb`) that it covers 48 complete months — no partial months — and that the only
missing column is `Postal Code` (populated for US rows only, so city-level geography is
unusable outside the US).

**The one person this dashboard is for:** the *regional sales manager*. Not the CEO, not
"everyone": they review their own region's numbers repeatedly, and they are the person who
approves or refuses the discounts that drive the losses in this data.

**What is actually in the file** (three sheets, `Global Superstore.xls`):

| Sheet | Size | What it holds |
|---|---|---|
| `Orders` | 51,290 × 24 | One line of an order: order/ship dates, Market–Region–Country–City, customer + segment, category/sub-category/product, **Sales, Quantity, Discount, Profit, Shipping Cost**, ship mode, order priority |
| `Returns` | 1,173 × 3 | Returned flag, Order ID, Market — no refund amounts |
| `People` | 14 × 2 | Regional manager name ↔ Region (i.e. who owns each area) |

`Sales` is **post-discount** revenue, `Discount` runs 0–0.85, and `Profit` is the line-level
result after discount. The file has no unit-cost column, so cost structure cannot be broken out.
Consequently the data **cannot** answer: stock levels, why an order was returned, marketing
spend/ROI, or cost breakdowns. That is deliberate scope-setting — the dashboard stays on
revenue/profit and does not pretend to be an inventory or marketing tool.

## Step 2 — Why this dashboard

1. **Who looks at it, how often?** The regional sales manager, weekly for a quick glance and
   monthly for their business review.
2. **The decision it supports:** *"If the regional manager sees profit margin trending down while
   the red (≥30% discount) share of profit grows, they will cap or refuse deep-discount
   approvals in their region and pull the loss-making sub-categories (e.g. Tables) into a
   pricing review."*
3. **What they do today without it:** dig through order extracts in a spreadsheet each month,
   where losses hide inside healthy totals — company-wide margin is a stable ~11.6% and no
   single month is loss-making, yet **24.5% of all line items sell at a loss**. Finding that in
   a spreadsheet takes hours, so in practice it is not found until the quarterly P&L lands.
4. **Why a dashboard, not an email/report/alert?** The same person asks the same question on a
   recurring cadence and acts on what they see — the definition of a dashboard use case. A
   monthly email would be stale between reviews; a one-off report cannot follow a changing
   region filter; a pure alert (see Step 4) covers only the extreme case, not the review ritual.

## Step 3 — What we show, what we cut, and why

The EDA (`eda.ipynb`) found one dominant pattern: **margin collapses with discount depth** —
0%-discount lines earn ≈26% margin, while the 20.9% of lines sold at ≥30% discount are sold at a
loss and destroyed ≈$0.81M over the four years. `Tables` is the only sub-category loss-making
overall, and most of that loss comes from deep-discount lines. That pattern is also *controllable
by our decision-maker*, which is what earns it the page.

**Page sketch, top to bottom** (drawn before any code was written):

```
┌──────────────────────────────────────────────────────────────┐
│ [sidebar]           Team ProfitWatch · Regional Profit Watch │
│ Market ▾ APAC       for the regional sales manager: cap deep │
│ Region ▾ Oceania    discounts when margin falls              │
│ Years  ▸ 2013–2014  Data: Jan 2011 – Dec 2014 · nightly       │
│ ┌─ Sales ────┐ ┌─ Profit ──┐ ┌─ Margin ──┐                  │
│ │ $0.68M     │ │ $69k      │ │ 10.2%     │  ← 5-second      │
│ │ +257k      │ │ +18k      │ │ -2.0 pts  │     answer       │
│ └────────────┘ └───────────┘ └───────────┘                  │
│ Monthly sales & profit  ╱╲╱╲___╱╲                            │
│                         ── sales  ── profit   ← when it moved│
│ Profit by sub-category  ▇▇▇▇▇  normal discount                │
│                         ▇▇▇▇▇  ≥30% discount  ← where it leaks│
│ ▸ Loss-making line items at ≥30% discount (collapsed)  ← rows │
└──────────────────────────────────────────────────────────────┘
```

**Top (the 5-second answer):** three headline metrics in `st.columns` — **Sales**, **Profit**,
**Profit margin**, each with a delta vs the preceding equal-length period. Anything wrong shows
up as a red delta here.

**Middle (the *why*):** two supporting charts, in reading order:
1. *Monthly sales & profit trend* — explains **when** a headline moved; makes Q4 seasonality visible
   so a December dip is not misread as a problem.
2. *Profit by sub-category, split by discount depth* (green <30% vs red ≥30%) — explains **where**
   the leak is and names the lever. One glance shows, e.g., that Tables loses money *because of*
   its deep-discount lines.

**Bottom (only for those who dig):** an expander with the 50 worst loss-making line items sold at
≥30% discount — the concrete rows a pricing review starts from. Collapsed by default; nobody
scrolled to it unless they need it.

**Filters:** Market → Region (cascading) and a year range. A regional manager looks at *their*
region, so the region selector is the filter that matters; we deliberately added nothing else.

**Two things we chose *not* to show:**
- **Shipping cost / ship-mode analysis.** Interesting in the EDA (shipping costs reach ~$1k per
  line), but the manager cannot renegotiate carriers between monthly reviews — it would not
  change any decision on this cadence.
- **Customer leaderboard / segment breakdown.** A marketing question with a different owner;
  synthetic customer names add no decision value for a regional P&L review.

**What could mislead the viewer, and how the app handles it:**
- **Totals are gross of returns:** 1,173 of 25,035 orders (4.7%) were returned, and 5.9% of line
  items sit on a returned order — but the Returns sheet carries only order IDs and no amounts, so
  nothing can be netted down. A caption in the expander says so explicitly.
- **Synthetic snapshot data:** the page labels the data period and source ("Data: Jan 2011 –
  Dec 2014, Kaggle snapshot") so nobody quotes the levels as audited numbers.
- **No partial months:** verified in the EDA — the trend's last point is a real full month.
- **Skewed totals:** a handful of very large lines dominate revenue; the trend + breakdown pair
  (rather than a single average) keeps that from being misread.

Every element survived one test: *if it disappeared, the manager would notice.* The KPI row
answers "is anything wrong", the two charts answer "why", the expander answers "show me the rows".

## Step 4 — Refresh frequency (production)

- **Data refresh: nightly**, batch from the order-management system. Real-time or hourly refresh
  would add cost without changing any decision, because the manager's actions (discount caps,
  pricing reviews) happen on a weekly/monthly cadence, not intra-day.
- **Review cadence: weekly glance, monthly business review** — deliberately *not* the same as the
  refresh rate. Fresh data every morning, but the ritual is Monday morning plus the monthly review.
- **The metric that should trigger action:** *share of sales sold at ≥30% discount*. If a region's
  4-week rolling deep-discount share rises more than ~5 points above its trailing average, or any
  sub-category's 4-week profit turns negative, that should page the manager **as an alert, not a
  dashboard check** — it is the one number where waiting for the next review costs money.
- **Cost of stale data:** in this snapshot, deep-discount lines lose ≈$200k per year globally
  (~$4k a week). A week-stale dashboard means a week of unbounded discount approvals; a
  month-stale one means a pricing review starts a month late.

The dashboard itself states: *"Data: Jan 2011 – Dec 2014 (Kaggle snapshot) · Production refresh:
nightly from the order system."*

## Step 5 — App and repo

```
superstore-dashboard/
├── app.py                  # the Streamlit app: title, caption, 3 metrics, 2 charts, 3 filters, detail table
├── eda.ipynb               # executed EDA behind every include/exclude decision above
├── data/superstore.csv     # Orders sheet converted from the Kaggle .xls (12.5 MB, untouched otherwise)
├── data/returns.csv        # Returns sheet (order IDs only, no amounts)
├── .streamlit/config.toml  # fixed light theme so the deployed page looks the same for every visitor
├── smoke_test.py           # AppTest check: page renders, filters cascade, no exceptions
├── pyproject.toml          # uv project, Python 3.14
└── README.md               # this file
```

Run locally:

```bash
uv sync
uv run streamlit run app.py
```

Deploy from this repository to Streamlit Community Cloud:

1. Push the repo to GitHub (public) — `git push -u origin main`.
2. <https://share.streamlit.io> → **New app** → pick the repo → main file `app.py`.
3. **Advanced settings → Python version = 3.14** (the repo already pins `.python-version` to 3.14 and ships a `uv.lock`).
4. Deploy, then paste the app URL into the *Deployed app* line at the top of this file.

## Before submitting (checklist)

- [ ] Replace `Team ProfitWatch` with your real team name (the `TEAM_NAME` constant on line 17 of `app.py`, and the title/Team line in this README).
- [ ] Replace `https://YOUR-APP-URL.streamlit.app` above with the deployed app URL.
- [ ] Push to **your own** public GitHub repo and submit both URLs on Canvas (each student submits individually; the app and repo must be your own).

