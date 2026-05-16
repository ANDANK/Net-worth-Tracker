"""
Retirement tracker service.

Handles:
- IRS contribution limits 2024–2040 (confirmed through 2025, estimated beyond)
- Balance snapshot save / load
- Year-over-year and monthly aggregations
- Projection engine: annual growth + IRS-max contributions to 2040
"""
from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import date, datetime
from typing import Optional

import pandas as pd

from google_sheets.client import sheets_client

# ── Account types treated as retirement ───────────────────────────────────────
RETIREMENT_ACCOUNT_TYPES: frozenset[str] = frozenset(
    {"roth_ira", "traditional_ira", "401k", "roth_401k", "solo_401k", "sep_ira", "hsa"}
)

PROJECTION_END_YEAR = 2040

# Default dates of birth (fake but user-specified)
DEFAULT_SELF_DOB   = date(1975, 1,  1)   # AK
DEFAULT_SPOUSE_DOB = date(1980, 10, 1)   # PA

# ── IRS contribution limits ───────────────────────────────────────────────────
# Sources:
#   2024-2025 → IRS Rev. Proc. 2023-34 / 2024-40 (confirmed)
#   2026+     → projected from historical ~3 % COLA, rounded to $500 increments
#
# Keys:
#   401k          – employee elective deferral (traditional)
#   401k_catchup  – 50+ catch-up (pre-2026: all traditional; 2026+: must be Roth)
#   ira           – Roth / Traditional IRA base
#   ira_catchup   – 50+ IRA catch-up (always traditional allowed)
#   hsa_self      – self-only HDHP HSA
#   hsa_family    – family HDHP HSA
#   confirmed     – True if the limit is an official IRS figure
IRS_LIMITS: dict[int, dict] = {
    2024: dict(confirmed=True,  irs_401k=23_000, irs_401k_cu=7_500,  ira=7_000, ira_cu=1_000, hsa_self=4_150, hsa_fam=8_300),
    2025: dict(confirmed=True,  irs_401k=23_500, irs_401k_cu=7_500,  ira=7_000, ira_cu=1_000, hsa_self=4_300, hsa_fam=8_550),
    2026: dict(confirmed=False, irs_401k=24_000, irs_401k_cu=7_500,  ira=7_500, ira_cu=1_000, hsa_self=4_450, hsa_fam=8_900),
    2027: dict(confirmed=False, irs_401k=24_000, irs_401k_cu=8_000,  ira=7_500, ira_cu=1_000, hsa_self=4_600, hsa_fam=9_200),
    2028: dict(confirmed=False, irs_401k=24_500, irs_401k_cu=8_000,  ira=7_500, ira_cu=1_000, hsa_self=4_750, hsa_fam=9_500),
    2029: dict(confirmed=False, irs_401k=25_000, irs_401k_cu=8_000,  ira=8_000, ira_cu=1_000, hsa_self=4_900, hsa_fam=9_800),
    2030: dict(confirmed=False, irs_401k=25_000, irs_401k_cu=8_500,  ira=8_000, ira_cu=1_000, hsa_self=5_050, hsa_fam=10_100),
    2031: dict(confirmed=False, irs_401k=25_500, irs_401k_cu=8_500,  ira=8_000, ira_cu=1_000, hsa_self=5_200, hsa_fam=10_400),
    2032: dict(confirmed=False, irs_401k=26_000, irs_401k_cu=9_000,  ira=8_500, ira_cu=1_000, hsa_self=5_350, hsa_fam=10_700),
    2033: dict(confirmed=False, irs_401k=26_000, irs_401k_cu=9_000,  ira=8_500, ira_cu=1_000, hsa_self=5_500, hsa_fam=11_000),
    2034: dict(confirmed=False, irs_401k=26_500, irs_401k_cu=9_500,  ira=9_000, ira_cu=1_000, hsa_self=5_650, hsa_fam=11_300),
    2035: dict(confirmed=False, irs_401k=27_000, irs_401k_cu=9_500,  ira=9_000, ira_cu=1_000, hsa_self=5_800, hsa_fam=11_600),
    2036: dict(confirmed=False, irs_401k=27_000, irs_401k_cu=10_000, ira=9_000, ira_cu=1_000, hsa_self=5_950, hsa_fam=11_900),
    2037: dict(confirmed=False, irs_401k=27_500, irs_401k_cu=10_000, ira=9_500, ira_cu=1_000, hsa_self=6_100, hsa_fam=12_200),
    2038: dict(confirmed=False, irs_401k=28_000, irs_401k_cu=10_000, ira=9_500, ira_cu=1_000, hsa_self=6_250, hsa_fam=12_500),
    2039: dict(confirmed=False, irs_401k=28_000, irs_401k_cu=10_500, ira=10_000, ira_cu=1_000, hsa_self=6_400, hsa_fam=12_800),
    2040: dict(confirmed=False, irs_401k=28_500, irs_401k_cu=10_500, ira=10_000, ira_cu=1_000, hsa_self=6_550, hsa_fam=13_100),
}


