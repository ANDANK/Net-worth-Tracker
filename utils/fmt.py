"""Formatting helpers shared across all Streamlit pages."""


def fmt_currency(value, decimals: int = 0) -> str:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "$0"
    sign = "-" if v < 0 else ""
    return f"{sign}${abs(v):,.{decimals}f}"


def fmt_pct(value, with_sign: bool = True) -> str:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "0.0%"
    fmt = f"{v:+.1f}%" if with_sign else f"{v:.1f}%"
    return fmt


def delta_str(value, prefix: str = "") -> str:
    """Returns '+$1,234' or '-$567' for st.metric delta."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return ""
    sign = "+" if v >= 0 else "-"
    return f"{sign}{prefix}${abs(v):,.0f}"
