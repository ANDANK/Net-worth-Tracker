"""Transactions page — browse and filter all imported transactions."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import streamlit as st
import pandas as pd

st.set_page_config(page_title="Transactions · NetWorth Tracker", page_icon="📋", layout="wide")

from utils.auth import require_auth
from utils.fmt import fmt_currency
require_auth()

from services.transactions import list_transactions
from services.accounts import list_accounts

with st.sidebar:
    if st.button("🚪 Sign out", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

@st.cache_data(ttl=120)
def load_accounts():
    return list_accounts()

# ── Filters ───────────────────────────────────────────────────────────────────
st.title("📋 Transactions")

try:
    accounts = load_accounts()
except Exception as e:
    st.error(f"Could not load accounts: {e}")
    accounts = []

col1, col2, col3, col4 = st.columns([2, 2, 1.5, 1])
with col1:
    account_options = {"All accounts": None}
    account_options.update({
        f"{a['account_name']} ({a['broker_name']})": a["account_id"]
        for a in accounts
    })
    acc_label  = st.selectbox("Account", list(account_options.keys()))
    account_id = account_options[acc_label]

with col2:
    ticker_filter = st.text_input("Ticker", placeholder="e.g. AAPL").strip().upper() or None

with col3:
    period = st.selectbox("Period", ["All", "Last 30 days", "Last 90 days", "This year"])

with col4:
    limit = st.selectbox("Show", [200, 500, 1000, 5000], index=0)

# Derive date filters from period
from datetime import date, timedelta
today = date.today()
start_date = None
if period == "Last 30 days":
    start_date = (today - timedelta(days=30)).isoformat()
elif period == "Last 90 days":
    start_date = (today - timedelta(days=90)).isoformat()
elif period == "This year":
    start_date = f"{today.year}-01-01"

if st.button("🔄 Refresh"):
    st.cache_data.clear()
    st.rerun()

# ── Load transactions ─────────────────────────────────────────────────────────
with st.spinner("Loading transactions…"):
    try:
        txs = list_transactions(
            account_id=account_id,
            ticker=ticker_filter,
            start_date=start_date,
            limit=limit,
        )
    except Exception as e:
        st.error(f"Could not load transactions: {e}")
        st.stop()

st.caption(f"Showing **{len(txs)}** transactions")

if not txs:
    st.info("No transactions found for the selected filters.")
    st.stop()

# ── Display ───────────────────────────────────────────────────────────────────
df = pd.DataFrame(txs)

# Format for display
display_cols = [c for c in ["date", "ticker", "action", "quantity", "price", "total_amount",
                              "fees", "broker", "account_id"] if c in df.columns]
df_show = df[display_cols].copy()

if "total_amount" in df_show.columns:
    df_show["total_amount"] = pd.to_numeric(df_show["total_amount"], errors="coerce")
if "price" in df_show.columns:
    df_show["price"] = pd.to_numeric(df_show["price"], errors="coerce")
if "quantity" in df_show.columns:
    df_show["quantity"] = pd.to_numeric(df_show["quantity"], errors="coerce")

# Colour-code action column
action_colors = {
    "BUY": "🟢", "SELL": "🔴", "DIVIDEND": "💛",
    "INTEREST": "💛", "DEPOSIT": "🔵", "WITHDRAWAL": "🟠",
    "TRANSFER": "⚪", "OPTION_BUY": "🟢", "OPTION_SELL": "🔴",
}

if "action" in df_show.columns:
    df_show["action"] = df_show["action"].apply(
        lambda a: f"{action_colors.get(a, '⚪')} {a}"
    )

st.dataframe(
    df_show,
    use_container_width=True,
    height=550,
    column_config={
        "date":         st.column_config.TextColumn("Date"),
        "ticker":       st.column_config.TextColumn("Ticker"),
        "action":       st.column_config.TextColumn("Action"),
        "quantity":     st.column_config.NumberColumn("Qty",    format="%.4f"),
        "price":        st.column_config.NumberColumn("Price",  format="$%.4f"),
        "total_amount": st.column_config.NumberColumn("Total",  format="$%.2f"),
        "fees":         st.column_config.NumberColumn("Fees",   format="$%.2f"),
    },
)

# ── Summary strip ─────────────────────────────────────────────────────────────
num = pd.to_numeric(df.get("total_amount", pd.Series(dtype=float)), errors="coerce").fillna(0)
buys  = df[df.get("action", pd.Series()) == "BUY"] if "action" in df.columns else pd.DataFrame()
sells = df[df.get("action", pd.Series()) == "SELL"] if "action" in df.columns else pd.DataFrame()

st.divider()
mc1, mc2, mc3, mc4 = st.columns(4)
mc1.metric("Total rows", len(txs))
mc2.metric("Buy txns",   len(buys))
mc3.metric("Sell txns",  len(sells))
mc4.metric("Tickers",    df["ticker"].nunique() if "ticker" in df.columns else 0)
