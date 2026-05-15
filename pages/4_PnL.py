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

from services.pnl import compute_pnl, validate_pnl, trace_ticker_fifo
from services.accounts import list_accounts
from services.transactions import list_transactions

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

# ── Open Positions filter ──────────────────────────────────────────────────────
_all_tickers = sorted({b["ticker"] for b in data.get("by_ticker", []) if b.get("ticker")})

# Auto-detect likely open positions: tickers where cost_basis > proceeds
# (user spent more buying than they received selling → still holding)
_auto_open = {
    b["ticker"] for b in data.get("by_ticker", [])
    if b.get("cost_basis", 0) > b.get("proceeds", 0)
}

# Keep whatever the user had previously selected (if it's still in the data).
# On very first load, pre-populate with the auto-detected set.
if "open_tickers" not in st.session_state:
    st.session_state["open_tickers"] = sorted(_auto_open)

_prev_open = [t for t in st.session_state["open_tickers"] if t in _all_tickers]

with st.expander(
    f"📂 Open Positions  —  {len(_prev_open)} ticker(s) marked as still held",
    expanded=bool(_prev_open),
):
    st.caption(
        "Tickers you **still own** are excluded from the Realized P&L totals and "
        "shown in a separate **Open Positions** section below.  "
        "Auto-detected based on BUY > SELL amounts — adjust as needed."
    )
    open_tickers_selected = st.multiselect(
        "Tickers still held",
        options=_all_tickers,
        default=_prev_open,
        placeholder="Type to search / select tickers…",
        label_visibility="collapsed",
    )
    st.session_state["open_tickers"] = open_tickers_selected

open_set = set(st.session_state["open_tickers"])

# Split by_ticker into closed and open buckets
_by_all    = data.get("by_ticker", [])
by_closed  = [b for b in _by_all if b["ticker"] not in open_set]
by_open    = [b for b in _by_all if b["ticker"] in open_set]

# Closed-position KPIs (recomputed from filtered list)
_c_real    = sum(b["realized_gain"]   for b in by_closed)
_c_div     = sum(b["dividend_income"] for b in by_closed)
_c_total   = _c_real + _c_div
_c_inv     = sum(b["cost_basis"]      for b in by_closed)
_c_winners = [b for b in by_closed if b["realized_gain"] > 0]
_c_losers  = [b for b in by_closed if b["realized_gain"] < 0]
_c_scnt    = len(_c_winners) + len(_c_losers)
_c_wrate   = round(len(_c_winners) / _c_scnt * 100, 1) if _c_scnt else 0.0

# ── Validation banner ─────────────────────────────────────────────────────────
if validation.get("has_issues"):
    count    = validation.get("zero_basis_sell_count", 0)
    inflated = validation.get("total_inflated_gain", 0)
    # Escape $ so Streamlit doesn't treat them as LaTeX delimiters.
    inflated_str = fmt_currency(inflated).replace("$", r"\$")
    st.warning(
        f"Data quality issue: {count} sell(s) have a \\$0 cost basis "
        f"— likely missing BUY records from a partial import. "
        f"Estimated inflated gain: {inflated_str}. "
        f"Re-import older transaction history to fix this."
    )

# ── KPIs (closed positions only when open_set is non-empty) ───────────────────
if open_set:
    lbl_sfx = " *(closed)*"
    st.info(
        f"📂 **{len(open_set)} open position(s) excluded:** "
        + ", ".join(f"`{t}`" for t in sorted(open_set))
        + " — see **Open Positions** section below for their cost & dividends."
    )
else:
    lbl_sfx = ""

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric(f"Realized Gain{lbl_sfx}",    fmt_currency(_c_real),
          delta=fmt_pct(_c_real / _c_inv * 100) if _c_inv else None)
k2.metric(f"Dividend Income{lbl_sfx}",  fmt_currency(_c_div))
k3.metric(f"Total Return{lbl_sfx}",     fmt_currency(_c_total),
          delta=fmt_pct(_c_total / _c_inv * 100) if _c_inv else None)
k4.metric("Capital Deployed",           fmt_currency(_c_inv))
k5.metric(f"Win Rate{lbl_sfx}",         f"{_c_wrate:.1f}%",
          delta=f"{len(_c_winners)}W / {len(_c_losers)}L")

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

# ── Per-ticker breakdown (closed positions) ────────────────────────────────────
if not by_closed:
    st.info("No realized P&L events for the selected filters.")
    st.stop()

st.subheader("Breakdown by Ticker" + (" — Closed Positions" if open_set else ""))

df_tk = pd.DataFrame(by_closed)

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

