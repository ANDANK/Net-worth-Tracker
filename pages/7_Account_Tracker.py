"""Account Tracker — balance input, history, and projections for all accounts."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import date, datetime

st.set_page_config(
    page_title="Account Tracker · NetWorth Tracker",
    page_icon="📊",
    layout="wide",
)

from utils.auth import require_auth
from utils.fmt import fmt_currency
require_auth()

from services.accounts import list_accounts
from services.retirement import (
    RETIREMENT_ACCOUNT_TYPES,
    PROJECTION_END_YEAR,
    IRS_LIMITS,
    DEFAULT_SELF_DOB,
    DEFAULT_SPOUSE_DOB,
    save_retirement_snapshot,
    load_retirement_history,
    project_retirement,
    monthly_totals,
    yearend_totals,
)

# ── Constants ─────────────────────────────────────────────────────────────────
_VIEW_KEY = "acct_tracker_view"
_VIEW_RET = "retirement"
_VIEW_NON = "non_retirement"
_VIEW_ALL = "all"

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

/* ── Sidebar logo ── */
[data-testid="stSidebarNav"]::before {
    content: "💰 NetWorth Tracker";
    display: block;
    font-family: 'Inter', sans-serif;
    font-size: 17px; font-weight: 700; color: #f1f5f9;
    padding: 20px 16px 8px 16px; letter-spacing: -0.02em;
}
[data-testid="stSidebarNav"] li:first-child a span { display: none; }
[data-testid="stSidebarNav"] li:first-child a::before {
    content: "🏠  Dashboard";
    font-family: 'Inter', sans-serif; font-size: 14px; color: #94a3b8;
}

/* ── 3-D Tabs ── */
button[data-baseweb="tab"] {
    font-family: 'Inter', sans-serif !important;
    font-weight: 500 !important; font-size: 14px !important;
    border-radius: 10px 10px 0 0 !important;
    border: 1px solid rgba(255,255,255,0.10) !important;
    border-bottom: none !important;
    background: rgba(255,255,255,0.04) !important;
    padding: 10px 24px !important; margin-right: 4px !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.07), 0 -2px 6px rgba(0,0,0,0.25) !important;
    transition: all 0.15s ease !important;
}
button[data-baseweb="tab"]:hover {
    background: rgba(255,255,255,0.08) !important;
    border-color: rgba(255,255,255,0.2) !important;
}
button[aria-selected="true"][data-baseweb="tab"] {
    background: rgba(16,185,129,0.14) !important;
    border-color: rgba(16,185,129,0.40) !important;
    color: #10b981 !important; font-weight: 700 !important;
    box-shadow: 0 -3px 14px rgba(16,185,129,0.18),
                inset 0 1px 0 rgba(16,185,129,0.25) !important;
}

/* ── Section headers ── */
.section-ret {
    font-family: 'Inter', sans-serif;
    font-size: 14px; font-weight: 700; color: #10b981;
    background: rgba(16,185,129,0.09); border-left: 3px solid #10b981;
    border-radius: 0 6px 6px 0; padding: 6px 14px; margin: 6px 0 10px 0;
}
.section-ret span { color: #6ee7b7; font-weight: 400; font-size: 12px; }
.section-nonret {
    font-family: 'Inter', sans-serif;
    font-size: 14px; font-weight: 700; color: #60a5fa;
    background: rgba(96,165,250,0.09); border-left: 3px solid #60a5fa;
    border-radius: 0 6px 6px 0; padding: 6px 14px; margin: 6px 0 10px 0;
}
.section-nonret span { color: #93c5fd; font-weight: 400; font-size: 12px; }
.section-self {
    font-family: 'Inter', sans-serif;
    font-size: 13px; font-weight: 600; color: #34d399;
    border-bottom: 1px solid rgba(16,185,129,0.2);
    padding-bottom: 4px; margin: 8px 0 6px 0;
}
.section-spouse {
    font-family: 'Inter', sans-serif;
    font-size: 13px; font-weight: 600; color: #fbbf24;
    border-bottom: 1px solid rgba(245,158,11,0.2);
    padding-bottom: 4px; margin: 8px 0 6px 0;
}
.section-joint {
    font-family: 'Inter', sans-serif;
    font-size: 13px; font-weight: 600; color: #93c5fd;
    border-bottom: 1px solid rgba(96,165,250,0.2);
    padding-bottom: 4px; margin: 8px 0 6px 0;
}

/* ── Account cards ── */
div[data-testid="stVerticalBlockBorderWrapper"] {
    border: 1px solid rgba(16,185,129,0.28) !important;
    border-radius: 10px !important;
    background: rgba(16,185,129,0.03) !important;
    transition: border-color 0.15s, background 0.15s;
}
div[data-testid="stVerticalBlockBorderWrapper"]:hover {
    border-color: rgba(16,185,129,0.55) !important;
    background: rgba(16,185,129,0.07) !important;
}
.acct-name {
    font-family: 'Inter', sans-serif;
    font-size: 13px; font-weight: 600; color: #e2e8f0;
    letter-spacing: 0.005em; margin-bottom: 2px;
}
.acct-type { font-size: 11px; font-weight: 400; color: #64748b; margin-left: 4px; }
.acct-last { font-size: 11px; color: #475569; margin-top: 3px; margin-bottom: 8px; }

/* ── Number input ── */
div[data-testid="stNumberInput"] input {
    font-family: 'Inter', sans-serif; font-size: 15px; font-weight: 600;
}

/* ── Page title ── */
.page-title {
    font-family: 'Inter', sans-serif;
    font-size: 26px; font-weight: 700; color: #f1f5f9; letter-spacing: -0.03em;
}
.page-sub { font-size: 12px; color: #64748b; margin-top: 2px; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("**People**")
    self_name   = st.text_input("Person 1 (Self)",   value="AK")
    spouse_name = st.text_input("Person 2 (Spouse)", value="PA")
    self_dob    = st.date_input("Person 1 DOB",   value=DEFAULT_SELF_DOB,   min_value=date(1940,1,1))
    spouse_dob  = st.date_input("Person 2 DOB",   value=DEFAULT_SPOUSE_DOB, min_value=date(1940,1,1))

# ── Account type labels / icons ───────────────────────────────────────────────
_ATYPE_LABEL = {
    "brokerage":"Brokerage","roth_ira":"Roth IRA","traditional_ira":"Traditional IRA",
    "401k":"401(k)","roth_401k":"Roth 401(k)","solo_401k":"Solo 401(k)",
    "sep_ira":"SEP IRA","hsa":"HSA","fsa":"FSA","crypto":"Crypto",
    "savings":"Savings","checking":"Checking","treasury":"Treasury",
    "cd":"CD","real_estate":"Real Estate",
}
_ATYPE_ICON = {
    "brokerage":"📈","roth_ira":"🌱","traditional_ira":"🏛️","401k":"💼",
    "roth_401k":"🔵","solo_401k":"🧑‍💼","sep_ira":"📋","hsa":"🏥",
    "fsa":"🩺","crypto":"🪙","savings":"🏦","checking":"💳",
    "treasury":"🇺🇸","cd":"🔒","real_estate":"🏠",
}
def _label(t): return _ATYPE_LABEL.get(t, t.replace("_"," ").title())
def _icon(t):  return _ATYPE_ICON.get(t, "💰")

# ── Data loaders ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=600)
def _load_all_accounts():
    return [
        a for a in list_accounts()
        if str(a.get("active", "TRUE")).upper() in ("TRUE", "1", "YES")
    ]

@st.cache_data(ttl=300)
def _load_history():
    return load_retirement_history()

def _compute_latest(history):
    latest = {}
    for r in history:
        aid = r.get("account_id", "")
        if aid and aid not in latest:
            latest[aid] = float(r.get("balance", 0) or 0)
    return latest

def _is_retirement(a):
    return a.get("account_type", "").lower() in RETIREMENT_ACCOUNT_TYPES

# ── Top bar ───────────────────────────────────────────────────────────────────
hdr_t, hdr_gap, hdr_ref, hdr_home, hdr_out = st.columns([5, 2, 1.1, 1, 1])
with hdr_t:
    st.markdown(
        '<div class="page-title">📊 Account Tracker</div>'
        '<div class="page-sub">Track, compare and project all your accounts through 2040</div>',
        unsafe_allow_html=True,
    )
with hdr_ref:
    if st.button("🔄 Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
with hdr_home:
    st.page_link("app.py", label="🏠 Home", use_container_width=True)
with hdr_out:
    if st.button("🚪 Sign out", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

# ── Account view toggle (3 bright buttons) ────────────────────────────────────
st.markdown("<div style='margin:10px 0 4px 0'></div>", unsafe_allow_html=True)
cur_view = st.session_state.get(_VIEW_KEY, _VIEW_RET)

tog_l, tog_m, tog_r, tog_gap = st.columns([1.6, 1.9, 1.6, 4])
with tog_l:
    if st.button("🎯 Retirement",
                 type="primary" if cur_view == _VIEW_RET else "secondary",
                 use_container_width=True):
        st.session_state[_VIEW_KEY] = _VIEW_RET; st.rerun()
with tog_m:
    if st.button("💼 Non-Retirement",
                 type="primary" if cur_view == _VIEW_NON else "secondary",
                 use_container_width=True):
        st.session_state[_VIEW_KEY] = _VIEW_NON; st.rerun()
with tog_r:
    if st.button("📊 All Accounts",
                 type="primary" if cur_view == _VIEW_ALL else "secondary",
                 use_container_width=True):
        st.session_state[_VIEW_KEY] = _VIEW_ALL; st.rerun()

st.markdown("<div style='margin-bottom:6px'></div>", unsafe_allow_html=True)
st.divider()

# ── Load & filter accounts ────────────────────────────────────────────────────
current_year = datetime.now().year

try:
    all_accounts = _load_all_accounts()
except Exception as e:
    st.error(f"Could not load accounts: {e}")
    st.stop()

view = st.session_state.get(_VIEW_KEY, _VIEW_RET)

ret_accounts_all = [a for a in all_accounts if _is_retirement(a)]
nonret_accounts  = [a for a in all_accounts if not _is_retirement(a)]

if view == _VIEW_RET:
    display_accounts = ret_accounts_all
elif view == _VIEW_NON:
    display_accounts = nonret_accounts
else:
    display_accounts = all_accounts

if not display_accounts:
    kind = "retirement" if view == _VIEW_RET else ("non-retirement" if view == _VIEW_NON else "")
    st.warning(f"No active {kind} accounts found. Go to **Accounts** to add some.")
    st.stop()

def _split_by_owner(accounts):
    s = sorted([a for a in accounts if a.get("owner") == "self"],   key=lambda a: a.get("account_type",""))
    p = sorted([a for a in accounts if a.get("owner") == "spouse"], key=lambda a: a.get("account_type",""))
    j =        [a for a in accounts if a.get("owner") == "joint"]
    return s, p, j

# ── SECURE 2.0 warning ────────────────────────────────────────────────────────
if view in (_VIEW_RET, _VIEW_ALL) and current_year >= 2026:
    s_ret, sp_ret, _ = _split_by_owner(ret_accounts_all)
    missing = []
    if not any(a.get("account_type") == "roth_401k" for a in s_ret):
        missing.append(f"{self_name} Roth 401(k) (Self)")
    if not any(a.get("account_type") == "roth_401k" for a in sp_ret) and current_year >= 2029:
        missing.append(f"{spouse_name} Roth 401(k) (Spouse)")
    if missing:
        with st.expander("⚠️  SECURE 2.0: Add Roth 401(k) for catch-up tracking", expanded=False):
            st.warning("From 2026, 401(k) catch-up must go to a Roth 401(k). "
                       "Add: " + ", ".join(missing) + " in the Accounts page.")

tab1, tab2 = st.tabs(["📥  Balance Input", "📊  Analytics & Projections"])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Balance Input
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:

    d_col, hint_col = st.columns([2, 5])
    with d_col:
        snap_date = st.date_input("📅 Snapshot Date", value=date.today())
    with hint_col:
        st.info(
            "Enter the **current balance** for each account. "
            "Use **Hide from forecast** to remove an account from Tab 2 projections "
            "without deleting its history."
        )

    try:
        last_bal = _compute_latest(_load_history())
    except Exception:
        last_bal = {}

    balance_inputs: dict[str, float] = {}
    skip_set: set[str] = set(st.session_state.get("ret_excluded", set()))

    def _account_card(acc, col_ctx):
        if acc is None:
            with col_ctx:
                st.markdown("<div style='height:148px'></div>", unsafe_allow_html=True)
            return
        aid      = acc["account_id"]
        atype    = acc.get("account_type", "")
        aname    = acc.get("account_name", "Unknown")
        last     = float(last_bal.get(aid, 0) or 0)
        last_str = fmt_currency(last) if last else "—"
        with col_ctx:
            with st.container(border=True):
                st.markdown(
                    f'<div class="acct-name">{_icon(atype)} {aname}'
                    f'<span class="acct-type">· {_label(atype)}</span></div>',
                    unsafe_allow_html=True,
                )
                bal = st.number_input(
                    "Balance", min_value=0.0, value=last, step=500.0,
                    format="%.2f", key=f"bal_{aid}", label_visibility="collapsed",
                )
                st.markdown(f'<div class="acct-last">Last: {last_str}</div>', unsafe_allow_html=True)
                skipped = st.checkbox(
                    "Hide from forecast",
                    key=f"skip_{aid}",
                    value=aid in skip_set,
                    help=(
                        "Removes this entire account from the projection chart and all "
                        "calculations in Tab 2. Saved history is NOT deleted — "
                        "uncheck anytime to include it again."
                    ),
                )
        balance_inputs[aid] = bal
        if skipped: skip_set.add(aid)
        else:       skip_set.discard(aid)

    def _render_owner_grid(accounts):
        s_list, p_list, j_list = _split_by_owner(accounts)
        c_self, c_spouse = st.columns(2, gap="large")

        def _padded_pairs(lst):
            return lst + ([None] * (2 - len(lst) % 2 if len(lst) % 2 else 0))

        with c_self:
            st.markdown(f'<div class="section-self">👤 {self_name}</div>', unsafe_allow_html=True)
            if s_list:
                for i in range(0, len(_padded_pairs(s_list)), 2):
                    p = _padded_pairs(s_list)
                    sl, sr = st.columns(2, gap="medium")
                    _account_card(p[i], sl)
                    _account_card(p[i+1], sr)
            else:
                st.caption("No accounts.")

        with c_spouse:
            st.markdown(f'<div class="section-spouse">👥 {spouse_name}</div>', unsafe_allow_html=True)
            if p_list:
                for i in range(0, len(_padded_pairs(p_list)), 2):
                    p = _padded_pairs(p_list)
                    sl, sr = st.columns(2, gap="medium")
                    _account_card(p[i], sl)
                    _account_card(p[i+1], sr)
            else:
                st.caption("No accounts.")

        if j_list:
            st.markdown("<div style='margin-top:10px'></div>", unsafe_allow_html=True)
            st.markdown('<div class="section-joint">🤝 Joint</div>', unsafe_allow_html=True)
            padded_j = j_list + ([None] * (3 - len(j_list) % 3 if len(j_list) % 3 else 0))
            for i in range(0, len(padded_j), 3):
                jc1, jc2, jc3 = st.columns(3, gap="medium")
                _account_card(padded_j[i], jc1)
                _account_card(padded_j[i+1], jc2)
                _account_card(padded_j[i+2], jc3)

    # ── Render sections based on view ────────────────────────────────────────
    if view == _VIEW_ALL:
        if ret_accounts_all:
            st.markdown('<div class="section-ret">🎯 Retirement Accounts <span>· Tax-advantaged</span></div>',
                        unsafe_allow_html=True)
            _render_owner_grid(ret_accounts_all)
        if nonret_accounts:
            st.markdown("<hr style='margin:20px 0;border-color:rgba(255,255,255,0.07)'>",
                        unsafe_allow_html=True)
            st.markdown('<div class="section-nonret">💼 Non-Retirement Accounts <span>· Taxable &amp; other</span></div>',
                        unsafe_allow_html=True)
            _render_owner_grid(nonret_accounts)
    elif view == _VIEW_NON:
        st.markdown('<div class="section-nonret">💼 Non-Retirement Accounts</div>', unsafe_allow_html=True)
        _render_owner_grid(display_accounts)
    else:
        _render_owner_grid(display_accounts)

    st.session_state["ret_excluded"] = skip_set

    # ── Save ──────────────────────────────────────────────────────────────────
    st.markdown("---")
    sv_col, _ = st.columns([2, 5])
    with sv_col:
        if st.button("💾  Save All Balances", type="primary", use_container_width=True):
            entries = [
                {"account_id": aid,
                 "account_name": next((a["account_name"] for a in all_accounts if a["account_id"]==aid), aid),
                 "balance": bal}
                for aid, bal in balance_inputs.items() if bal > 0
            ]
            if entries:
                try:
                    save_retirement_snapshot(entries, snap_date.isoformat())
                    st.success(f"✅ Saved {len(entries)} balance(s) for {snap_date}.")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as exc:
                    st.error(f"Save failed: {exc}")
            else:
                st.warning("Enter at least one balance > $0 before saving.")

    # ── IRS limits reference (retirement views only) ──────────────────────────
    if view in (_VIEW_RET, _VIEW_ALL):
        with st.expander("📋 IRS Contribution Limits Reference (2024–2040)", expanded=False):
            rows = [{"Year": yr,
                     "401k Regular": lim["irs_401k"], "401k Catch-up (50+)": lim["irs_401k_cu"],
                     "IRA": lim["ira"], "IRA Catch-up (50+)": lim["ira_cu"],
                     "HSA (Self)": lim["hsa_self"], "HSA (Family)": lim["hsa_fam"],
                     "Status": "✅ Confirmed" if lim["confirmed"] else "📊 Estimated"}
                    for yr, lim in sorted(IRS_LIMITS.items())]
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True,
                         column_config={k: st.column_config.NumberColumn(format="$%d")
                                        for k in ["401k Regular","401k Catch-up (50+)",
                                                  "IRA","IRA Catch-up (50+)","HSA (Self)","HSA (Family)"]})


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Analytics & Projections
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:

    # ── Controls ─────────────────────────────────────────────────────────────
    ctrl1, ctrl2, ctrl3, ctrl4 = st.columns([3, 2, 2, 3])
    with ctrl1:
        growth_pct  = st.slider("📈 Annual Growth Rate", 3.0, 15.0, 7.0, 0.5, format="%.1f%%")
        growth_rate = growth_pct / 100
    with ctrl2:
        proj_start = st.number_input("Start Year", min_value=2024, max_value=current_year, value=current_year)
    with ctrl3:
        target_year = st.number_input("🎯 Target Year", min_value=current_year+1,
                                      max_value=PROJECTION_END_YEAR, value=min(2040, PROJECTION_END_YEAR))
    with ctrl4:
        target_amount = st.select_slider(
            "🏁 Retirement Target",
            options=[250_000,500_000,750_000,1_000_000,1_250_000,1_500_000,
                     2_000_000,2_500_000,3_000_000,4_000_000,5_000_000],
            value=2_000_000,
            format_func=lambda v: f"${v/1e6:.2f}M" if v>=1e6 else f"${v//1000}K",
        )

    if view == _VIEW_NON:
        st.caption("ℹ️ Non-retirement accounts projected with growth only — no IRS contribution modeling.")
    else:
        st.caption("IRS limits: ✅ 2024–2025 confirmed · 📊 2026+ estimated. Year-end contributions.")

    # ── Load ─────────────────────────────────────────────────────────────────
    try:
        history = _load_history()
        latest  = _compute_latest(history)
    except Exception as exc:
        st.error(f"Could not load history: {exc}")
        st.stop()

    if not history:
        st.info("No balance data yet — use the Balance Input tab first.")
        st.stop()

    excluded = st.session_state.get("ret_excluded", set())
    disp_ids = {a["account_id"] for a in display_accounts}

    # ── Project ───────────────────────────────────────────────────────────────
    proj_df = project_retirement(
        display_accounts, latest, growth_rate=growth_rate,
        excluded=excluded, self_dob=self_dob, spouse_dob=spouse_dob,
        start_year=int(proj_start),
    )

    # ── Totals ────────────────────────────────────────────────────────────────
    total_now  = sum(v for aid, v in latest.items() if aid not in excluded and aid in disp_ids)
    self_now   = sum(v for aid, v in latest.items()
                     if aid not in excluded and aid in disp_ids
                     and any(a["account_id"]==aid and a.get("owner")=="self" for a in display_accounts))
    spouse_now = sum(v for aid, v in latest.items()
                     if aid not in excluded and aid in disp_ids
                     and any(a["account_id"]==aid and a.get("owner")=="spouse" for a in display_accounts))

    ret_ids    = {a["account_id"] for a in ret_accounts_all}
    nonret_ids = {a["account_id"] for a in nonret_accounts}

    proj_at_ty = 0.0
    if not proj_df.empty and target_year in proj_df["year"].values:
        proj_at_ty = proj_df[proj_df["year"]==target_year]["balance"].sum()

    # ── KPIs ─────────────────────────────────────────────────────────────────
    k1, k2, k3, k4, k5 = st.columns(5)
    if view == _VIEW_ALL:
        ret_now    = sum(v for aid, v in latest.items() if aid not in excluded and aid in ret_ids)
        nonret_now = sum(v for aid, v in latest.items() if aid not in excluded and aid in nonret_ids)
        k1.metric("Total Balance",     fmt_currency(total_now))
        k2.metric("🎯 Retirement",     fmt_currency(ret_now))
        k3.metric("💼 Non-Retirement", fmt_currency(nonret_now))
    else:
        k1.metric("Combined Balance",  fmt_currency(total_now))
        k2.metric(f"{self_name}",      fmt_currency(self_now))
        k3.metric(f"{spouse_name}",    fmt_currency(spouse_now))

    gap = target_amount - proj_at_ty
    k4.metric(f"Projected {target_year}", fmt_currency(proj_at_ty),
              delta=f"{fmt_currency(proj_at_ty - target_amount)} vs goal" if proj_at_ty else None)
    ak_age = target_year - self_dob.year
    pa_age = target_year - spouse_dob.year
    k5.metric(f"Gap to {fmt_currency(target_amount,0)}",
              fmt_currency(max(gap,0),0) if gap>0 else "✅ On Track",
              delta=f"{self_name} {ak_age} · {spouse_name} {pa_age} in {target_year}",
              delta_color="off")

    st.divider()

    # ── History chart + pie ───────────────────────────────────────────────────
    df_h = pd.DataFrame(history)
    df_h["date"]    = pd.to_datetime(df_h["date"], errors="coerce")
    df_h["balance"] = pd.to_numeric(df_h["balance"], errors="coerce").fillna(0)
    df_h = df_h[df_h["account_id"].isin(disp_ids)]

    color_pool = {
        "roth_ira":"#06b6d4","traditional_ira":"#8b5cf6","401k":"#3b82f6",
        "roth_401k":"#60a5fa","hsa":"#f97316","sep_ira":"#ec4899","solo_401k":"#a78bfa",
        "brokerage":"#10b981","crypto":"#f59e0b","savings":"#34d399",
        "checking":"#fbbf24","treasury":"#6ee7b7","cd":"#a3e635",
        "real_estate":"#fb923c","fsa":"#e879f9",
    }

    hist_col, pie_col = st.columns([2, 1])
    with hist_col:
        st.subheader("📈 Balance Over Time")
        fig_h = go.Figure()
        for acc in display_accounts:
            aid  = acc["account_id"]
            df_a = df_h[df_h["account_id"]==aid].sort_values("date")
            if df_a.empty: continue
            fig_h.add_trace(go.Scatter(
                x=df_a["date"], y=df_a["balance"], name=acc["account_name"],
                mode="lines+markers",
                line=dict(width=1.5, color=color_pool.get(acc.get("account_type",""),"#94a3b8")),
                opacity=0.75,
                hovertemplate=f"{acc['account_name']}<br>%{{x|%b %Y}}: $%{{y:,.0f}}<extra></extra>",
            ))
        df_comb = df_h.groupby("date")["balance"].sum().reset_index().sort_values("date")
        fig_h.add_trace(go.Scatter(
            x=df_comb["date"], y=df_comb["balance"], name="Combined",
            mode="lines+markers", line=dict(width=3, color="#3b82f6"),
            hovertemplate="Combined<br>%{x|%b %Y}: $%{y:,.0f}<extra></extra>",
        ))
        fig_h.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            height=330, margin=dict(l=0,r=0,t=8,b=0),
            legend=dict(orientation="h", y=-0.32, font_size=11),
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)",
                       tickprefix="$", tickformat=",.0f"),
            hovermode="x unified",
        )
        st.plotly_chart(fig_h, use_container_width=True)

    with pie_col:
        st.subheader("🥧 Allocation")
        pie_labels, pie_vals, pie_colors = [], [], []
        _pal = px.colors.qualitative.Set2
        for i, acc in enumerate(display_accounts):
            bal = latest.get(acc["account_id"], 0)
            if bal > 0 and acc["account_id"] not in excluded:
                pie_labels.append(acc["account_name"])
                pie_vals.append(bal)
                pie_colors.append(_pal[i % len(_pal)])
        if pie_labels:
            fig_pie = go.Figure(go.Pie(
                labels=pie_labels, values=pie_vals, hole=0.55,
                marker=dict(colors=pie_colors), textinfo="percent",
                hovertemplate="%{label}<br>$%{value:,.0f} (%{percent})<extra></extra>",
            ))
            fig_pie.add_annotation(text=fmt_currency(total_now), x=0.5, y=0.5,
                                   font=dict(size=15, color="white"), showarrow=False)
            fig_pie.update_layout(paper_bgcolor="rgba(0,0,0,0)",
                                  margin=dict(l=0,r=0,t=8,b=0), height=330,
                                  legend=dict(orientation="v", font_size=10))
            st.plotly_chart(fig_pie, use_container_width=True)

    st.divider()

    # ── Self vs Spouse bar ────────────────────────────────────────────────────
    st.subheader(f"👤 {self_name} vs 👥 {spouse_name}")
    cmp_rows = [
        {"Account": a["account_name"],
         "Person":  self_name if a.get("owner")=="self" else (spouse_name if a.get("owner")=="spouse" else "Joint"),
         "Balance": latest.get(a["account_id"], 0)}
        for a in display_accounts if a["account_id"] not in excluded
    ]
    if cmp_rows:
        df_cmp = pd.DataFrame(cmp_rows)
        fig_cmp = px.bar(df_cmp, x="Account", y="Balance", color="Person", barmode="group",
                         color_discrete_map={self_name:"#10b981", spouse_name:"#f59e0b", "Joint":"#3b82f6"},
                         text="Balance")
        fig_cmp.update_traces(texttemplate="$%{text:,.0f}", textposition="outside",
                              hovertemplate="%{x}<br>$%{y:,.0f}<extra></extra>")
        fig_cmp.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              height=300, margin=dict(l=0,r=0,t=8,b=0),
                              xaxis=dict(showgrid=False),
                              yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)",
                                         tickprefix="$", tickformat=",.0f"))
        st.plotly_chart(fig_cmp, use_container_width=True)

    st.divider()

    # ── Monthly trend ─────────────────────────────────────────────────────────
    st.subheader("📅 Monthly Trend — Last 8 Months")
    hist_filtered = [r for r in history if r.get("account_id","") in disp_ids]
    df_mo = monthly_totals(hist_filtered, months=8)
    if df_mo.empty:
        st.info("Not enough history for monthly trend yet.")
    else:
        mo_c, mo_t = st.columns([1.6, 1])
        with mo_c:
            fig_mo = go.Figure(go.Bar(
                x=df_mo["month_str"], y=df_mo["total"], marker_color="#3b82f6",
                text=df_mo["total"].apply(lambda v: f"${v/1e6:.2f}M" if v>=1e6 else f"${v:,.0f}"),
                textposition="outside",
                hovertemplate="%{x}<br>$%{y:,.0f}<extra></extra>",
            ))
            fig_mo.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                 height=260, margin=dict(l=0,r=0,t=10,b=0),
                                 xaxis=dict(showgrid=False),
                                 yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)",
                                            tickprefix="$", tickformat=",.0f"))
            st.plotly_chart(fig_mo, use_container_width=True)
        with mo_t:
            df_mo_s = df_mo[["month_str","total","mom_change"]].copy()
            df_mo_s.columns = ["Month","Total","MoM Change"]
            st.dataframe(df_mo_s, use_container_width=True, hide_index=True, height=260,
                         column_config={"Total":st.column_config.NumberColumn(format="$%.0f"),
                                        "MoM Change":st.column_config.NumberColumn(format="$%.0f")})

    st.divider()

    # ── Year-end historical balances ──────────────────────────────────────────
    st.subheader("📆 Year-End Balances (Historical)")
    df_ye = yearend_totals(hist_filtered)
    if df_ye.empty:
        st.info("Not enough history for year-end summary yet.")
    else:
        ye_c, ye_t = st.columns([1.6, 1])
        with ye_c:
            bar_colors = [
                "#3b82f6" if i==0 or pd.isna(r["yoy_change"])
                else ("#10b981" if r["yoy_change"]>=0 else "#ef4444")
                for i, r in df_ye.iterrows()
            ]
            fig_ye = go.Figure(go.Bar(
                x=df_ye["year"].astype(str), y=df_ye["total"], marker_color=bar_colors,
                text=df_ye["total"].apply(lambda v: f"${v/1e6:.2f}M" if v>=1e6 else f"${v:,.0f}"),
                textposition="outside",
                hovertemplate="Year %{x}<br>$%{y:,.0f}<extra></extra>",
            ))
            fig_ye.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                 height=260, margin=dict(l=0,r=0,t=10,b=0),
                                 xaxis=dict(showgrid=False),
                                 yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)",
                                            tickprefix="$", tickformat=",.0f"))
            st.plotly_chart(fig_ye, use_container_width=True)
        with ye_t:
            df_ye_s = df_ye[["year","total","yoy_change","yoy_pct"]].copy()
            df_ye_s.columns = ["Year","Balance","YoY $","YoY %"]
            st.dataframe(df_ye_s, use_container_width=True, hide_index=True, height=260,
                         column_config={"Balance":st.column_config.NumberColumn(format="$%.0f"),
                                        "YoY $":st.column_config.NumberColumn(format="$%.0f"),
                                        "YoY %":st.column_config.NumberColumn(format="%.1f%%")})

    st.divider()

    # ── Projection chart ──────────────────────────────────────────────────────
    st.subheader(f"🔮 Projection to {PROJECTION_END_YEAR}  ·  {growth_pct:.1f}% Annual Growth")

    if proj_df.empty:
        st.info("No starting balances — record data in the Balance Input tab first.")
    else:
        proj_comb   = proj_df.groupby("year")["balance"].sum().reset_index()
        proj_self   = proj_df[proj_df["owner"]=="self"].groupby("year")["balance"].sum().reset_index()
        proj_spouse = proj_df[proj_df["owner"]=="spouse"].groupby("year")["balance"].sum().reset_index()

        fig_p = go.Figure()

        if view == _VIEW_ALL and not proj_df.empty:
            proj_ret    = proj_df[proj_df["account_id"].isin(ret_ids)].groupby("year")["balance"].sum().reset_index()
            proj_nonret = proj_df[proj_df["account_id"].isin(nonret_ids)].groupby("year")["balance"].sum().reset_index()
            if not proj_ret.empty:
                fig_p.add_trace(go.Scatter(
                    x=proj_ret["year"], y=proj_ret["balance"], name="🎯 Retirement",
                    fill="tozeroy", line=dict(color="#10b981", width=2),
                    fillcolor="rgba(16,185,129,0.12)",
                    hovertemplate="Retirement %{x}: $%{y:,.0f}<extra></extra>",
                ))
            if not proj_nonret.empty:
                fig_p.add_trace(go.Scatter(
                    x=proj_nonret["year"], y=proj_nonret["balance"], name="💼 Non-Retirement",
                    fill="tozeroy", line=dict(color="#60a5fa", width=2),
                    fillcolor="rgba(96,165,250,0.12)",
                    hovertemplate="Non-Ret %{x}: $%{y:,.0f}<extra></extra>",
                ))
        else:
            if not proj_self.empty:
                fig_p.add_trace(go.Scatter(
                    x=proj_self["year"], y=proj_self["balance"],
                    name=f"{self_name} (Self)", fill="tozeroy",
                    line=dict(color="#10b981", width=2), fillcolor="rgba(16,185,129,0.12)",
                    hovertemplate=f"{self_name} %{{x}}: $%{{y:,.0f}}<extra></extra>",
                ))
            if not proj_spouse.empty:
                fig_p.add_trace(go.Scatter(
                    x=proj_spouse["year"], y=proj_spouse["balance"],
                    name=f"{spouse_name} (Spouse)", fill="tozeroy",
                    line=dict(color="#f59e0b", width=2), fillcolor="rgba(245,158,11,0.12)",
                    hovertemplate=f"{spouse_name} %{{x}}: $%{{y:,.0f}}<extra></extra>",
                ))

        fig_p.add_trace(go.Scatter(
            x=proj_comb["year"], y=proj_comb["balance"], name="Combined",
            line=dict(color="#3b82f6", width=3),
            hovertemplate="Combined %{x}: $%{y:,.0f}<extra></extra>",
        ))
        # Goal line + target year marker
        fig_p.add_hline(y=target_amount, line_dash="dash", line_color="#f43f5e", line_width=2,
                        annotation_text=f"🎯 {fmt_currency(target_amount,0)}",
                        annotation_position="right", annotation_font=dict(size=12, color="#f43f5e"))
        if target_year in proj_comb["year"].values:
            fig_p.add_vline(x=target_year, line_dash="dot", line_color="rgba(244,63,94,0.35)",
                            annotation_text=str(target_year), annotation_position="top",
                            annotation_font_size=11)
        # Standard milestone dashes
        max_p = proj_comb["balance"].max()
        for tgt, lbl in [(500_000,"$500K"),(1_000_000,"$1M"),(1_500_000,"$1.5M"),(2_000_000,"$2M"),(3_000_000,"$3M")]:
            if tgt != target_amount and max_p >= tgt * 0.8:
                fig_p.add_hline(y=tgt, line_dash="dot", line_color="rgba(255,255,255,0.10)",
                                annotation_text=lbl, annotation_position="right", annotation_font_size=10)

        fig_p.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            height=420, margin=dict(l=0,r=90,t=8,b=0),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis=dict(showgrid=False, dtick=1, tickangle=-45),
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)",
                       tickprefix="$", tickformat=",.0f"),
            hovermode="x unified",
        )
        st.plotly_chart(fig_p, use_container_width=True)

        # ── Annual contributions bar ──────────────────────────────────────────
        contrib_df = proj_df[proj_df["contribution"] > 0].copy()
        if not contrib_df.empty:
            st.subheader("💰 Annual Contributions by Account")
            fig_cont = px.bar(contrib_df, x="year", y="contribution", color="account_name",
                              barmode="stack",
                              labels={"contribution":"Contribution ($)","year":"Year","account_name":"Account"},
                              color_discrete_sequence=px.colors.qualitative.Set2)
            fig_cont.update_traces(hovertemplate="%{fullData.name}<br>%{x}: $%{y:,.0f}<extra></extra>")
            fig_cont.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                   height=300, margin=dict(l=0,r=0,t=8,b=0),
                                   legend=dict(orientation="h", y=-0.4, font_size=10),
                                   xaxis=dict(showgrid=False, dtick=1, tickangle=-45),
                                   yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)",
                                              tickprefix="$", tickformat=",.0f"))
            st.plotly_chart(fig_cont, use_container_width=True)

        # ── Full projection table ─────────────────────────────────────────────
        with st.expander("📋 Full Projection Table", expanded=False):
            _confirmed = {y for y, v in IRS_LIMITS.items() if v.get("confirmed")}
            tbl = proj_comb.copy()
            tbl = tbl.merge(proj_self.rename(columns={"balance":f"{self_name}"}),   on="year", how="left")
            tbl = tbl.merge(proj_spouse.rename(columns={"balance":f"{spouse_name}"}),on="year", how="left")
            tbl = tbl.merge(proj_df.groupby("year")["contribution"].sum().reset_index()
                              .rename(columns={"contribution":"Contributions"}), on="year", how="left")
            tbl = tbl.merge(proj_df.groupby("year")["growth_dollars"].sum().reset_index()
                              .rename(columns={"growth_dollars":"Growth $"}), on="year", how="left")
            if view in (_VIEW_RET, _VIEW_ALL):
                tbl["IRS"] = tbl["year"].apply(lambda y: "✅" if y in _confirmed else "📊")
            tbl["vs Goal"] = tbl["balance"].apply(
                lambda v: f"{'✅' if v>=target_amount else '❌'} "
                          f"{fmt_currency(abs(v-target_amount),0)} "
                          f"{'ahead' if v>=target_amount else 'short'}"
            )
            tbl.rename(columns={"year":"Year","balance":"Combined"}, inplace=True)
            st.dataframe(tbl, hide_index=True, use_container_width=True,
                         column_config={
                             "Combined":st.column_config.NumberColumn(format="$%.0f"),
                             f"{self_name}":st.column_config.NumberColumn(format="$%.0f"),
                             f"{spouse_name}":st.column_config.NumberColumn(format="$%.0f"),
                             "Contributions":st.column_config.NumberColumn(format="$%.0f"),
                             "Growth $":st.column_config.NumberColumn(format="$%.0f"),
                         })

        st.divider()

        # ── Milestones ────────────────────────────────────────────────────────
        st.subheader("🎯 Milestones")
        milestones = sorted(set([250_000,500_000,750_000,1_000_000,1_500_000,2_000_000,3_000_000,target_amount]))
        found = []
        for tgt in milestones:
            hit = proj_comb[proj_comb["balance"] >= tgt]
            lbl = f"${tgt/1e6:.2f}M" if tgt>=1e6 else f"${tgt//1000}K"
            if not hit.empty:
                yr = int(hit.iloc[0]["year"])
                found.append({"label":lbl,"year":yr,"ak":yr-self_dob.year,"pa":yr-spouse_dob.year,"reached":True})
            else:
                found.append({"label":lbl,"year":"—","reached":False})

        ms_cols = st.columns(min(len(found), 4))
        for i, m in enumerate(found):
            with ms_cols[i % 4]:
                if m["reached"]:
                    st.metric(m["label"], str(m["year"]),
                              delta=f"{self_name} {m['ak']} · {spouse_name} {m['pa']}")
                else:
                    st.metric(m["label"], "Beyond 2040", delta="Not reached", delta_color="off")

        st.divider()

        # ── Cumulative contributions vs growth ────────────────────────────────
        st.subheader("📊 Cumulative: Contributions vs. Growth")
        cumul = proj_df.groupby("year").agg(
            total_contrib=("contribution","sum"),
            total_growth=("growth_dollars","sum"),
        ).reset_index()
        cumul["cum_contrib"] = cumul["total_contrib"].cumsum()
        cumul["cum_growth"]  = cumul["total_growth"].cumsum()
        fig_cg = go.Figure()
        fig_cg.add_trace(go.Bar(x=cumul["year"], y=cumul["cum_contrib"],
                                name="Cumulative Contributions", marker_color="#10b981",
                                hovertemplate="Year %{x}<br>Contributions: $%{y:,.0f}<extra></extra>"))
        fig_cg.add_trace(go.Bar(x=cumul["year"], y=cumul["cum_growth"],
                                name="Cumulative Growth", marker_color="#3b82f6",
                                hovertemplate="Year %{x}<br>Growth: $%{y:,.0f}<extra></extra>"))
        fig_cg.update_layout(barmode="stack",
                             paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                             height=300, margin=dict(l=0,r=0,t=8,b=0),
                             legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                             xaxis=dict(showgrid=False, dtick=1, tickangle=-45),
                             yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)",
                                        tickprefix="$", tickformat=",.0f"))
        st.plotly_chart(fig_cg, use_container_width=True)
