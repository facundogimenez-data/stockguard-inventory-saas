"""
StockGuard — Inventory Intelligence Dashboard (demo reconstruction)

Three views over the same alert engine output:
  - Overview  : KPIs + alert distribution + top critical risks
  - Alerts    : full filterable alert table (critical / excess / stagnant)
  - Inventory : live stock levels and days-of-coverage per product
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import create_engine, text

st.set_page_config(page_title="StockGuard | Inventory Intelligence", page_icon="📦", layout="wide")

ALERTS_JSON = Path(__file__).parent / 'outputs' / 'alerts.json'

st.markdown("""
<style>
  .kpi-card { background:#1e293b; border-radius:10px; padding:16px 20px; border-left:4px solid #3b82f6; }
  .kpi-card.critical { border-left-color:#ef4444; }
  .kpi-card.high     { border-left-color:#f59e0b; }
  .kpi-card.medium   { border-left-color:#3b82f6; }
  .kpi-card.money    { border-left-color:#10b981; }
  .kpi-label { font-size:.78rem; color:#94a3b8; text-transform:uppercase; letter-spacing:.05em; }
  .kpi-value { font-size:1.8rem; font-weight:700; color:#f1f5f9; margin:4px 0; }
  .kpi-sub   { font-size:.75rem; color:#64748b; }
  .badge-critical { background:#fef2f2; color:#b91c1c; padding:2px 10px; border-radius:20px; font-size:.78rem; font-weight:600; }
  .badge-high     { background:#fffbeb; color:#92400e; padding:2px 10px; border-radius:20px; font-size:.78rem; font-weight:600; }
  .badge-medium   { background:#eff6ff; color:#1d4ed8; padding:2px 10px; border-radius:20px; font-size:.78rem; font-weight:600; }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_engine():
    user = os.getenv('DB_USER', 'demo_user')
    password = os.getenv('DB_PASSWORD', 'demo_password')
    host = os.getenv('DB_HOST', 'localhost')
    port = os.getenv('DB_PORT', '3306')
    name = os.getenv('DB_NAME', 'stockguard_demo')
    return create_engine(f"mysql+mysqlconnector://{user}:{password}@{host}:{port}/{name}")


@st.cache_data(ttl=300)
def load_inventory() -> pd.DataFrame:
    try:
        with get_engine().connect() as conn:
            return pd.read_sql(text("""
                SELECT name AS producto, sku, category AS categoria,
                       current_stock AS stock_actual, sales_last_30d AS ventas_30d,
                       days_of_inventory AS dias_cobertura, lead_time_days AS lead_time
                FROM v_inventory_metrics
                ORDER BY days_of_inventory ASC, current_stock DESC
            """), conn)
    except Exception:
        return pd.DataFrame()


def load_alerts() -> dict:
    if not ALERTS_JSON.exists():
        return {}
    try:
        with open(ALERTS_JSON, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def run_engine() -> tuple[bool, str]:
    engine_path = Path(__file__).parent / 'forecast_engine.py'
    try:
        result = subprocess.run([sys.executable, str(engine_path)], capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            load_alerts.clear()
            load_inventory.clear()
            return True, result.stdout
        return False, result.stderr or result.stdout
    except Exception as e:
        return False, str(e)


def fmt_money(v):
    try:
        return f"${float(v):,.0f}"
    except Exception:
        return "—"


def fmt_days(v):
    try:
        return f"{float(v):.0f} days"
    except Exception:
        return "no sales"


SEVERITY_BADGE = {
    'critical': '<span class="badge-critical">🔴 Critical</span>',
    'high':     '<span class="badge-high">🟡 High</span>',
    'medium':   '<span class="badge-medium">🔵 Medium</span>',
}

with st.sidebar:
    st.markdown("## 📦 StockGuard")
    st.caption("Inventory intelligence — demo dataset (synthetic food distributor)")
    page = st.radio("Navigation", ["📊 Overview", "🚨 Alerts", "📦 Inventory"], label_visibility="collapsed")
    st.markdown("---")
    if st.button("🔄 Run analysis", use_container_width=True, type="primary"):
        with st.spinner("Running forecast engine..."):
            ok, msg = run_engine()
        if ok:
            st.success("Analysis complete")
            st.rerun()
        else:
            st.error("Engine failed")
            st.code(msg)
    data = load_alerts()
    if data.get('generated_at'):
        ts = datetime.fromisoformat(data['generated_at'])
        st.caption(f"Last run: {ts.strftime('%Y-%m-%d %H:%M')}")

alerts_data = load_alerts()
alerts = alerts_data.get('alerts', [])
df_inv = load_inventory()

if page == "📊 Overview":
    st.title("📊 Overview")
    st.caption("Executive summary of inventory health")

    n_critical = alerts_data.get('critical_count', 0)
    n_high = alerts_data.get('high_count', 0)
    n_medium = alerts_data.get('medium_count', 0)
    risk_capital = sum(a.get('lost_sales_risk', 0) for a in alerts if a.get('severity') == 'critical')

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">Products tracked</div>'
                    f'<div class="kpi-value">{len(df_inv) if not df_inv.empty else "—"}</div>'
                    f'<div class="kpi-sub">active SKUs</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="kpi-card critical"><div class="kpi-label">🔴 Critical</div>'
                    f'<div class="kpi-value">{n_critical}</div><div class="kpi-sub">stockout risk</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="kpi-card high"><div class="kpi-label">🟡 High</div>'
                    f'<div class="kpi-value">{n_high}</div><div class="kpi-sub">excess inventory</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="kpi-card medium"><div class="kpi-label">🔵 Medium</div>'
                    f'<div class="kpi-value">{n_medium}</div><div class="kpi-sub">stagnant products</div></div>', unsafe_allow_html=True)
    with c5:
        st.markdown(f'<div class="kpi-card money"><div class="kpi-label">💰 Capital at risk</div>'
                    f'<div class="kpi-value" style="font-size:1.3rem">{fmt_money(risk_capital)}</div>'
                    f'<div class="kpi-sub">potential lost sales</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown("#### Alert distribution")
        total = n_critical + n_high + n_medium
        if total:
            fig = go.Figure(data=[go.Pie(labels=['Critical', 'High', 'Medium'], values=[n_critical, n_high, n_medium],
                                          hole=.55, marker_colors=['#ef4444', '#f59e0b', '#3b82f6'])])
            fig.update_layout(showlegend=False, height=280, margin=dict(t=20, b=20, l=20, r=20),
                              paper_bgcolor='rgba(0,0,0,0)', font_color='#e2e8f0')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No alerts yet — click 'Run analysis' in the sidebar.")
    with col_r:
        st.markdown("#### Critical alerts by category")
        critical = [a for a in alerts if a.get('severity') == 'critical']
        if critical:
            cats = {}
            for a in critical:
                cat = a['product']['category']
                cats[cat] = cats.get(cat, 0) + 1
            df_cat = pd.DataFrame(cats.items(), columns=['Category', 'Alerts']).sort_values('Alerts')
            fig2 = px.bar(df_cat, x='Alerts', y='Category', orientation='h', color_discrete_sequence=['#ef4444'])
            fig2.update_layout(height=280, margin=dict(t=20, b=20, l=10, r=20),
                               paper_bgcolor='rgba(0,0,0,0)', font_color='#e2e8f0')
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.success("No active critical alerts.")

    st.markdown("#### 🔥 Top critical risks")
    critical = sorted([a for a in alerts if a.get('severity') == 'critical'],
                      key=lambda a: a.get('lost_sales_risk', 0), reverse=True)[:5]
    if critical:
        st.dataframe(pd.DataFrame([{
            'Product': a['product']['name'], 'SKU': a['product']['sku'],
            'Stock': a['current_stock'], 'Days left': fmt_days(a.get('days_of_inventory')),
            'Order (units)': a.get('suggested_order', '—'), 'Risk': fmt_money(a.get('lost_sales_risk', 0)),
        } for a in critical]), use_container_width=True, hide_index=True)
    else:
        st.success("✅ No critical risks active.")

elif page == "🚨 Alerts":
    st.title("🚨 Alerts")
    st.caption("Every product that needs attention, ranked by priority")
    severities = st.multiselect("Filter by severity", ['critical', 'high', 'medium'],
                                default=['critical', 'high', 'medium'],
                                format_func=lambda s: {'critical': '🔴 Critical', 'high': '🟡 High', 'medium': '🔵 Medium'}[s])
    filtered = [a for a in alerts if a.get('severity') in severities]
    if filtered:
        st.dataframe(pd.DataFrame([{
            'Severity': SEVERITY_BADGE.get(a['severity'], a['severity']),
            'Product': a['product']['name'], 'SKU': a['product']['sku'], 'Category': a['product']['category'],
            'Stock': a['current_stock'], 'Days of stock': fmt_days(a.get('days_of_inventory')),
            'Recommendation': a.get('recommendation', '—'),
        } for a in filtered]), use_container_width=True, hide_index=True,
            column_config={'Severity': st.column_config.Column(width='small')})
    else:
        st.info("No alerts match this filter.")

else:  # Inventory
    st.title("📦 Inventory")
    st.caption("Live stock position across the catalog")
    if df_inv.empty:
        st.info("No data yet — start the stack with `docker compose up` to load the demo dataset.")
    else:
        search = st.text_input("Search by product or SKU")
        view = df_inv
        if search:
            mask = view['producto'].str.contains(search, case=False) | view['sku'].str.contains(search, case=False)
            view = view[mask]
        st.dataframe(view, use_container_width=True, hide_index=True)