# ── Win / Loss donut (closed positions) ───────────────────────────────────────
wins   = len(_c_winners)
losses = len(_c_losers)
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
    with st.expander("🔍 Why is the cost basis missing? — per-ticker diagnosis", expanded=True):
        affected = validation.get("affected_tickers", [])
        if affected:
            st.markdown(
                "For each affected ticker the table shows how many **BUY** rows vs **SELL** rows "
                "are in your Transactions sheet.  "
                "If **sell qty > buy qty** the missing BUYs were either:\n"
                "- Bought **before your CSV export date range** starts\n"
                "- Received via **ACATS transfer** (mapped as TRANSFER, not BUY — cost basis unknown)\n"
                "- Received via **option exercise / assignment** (OEXCS/OASGN — mapped as TRANSFER)\n\n"
                "**Fix:** export a longer date range from your broker, or manually add the missing BUY rows."
            )
            df_aff = pd.DataFrame(affected)
            # Rename columns for readability
            col_map = {
                "ticker":          "Ticker",
                "buy_rows":        "BUY rows",
                "sell_rows":       "SELL rows",
                "buy_qty":         "BUY shares",
                "sell_qty":        "SELL shares",
                "buy_value":       "BUY value",
                "sell_value":      "SELL value (proceeds)",
                "inflated_gain":   "Phantom gain",
                "first_sell_date": "First zero-basis sell",
                "last_sell_date":  "Last zero-basis sell",
            }
            df_show = df_aff[[c for c in col_map if c in df_aff.columns]].rename(columns=col_map)
            st.dataframe(
                df_show,
                use_container_width=True,
                column_config={
                    "BUY value":            st.column_config.NumberColumn(format="$%.0f"),
                    "SELL value (proceeds)": st.column_config.NumberColumn(format="$%.0f"),
                    "Phantom gain":          st.column_config.NumberColumn(format="$%.0f"),
                },
                hide_index=True,
            )

# ── Open Positions tracker ────────────────────────────────────────────────────
if by_open:
    st.divider()
    st.subheader("📂 Open Positions")
    st.caption(
        "Tickers you marked as still held. "
        "**Net Cost Remaining** = Total Invested − any Partial Proceeds (partial sells). "
        "Unrealized gain requires current market prices — not shown here."
    )

    # Summary KPIs
    _o_inv   = sum(b["cost_basis"]      for b in by_open)
    _o_proc  = sum(b["proceeds"]        for b in by_open)
    _o_net   = _o_inv - _o_proc
    _o_div   = sum(b["dividend_income"] for b in by_open)

    oc1, oc2, oc3, oc4 = st.columns(4)
    oc1.metric("Open Tickers",          len(by_open))
    oc2.metric("Total Invested",        fmt_currency(_o_inv))
    oc3.metric("Net Cost Remaining",    fmt_currency(_o_net),
               help="How much capital is still deployed in these positions.")
    oc4.metric("Dividends Received",    fmt_currency(_o_div))

    # Detail table
    df_open = pd.DataFrame(by_open).copy()
    df_open["net_cost"] = df_open["cost_basis"] - df_open["proceeds"]
    _open_cols = {
        "ticker":          "Ticker",
        "cost_basis":      "Total Invested",
        "proceeds":        "Partial Proceeds",
        "net_cost":        "Net Cost Remaining",
        "dividend_income": "Dividends",
        "realized_gain":   "Partial Realized",   # gain on any shares already sold
    }
    df_open_show = df_open[[c for c in _open_cols if c in df_open.columns]].rename(columns=_open_cols)
    st.dataframe(
        df_open_show,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Total Invested":    st.column_config.NumberColumn(format="$%.0f"),
            "Partial Proceeds":  st.column_config.NumberColumn(format="$%.0f"),
            "Net Cost Remaining":st.column_config.NumberColumn(format="$%.0f"),
            "Dividends":         st.column_config.NumberColumn(format="$%.0f"),
            "Partial Realized":  st.column_config.NumberColumn(format="$%.0f",
                help="Gain/loss on any shares already sold from this position."),
        },
    )

# ── FIFO tracer ───────────────────────────────────────────────────────────────
st.divider()
st.subheader("🔬 FIFO Trace — step-by-step debug for one ticker")
st.caption(
    "Enter any ticker to see every BUY and SELL in date order, "
    "exactly what entered the FIFO queue, what was matched, and what was skipped. "
    "This will show precisely why cost basis looks wrong for a specific stock."
)
trace_col1, trace_col2 = st.columns([2, 1])
with trace_col1:
    trace_ticker = st.text_input("Ticker to trace", placeholder="e.g. AMZN").strip().upper()
with trace_col2:
    st.markdown("<br>", unsafe_allow_html=True)
    run_trace = st.button("🔬 Run FIFO Trace", type="secondary")

if run_trace and not trace_ticker:
    st.warning("Enter a ticker first.")