def _limits(year: int) -> dict:
    """Return the IRS limit row for `year`, clamped to the table boundaries."""
    years = sorted(IRS_LIMITS)
    if year <= years[0]:
        return IRS_LIMITS[years[0]]
    if year >= years[-1]:
        return IRS_LIMITS[years[-1]]
    return IRS_LIMITS.get(year, IRS_LIMITS[years[-1]])


def _age_at_year_end(dob: date, year: int) -> int:
    ye = date(year, 12, 31)
    age = ye.year - dob.year
    if (ye.month, ye.day) < (dob.month, dob.day):
        age -= 1
    return age


# ── Contribution calculator ───────────────────────────────────────────────────

def get_annual_contribution(
    account_type: str,
    owner: str,               # "self" | "spouse"
    year: int,
    self_dob:   date = DEFAULT_SELF_DOB,
    spouse_dob: date = DEFAULT_SPOUSE_DOB,
) -> float:
    """
    Return the maximum IRS contribution for one account in one calendar year.

    401k / Roth 401k split (SECURE 2.0, effective 2026):
      • Pre-2026:  catch-up goes entirely to traditional 401k
      • 2026+:     regular deferral → traditional 401k (account_type=401k)
                   catch-up         → Roth 401k       (account_type=roth_401k)

    HSA rules:
      • AK (self):   old HSA, no new contributions — just projects growth at chosen rate
      • PA (spouse): family HDHP → family HSA limit each year
    """
    lim  = _limits(year)
    dob  = self_dob if owner == "self" else spouse_dob
    age  = _age_at_year_end(dob, year)
    cu50 = age >= 50          # standard 50+ catch-up eligibility

    t = account_type.lower()

    # ── IRA (Roth or Traditional) ────────────────────────────────────────────
    if t in ("roth_ira", "traditional_ira"):
        return lim["ira"] + (lim["ira_cu"] if cu50 else 0)

    # ── Traditional 401k (incl. solo) ───────────────────────────────────────
    if t in ("401k", "solo_401k"):
        base = lim["irs_401k"]
        if cu50 and year < 2026:
            # Pre-2026 SECURE 2.0: catch-up stays in traditional 401k
            return base + lim["irs_401k_cu"]
        # 2026+: catch-up is now Roth 401k — traditional gets base only
        return base

    # ── Roth 401k — SECURE 2.0 catch-up (2026+) ─────────────────────────────
    if t == "roth_401k":
        if year < 2026:
            return 0.0          # no Roth 401k catch-up mandated before 2026
        return lim["irs_401k_cu"] if cu50 else 0.0

    # ── HSA ──────────────────────────────────────────────────────────────────
    if t == "hsa":
        if owner == "self":
            return 0.0          # AK's old HSA: no new contributions (per user)
        return lim["hsa_fam"]   # PA has family HDHP

    # ── SEP-IRA ──────────────────────────────────────────────────────────────
    # Limit is 25 % of compensation (up to ~$69K); we can't know salary,
    # so return 0 and let the user's actual saved balances drive history.
    if t == "sep_ira":
        return 0.0

    return 0.0


# ── Snapshot persistence ──────────────────────────────────────────────────────

def save_retirement_snapshot(entries: list[dict], snapshot_date: str) -> None:
    """
    Persist a batch of balance entries.

    Parameters
    ----------
    entries : list of {"account_id", "account_name", "balance"}
    snapshot_date : ISO date string, e.g. "2026-05-16"
    """
    ts   = datetime.utcnow().isoformat()
    rows = []
    for e in entries:
        rows.append([
            str(uuid.uuid4())[:16],
            snapshot_date,
            e["account_id"],
            e["account_name"],
            round(float(e["balance"]), 2),
            ts,
        ])
    sheets_client.append_rows_batch("retirement_balances", rows)


def load_retirement_history() -> list[dict]:
    """Return all saved snapshots, newest first."""
    records = sheets_client.get_all_records("retirement_balances")
    for r in records:
        try:
            r["balance"] = float(r["balance"])
        except (ValueError, TypeError):
            r["balance"] = 0.0
    records.sort(
        key=lambda r: (r.get("date", ""), r.get("upload_timestamp", "")),
        reverse=True,
    )
    return records


