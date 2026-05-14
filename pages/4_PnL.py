"""P&L page — realized gains, dividends, FIFO breakdown with charts."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(page_title="P&L · NetWorth Tracker", page_icon="📈", layout="wide")

from utils.auth import require_auth
from utils.fmt import fmt_currency, fmt_pct
require_auth()

from services.pnl import compute_pnl, validate_pnl
from services.accounts import list_accounts

with st.sidebar:
    if st.button("🚪 Sign out", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

@st.cache_data(ttl=120)
def load_accounts():
    return list_accounts()

# ── Filters ───────────────────────────────────────────────────────────────────
st.title("📈 Profit & Loss")

try:
    accounts = load_accounts()
except Exception as e:
    accounts = []

col1, col2, col3, col_btn = st.columns([2.5, 1.5, 2, 0.8])

with col1:
    account_options = {"All accounts": None}
    account_options.update({
        f"{a['account_name']} ({a['broker_name']})": a["account_id"]
        for a in accounts
    })
    acc_label  = st.selectbox("Account", list(account_options.keys()), label_visibility="visible")
    account_id = account_options[acc_label]

with col2:
    period = st.selectbox("Period", ["all", "1m", "3m", "6m", "1y", "3y", "5y"],
                           format_func=lambda x: {
                               "all": "All time", "1m": "1 Month", "3m": "3 Months",
                               "6m": "6 Months", "1y": "1 Year", "3y": "3 Years", "5y": "5 Years"
                           }.get(x, x))

with col3:
    ticker_filter = st.text_input("Filter by ticker", placeholder="e.g. AAPL (optional)").strip().upper() or None

with col_btn:
    st.markdown("<br>", unsafe_allow_html=True)
    run = st.button("Run", type="primary", use_container_width=True)

if not run and "pnl_data" not in st.session_state:
    st.info("Select filters and click **Run** to compute P&L.")
    st.stop()

if run:
    with st.spinner("Computing P&L (FIFO cost basis)…"):
        try:
            data = compute_pnl(account_id=account_id, period=period, ticker=ticker_filter)
            validation = validate_pnl(account_id=account_id)
            st.session_state["pnl_data"] = data
            st.session_state["pnl_val"]  = validation
            st.session_state["pnl_ticker"] = ticker_filter
        except Exception as e:
            st.error(f"Error computing P&L: {e}")
            st.stop()

data       = st.session_state["pnl_data"]
validation = st.session_state["pnl_val"]

# ── Validation banner ─────────────────────────────────────────────────────────
if validation.get("has_issues"):
    count   = validation.get("zero_basis_sell_count", 0)
    inflated = validation.get("total_inflated_gain", 0)
    st.warning(
        f"⚠️ **Data quality issue:** {count} sell(s) have a $0 cost basis "
        f"— likely missing BUY records from a partial import. "
        f"Estimated inflated gain: **{fmt_currency(inflated)}**. "
        f"Re-import older transaction history to fix this.",
        icon="⚠️",
    )

# ── KPIs ──────────────────────────────────────────────────────────────────────
k1, k2, k3, k4, k5 = st.columns(5)
total_r = data.get("total_realized", 0)
total_d = data.get("total_dividends", 0)
total   = data.get("total_return", 0)
invested = data.get("total_invested", 0)
win_rate = data.get("win_rate", 0)

k1.metric("Realized Gain",     fmt_currency(total_r), delta=fmt_pct(total_r / invested * 100) if invested else None)
k2.metric("Dividend Income",   fmt_currency(total_d))
k3.metric("Total Return",      fmt_currency(total),   delta=fmt_pct(total / invested * 100) if invested else None)
k4.metric("Capital Deployed",  fmt_currency(invested))
k5.metric("Win Rate",          f"{win_rate:.1f}%",
          delta=f"{data.get('win_count',0)}W / {data.get('loss_count',0)}L")

st.divider()

# ── Timeline chart ────────────────────────────────────────────────────────────
timeline = data.get("timeline", [])
if timeline:
    st.subheader("Cumulative P&L Over Time")
    df_t = pd.DataFrame(timeline)
    df_t["date"] = pd.to_datetime(df_t["date"])

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_t["date"], y=df_t["total"],
        name="Total Return", fill="tozeroy",
        line=dict(color="#3b82f6", width=2),
        fillcolor="rgba(59,130,246,0.12)",
        hovertemplate="%{x|%b %d, %Y}<br>Total: $%{y:,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=df_t["date"], y=df_t["realized"],
        name="Realized Gains", line=dict(color="#10b981", width=1.5, dash="dot"),
        hovertemplate="%{x|%b %d, %Y}<br>Realized: $%{y:,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=df_t["date"], y=df_t["dividends"],
        name="Dividends", line=dict(color="#f59e0b", width=1.5, dash="dot"),
        hovertemplate="%{x|%b %d, %Y}<br>Dividends: $%{y:,.0f}<extra></extra>",
    ))
    fig.add_hline(y=0, line_dash="solid", line_color="rgba(255,255,255,0.15)")
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=10, b=0), height=280,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)",
                   tickprefix="$", tickformat=",.0f", zeroline=False),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)

# ── Per-ticker breakdown ───────────────────────────────────────────────────────
by_ticker = data.get("by_ticker", [])
if not by_ticker:
    st.info("No realized P&L events for the selected filters.")
    st.stop()

st.subheader("Breakdown by Ticker")

df_tk = pd.DataFrame(by_ticker)

# Side-by-side: bar chart + table
chart_col, table_col = st.columns([1.2, 1])

with chart_col:
    top15 = df_tk.head(15).copy()
    top15["color"] = top15["total_return"].apply(
        lambda v: "#10b981" if v >= 0 else "#ef4444"
    )
    bar = go.Figure(go.Bar(
        x=top15["total_return"],
        y=top15["ticker"],
        orientation="h",
        marker_color=top15["color"],
        text=top15["total_return"].apply(lambda v: fmt_currency(v)),
        textposition="outside",
        hovertemplate="%{y}<br>Total: $%{x:,.0f}<extra></extra>",
    ))
    bar.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=60, t=10, b=0),
        height=max(280, len(top15) * 26 + 40),
        xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)",
                   tickprefix="$", tickformat=",.0f"),
        yaxis=dict(showgrid=False, autorange="reversed"),
    )
    st.plotly_chart(bar, use_container_width=True)

with table_col:
    df_show = df_tk[["ticker", "realized_gain", "dividend_income",
                      "total_return", "proceeds", "cost_basis"]].copy()
    df_show.columns = ["Ticker", "Realized", "Dividends", "Total", "Proceeds", "Cost Basis"]
    st.dataframe(
        df_show,
        use_container_width=True,
        height=400,
        column_config={
            "Realized":   st.column_config.NumberColumn(format="$%.0f"),
            "Dividends":  st.column_config.NumberColumn(format="$%.0f"),
            "Total":      st.column_config.NumberColumn(format="$%.0f"),
            "Proceeds":   st.column_config.NumberColumn(format="$%.0f"),
            "Cost Basis": st.column_config.NumberColumn(format="$%.0f"),
        },
    )

# ── Win / Loss donut ──────────────────────────────────────────────────────────
wins   = data.get("win_count", 0)
losses = data.get("loss_count", 0)
if wins + losses > 0:
    st.subheader("Win / Loss Split")
    donut = go.Figure(go.Pie(
        labels=["Winners", "Losers"],
        values=[wins, losses],
        hole=0.6,
        marker_colors=["#10b981", "#ef4444"],
        textinfo="label+value",
        hovertemplate="%{label}: %{value}<extra></extra>",
    ))
    donut.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        margin=dict(l=0, r=0, t=10, b=10),
        height=220,
    )
    _, mid, _ = st.columns([1, 1, 1])
    with mid:
        st.plotly_chart(donut, use_container_width=True)

# ── Zero-basis detail ─────────────────────────────────────────────────────────
if validation.get("has_issues"):
    with st.expander("🔍 Zero-basis sells detail"):
        affected = validation.get("affected_tickers", [])
        if affected:
            st.dataframe(pd.DataFrame(affected), use_container_width=True)
