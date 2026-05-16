"""Upload page — import broker CSV/XLSX with full pre-import diagnostics."""
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
@st.cache_data(ttl=600)
def load_accounts():
    return list_accounts()

@st.cache_data(ttl=600)
def load_brokers():
    return list_brokers(include_inactive=False)

# ── Page header ───────────────────────────────────────────────────────────────
st.title("📤 Upload Transactions")
st.caption("Upload a broker CSV or XLSX — see exactly what will be imported, "
           "what becomes OTHER, and any issues, before touching Google Sheets.")

# ── Step 1 ────────────────────────────────────────────────────────────────────
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
    st.warning("No active accounts. Add one on the Accounts page first.")
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
    account_id     = active_accounts[account_labels.index(
                         st.selectbox("Account", account_labels))]["account_id"]

# ── Step 2 ────────────────────────────────────────────────────────────────────
st.subheader("Step 2 — Upload file")
uploaded = st.file_uploader("CSV or XLSX", type=["csv", "xlsx"],
                             label_visibility="collapsed")
if not uploaded:
    st.info("Waiting for file…")
    st.stop()

file_bytes = uploaded.read()

# ── Step 3 — Full diagnosis ───────────────────────────────────────────────────
st.subheader("Step 3 — Pre-import analysis")

with st.spinner("Analysing file…"):
    diag = diagnose_file(file_bytes, uploaded.name, broker_id, account_id)

if "error" in diag:
    st.error(f"❌ {diag['error']}")
    st.stop()

if not diag.get("sheets_connected"):
    st.warning("⚠️ Could not reach Google Sheets for duplicate check — "
               "duplicate detection disabled for this session.")

total        = diag.get("total_rows_in_file", 0)
parsed       = diag.get("parsed_count", 0)
will_imp     = diag.get("would_import", 0)
dup_upload   = diag.get("duplicate_upload", 0)
other_count  = diag.get("other_count", 0)
blank_skip   = diag.get("skipped_blank", 0)
parse_errors = diag.get("parse_errors", [])
other_acts   = diag.get("other_actions", {})
rec_acts     = diag.get("recognised_actions", {})

total_to_write = will_imp + dup_upload + other_count

# ── Sheets-connection notice ───────────────────────────────────────────────────
if not diag.get("sheets_connected"):
    st.warning(
        "Google Sheets could not be reached — duplicate detection is disabled. "
        "All rows will be treated as new."
    )

# ── Summary metrics ───────────────────────────────────────────────────────────
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Rows in file",            total)
m2.metric("✅ New (financial)",       will_imp,
          help="New financial transactions — imported normally")
m3.metric("🟡 DUPLICATE",            dup_upload,
          help="Already in Google Sheets — uploaded again with action=DUPLICATE for your audit trail")
m4.metric("🔵 OTHER",                other_count,
          help="Unrecognised action codes — uploaded as OTHER for manual review, excluded from P&L")
m5.metric("🚫 Blank / parse errors", blank_skip + len(parse_errors),
          help="Blank/header rows and rows that threw a parse exception — not uploaded")

# ── Issues / info panels ──────────────────────────────────────────────────────
if dup_upload:
    with st.expander(f"🟡 {dup_upload} DUPLICATE rows — uploaded for audit trail", expanded=False):
        st.caption(
            "These rows already exist in Google Sheets (same transaction ID). "
            "They will be uploaded again with **action = DUPLICATE** so you can spot "
            "re-imports in the Transactions sheet. They are **excluded from P&L and net worth**."
        )

# OTHER action codes
if other_acts:
    with st.expander(
        f"🔵 {other_count} rows have unrecognised action codes → uploaded as **OTHER**",
        expanded=True,
    ):
        st.caption(
            "These rows will be uploaded with action = **OTHER** so you can review them "
            "in Google Sheets. They are **excluded from P&L and net worth calculations**. "
            "If any of these are real trades that should be recognised, share the code "
            "and I will add parser support."
        )
        df_other = pd.DataFrame([
            {"Action Code": k, "Rows": v, "Will be": "🔵 OTHER (uploaded, not in P&L)"}
            for k, v in sorted(other_acts.items(), key=lambda x: -x[1])
        ])
        st.dataframe(df_other, use_container_width=True, hide_index=True)

