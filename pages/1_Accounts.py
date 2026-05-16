"""Accounts page — list, add brokerage accounts and manual entries."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import streamlit as st

st.set_page_config(page_title="Accounts · NetWorth Tracker", page_icon="🏦", layout="wide")

from utils.auth import require_auth
from utils.fmt import fmt_currency

require_auth()

from services.accounts import list_accounts, create_account, deactivate_account
from services.manual_accounts import list_manual_accounts, add_manual_entry
from services.brokers import list_brokers
from models.schemas import AccountCreate, ManualAccountCreate

# ── Human-readable labels ──────────────────────────────────────────────────────
_ACCT_TYPE_LABELS = {
    "brokerage":       "Brokerage",
    "roth_ira":        "Roth IRA",
    "traditional_ira": "Traditional IRA",
    "401k":            "401(k)",
    "roth_401k":       "Roth 401(k)",
    "solo_401k":       "Solo 401(k)",
    "sep_ira":         "SEP IRA",
    "hsa":             "HSA",
    "fsa":             "FSA",
    "crypto":          "Crypto",
    "savings":         "Savings",
    "checking":        "Checking",
    "treasury":        "Treasury",
    "cd":              "CD",
    "real_estate":     "Real Estate",
}
_OWNER_LABELS  = {"self": "Self", "spouse": "Spouse", "joint": "Joint"}
_TAX_LABELS    = {"taxable": "Taxable", "tax_deferred": "Tax-Deferred", "tax_free": "Tax-Free"}

def _fmt_acct(v):  return _ACCT_TYPE_LABELS.get(v, v.replace("_", " ").title())
def _fmt_owner(v): return _OWNER_LABELS.get(v, v.title())
def _fmt_tax(v):   return _TAX_LABELS.get(v, v.replace("_", " ").title())

# ── Sidebar logout ────────────────────────────────────────────────────────────
with st.sidebar:
    if st.button("🚪 Sign out", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

# ── Data loaders ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=600, show_spinner="Loading accounts…")
def load_accounts():
    return list_accounts()

@st.cache_data(ttl=600, show_spinner=False)
def load_manual():
    return list_manual_accounts()

@st.cache_data(ttl=600, show_spinner=False)
def load_brokers():
    return list_brokers(include_inactive=False)

# ── Page header ───────────────────────────────────────────────────────────────
st.title("🏦 Accounts")

col_refresh, col_add, col_manual = st.columns([6, 1, 1.4])
with col_refresh:
    if st.button("🔄 Refresh"):
        st.cache_data.clear()
        st.rerun()
with col_add:
    if st.button("➕ Add Account", use_container_width=True, type="primary"):
        st.session_state.show_add = True
with col_manual:
    if st.button("📝 Manual Entry", use_container_width=True):
        st.session_state.show_manual = True

st.divider()

# ── Add Account modal (expander) ──────────────────────────────────────────────
if st.session_state.get("show_add"):
    with st.expander("➕ New Account", expanded=True):
        brokers = load_brokers()
        broker_names = [b["name"] for b in brokers] if brokers else []

        with st.form("add_account_form"):
            col1, col2 = st.columns(2)
            with col1:
                if broker_names:
                    broker_choice = st.selectbox("Broker / Institution",
                                                  broker_names + ["Other…"])
                    if broker_choice == "Other…":
                        broker_name = st.text_input("Institution name")
                    else:
                        broker_name = broker_choice
                else:
                    broker_name = st.text_input("Broker / Institution", placeholder="e.g. Fidelity")
                account_name = st.text_input("Account Name", placeholder="e.g. My Roth IRA")

            with col2:
                account_type = st.selectbox(
                    "Account Type",
                    list(_ACCT_TYPE_LABELS.keys()),
                    format_func=_fmt_acct,
                )
                owner = st.selectbox(
                    "Owner",
                    ["self", "spouse", "joint"],
                    format_func=_fmt_owner,
                )
                _tax_map = {
                    "brokerage": "taxable",       "roth_ira": "tax_free",
                    "traditional_ira": "tax_deferred", "401k": "tax_deferred",
                    "solo_401k": "tax_deferred",  "sep_ira": "tax_deferred",
                    "hsa": "tax_free",             "fsa": "tax_free",
                    "crypto": "taxable",           "savings": "taxable",
                    "checking": "taxable",         "treasury": "taxable",
                    "cd": "taxable",               "real_estate": "taxable",
                }
                tax_status = st.selectbox(
                    "Tax Status",
                    ["taxable", "tax_deferred", "tax_free"],
                    format_func=_fmt_tax,
                    index=["taxable", "tax_deferred", "tax_free"].index(
                        _tax_map.get(account_type, "taxable")),
                )

            submitted = st.form_submit_button("Save Account", type="primary")
            cancelled = st.form_submit_button("Cancel")

        if cancelled:
            st.session_state.show_add = False
            st.rerun()

        if submitted:
            if not broker_name or not account_name:
                st.error("Broker and Account Name are required.")
            else:
                try:
                    data = AccountCreate(
                        broker_name=broker_name,
                        account_name=account_name,
                        account_type=account_type,
                        owner=owner,
                        tax_status=tax_status,
                    )
                    create_account(data)
                    st.success(f"Account **{account_name}** added!")
                    st.session_state.show_add = False
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

# ── Manual Entry modal ────────────────────────────────────────────────────────
if st.session_state.get("show_manual"):
    with st.expander("📝 Manual Account Entry", expanded=True):
        with st.form("manual_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                m_name = st.text_input("Account Name", placeholder="e.g. 401k at Work")
            with col2:
                m_owner = st.selectbox("Owner", ["self", "spouse", "joint"], format_func=_fmt_owner)
            with col3:
                m_value = st.number_input("Current Value ($)", min_value=0.0, step=100.0)
            m_notes = st.text_input("Notes (optional)")
            sub = st.form_submit_button("Save Entry", type="primary")
            can = st.form_submit_button("Cancel")

        if can:
            st.session_state.show_manual = False
            st.rerun()
        if sub:
            if not m_name or m_value == 0:
                st.error("Name and value are required.")
            else:
                try:
                    add_manual_entry(ManualAccountCreate(
                        account_name=m_name, owner=m_owner,
                        value=m_value, notes=m_notes,
                    ))
                    st.success("Manual entry saved!")
                    st.session_state.show_manual = False
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

# ── Account list ──────────────────────────────────────────────────────────────
try:
    accounts = load_accounts()
except Exception as e:
    st.error(f"Could not load accounts: {e}")
    accounts = []

if not accounts:
    st.info("No accounts yet. Click **➕ Add Account** to get started.")
else:
    st.subheader(f"Brokerage Accounts ({len(accounts)})")
    for acc in accounts:
        active = str(acc.get("active", "TRUE")).upper() in ("TRUE", "1", "YES")
        badge = "🟢" if active else "⚫"
        tax   = _fmt_tax(acc.get("tax_status", ""))

        with st.container():
            c1, c2, c3, c4 = st.columns([3, 2, 1.5, 0.5])
            with c1:
                st.markdown(f"**{acc.get('account_name', '')}**  \n"
                            f"<span style='color:#94a3b8;font-size:13px'>"
                            f"{acc.get('broker_name','')} · "
                            f"{_fmt_acct(acc.get('account_type',''))} · "
                            f"{_fmt_owner(acc.get('owner',''))}"
                            f"</span>", unsafe_allow_html=True)
            with c2:
                st.caption(tax)
            with c3:
                st.caption(f"{badge} {'Active' if active else 'Inactive'}")
            with c4:
                if active and st.button("✕", key=f"deact_{acc['account_id']}", help="Deactivate"):
                    try:
                        deactivate_account(acc["account_id"])
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
        st.divider()

# ── Manual entries ────────────────────────────────────────────────────────────
try:
    manual = load_manual()
except Exception as e:
    st.error(f"Could not load manual entries: {e}")
    manual = []

if manual:
    st.subheader("Manual Entries (latest per account)")
    # Show only latest per account name
    seen = {}
    for e in sorted(manual, key=lambda r: r.get("entry_date", ""), reverse=True):
        name = e.get("account_name", "")
        if name not in seen:
            seen[name] = e

    for e in seen.values():
        c1, c2, c3 = st.columns([3, 1.5, 1.5])
        with c1:
            st.markdown(f"**{e.get('account_name','')}**  \n"
                        f"<span style='color:#94a3b8;font-size:13px'>"
                        f"{_fmt_owner(e.get('owner',''))} · {e.get('entry_date','')}"
                        f"</span>", unsafe_allow_html=True)
        with c2:
            st.caption(e.get("notes", ""))
        with c3:
            st.markdown(f"<div style='text-align:right;font-size:18px;font-weight:700;"
                        f"color:#60a5fa'>{fmt_currency(e.get('value', 0))}</div>",
                        unsafe_allow_html=True)
        st.divider()
