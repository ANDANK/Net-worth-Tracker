"""Financial metrics calculations."""
from datetime import datetime, date
from typing import Optional
import numpy as np


def cagr(start_value: float, end_value: float, years: float) -> Optional[float]:
    if start_value <= 0 or years <= 0:
        return None
    return (end_value / start_value) ** (1 / years) - 1


def total_return(start_value: float, end_value: float) -> Optional[float]:
    if start_value == 0:
        return None
    return (end_value - start_value) / start_value


def annualized_return(returns: list[float], periods_per_year: int = 252) -> Optional[float]:
    if not returns:
        return None
    r = np.array(returns)
    cumulative = np.prod(1 + r)
    years = len(returns) / periods_per_year
    if years <= 0:
        return None
    return cumulative ** (1 / years) - 1


def project_portfolio(
    current_value: float,
    monthly_contribution: float,
    annual_return: float,
    inflation: float,
    years: int,
) -> tuple[list[float], list[float]]:
    """Returns (nominal_values, real_values) for each year."""
    monthly_rate = annual_return / 12
    monthly_inflation = inflation / 12
    nominal = []
    real = []
    value = current_value

    for month in range(1, years * 12 + 1):
        value = value * (1 + monthly_rate) + monthly_contribution
        if month % 12 == 0:
            year = month // 12
            nominal.append(round(value, 2))
            real_value = value / ((1 + inflation) ** year)
            real.append(round(real_value, 2))

    return nominal, real


def fire_number(annual_expenses: float, withdrawal_rate: float = 0.04) -> float:
    return annual_expenses / withdrawal_rate


def coast_fire(
    target: float,
    current_age: int,
    retirement_age: int,
    annual_return: float,
) -> float:
    years = retirement_age - current_age
    if years <= 0:
        return target
    return target / ((1 + annual_return) ** years)


def savings_rate(income: float, savings: float) -> Optional[float]:
    if income == 0:
        return None
    return savings / income


def portfolio_concentration(holdings: list[dict]) -> dict:
    total = sum(h.get("market_value", 0) for h in holdings)
    if total == 0:
        return {}
    return {
        h["ticker"]: round(h["market_value"] / total * 100, 2)
        for h in holdings
    }


def years_between(d1: str, d2: str) -> float:
    dt1 = datetime.fromisoformat(d1)
    dt2 = datetime.fromisoformat(d2)
    return (dt2 - dt1).days / 365.25