if run_trace and trace_ticker:
    with st.spinner(f"Tracing FIFO for {trace_ticker}…"):
        try:
            tr = trace_ticker_fifo(
                trace_ticker,
                account_id=st.session_state.get("pnl_account_id"),
            )
        except Exception as e:
            st.error(f"Trace error: {e}")
            tr = None

    if tr:
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Transactions", tr["total_transactions"])
        c2.metric("Total BUY value", f"${tr['total_buy_value']:,.0f}")
        c3.metric("Total proceeds", f"${tr['total_proceeds']:,.0f}")
        c4.metric("Stock gain", f"${tr['stock_gain']:+,.0f}")
        c5.metric("Option P&L", f"${tr['option_pl']:+,.0f}")

        if tr["skipped_zero_qty"]:
            st.error(
                f"⚠️ **{tr['skipped_zero_qty']} BUY rows were SKIPPED** because "
                f"Quantity = 0 and could not be inferred from Amount/Price. "
                f"These rows contribute to the pivot total but NOT to FIFO cost. "
                f"Check the Transactions sheet — those rows need a valid Quantity."
            )

        if tr["remaining_qty"] > 0.001:
            st.info(
                f"After all sells, **{tr['remaining_qty']:.4f} shares** remain "
                f"in the FIFO queue (cost \\${tr['remaining_value']:,.2f}). "
                f"If you have no open positions, these are unmatched BUY lots — "
                f"likely shares transferred out via ACATS or sold by a transaction "
                f"not recorded as SELL (e.g., option assignment)."
            )

        total_pl = tr["total_pl"]
        st.success(
            f"**{trace_ticker} total P&L: \\${total_pl:+,.2f}** "
            f"(stock \\${tr['stock_gain']:+,.2f} + options \\${tr['option_pl']:+,.2f})"
        )

        events_df = pd.DataFrame(tr["events"])
        if not events_df.empty:
            with st.expander("📋 Full transaction trace", expanded=True):
                st.dataframe(events_df, use_container_width=True, height=400, hide_index=True)

# ── Raw Transactions Inspector ─────────────────────────────────────────────────
st.divider()
st.subheader("🗂️ Raw Transactions Inspector")
st.caption(
    "Shows **every row stored in Sheets** for a ticker — including rows marked as "
    "`OTHER` or `DUPLICATE` that P&L ignores.  "
    "Use this to verify that BUY/OPTION_BUY amounts are actually stored correctly "
    "and the ticker field isn't garbled (e.g. a full option contract description "
    "like `AVGO 01/20/2025 200.00 C` instead of just `AVGO`)."
)

raw_col1, raw_col2 = st.columns([2, 1])
with raw_col1:
    raw_ticker = st.text_input("Ticker to inspect", placeholder="e.g. AVGO",
                               key="raw_inspect_ticker").strip().upper()
with raw_col2:
    st.markdown("<br>", unsafe_allow_html=True)
    run_raw = st.button("🗂️ Load Raw Rows", type="secondary")

if run_raw and raw_ticker:
    with st.spinner(f"Loading all rows for {raw_ticker}…"):
        try:
            # list_transactions does exact-match filter on ticker column
            # also pull rows where ticker starts with this symbol (option contracts)
            all_rows = list_transactions(
                account_id=account_id,   # respect the account filter at top
                limit=50000,
            )
            # Manual filter: normalize ticker and match
            import re as _re
            def _norm(t):
                t = str(t).strip()
                if " " not in t:
                    return t.upper()
                first = t.strip().split()[0].upper()
                return first if _re.match(r"^[A-Z]{1,6}(\.[A-Z])?$", first) else t.upper()

            matched = [r for r in all_rows if _norm(r.get("ticker", "")) == raw_ticker]
        except Exception as e:
            st.error(f"Error: {e}")
            matched = []

    if not matched:
        st.info(f"No rows found for **{raw_ticker}** (including partial matches).")
    else:
        df_raw = pd.DataFrame(matched)
        # Show the most useful columns
        _cols = [c for c in ["date", "action", "ticker", "quantity", "price",
                              "total_amount", "fees", "broker", "imported_file"]
                 if c in df_raw.columns]
        df_raw_show = df_raw[_cols].sort_values("date")

        _action_counts = df_raw_show["action"].value_counts().to_dict() if "action" in df_raw_show.columns else {}
        st.markdown(
            f"**{len(matched)} rows** found for `{raw_ticker}`.  "
            + "  ".join(f"`{k}`: {v}" for k, v in sorted(_action_counts.items()))
        )

        # Highlight OTHER rows that are invisible to P&L
        _other_count = _action_counts.get("OTHER", 0)
        if _other_count:
            st.warning(
                f"⚠️ **{_other_count} row(s) stored as `OTHER`** — these are "
                f"excluded from all P&L calculations.  "
                f"They were imported with an unrecognised broker action code.  "
                f"To fix: delete these rows from the Transactions sheet and "
                f"re-import the original CSV (the parser now maps those codes correctly)."
            )

        st.dataframe(
            df_raw_show,
            use_container_width=True,
            height=min(600, 50 + len(df_raw_show) * 35),
            hide_index=True,
            column_config={
                "total_amount": st.column_config.NumberColumn("Amount", format="$%.2f"),
                "quantity":     st.column_config.NumberColumn("Qty",    format="%.4f"),
                "price":        st.column_config.NumberColumn("Price",  format="$%.4f"),
                "fees":         st.column_config.NumberColumn("Fees",   format="$%.2f"),
            },
        )
