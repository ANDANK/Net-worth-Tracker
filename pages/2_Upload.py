"""Upload page — import broker CSV/XLSX files into Google Sheets."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import streamlit as st
import pandas as pd

st.set_page_config(page_title="Upload · NetWorth Tracker", page_icon="📤", layout="wide")

from utils.auth import require_auth
require_auth()

from services.accounts import list_accounts
from services.brokers import list_brokers
from services.transactions import import_file, preview_file

with st.sidebar:
    if st.button("🚪 Sign out", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

# ── Loaders ───────────────────────────────────────────────────────────────────
@st.cache_data(ttl=120)
def load_accounts():
    return list_accounts()

@st.cache_data(ttl=300)
def load_brokers():
    return list_brokers(include_inactive=False)

# ── Page ──────────────────────────────────────────────────────────────────────
st.title("📤 Upload Transactions")
st.caption("Upload a broker CSV or XLSX export — duplicates are detected automatically.")

# ── Step 1: pick broker + account ─────────────────────────────────────────────
st.subheader("Step 1 — Select broker & account")

try:
    brokers = load_brokers()
    accounts = load_accounts()
except Exception as e:
    st.error(f"Could not load data: {e}")
    st.stop()

active_accounts = [a for a in accounts if str(a.get("active", "TRUE")).upper() in ("TRUE", "1", "YES")]

if not active_accounts:
    st.warning("No active accounts. Add an account first.")
    st.stop()

broker_names = [b["name"] for b in brokers] if brokers else []
broker_ids   = [b["id"]   for b in brokers] if brokers else []

col1, col2 = st.columns(2)
with col1:
    if broker_names:
        broker_label = st.selectbox("Broker", broker_names)
        broker_id    = broker_ids[broker_names.index(broker_label)] if broker_label in broker_names else broker_label.lower()
    else:
        broker_id = st.text_input("Broker ID", placeholder="e.g. robinhood").strip().lower()

with col2:
    account_labels = [f"{a['account_name']} ({a['broker_name']})" for a in active_accounts]
    account_choice = st.selectbox("Account", account_labels)
    account_idx    = account_labels.index(account_choice)
    account_id     = active_accounts[account_idx]["account_id"]

# ── Step 2: upload file ───────────────────────────────────────────────────────
st.subheader("Step 2 — Upload file")
uploaded = st.file_uploader("Choose CSV or XLSX", type=["csv", "xlsx"],
                             label_visibility="collapsed")

if not uploaded:
    st.info("Waiting for file…")
    st.stop()

file_bytes = uploaded.read()

# ── Step 3: preview ───────────────────────────────────────────────────────────
st.subheader("Step 3 — Preview parsed rows")

with st.spinner("Parsing file…"):
    try:
        preview_rows = preview_file(file_bytes, uploaded.name, broker_id, account_id)
    except Exception as e:
        st.error(f"Parse error: {e}")
        st.stop()

if not preview_rows:
    st.error("No rows could be parsed. Check that you selected the correct broker.")
    st.stop()

st.success(f"Parsed **{len(preview_rows)}** transactions from `{uploaded.name}`")

df_prev = pd.DataFrame(preview_rows)
show_cols = [c for c in ["date", "ticker", "action", "quantity", "price", "total_amount", "fees"] if c in df_prev.columns]
st.dataframe(df_prev[show_cols].head(50), use_container_width=True, height=280)
if len(preview_rows) > 50:
    st.caption(f"Showing first 50 of {len(preview_rows)} rows.")

# ── Step 4: import ────────────────────────────────────────────────────────────
st.subheader("Step 4 — Import to Google Sheets")
st.caption("Duplicates (same transaction ID) are automatically skipped.")

if st.button("✅ Import now", type="primary", use_container_width=False):
    with st.spinner(f"Writing {len(preview_rows)} rows to Google Sheets (chunked — may take a moment)…"):
        try:
            result = import_file(file_bytes, uploaded.name, broker_id, account_id)
        except Exception as e:
            st.error(f"Import failed: {e}")
            st.stop()

    if result.errors:
        st.error(f"Import finished with errors: {result.error_details}")
    else:
        st.success(
            f"**Done!** Imported **{result.imported}** new transactions · "
            f"Skipped **{result.skipped_duplicates}** duplicates"
        )
        st.cache_data.clear()