def get_latest_balances() -> dict[str, float]:
    """Return the most-recent balance for every account_id."""
    history = load_retirement_history()
    latest: dict[str, float] = {}
    for r in history:
        aid = r.get("account_id", "")
        if aid and aid not in latest:
            latest[aid] = float(r.get("balance", 0) or 0)
    return latest


# ── Monthly / yearly aggregation helpers ─────────────────────────────────────

def monthly_totals(history: list[dict], months: int = 8) -> pd.DataFrame:
    """
    Returns a DataFrame with columns [month_str, total, mom_change]
    covering the last `months` calendar months that have data.
    """
    if not history:
        return pd.DataFrame(columns=["month_str", "total", "mom_change"])

    df = pd.DataFrame(history)
    df["date"]    = pd.to_datetime(df["date"], errors="coerce")
    df["balance"] = pd.to_numeric(df["balance"], errors="coerce").fillna(0)
    df["month"]   = df["date"].dt.to_period("M")

    # Latest balance per account per month
    last_per_month = (
        df.sort_values("date")
        .groupby(["month", "account_id"])["balance"]
        .last()
        .reset_index()
    )
    totals = last_per_month.groupby("month")["balance"].sum().reset_index()
    totals = totals.sort_values("month").tail(months).reset_index(drop=True)
    totals["month_str"]  = totals["month"].astype(str)
    totals["mom_change"] = totals["balance"].diff()
    return totals[["month_str", "balance", "mom_change"]].rename(columns={"balance": "total"})


def yearend_totals(history: list[dict]) -> pd.DataFrame:
    """
    Returns a DataFrame with columns [year, total, yoy_change, yoy_pct]
    using the last snapshot of each calendar year per account.
    """
    if not history:
        return pd.DataFrame(columns=["year", "total", "yoy_change", "yoy_pct"])

    df = pd.DataFrame(history)
    df["date"]    = pd.to_datetime(df["date"], errors="coerce")
    df["balance"] = pd.to_numeric(df["balance"], errors="coerce").fillna(0)
    df["year"]    = df["date"].dt.year

    last_per_year = (
        df.sort_values("date")
        .groupby(["year", "account_id"])["balance"]
        .last()
        .reset_index()
    )
    totals = last_per_year.groupby("year")["balance"].sum().reset_index()
    totals = totals.sort_values("year").reset_index(drop=True)
    totals.rename(columns={"balance": "total"}, inplace=True)
    totals["yoy_change"] = totals["total"].diff()
    totals["yoy_pct"]    = totals["total"].pct_change() * 100
    return totals


# ── Projection engine ─────────────────────────────────────────────────────────

def project_retirement(
    accounts:    list[dict],
    start_balances: dict[str, float],
    growth_rate: float = 0.07,
    excluded:    Optional[set] = None,
    self_dob:    date = DEFAULT_SELF_DOB,
    spouse_dob:  date = DEFAULT_SPOUSE_DOB,
    start_year:  Optional[int] = None,
    end_year:    int = PROJECTION_END_YEAR,
) -> pd.DataFrame:
    """
    Project retirement balances year-by-year to `end_year`.

    Mechanics
    ---------
    Each year:
      1. Grow the opening balance:  balance *= (1 + growth_rate)
      2. Add IRS-max contribution at year-end (no contribution if excluded or 0)

    Returns a DataFrame with one row per (year, account).
    Columns: year, account_id, account_name, account_type, owner,
             balance, contribution, growth_dollars
    """
    if excluded is None:
        excluded = set()
    if start_year is None:
        start_year = datetime.now().year

    active_accounts = [a for a in accounts if a["account_id"] not in excluded]

    balances: dict[str, float] = {
        a["account_id"]: float(start_balances.get(a["account_id"], 0))
        for a in active_accounts
    }

    rows = []
    for year in range(start_year, end_year + 1):
        for acc in active_accounts:
            aid   = acc["account_id"]
            atype = acc.get("account_type", "")
            owner = acc.get("owner", "self")

            bal_open   = balances.get(aid, 0.0)
            growth_$   = bal_open * growth_rate
            bal_grown  = bal_open + growth_$
            contrib    = get_annual_contribution(atype, owner, year, self_dob, spouse_dob)
            bal_close  = bal_grown + contrib
            balances[aid] = bal_close

            rows.append({
                "year":          year,
                "account_id":    aid,
                "account_name":  acc.get("account_name", ""),
                "account_type":  atype,
                "owner":         owner,
                "balance":       round(bal_close, 2),
                "contribution":  round(contrib, 2),
                "growth_dollars": round(growth_$, 2),
            })

    return pd.DataFrame(rows) if rows else pd.DataFrame()
