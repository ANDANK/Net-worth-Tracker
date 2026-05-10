"""Net worth history and dashboard aggregation."""
from datetime import datetime
from google_sheets.client import sheets_client
from services.manual_accounts import get_latest_manual_values
from models.schemas import DashboardSummary, NetWorthEntry

RETIREMENT_TYPES = {"401k", "roth_ira", "traditional_ira", "solo_401k", "sep_ira", "hsa", "fsa"}
CASH_TYPES = {"savings", "checking", "cd", "treasury"}
CRYPTO_TYPES = {"crypto"}
REAL_ESTATE_TYPES = {"real_estate"}


def record_networth_snapshot(
    investment_value: float,
    retirement_value: float,
    cash_value: float,
    crypto_value: float = 0,
    real_estate_value: float = 0,
    liabilities: float = 0,
) -> dict:
    today = datetime.utcnow().strftime("%Y-%m-%d")
    total_assets = investment_value + retirement_value + cash_value + crypto_value + real_estate_value
    net_worth = total_assets - liabilities
    row = [today, total_assets, liabilities, net_worth, investment_value, retirement_value, cash_value]
    sheets_client.append_row("networth", row)
    return {
        "date": today,
        "total_assets": total_assets,
        "total_liabilities": liabilities,
        "net_worth": net_worth,
        "investment_value": investment_value,
        "retirement_value": retirement_value,
        "cash_value": cash_value,
    }


def get_networth_history(period: str = "all") -> list[dict]:
    records = sheets_client.get_all_records("networth")
    records.sort(key=lambda r: r.get("date", ""))

    if not records:
        return records

    if period == "1m":
        cutoff = _months_ago(1)
    elif period == "3m":
        cutoff = _months_ago(3)
    elif period == "1y":
        cutoff = _months_ago(12)
    elif period == "5y":
        cutoff = _months_ago(60)
    else:
        return records

    return [r for r in records if r.get("date", "") >= cutoff]


def get_dashboard_summary() -> dict:
    history = get_networth_history("all")
    manual = get_latest_manual_values()

    manual_retirement = sum(
        v for k, v in manual.items()
        if any(t in k.lower() for t in ["401k", "ira", "hsa", "fsa", "retirement"])
    )
    manual_cash = sum(
        v for k, v in manual.items()
        if any(t in k.lower() for t in ["savings", "checking", "cash"])
    )
    manual_crypto = sum(v for k, v in manual.items() if "crypto" in k.lower())
    manual_real_estate = sum(v for k, v in manual.items() if "real estate" in k.lower() or "property" in k.lower())
    manual_other = sum(v for k, v in manual.items()
                       if not any(t in k.lower() for t in
                                  ["401k", "ira", "hsa", "fsa", "retirement",
                                   "savings", "checking", "cash", "crypto",
                                   "real estate", "property"]))

    current = history[-1] if history else {}
    previous_month = history[-2] if len(history) >= 2 else {}
    start_of_year = _get_start_of_year_record(history)

    current_nw = _safe_float(current.get("net_worth", 0)) + sum(manual.values())
    prev_nw = _safe_float(previous_month.get("net_worth", 0)) if previous_month else current_nw
    ytd_nw = _safe_float(start_of_year.get("net_worth", 0)) if start_of_year else current_nw

    monthly_change = current_nw - prev_nw
    monthly_pct = (monthly_change / prev_nw * 100) if prev_nw else 0
    ytd_change = current_nw - ytd_nw
    ytd_pct = (ytd_change / ytd_nw * 100) if ytd_nw else 0

    return {
        "total_net_worth": current_nw,
        "investment_value": _safe_float(current.get("investment_value", 0)),
        "retirement_value": _safe_float(current.get("retirement_value", 0)) + manual_retirement,
        "cash_value": _safe_float(current.get("cash_value", 0)) + manual_cash,
        "crypto_value": manual_crypto,
        "real_estate_value": manual_real_estate,
        "monthly_change": round(monthly_change, 2),
        "monthly_change_pct": round(monthly_pct, 2),
        "ytd_change": round(ytd_change, 2),
        "ytd_change_pct": round(ytd_pct, 2),
        "last_updated": current.get("date", datetime.utcnow().strftime("%Y-%m-%d")),
    }


def _safe_float(val) -> float:
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def _months_ago(n: int) -> str:
    now = datetime.utcnow()
    month = now.month - n
    year = now.year + month // 12
    month = month % 12 or 12
    return f"{year:04d}-{month:02d}-01"


def _get_start_of_year_record(history: list[dict]) -> dict | None:
    year = datetime.utcnow().year
    prefix = f"{year}-"
    for record in history:
        if record.get("date", "").startswith(prefix):
            return record
    return None
