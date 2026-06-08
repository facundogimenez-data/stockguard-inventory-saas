# StockGuard — Inventory Intelligence SaaS

![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-4479A1?style=flat&logo=mysql&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat&logo=streamlit&logoColor=white)
![n8n](https://img.shields.io/badge/n8n-EA4B71?style=flat&logo=n8n&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white)

## ⚠️ Confidentiality note — data has been changed

**StockGuard is a commercial inventory-forecasting product designed, built, and sold
by [Mowarama](https://github.com/facundogimenez-data)**, currently running in production
for a real client. **For GDPR / commercial-confidentiality reasons, the client's actual
product catalog, sales figures, and stock data cannot be published.**

What you'll find in this repo is a **demo reconstruction running on a synthetic
dataset**: a fictional grocery distributor catalog (27 generic products, 90 days of
simulated sales and stock movements) generated to reproduce the same alert patterns
— stockout risk, excess inventory, dead stock — that StockGuard detects in the real
deployment, without exposing any real client data, names, or figures. The
architecture, alert logic, and dashboard are faithful to the live product; only the
underlying data has been replaced.

## What this is

StockGuard is not a one-off automation — it's a packaged SaaS aimed at SMEs in
distribution and retail (food distributors, hardware stores, pharmacies, bakeries)
that manage 50–500 active SKUs with manual, reactive inventory processes.

## The problem it solves

SMEs that manage inventory with spreadsheets or "experience and intuition" lose
revenue two ways at once: products run out **without warning** (lost sales, lost
customers) while capital sits **frozen in stock that doesn't move** (less cash to
buy what actually sells). Both problems are predictable from data the business
already has — sales history, current stock, supplier lead times — but almost nobody
turns that data into a daily, actionable signal.

## What StockGuard does

Every day, StockGuard analyzes the full product catalog and classifies each SKU into
one of three alert types, each with a concrete recommendation — not just "stock is
low," but **"order 187 units today, your supplier takes 45 days and you have 12 days
of stock left, this prevents an estimated €1,200 in lost sales."**

| Alert | Trigger | What it tells the owner |
|---|---|---|
| 🔴 **Critical — stockout risk** | Days of stock < lead time threshold | Exact quantity to reorder *today* and the revenue at risk if they don't |
| 🟡 **Excess — capital tied up** | Days of stock far above a healthy level | How many units are "too many" and how much capital that represents |
| 🔵 **Stagnant — dead stock** | Zero sales in 30 days | How much capital is locked in a product that stopped selling |

Alerts are delivered every morning by email and Telegram, and the underlying data
feeds a live dashboard so the owner can drill into any product at any time.

## Architecture

```
 POS / sales system ──► MySQL (products, sales, inventory_movements)
                              │
                  ┌───────────┴────────────┐
                  ▼                        ▼
        Forecast & Alert Engine    Streamlit Dashboard
        (Python — runs daily,      (Overview / Alerts /
         classifies every SKU,      Inventory — live view
         writes alerts.json)        of stock health)
                  │
                  ▼
        n8n — multi-channel delivery
        (email + Telegram, daily digest
         + on-demand "/report" via bot)
```

## Tech stack

| Technology | Role |
|---|---|
| **Python** | `forecast_engine.py` — reads sales velocity & stock per SKU, classifies alerts, computes suggested order quantities and capital-at-risk figures |
| **MySQL** | Stores the product catalog, sales history, and stock movements; a SQL view (`v_inventory_metrics`) precomputes days-of-coverage per product |
| **Streamlit + Plotly** | Live dashboard — KPI overview, full alert table with severity filters, and a searchable inventory view |
| **n8n** | Schedules the daily run and delivers alerts through email + Telegram (and answers on-demand "/report" requests via a Telegram bot) |
| **Docker / docker-compose** | One-command local deployment (MySQL + dashboard) |

## Results (real deployment)

For the live client deployment (a food distribution business, ~70 SKUs):

- **100+ stockouts prevented per year** — each one previously cost between
  €500 and €15,000 in lost sales depending on the product and how long it took
  to restock
- **Capital tied up in excess inventory identified and reduced**, freeing cash
  that was previously frozen in slow-moving stock
- **From reactive to proactive**: the owner now gets a same-day, actionable
  recommendation instead of discovering a stockout when a customer asks for a
  product that isn't there

## Running the demo locally

```bash
git clone https://github.com/facundogimenez-data/stockguard-inventory-saas.git
cd stockguard-inventory-saas
cp .env.example .env
docker compose up --build
```

This starts a MySQL instance pre-loaded with a synthetic catalog
([`db/schema.sql`](db/schema.sql) — 27 products, 90 days of simulated sales and
stock movements calibrated to reproduce all three alert types) and the dashboard
at `http://localhost:8501`. Click **"Run analysis"** in the sidebar to generate
alerts from the seed data.

To run the dashboard alone against your own MySQL instance:

```bash
cd app
pip install -r requirements.txt
streamlit run app.py
```

## Project structure

| Path | Purpose |
|------|---------|
| [`app/forecast_engine.py`](app/forecast_engine.py) | Classifies every SKU into critical / excess / stagnant and writes `alerts.json` |
| [`app/app.py`](app/app.py) | Streamlit dashboard (Overview, Alerts, Inventory) |
| [`db/schema.sql`](db/schema.sql) | MySQL schema + synthetic demo dataset |
| [`docker-compose.yml`](docker-compose.yml) / [`Dockerfile`](Dockerfile) | One-command local deployment |
| `n8n workflow` | Daily scheduling + multi-channel alert delivery (email, Telegram, on-demand bot reports) — runs on the live deployment, not exported here as it references production credentials |

## Author

**Facundo Gimenez** — Data Analyst & AI Automation Specialist, founder of Mowarama
[LinkedIn](https://www.linkedin.com/in/facundo-r-gimenez/) | [GitHub](https://github.com/facundogimenez-data)
