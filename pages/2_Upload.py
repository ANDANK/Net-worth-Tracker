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
from services.transactions import import_file, preview_file, diagnose_file

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

# ── Step 1: broker + account ──────────────────────────────────────────────────
st.subheader("Step 1 — Select broker & account")

try:
    brokers  = load_brokers()
    accounts = load_accounts()
except Exception as e:
    st.error(f"Could not load data: {e}")
    st.stop()

active_accounts = [a for a in accounts
                   if str(a.get("active", "TRUE")).upper() in ("TRUE", "1", "YES")]
if not active_accounts:
    st.warning("No active accounts. Add an account first on the Accounts page.")
    st.stop()

broker_names = [b["name"] for b in brokers] if brokers else []
broker_ids   = [b["id"]   for b in brokers] if brokers else []

col1, col2 = st.columns(2)
with col1:
    if broker_names:
        broker_label = st.selectbox("Broker", broker_names)
        broker_id    = broker_ids[broker_names.index(broker_label)]
    else:
        broker_id = st.text_input("Broker ID", placeholder="e.g. robinhood").strip().lower()

with col2:
    account_labels = [f"{a['account_name']} ({a['broker_name']})" for a in active_accounts]
    account_choice = st.selectbox("Account", account_labels)
    account_id     = active_accounts[account_labels.index(account_choice)]["account_id"]

# ── Step 2: file upload ───────────────────────────────────────────────────────
st.subheader("Step 2 — Upload file")
uploaded = st.file_uploader("Choose CSV or XLSX", type=["csv", "xlsx"],
                             label_visibility="collapsed")
if not uploaded:
    st.info("Waiting for file…")
    st.stop()

file_bytes = uploaded.read()

# ── Step 3: Diagnose BEFORE importing ─────────────────────────────────────────
st.subheader("Step 3 — File analysis")

with st.spinner("Analysing file…"):
    diag = diagnose_file(file_bytes, uploaded.name, broker_id, account_id)

if "error" in diag:
    st.error(diag["error"])
    st.stop()

total      = diag.get("total_rows_in_file", 0)
parsed     = diag.get("parsed_count", 0)
will_imp   = diag.get("would_import", 0)
will_dup   = diag.get("would_skip_duplicates", 0)
unrec_skip = diag.get("skipped_unrecognised_action", 0)

# Summary metrics
m1, m2, m3, m4 = st.columns(4)
m1.metric("Rows in file",           total)
m2.metric("Parsed (recognised)",    parsed,
          delta=f"-{unrec_skip} unrecognised" if unrec_skip else None,
          delta_color="off" if unrec_skip else "normal")
m3.metric("Will import (new)",      will_imp)
m4.metric("Will skip (duplicates)", will_dup,
          delta="already in sheet" if will_dup else None,
          delta_color="off")

# ── Unrecognised action codes ─────────────────────────────────────────────────
unrec = diag.get("unrecognised_actions", {})
if unrec:
    with st.expander(f"⚠️ {unrec_skip} rows will be DROPPED — unrecognised action codes", expanded=True):
        st.caption(
            "These action codes exist in your file but the parser doesn't know what they mean. "
            "Those rows won't be imported. If they are trades, let me know the code and I'll add support."
        )
        df_unrec = pd.DataFrame(
            [{"Action Code": k, "Row Count": v, "Status": "❌ Not imported"} for k, v in unrec.items()]
        ).sort_values("Row Count", ascending=False)
        st.dataframe(df_unrec, use_container_width=True, hide_index=True)

# ── Recognised action codes ───────────────────────────────────────────────────
rec = diag.get("recognised_actions", {})
if rec:
    with st.expander("✅ Recognised action codes (will be imported)"):
        df_rec = pd.DataFrame(
            [{"Action Code": k, "Row Count": v} for k, v in rec.items()]
        ).sort_values("Row Count", ascending=False)
        st.dataframe(df_rec, use_container_width=True, hide_index=True)

# ── By action type (parsed breakdown) ────────────────────────────────────────
by_action = diag.get("parsed_by_action", {})
if by_action:
    with st.expander("📊 Parsed breakdown by transaction type"):
        df_act = pd.DataFrame(
            [{"Type": k.replace("TransactionType.", ""), "Count": v}
             for k, v in by_action.items()]
        ).sort_values("Count", ascending=False)
        st.dataframe(df_act, use_container_width=True, hide_index=True)

# ── Preview rows ─────────────────────────────────────────────────────────────
with st.expander("🔍 Preview parsed rows (first 50)"):
    preview_rows = preview_file(file_bytes, uploaded.name, broker_id, account_id)
    if preview_rows:
        df_prev = pd.DataFrame(preview_rows)
        show_cols = [c for c in ["date", "ticker", "action", "quantity", "price",
                                  "total_amount", "fees"] if c in df_prev.columns]
        st.dataframe(df_prev[show_cols].head(50), use_container_width=True, height=260)
    else:
        st.info("No rows parsed.")

# ── Step 4: Import ────────────────────────────────────────────────────────────
st.subheader("Step 4 — Import to Google Sheets")

if will_imp == 0 and will_dup > 0:
    st.info(f"All {will_dup} parsed rows already exist in the sheet — nothing new to import.")
elif will_imp == 0:
    st.warning("Nothing to import. Check the unrecognised action codes above.")
else:
    st.caption(f"Ready to import **{will_imp}** new transactions. "
               f"{will_dup} duplicates will be skipped automatically.")

    if st.button(f"✅ Import {will_imp} transactions", type="primary"):
        with st.spinner(f"Writing {will_imp} rows to Google Sheets (chunked — may take a moment)…"):
            try:
                result = import_file(file_bytes, uploaded.name, broker_id, account_id)
            except Exception as e:
                st.error(f"Import failed: {e}")
                st.stop()

        if result.errors:
            st.error(f"Import finished with errors: {result.error_details}")
        else:
            st.success(
                f"✅ **Done!**  "
                f"Imported **{result.imported}** new transactions · "
                f"Skipped **{result.skipped_duplicates}** duplicates"
            )
            if unrec_skip:
                st.warning(
                    f"⚠️ **{unrec_skip} rows were NOT imported** because their action codes "
                    f"are unrecognised by the parser. See the breakdown above for details."
                )
            st.cache_data.clear()
