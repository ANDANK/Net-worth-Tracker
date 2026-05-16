"""NetWorth Tracker — Streamlit entry point (Dashboard)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

import streamlit as st

st.set_page_config(
    page_title="NetWorth Tracker",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

from utils.auth import require_auth
from utils.fmt import fmt_currency, fmt_pct, delta_str

require_auth()

import plotly.graph_objects as go
import pandas as pd
from services.networth import get_dashboard_summary, get_networth_history

# ── Shared sidebar CSS (rename "app" → logo, applied on every page) ──────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
[data-testid="stSidebarNav"]::before {
    content: "💰 NetWorth Tracker";
    display: block;
    font-family: 'Inter', sans-serif;
    font-size: 17px;
    font-weight: 700;
    color: #f1f5f9;
    padding: 20px 16px 8px 16px;
    letter-spacing: -0.02em;
}
[data-testid="stSidebarNav"] li:first-child a span { display: none; }
[data-testid="stSidebarNav"] li:first-child a::before {
    content: "🏠  Dashboard";
    font-family: 'Inter', sans-serif;
    font-size: 14px;
    color: #94a3b8;
}
</style>
""", unsafe_allow_html=True)

# ── Sidebar: compact sign-out only ────────────────────────────────────────────
with st.sidebar:
    if st.button("🚪 Sign out", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

# ── Load data ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner="Loading dashboard…")
def load_summary():
    return get_dashboard_summary()

@st.cache_data(ttl=300, show_spinner=False)
def load_history():
    return get_networth_history("all")

try:
    summary = load_summary()
    history = load_history()
except Exception as e:
    st.error(f"Could not connect to Google Sheets: {e}")
    st.stop()

# ── Page title ────────────────────────────────────────────────────────────────
st.title("Dashboard")
st.caption(f"Last updated: {summary.get('last_updated', '—')}")

if st.button("🔄 Refresh", key="dash_refresh"):
    st.cache_data.clear()
    st.rerun()

# ── KPI cards ─────────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)

nw      = summary.get("total_net_worth", 0)
mom     = summary.get("monthly_change", 0)
mom_pct = summary.get("monthly_change_pct", 0)
ytd     = summary.get("ytd_change", 0)
ytd_pct = summary.get("ytd_change_pct", 0)

c1.metric("Net Worth",    fmt_currency(nw),
          delta=f"{delta_str(mom)} ({fmt_pct(mom_pct)} MoM)")
c2.metric("Investments",  fmt_currency(summary.get("investment_value", 0)))
c3.metric("Retirement",   fmt_currency(summary.get("retirement_value", 0)))
c4.metric("Cash",         fmt_currency(summary.get("cash_value", 0)))
c5.metric("YTD Change",   fmt_currency(ytd),
          delta=fmt_pct(ytd_pct))

st.divider()

# ── Net worth history chart ────────────────────────────────────────────────────
st.subheader("Net Worth History")

period_map = {"All time": None, "1 Year": "1y", "3 Years": "3y", "5 Years": "5y"}
period_label = st.radio("Period", list(period_map.keys()), horizontal=True,
                         label_visibility="collapsed", index=0)

if history:
    df = pd.DataFrame(history)
    df["date"] = pd.to_datetime(df["date"])

    sel = period_map[period_label]
    if sel:
        df = df[df["date"] >= pd.Timestamp.now() - pd.DateOffset(
            months={"1y": 12, "3y": 36, "5y": 60}.get(sel, 999)
        )]

    # Area chart — net worth
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["net_worth"].apply(lambda v: round(float(v or 0), 2)),
        name="Net Worth",
        fill="tozeroy",
        line=dict(color="#3b82f6", width=2),
        fillcolor="rgba(59,130,246,0.12)",
        hovertemplate="%{x|%b %d, %Y}<br><b>$%{y:,.0f}</b><extra></extra>",
    ))

    # Stacked asset lines if columns present
    for col, color, label in [
        ("investment_value", "#10b981", "Investments"),
        ("retirement_value", "#8b5cf6", "Retirement"),
        ("cash_value",       "#f59e0b", "Cash"),
    ]:
        if col in df.columns:
            fig.add_trace(go.Scatter(
                x=df["date"], y=df[col].apply(lambda v: round(float(v or 0), 2)),
                name=label, line=dict(width=1.5, dash="dot", color=color),
                hovertemplate="%{x|%b %d, %Y}<br>" + label + ": $%{y:,.0f}<extra></extra>",
            ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=10, b=0),
        height=320,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(showgrid=False, zeroline=False),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)",
                   tickprefix="$", tickformat=",.0f", zeroline=False),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No net worth history yet. Record your first snapshot in **Settings**.")

# ── Allocation breakdown ───────────────────────────────────────────────────────
st.subheader("Allocation")

assets = {
    "Investments": summary.get("investment_value", 0),
    "Retirement":  summary.get("retirement_value", 0),
    "Cash":        summary.get("cash_value", 0),
    "Crypto":      summary.get("crypto_value", 0),
    "Real Estate": summary.get("real_estate_value", 0),
}
assets = {k: float(v or 0) for k, v in assets.items() if float(v or 0) > 0}

if assets:
    pie = go.Figure(go.Pie(
        labels=list(assets.keys()),
        values=list(assets.values()),
        hole=0.55,
        marker_colors=["#3b82f6", "#8b5cf6", "#f59e0b", "#f97316", "#10b981"],
        textinfo="label+percent",
        hovertemplate="%{label}<br>$%{value:,.0f}<br>%{percent}<extra></extra>",
    ))
    pie.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        margin=dict(l=0, r=0, t=10, b=10),
        height=280,
    )
    _, mid, _ = st.columns([1, 1.5, 1])
    with mid:
        st.plotly_chart(pie, use_container_width=True)
else:
    st.info("Record a snapshot with values to see the allocation chart.")
