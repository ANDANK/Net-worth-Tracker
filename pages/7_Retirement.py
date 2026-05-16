"""Retirement Tracker — balance input, history, and projections to 2040."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import date, datetime

st.set_page_config(
    page_title="Retirement · NetWorth Tracker",
    page_icon="🎯",
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
    get_latest_balances,
    project_retirement,
    get_annual_contribution,
    monthly_totals,
    yearend_totals,
)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    if st.button("🚪 Sign out", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

    st.divider()
    st.markdown("**People**")
    self_name   = st.text_input("Person 1 (Self)",   value="AK")
    spouse_name = st.text_input("Person 2 (Spouse)", value="PA")
    self_dob    = st.date_input("Person 1 DOB",   value=DEFAULT_SELF_DOB,   min_value=date(1940,1,1))
    spouse_dob  = st.date_input("Person 2 DOB",   value=DEFAULT_SPOUSE_DOB, min_value=date(1940,1,1))

# ── Account types display names ───────────────────────────────────────────────
_ATYPE_LABEL = {
    "roth_ira":        "Roth IRA",
    "traditional_ira": "Traditional IRA",
    "401k":            "401(k)",
    "roth_401k":       "Roth 401(k)",
    "solo_401k":       "Solo 401(k)",
    "sep_ira":         "SEP IRA",
    "hsa":             "HSA",
}
_ATYPE_ICON = {
    "roth_ira":        "🌱",
    "traditional_ira": "🏛️",
    "401k":            "💼",
    "roth_401k":       "🔵",
    "solo_401k":       "🧑‍💼",
    "sep_ira":         "📋",
    "hsa":             "🏥",
}

def _label(atype: str) -> str:
    return _ATYPE_LABEL.get(atype, atype.replace("_", " ").title())

def _icon(atype: str) -> str:
    return _ATYPE_ICON.get(atype, "💰")

# ── Data loaders ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=600)
def _load_ret_accounts():
    all_accs = list_accounts()
    return [
        a for a in all_accs
        if a.get("account_type", "").lower() in RETIREMENT_ACCOUNT_TYPES
        and str(a.get("active", "TRUE")).upper() in ("TRUE", "1", "YES")
    ]

@st.cache_data(ttl=300)
def _load_history():
    return load_retirement_history()

def _compute_latest(history: list[dict]) -> dict[str, float]:
    """Derive the most-recent balance per account_id from already-cached history."""
    latest: dict[str, float] = {}
    for r in history:
        aid = r.get("account_id", "")
        if aid and aid not in latest:
            latest[aid] = float(r.get("balance", 0) or 0)
    return latest

# ── Page header ───────────────────────────────────────────────────────────────
hdr_l, hdr_r = st.columns([3, 1])
with hdr_l:
    st.title("🎯 Retirement Tracker")
    st.caption(
        f"Tracks all retirement accounts for **{self_name}** and **{spouse_name}**. "
        f"Projected through **{PROJECTION_END_YEAR}** using IRS contribution limits "
        f"(2024–2025 confirmed · 2026+ estimated)."
    )
with hdr_r:
    if st.button("🔄 Refresh data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ── Load accounts ─────────────────────────────────────────────────────────────
try:
    ret_accounts = _load_ret_accounts()
except Exception as e:
    st.error(f"Could not load accounts: {e}")
    st.stop()

if not ret_accounts:
    st.warning(
        "No retirement accounts found. "
        "Go to **Accounts** and add accounts with type: "
        "Roth IRA, Traditional IRA, 401(k), Roth 401(k), SEP IRA, or HSA. "
        "Make sure they are marked **Active**."
    )
    st.stop()

self_accs   = sorted([a for a in ret_accounts if a.get("owner") == "self"],
                     key=lambda a: a.get("account_type", ""))
spouse_accs = sorted([a for a in ret_accounts if a.get("owner") == "spouse"],
                     key=lambda a: a.get("account_type", ""))
joint_accs  = [a for a in ret_accounts if a.get("owner") == "joint"]

# ── SECURE 2.0 Roth 401k accounts check ─────────────────────────────────────
_has_self_roth401k   = any(a.get("account_type") == "roth_401k" for a in self_accs)
_has_spouse_roth401k = any(a.get("account_type") == "roth_401k" for a in spouse_accs)
current_year = datetime.now().year
if current_year >= 2026:
    missing = []
    if not _has_self_roth401k:
        missing.append(f"{self_name} Roth 401(k) (Self) — catch-up from 2025")
    # PA turns 50 in 2030
    if not _has_spouse_roth401k and current_year >= 2029:
        missing.append(f"{spouse_name} Roth 401(k) (Spouse) — catch-up from 2030")
    if missing:
        with st.expander("⚠️  Add Roth 401(k) accounts for SECURE 2.0 catch-up tracking", expanded=True):
            st.warning(
                "From 2026, 401(k) catch-up contributions must go into a **Roth 401(k)**. "
                "Add these accounts in the **Accounts** page so the projection tracks them separately:\n\n"
                + "\n".join(f"- {m}" for m in missing)
            )

tab1, tab2 = st.tabs(["📥  Balance Input", "📊  Analytics & Projections"])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Balance Input
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:

    # ── Custom card CSS ──────────────────────────────────────────────────────
    st.markdown("""
    <style>
    .ret-label  { font-size:12px; color:#94a3b8; font-weight:600; margin-bottom:2px; }
    .ret-last   { font-size:11px; color:#64748b; margin-top:4px; }
    .ret-section{ font-size:17px; font-weight:700; margin:8px 0 4px 0; }
    </style>
    """, unsafe_allow_html=True)

    # ── Date + hint ──────────────────────────────────────────────────────────
    d_col, hint_col = st.columns([2, 5])
    with d_col:
        snap_date = st.date_input("📅 Snapshot Date", value=date.today())
    with hint_col:
        st.info(
            "Enter the **current balance** for each account. "
            "Balances are saved with the snapshot date — you can record as often as you like. "
            "Check **Skip** to exclude an account from the projection without deleting history."
        )

    try:
        last_bal = _compute_latest(_load_history())
    except Exception:
        last_bal = {}

    # ── Track inputs ─────────────────────────────────────────────────────────
    balance_inputs: dict[str, float] = {}
    skip_set: set[str] = set(st.session_state.get("ret_excluded", set()))

    def _account_card(acc: dict, col_ctx):
        """Render one account input block inside a given column context."""
        aid   = acc["account_id"]
        atype = acc.get("account_type", "")
        aname = acc.get("account_name", "Unknown")
        icon  = _icon(atype)
        typ_label = _label(atype)
        last  = float(last_bal.get(aid, 0) or 0)

        with col_ctx:
            st.markdown(
                f'<div class="ret-label">{icon} {aname}'
                f'<span style="color:#475569;font-weight:400"> · {typ_label}</span></div>',
                unsafe_allow_html=True,
            )
            bal = st.number_input(
                "Balance ($)", min_value=0.0, value=last, step=500.0,
                format="%.2f", key=f"bal_{aid}", label_visibility="collapsed",
            )
            skipped = st.checkbox("⏭ Skip projection", key=f"skip_{aid}",
                                  value=aid in skip_set)
            last_str = f"Last: {fmt_currency(last)}" if last else "Last: —"
            st.markdown(f'<div class="ret-last">{last_str}</div>', unsafe_allow_html=True)
            st.markdown("<div style='margin-bottom:16px'></div>", unsafe_allow_html=True)

        balance_inputs[aid] = bal
        if skipped:
            skip_set.add(aid)
        else:
            skip_set.discard(aid)

    # ── Two-column layout: Self | Spouse ─────────────────────────────────────
    c_self, c_spouse = st.columns(2, gap="large")

    with c_self:
        st.markdown(
            f'<div class="ret-section">👤 {self_name} <span style="color:#475569;'
            f'font-size:13px;font-weight:400">(Self)</span></div>',
            unsafe_allow_html=True,
        )
        st.markdown("---")
        if self_accs:
            # Group by 2 per row within this column
            pairs = [self_accs[i:i+2] for i in range(0, len(self_accs), 2)]
            for pair in pairs:
                sub_cols = st.columns(len(pair), gap="medium")
                for acc, sc in zip(pair, sub_cols):
                    _account_card(acc, sc)
        else:
            st.caption("No Self accounts found.")

    with c_spouse:
        st.markdown(
            f'<div class="ret-section">👥 {spouse_name} <span style="color:#475569;'
            f'font-size:13px;font-weight:400">(Spouse)</span></div>',
            unsafe_allow_html=True,
        )
        st.markdown("---")
        if spouse_accs:
            pairs = [spouse_accs[i:i+2] for i in range(0, len(spouse_accs), 2)]
            for pair in pairs:
                sub_cols = st.columns(len(pair), gap="medium")
                for acc, sc in zip(pair, sub_cols):
                    _account_card(acc, sc)
        else:
            st.caption("No Spouse accounts found.")

    if joint_accs:
        st.markdown("---")
        st.markdown('<div class="ret-section">🤝 Joint Accounts</div>', unsafe_allow_html=True)
        j_cols = st.columns(min(len(joint_accs), 3), gap="medium")
        for acc, jc in zip(joint_accs, j_cols):
            _account_card(acc, jc)

    st.session_state["ret_excluded"] = skip_set

    # ── Save button ──────────────────────────────────────────────────────────
    st.markdown("---")
    sv_col, _ = st.columns([2, 5])
    with sv_col:
        if st.button("💾  Save All Balances", type="primary", use_container_width=True):
            entries = [
                {
                    "account_id":   aid,
                    "account_name": next(
                        (a["account_name"] for a in ret_accounts if a["account_id"] == aid), aid
                    ),
                    "balance": bal,
                }
                for aid, bal in balance_inputs.items()
                if bal > 0
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

    # ── IRS limits quick reference ───────────────────────────────────────────
    with st.expander("📋 IRS Contribution Limits Reference (2024 – 2040)", expanded=False):
        limit_rows = []
        for yr, lim in sorted(IRS_LIMITS.items()):
            limit_rows.append({
                "Year":        yr,
                "401k Regular": lim["irs_401k"],
                "401k Catch-up (50+)": lim["irs_401k_cu"],
                "IRA":         lim["ira"],
                "IRA Catch-up (50+)": lim["ira_cu"],
                "HSA (Self)":  lim["hsa_self"],
                "HSA (Family)": lim["hsa_fam"],
                "Status":      "✅ Confirmed" if lim["confirmed"] else "📊 Estimated",
            })
        df_lim = pd.DataFrame(limit_rows)
        st.dataframe(
            df_lim, hide_index=True, use_container_width=True,
            column_config={
                "401k Regular":        st.column_config.NumberColumn(format="$%d"),
                "401k Catch-up (50+)": st.column_config.NumberColumn(format="$%d"),
                "IRA":                 st.column_config.NumberColumn(format="$%d"),
                "IRA Catch-up (50+)":  st.column_config.NumberColumn(format="$%d"),
                "HSA (Self)":          st.column_config.NumberColumn(format="$%d"),
                "HSA (Family)":        st.column_config.NumberColumn(format="$%d"),
            },
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Analytics & Projections
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:

    # ── Controls ─────────────────────────────────────────────────────────────
    ctrl1, ctrl2, ctrl3 = st.columns([3, 2, 3])
    with ctrl1:
        growth_pct = st.slider(
            "📈 Annual Growth Rate", min_value=3.0, max_value=15.0,
            value=7.0, step=0.5, format="%.1f%%",
        )
        growth_rate = growth_pct / 100
    with ctrl2:
        proj_start = st.number_input(
            "Projection Start Year",
            min_value=2024, max_value=current_year,
            value=current_year,
        )
    with ctrl3:
        st.markdown("<br>", unsafe_allow_html=True)
        st.caption(
            "IRS limits: ✅ 2024–2025 confirmed · 📊 2026+ projected estimates. "
            "Contributions assumed at year-end; growth applied on opening balance first."
        )

    # ── Load data ─────────────────────────────────────────────────────────────
    try:
        history = _load_history()
        latest  = _compute_latest(history)
    except Exception as exc:
        st.error(f"Could not load history: {exc}")
        st.stop()

    if not history:
        st.info("No balance data yet — use the **Balance Input** tab to record your first snapshot.")
        st.stop()

    excluded = st.session_state.get("ret_excluded", set())

    # ── Project ───────────────────────────────────────────────────────────────
    proj_df = project_retirement(
        ret_accounts, latest, growth_rate=growth_rate,
        excluded=excluded, self_dob=self_dob, spouse_dob=spouse_dob,
        start_year=int(proj_start),
    )

    # ── Totals ────────────────────────────────────────────────────────────────
    total_now    = sum(v for aid, v in latest.items() if aid not in excluded)
    self_now     = sum(v for aid, v in latest.items()
                       if aid not in excluded
                       and any(a["account_id"]==aid and a.get("owner")=="self"   for a in ret_accounts))
    spouse_now   = sum(v for aid, v in latest.items()
                       if aid not in excluded
                       and any(a["account_id"]==aid and a.get("owner")=="spouse" for a in ret_accounts))

    proj_2040    = 0.0
    self_2040    = 0.0
    spouse_2040  = 0.0
    if not proj_df.empty and PROJECTION_END_YEAR in proj_df["year"].values:
        yr2040 = proj_df[proj_df["year"] == PROJECTION_END_YEAR]
        proj_2040   = yr2040["balance"].sum()
        self_2040   = yr2040[yr2040["owner"] == "self"]["balance"].sum()
        spouse_2040 = yr2040[yr2040["owner"] == "spouse"]["balance"].sum()

    # ── KPI cards ─────────────────────────────────────────────────────────────
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Combined Balance", fmt_currency(total_now))
    k2.metric(f"{self_name} Balance", fmt_currency(self_now))
    k3.metric(f"{spouse_name} Balance", fmt_currency(spouse_now))
    k4.metric(f"Projected {PROJECTION_END_YEAR}",
              fmt_currency(proj_2040),
              delta=f"+{fmt_currency(proj_2040 - total_now)}" if total_now else None)
    years_left = PROJECTION_END_YEAR - current_year
    ak_age_2040 = PROJECTION_END_YEAR - self_dob.year
    pa_age_2040 = PROJECTION_END_YEAR - spouse_dob.year
    k5.metric("Years to 2040", f"{years_left}y",
              delta=f"{self_name} {ak_age_2040} · {spouse_name} {pa_age_2040}")

    st.divider()

    # ── History: line chart + pie ─────────────────────────────────────────────
    df_h = pd.DataFrame(history)
    df_h["date"]    = pd.to_datetime(df_h["date"], errors="coerce")
    df_h["balance"] = pd.to_numeric(df_h["balance"], errors="coerce").fillna(0)
    aid_owner = {a["account_id"]: a.get("owner","?") for a in ret_accounts}
    df_h["owner"] = df_h["account_id"].map(aid_owner)

    hist_col, pie_col = st.columns([2, 1])

    with hist_col:
        st.subheader("📈 Balance Over Time")
        fig_hist = go.Figure()
        color_self   = "#10b981"
        color_spouse = "#f59e0b"
        color_pool   = {
            "roth_ira": "#06b6d4", "traditional_ira": "#8b5cf6",
            "401k": "#3b82f6", "roth_401k": "#60a5fa",
            "hsa": "#f97316", "sep_ira": "#ec4899", "solo_401k": "#a78bfa",
        }

        for acc in ret_accounts:
            aid   = acc["account_id"]
            aname = acc["account_name"]
            atype = acc.get("account_type","")
            df_acc = df_h[df_h["account_id"] == aid].sort_values("date")
            if df_acc.empty:
                continue
            fig_hist.add_trace(go.Scatter(
                x=df_acc["date"], y=df_acc["balance"],
                name=aname, mode="lines+markers",
                line=dict(width=1.5, color=color_pool.get(atype, "#94a3b8")),
                opacity=0.75,
                hovertemplate=f"{aname}<br>%{{x|%b %Y}}: $%{{y:,.0f}}<extra></extra>",
            ))

        # Bold combined total
        df_comb = df_h.groupby("date")["balance"].sum().reset_index().sort_values("date")
        fig_hist.add_trace(go.Scatter(
            x=df_comb["date"], y=df_comb["balance"],
            name="Combined", mode="lines+markers",
            line=dict(width=3, color="#3b82f6"),
            hovertemplate="Combined<br>%{x|%b %Y}: $%{y:,.0f}<extra></extra>",
        ))
        fig_hist.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            height=330, margin=dict(l=0, r=0, t=8, b=0),
            legend=dict(orientation="h", y=-0.32, font_size=11),
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)",
                       tickprefix="$", tickformat=",.0f"),
            hovermode="x unified",
        )
        st.plotly_chart(fig_hist, use_container_width=True)

    with pie_col:
        st.subheader("🥧 Current Allocation")
        pie_labels, pie_vals, pie_colors = [], [], []
        _palette = px.colors.qualitative.Set2
        for i, acc in enumerate(ret_accounts):
            bal = latest.get(acc["account_id"], 0)
            if bal > 0 and acc["account_id"] not in excluded:
                pie_labels.append(acc["account_name"])
                pie_vals.append(bal)
                pie_colors.append(_palette[i % len(_palette)])
        if pie_labels:
            fig_pie = go.Figure(go.Pie(
                labels=pie_labels, values=pie_vals,
                hole=0.55,
                marker=dict(colors=pie_colors),
                textinfo="percent",
                hovertemplate="%{label}<br>$%{value:,.0f} (%{percent})<extra></extra>",
            ))
            fig_pie.add_annotation(
                text=fmt_currency(total_now), x=0.5, y=0.5,
                font=dict(size=15, color="white"), showarrow=False,
            )
            fig_pie.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=0, r=0, t=8, b=0), height=330,
                legend=dict(orientation="v", font_size=10),
            )
            st.plotly_chart(fig_pie, use_container_width=True)

    st.divider()

    # ── Self vs Spouse side-by-side bar ───────────────────────────────────────
    st.subheader(f"👤 {self_name} vs 👥 {spouse_name} — Balance by Account")
    cmp_rows = []
    for acc in ret_accounts:
        aid = acc["account_id"]
        if aid in excluded:
            continue
        cmp_rows.append({
            "Account":  acc["account_name"],
            "Person":   self_name if acc.get("owner") == "self" else
                        (spouse_name if acc.get("owner") == "spouse" else "Joint"),
            "Balance":  latest.get(aid, 0),
            "Type":     _label(acc.get("account_type","")),
        })
    if cmp_rows:
        df_cmp = pd.DataFrame(cmp_rows)
        fig_cmp = px.bar(
            df_cmp, x="Account", y="Balance", color="Person",
            barmode="group",
            color_discrete_map={self_name: "#10b981", spouse_name: "#f59e0b", "Joint": "#3b82f6"},
            text="Balance",
        )
        fig_cmp.update_traces(
            texttemplate="$%{text:,.0f}", textposition="outside",
            hovertemplate="%{x}<br>$%{y:,.0f}<extra></extra>",
        )
        fig_cmp.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            height=300, margin=dict(l=0, r=0, t=8, b=0),
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)",
                       tickprefix="$", tickformat=",.0f"),
        )
        st.plotly_chart(fig_cmp, use_container_width=True)

    st.divider()

    # ── Monthly trend (last 8 months) ─────────────────────────────────────────
    st.subheader("📅 Monthly Trend — Last 8 Months")
    df_mo = monthly_totals(history, months=8)

    if df_mo.empty:
        st.info("Not enough history for monthly trend yet.")
    else:
        mo_chart, mo_table = st.columns([1.6, 1])
        with mo_chart:
            fig_mo = go.Figure(go.Bar(
                x=df_mo["month_str"], y=df_mo["total"],
                marker_color="#3b82f6",
                text=df_mo["total"].apply(lambda v: f"${v/1e6:.2f}M" if v >= 1e6 else f"${v:,.0f}"),
                textposition="outside",
                hovertemplate="%{x}<br>$%{y:,.0f}<extra></extra>",
            ))
            fig_mo.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                height=260, margin=dict(l=0, r=0, t=10, b=0),
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)",
                           tickprefix="$", tickformat=",.0f"),
            )
            st.plotly_chart(fig_mo, use_container_width=True)
        with mo_table:
            df_mo_show = df_mo[["month_str", "total", "mom_change"]].copy()
            df_mo_show.columns = ["Month", "Total", "MoM Change"]
            st.dataframe(
                df_mo_show, use_container_width=True, hide_index=True, height=260,
                column_config={
                    "Total":      st.column_config.NumberColumn(format="$%.0f"),
                    "MoM Change": st.column_config.NumberColumn(format="$%.0f"),
                },
            )

    st.divider()

    # ── Year-end balances ─────────────────────────────────────────────────────
    st.subheader("📆 Year-End Balances (Historical)")
    df_ye = yearend_totals(history)

    if df_ye.empty:
        st.info("Not enough history for year-end summary yet.")
    else:
        ye_chart, ye_table = st.columns([1.6, 1])
        with ye_chart:
            bar_colors = []
            for i, row in df_ye.iterrows():
                if i == 0 or pd.isna(row["yoy_change"]):
                    bar_colors.append("#3b82f6")
                elif row["yoy_change"] >= 0:
                    bar_colors.append("#10b981")
                else:
                    bar_colors.append("#ef4444")

            fig_ye = go.Figure(go.Bar(
                x=df_ye["year"].astype(str), y=df_ye["total"],
                marker_color=bar_colors,
                text=df_ye["total"].apply(lambda v: f"${v/1e6:.2f}M" if v >= 1e6 else f"${v:,.0f}"),
                textposition="outside",
                hovertemplate="Year %{x}<br>$%{y:,.0f}<extra></extra>",
            ))
            fig_ye.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                height=260, margin=dict(l=0, r=0, t=10, b=0),
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)",
                           tickprefix="$", tickformat=",.0f"),
            )
            st.plotly_chart(fig_ye, use_container_width=True)
        with ye_table:
            df_ye_show = df_ye[["year","total","yoy_change","yoy_pct"]].copy()
            df_ye_show.columns = ["Year", "Balance", "YoY $", "YoY %"]
            st.dataframe(
                df_ye_show, use_container_width=True, hide_index=True, height=260,
                column_config={
                    "Balance":  st.column_config.NumberColumn(format="$%.0f"),
                    "YoY $":    st.column_config.NumberColumn(format="$%.0f"),
                    "YoY %":    st.column_config.NumberColumn(format="%.1f%%"),
                },
            )

    st.divider()

    # ── Projection to 2040 ────────────────────────────────────────────────────
    st.subheader(f"🔮 Projection to {PROJECTION_END_YEAR}  ·  {growth_pct:.1f}% Annual Growth")

    if proj_df.empty:
        st.info("No starting balances — record some data in the Balance Input tab first.")
    else:
        proj_comb   = proj_df.groupby("year")["balance"].sum().reset_index()
        proj_self   = proj_df[proj_df["owner"]=="self"].groupby("year")["balance"].sum().reset_index()
        proj_spouse = proj_df[proj_df["owner"]=="spouse"].groupby("year")["balance"].sum().reset_index()

        fig_proj = go.Figure()
        fig_proj.add_trace(go.Scatter(
            x=proj_self["year"], y=proj_self["balance"],
            name=f"{self_name} (Self)", fill="tozeroy",
            line=dict(color="#10b981", width=2),
            fillcolor="rgba(16,185,129,0.12)",
            hovertemplate=f"{self_name} %{{x}}: $%{{y:,.0f}}<extra></extra>",
        ))
        fig_proj.add_trace(go.Scatter(
            x=proj_spouse["year"], y=proj_spouse["balance"],
            name=f"{spouse_name} (Spouse)", fill="tozeroy",
            line=dict(color="#f59e0b", width=2),
            fillcolor="rgba(245,158,11,0.12)",
            hovertemplate=f"{spouse_name} %{{x}}: $%{{y:,.0f}}<extra></extra>",
        ))
        fig_proj.add_trace(go.Scatter(
            x=proj_comb["year"], y=proj_comb["balance"],
            name="Combined", line=dict(color="#3b82f6", width=3),
            hovertemplate="Combined %{x}: $%{y:,.0f}<extra></extra>",
        ))

        # Milestone reference lines
        max_proj = proj_comb["balance"].max()
        for target, lbl in [(500_000,"$500K"),(1_000_000,"$1M"),(1_500_000,"$1.5M"),(2_000_000,"$2M"),(3_000_000,"$3M")]:
            if max_proj >= target * 0.8:
                fig_proj.add_hline(
                    y=target, line_dash="dot", line_color="rgba(255,255,255,0.18)",
                    annotation_text=lbl, annotation_position="right",
                    annotation_font_size=11,
                )

        fig_proj.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            height=400, margin=dict(l=0, r=70, t=8, b=0),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis=dict(showgrid=False, dtick=1, tickangle=-45),
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)",
                       tickprefix="$", tickformat=",.0f"),
            hovermode="x unified",
        )
        st.plotly_chart(fig_proj, use_container_width=True)

        # ── Growth vs Contributions stacked waterfall ─────────────────────────
        st.subheader("💰 Annual Contributions by Account")
        contrib_df = proj_df[proj_df["contribution"] > 0].copy()
        if not contrib_df.empty:
            fig_cont = px.bar(
                contrib_df, x="year", y="contribution", color="account_name",
                barmode="stack",
                labels={"contribution": "Contribution ($)", "year": "Year",
                        "account_name": "Account"},
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig_cont.update_traces(
                hovertemplate="%{fullData.name}<br>%{x}: $%{y:,.0f}<extra></extra>"
            )
            fig_cont.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                height=300, margin=dict(l=0, r=0, t=8, b=0),
                legend=dict(orientation="h", y=-0.4, font_size=10),
                xaxis=dict(showgrid=False, dtick=1, tickangle=-45),
                yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)",
                           tickprefix="$", tickformat=",.0f"),
            )
            st.plotly_chart(fig_cont, use_container_width=True)

        # ── Projection detail table ───────────────────────────────────────────
        with st.expander("📋 Full Projection Table (Year by Year)", expanded=False):
            _confirmed = {y for y, v in IRS_LIMITS.items() if v.get("confirmed")}
            tbl = proj_comb.copy()
            tbl = tbl.merge(proj_self.rename(columns={"balance":  f"{self_name}"}),   on="year", how="left")
            tbl = tbl.merge(proj_spouse.rename(columns={"balance": f"{spouse_name}"}), on="year", how="left")
            ann_contrib = proj_df.groupby("year")["contribution"].sum().reset_index()
            ann_growth  = proj_df.groupby("year")["growth_dollars"].sum().reset_index()
            tbl = tbl.merge(ann_contrib.rename(columns={"contribution":    "Contributions"}), on="year", how="left")
            tbl = tbl.merge(ann_growth.rename(columns={"growth_dollars": "Growth $"}),        on="year", how="left")
            tbl["IRS Status"] = tbl["year"].apply(
                lambda y: "✅ Confirmed" if y in _confirmed else "📊 Estimated"
            )
            tbl.rename(columns={"year": "Year", "balance": "Combined"}, inplace=True)
            st.dataframe(
                tbl, hide_index=True, use_container_width=True,
                column_config={
                    "Combined":      st.column_config.NumberColumn(format="$%.0f"),
                    f"{self_name}":  st.column_config.NumberColumn(format="$%.0f"),
                    f"{spouse_name}": st.column_config.NumberColumn(format="$%.0f"),
                    "Contributions": st.column_config.NumberColumn(format="$%.0f"),
                    "Growth $":      st.column_config.NumberColumn(format="$%.0f"),
                },
            )

        st.divider()

        # ── Milestone tracker ─────────────────────────────────────────────────
        st.subheader("🎯 Retirement Milestones")
        milestones = [250_000, 500_000, 750_000, 1_000_000, 1_500_000, 2_000_000, 3_000_000]
        found = []
        for target in milestones:
            hit = proj_comb[proj_comb["balance"] >= target]
            if not hit.empty:
                yr = int(hit.iloc[0]["year"])
                ak_age = yr - self_dob.year
                pa_age = yr - spouse_dob.year
                found.append({
                    "label": f"${target/1e6:.2f}M" if target >= 1e6 else f"${target//1000}K",
                    "year":  yr,
                    "ak":    ak_age,
                    "pa":    pa_age,
                })

        if found:
            ms_cols = st.columns(min(len(found), 4))
            for i, m in enumerate(found):
                with ms_cols[i % 4]:
                    st.metric(
                        m["label"], str(m["year"]),
                        delta=f"{self_name} {m['ak']} · {spouse_name} {m['pa']}",
                    )
        else:
            st.info("No milestones reached in the projection — try a higher growth rate or add balances.")

        st.divider()

        # ── Cumulative: contributions vs growth breakdown ─────────────────────
        st.subheader("📊 Cumulative: Contributions vs. Investment Growth")
        cumul = proj_df.groupby("year").agg(
            total_balance=("balance", "sum"),
            total_contrib=("contribution", "sum"),
            total_growth=("growth_dollars", "sum"),
        ).reset_index()
        cumul["cum_contrib"] = cumul["total_contrib"].cumsum()
        cumul["cum_growth"]  = cumul["total_growth"].cumsum()

        fig_cg = go.Figure()
        fig_cg.add_trace(go.Bar(
            x=cumul["year"], y=cumul["cum_contrib"],
            name="Cumulative Contributions",
            marker_color="#10b981",
            hovertemplate="Year %{x}<br>Contributions: $%{y:,.0f}<extra></extra>",
        ))
        fig_cg.add_trace(go.Bar(
            x=cumul["year"], y=cumul["cum_growth"],
            name="Cumulative Investment Growth",
            marker_color="#3b82f6",
            hovertemplate="Year %{x}<br>Growth: $%{y:,.0f}<extra></extra>",
        ))
        fig_cg.update_layout(
            barmode="stack",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            height=300, margin=dict(l=0, r=0, t=8, b=0),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis=dict(showgrid=False, dtick=1, tickangle=-45),
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)",
                       tickprefix="$", tickformat=",.0f"),
        )
        st.plotly_chart(fig_cg, use_container_width=True)
