"""Projections page — retirement portfolio scenarios with FIRE calculator."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

st.set_page_config(page_title="Projections · NetWorth Tracker", page_icon="🔮", layout="wide")

from utils.auth import require_auth
from utils.fmt import fmt_currency
require_auth()

from services.projections import run_projection, save_projection
from models.schemas import ProjectionScenario

with st.sidebar:
    if st.button("🚪 Sign out", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

# ── Page ──────────────────────────────────────────────────────────────────────
st.title("🔮 Projections")
st.caption("Model your portfolio growth to retirement. Compare scenarios side by side.")

# ── Inputs ────────────────────────────────────────────────────────────────────
with st.form("projection_form"):
    st.subheader("Scenario Parameters")

    c1, c2, c3 = st.columns(3)
    with c1:
        scenario_name     = st.text_input("Scenario Name", value="Base Case")
        current_value     = st.number_input("Current Portfolio ($)", min_value=0.0,
                                             value=100_000.0, step=5_000.0, format="%.0f")
        monthly_contrib   = st.number_input("Monthly Contribution ($)", min_value=0.0,
                                             value=2_000.0, step=100.0, format="%.0f")
    with c2:
        current_age       = st.number_input("Current Age", min_value=18, max_value=80,
                                             value=35, step=1)
        target_age        = st.number_input("Target Retirement Age", min_value=30, max_value=90,
                                             value=65, step=1)
    with c3:
        annual_return     = st.slider("Expected Annual Return (%)", 1.0, 15.0, 7.0, 0.5)
        inflation         = st.slider("Inflation Rate (%)", 0.5, 8.0, 3.0, 0.5)

    run = st.form_submit_button("▶ Run Projection", type="primary", use_container_width=False)

if not run and "projection_result" not in st.session_state:
    st.info("Set parameters and click **Run Projection**.")
    st.stop()

if run:
    if target_age <= current_age:
        st.error("Retirement age must be greater than current age.")
        st.stop()
    try:
        scenario = ProjectionScenario(
            scenario_name=scenario_name,
            current_value=current_value,
            monthly_contribution=monthly_contrib,
            annual_return=annual_return,
            inflation=inflation,
            current_age=current_age,
            target_age=target_age,
        )
        result = run_projection(scenario)
        st.session_state["projection_result"] = result
        st.session_state["projection_scenario"] = scenario
    except Exception as e:
        st.error(f"Projection error: {e}")
        st.stop()

result   = st.session_state["projection_result"]
scenario = st.session_state["projection_scenario"]

# ── KPIs ──────────────────────────────────────────────────────────────────────
years_to_go = scenario.target_age - scenario.current_age

k1, k2, k3, k4 = st.columns(4)
k1.metric("Portfolio at Retirement", fmt_currency(result.target_value or 0))
k2.metric("In Today's Dollars",      fmt_currency((result.real_values or [0])[-1]))
k3.metric("FIRE Age",                str(result.fire_age) if result.fire_age else "Not reached")
k4.metric("Coast FIRE Value Needed", fmt_currency(result.coast_fire_value or 0))

st.divider()

# ── Growth chart ──────────────────────────────────────────────────────────────
st.subheader("Portfolio Growth")

if result.years and result.nominal_values:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=result.years, y=result.nominal_values,
        name="Nominal", fill="tozeroy",
        line=dict(color="#3b82f6", width=2),
        fillcolor="rgba(59,130,246,0.12)",
        hovertemplate="Age %{x}<br>Nominal: $%{y:,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=result.years, y=result.real_values,
        name="Real (inflation-adjusted)", line=dict(color="#8b5cf6", width=1.5, dash="dot"),
        hovertemplate="Age %{x}<br>Real: $%{y:,.0f}<extra></extra>",
    ))

    if result.fire_age:
        fire_idx = result.years.index(result.fire_age) if result.fire_age in result.years else None
        if fire_idx is not None:
            fig.add_vline(x=result.fire_age, line_dash="dash", line_color="#f59e0b",
                          annotation_text=f"FIRE age {result.fire_age}",
                          annotation_position="top right")

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=10, b=0), height=320,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(title="Age", showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)",
                   tickprefix="$", tickformat=",.0f", zeroline=False),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)

# ── Data table ────────────────────────────────────────────────────────────────
with st.expander("📋 Year-by-year data"):
    df = pd.DataFrame({
        "Age":             result.years,
        "Nominal ($)":     [round(v, 0) for v in result.nominal_values],
        "Real ($)":        [round(v, 0) for v in result.real_values],
    })
    st.dataframe(df, use_container_width=True, height=300,
                 column_config={
                     "Nominal ($)": st.column_config.NumberColumn(format="$%.0f"),
                     "Real ($)":    st.column_config.NumberColumn(format="$%.0f"),
                 })

# ── Save to Sheets ────────────────────────────────────────────────────────────
st.divider()
if st.button("💾 Save scenario to Google Sheets"):
    try:
        save_projection(scenario, result)
        st.success(f"Scenario **{scenario.scenario_name}** saved!")
    except Exception as e:
        st.error(f"Could not save: {e}")