# Per-row parse exceptions
if parse_errors:
    with st.expander(
        f"💥 {len(parse_errors)} rows caused parse errors → skipped entirely",
        expanded=True,
    ):
        st.caption(
            "These rows threw an exception during parsing and were completely skipped. "
            "They are NOT uploaded. Fix the data or report the error."
        )
        df_err = pd.DataFrame(parse_errors)
        st.dataframe(df_err, use_container_width=True, hide_index=True)

# ── Recognised breakdown ─────────────────────────────────────────────────────
if rec_acts:
    with st.expander("✅ Recognised action codes (will be imported)"):
        df_rec = pd.DataFrame([
            {"Action Code": k, "Rows": v}
            for k, v in sorted(rec_acts.items(), key=lambda x: -x[1])
        ])
        st.dataframe(df_rec, use_container_width=True, hide_index=True)

# ── By type breakdown ─────────────────────────────────────────────────────────
by_action = diag.get("parsed_by_action", {})
if by_action:
    with st.expander("📊 Breakdown by transaction type"):
        df_act = pd.DataFrame([
            {"Type": k, "Count": v}
            for k, v in sorted(by_action.items(), key=lambda x: -x[1])
        ])
        st.dataframe(df_act, use_container_width=True, hide_index=True)

# ── Row preview ───────────────────────────────────────────────────────────────
with st.expander("🔍 Preview first 50 parsed rows"):
    try:
        preview_rows = preview_file(file_bytes, uploaded.name, broker_id, account_id)
        if preview_rows:
            df_prev = pd.DataFrame(preview_rows)
            show_cols = [c for c in ["date", "ticker", "action", "quantity",
                                      "price", "total_amount", "fees"] if c in df_prev.columns]
            st.dataframe(df_prev[show_cols].head(50), use_container_width=True, height=260)
        else:
            st.info("No rows parsed.")
    except Exception as e:
        st.warning(f"Preview error: {e}")

# ── Step 4 — Import ───────────────────────────────────────────────────────────
st.subheader("Step 4 — Import to Google Sheets")
st.markdown("---")

if total_to_write == 0:
    st.info("Nothing to upload — all rows are blank or caused parse errors.")
else:
    label_parts = []
    if will_imp:    label_parts.append(f"{will_imp} new financial")
    if dup_upload:  label_parts.append(f"{dup_upload} DUPLICATE")
    if other_count: label_parts.append(f"{other_count} OTHER")

    st.caption(
        f"Will write approximately **{total_to_write} rows** to Google Sheets: "
        f"{' · '.join(label_parts)}. "
        "DUPLICATE and OTHER rows are excluded from P&L and net worth. "
        "_Note: the duplicate count is an estimate — the actual count at upload time "
        "may differ slightly if the sheet changed between analysis and import._"
    )

    if st.button(f"✅ Upload {total_to_write} rows to Google Sheets", type="primary"):
        with st.spinner(f"Writing {total_to_write} rows (chunked — may take a moment)…"):
            try:
                result = import_file(file_bytes, uploaded.name, broker_id, account_id)
            except Exception as e:
                st.error(f"Upload failed: {e}")
                st.stop()

        if result.errors:
            st.error(f"Upload finished with errors:\n{chr(10).join(result.error_details)}")
        else:
            parts = [f"**{result.imported}** new financial rows"]
            if result.duplicate_uploaded:
                parts.append(f"**{result.duplicate_uploaded}** DUPLICATE rows")
            st.success(f"✅ **Done!** Uploaded {' · '.join(parts)}")

            if parse_errors:
                st.warning(
                    f"⚠️ {len(parse_errors)} rows were NOT uploaded due to parse errors. "
                    "See Issues panel above."
                )
            if other_count:
                st.info(
                    f"🔵 {other_count} OTHER rows uploaded — visible in Google Sheets "
                    "with action = OTHER for your review."
                )
            st.cache_data.clear()
