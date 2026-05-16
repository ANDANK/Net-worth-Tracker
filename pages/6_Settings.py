"""Settings page — broker management and net worth snapshots."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import streamlit as st

st.set_page_config(page_title="Settings · NetWorth Tracker", page_icon="⚙️", layout="wide")

from utils.auth import require_auth
from utils.fmt import fmt_currency
require_auth()

from services.brokers import list_brokers, add_broker, set_active
from services.networth import record_networth_snapshot
from google_sheets.client import sheets_client

with st.sidebar:
    if st.button("🚪 Sign out", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

# ── Loaders ───────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_brokers():
    return list_brokers(include_inactive=True)

# ── Page ──────────────────────────────────────────────────────────────────────
st.title("⚙️ Settings")

# ════════════════════════════════════════════════════════════════════════════════
# Section 1 — Broker Management
# ════════════════════════════════════════════════════════════════════════════════
st.subheader("Broker List")
st.caption(
    "Stored in the **Brokers** sheet in Google Sheets. "
    "Active brokers appear in Upload and Add Account dropdowns. "
    "You can edit the sheet directly and click Refresh to reload."
)

col_refresh, col_add = st.columns([8, 1.5])
with col_refresh:
    if st.button("🔄 Refresh Brokers"):
        st.cache_data.clear()
        st.rerun()
with col_add:
    if st.button("➕ Add Broker", use_container_width=True):
        st.session_state.show_add_broker = True

# Add broker form
if st.session_state.get("show_add_broker"):
    with st.form("add_broker_form"):
        bc1, bc2 = st.columns(2)
        with bc1:
            new_id   = st.text_input("Broker ID", placeholder="e.g. tdameritrade",
                                      help="Lowercase, no spaces. Must match parser key for CSV import.")
        with bc2:
            new_name = st.text_input("Display Name", placeholder="e.g. TD Ameritrade")
        sub = st.form_submit_button("Add", type="primary")
        can = st.form_submit_button("Cancel")

    if can:
        st.session_state.show_add_broker = False
        st.rerun()
    if sub:
        bid = new_id.strip().lower().replace(" ", "_")
        if not bid or not new_name.strip():
            st.error("Both fields are required.")
        else:
            try:
                add_broker(bid, new_name.strip())
                st.success(f"Broker **{new_name}** added!")
                st.session_state.show_add_broker = False
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

# Broker table
try:
    brokers = load_brokers()
except Exception as e:
    st.error(f"Could not load brokers: {e}")
    brokers = []

KNOWN_PARSERS = {"robinhood", "schwab", "fidelity", "vanguard", "webull", "etrade"}

if brokers:
    for b in brokers:
        c1, c2, c3, c4 = st.columns([2.5, 2, 1.5, 1])
        with c1:
            has_parser = b["id"] in KNOWN_PARSERS
            parser_tag = "" if has_parser else " ⚠️ *no parser*"
            st.markdown(f"**{b['name']}**{parser_tag}")
        with c2:
            st.caption(b["id"])
        with c3:
            status = "🟢 Active" if b.get("active") else "⚫ Inactive"
            st.caption(status)
        with c4:
            label = "Deactivate" if b.get("active") else "Activate"
            if st.button(label, key=f"tog_{b['id']}"):
                try:
                    set_active(b["id"], not b.get("active"))
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
        st.divider()
else:
    st.info("No brokers found. The sheet will be seeded automatically on next load.")

st.caption("⚠️ No parser = broker can be tracked manually but CSV import is not supported.")

# ════════════════════════════════════════════════════════════════════════════════
# Section 2 — Net Worth Snapshot
# ════════════════════════════════════════════════════════════════════════════════
st.divider()
st.subheader("Record Net Worth Snapshot")
st.caption("Manually record today's values to build your net worth history chart.")

with st.form("snapshot_form"):
    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        inv   = st.number_input("Investments ($)",  min_value=0.0, step=1_000.0, format="%.0f")
        ret   = st.number_input("Retirement ($)",   min_value=0.0, step=1_000.0, format="%.0f")
    with sc2:
        cash  = st.number_input("Cash ($)",         min_value=0.0, step=1_000.0, format="%.0f")
        crypto = st.number_input("Crypto ($)",      min_value=0.0, step=100.0,   format="%.0f")
    with sc3:
        realestate = st.number_input("Real Estate ($)", min_value=0.0, step=10_000.0, format="%.0f")
        liabilities = st.number_input("Liabilities ($)", min_value=0.0, step=1_000.0, format="%.0f")

    total_assets = inv + ret + cash + crypto + realestate
    st.info(f"Net Worth preview: **{fmt_currency(total_assets - liabilities)}** "
            f"(Assets: {fmt_currency(total_assets)} − Liabilities: {fmt_currency(liabilities)})")

    save_snap = st.form_submit_button("💾 Save Snapshot", type="primary")

if save_snap:
    try:
        record_networth_snapshot(
            investment_value=inv,
            retirement_value=ret,
            cash_value=cash,
            crypto_value=crypto,
            real_estate_value=realestate,
            liabilities=liabilities,
        )
        st.success("✅ Snapshot saved to Google Sheets! Refresh the Dashboard to see it.")
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Could not save: {e}")

# ════════════════════════════════════════════════════════════════════════════════
# Section 3 — Sheet Formatting
# ════════════════════════════════════════════════════════════════════════════════
st.divider()
st.subheader("Format Transactions Sheet")
st.caption(
    "Apply colour-coding and a frozen header to the **Transactions** tab in Google Sheets "
    "so you can validate records at a glance. "
    "Rows are coloured by action type: "
    "🟢 BUY · 🔴 SELL · 🟡 DIVIDEND/INTEREST · 🔵 DEPOSIT · 🟠 WITHDRAWAL · "
    "🟣 OTHER · ⬛ DUPLICATE. "
    "Safe to run multiple times — existing data is not changed."
)

if st.button("🎨 Apply Formatting to Transactions Sheet", type="primary"):
    with st.spinner("Applying formatting via Sheets API…"):
        try:
            result = sheets_client.format_transactions_sheet()
            st.success(
                "✅ Transactions sheet formatted! Open Google Sheets to see the changes. "
                "Conditional colours, frozen header row, and auto-resized columns applied."
            )
        except Exception as e:
            st.error(f"Formatting failed: {e}")

# ════════════════════════════════════════════════════════════════════════════════
# Section 4 — About
# ════════════════════════════════════════════════════════════════════════════════
st.divider()
st.subheader("About")
st.markdown("""
**NetWorth Tracker v2.0** · Streamlit Edition
Data stored in Google Sheets · Deployed on Streamlit Cloud

Credentials are stored in `.streamlit/secrets.toml` (local) or the Streamlit Cloud secrets UI — never committed to git.
""")
