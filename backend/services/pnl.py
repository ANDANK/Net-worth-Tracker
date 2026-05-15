"""Realized P&L and dividend income calculated from transaction history (FIFO cost basis)."""
import math
from collections import defaultdict
from datetime import datetime
from services.transactions import list_transactions

# Only these action types affect P&L.
# DEPOSIT, WITHDRAWAL, TRANSFER, SPLIT, OTHER, DUPLICATE are all excluded.
_PNL_ACTIONS = {"BUY", "SELL", "DIVIDEND", "INTEREST", "OPTION_BUY", "OPTION_SELL"}


def _period_start(period: str | None) -> str | None:
    if not period or period == "all":
        return None
    months = {"1m": 1, "3m": 3, "6m": 6, "1y": 12, "3y": 36, "5y": 60}
    n = months.get(period)
    if not n:
        return None
    now = datetime.utcnow()
    total_months = now.year * 12 + now.month - 1 - n
    year = total_months // 12
    month = total_months % 12 + 1
    return f"{year:04d}-{month:02d}-01"


def _f(v) -> float:
    try:
        return float(v)
    except (ValueError, TypeError):
        return 0.0


def _s(val) -> str:
    """
    NaN-safe string for values read back from Google Sheets.

    Two failure modes we must guard against:
    1. float('nan') — pandas / gspread can return actual NaN floats for empty cells.
       NaN is truthy in Python so  `nan or ""`  returns  nan  not  "".
    2. The *string* "nan" — if a ticker was stored as the literal text "nan"
       (because  str(float('nan')) == "nan"  slipped through at import time),
       it must also map to "" so it doesn't pollute FIFO queues or P&L buckets.
    """
    if val is None:
        return ""
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return ""
    s = str(val).strip()
    return "" if s.lower() == "nan" else s


def compute_pnl(account_id: str = None, period: str = None, ticker: str = None) -> dict:
    """
    Walk all transactions in date order.
    - Maintain FIFO buy queues per ticker for accurate cost basis.
    - Accumulate realized P&L and dividends only within the requested period.
    Returns summary metrics, per-ticker breakdown, and a cumulative timeline.
    """
    txs = list_transactions(account_id=account_id, limit=50000)
    # Ticker filter: still walk ALL buys for accurate FIFO, but restrict P&L output
    ticker_upper = ticker.upper().strip() if ticker else None
    txs_sorted = sorted(txs, key=lambda x: x.get("date", ""))

    period_start = _period_start(period)

    # FIFO buy queues: ticker -> [[remaining_qty, price_per_share], ...]
    buy_queues: dict[str, list] = defaultdict(list)

    # Period-scoped accumulators
    ticker_realized: dict[str, float] = defaultdict(float)
    ticker_proceeds: dict[str, float] = defaultdict(float)
    ticker_cost_used: dict[str, float] = defaultdict(float)
    ticker_dividends: dict[str, float] = defaultdict(float)

    # Raw events for timeline
    date_buckets: dict[str, dict] = defaultdict(lambda: {"realized": 0.0, "dividend": 0.0})

    for tx in txs_sorted:
        action = _s(tx.get("action"))
        if action not in _PNL_ACTIONS:
            continue                         # skip OTHER, DEPOSIT, TRANSFER, etc.
        ticker = _s(tx.get("ticker"))
        date_str = tx.get("date", "")
        qty = _f(tx.get("quantity"))
        price = _f(tx.get("price"))
        fees = _f(tx.get("fees"))
        total = _f(tx.get("total_amount"))
        in_period = not period_start or date_str >= period_start

        if action == "BUY" and ticker and qty > 0:
            # Derive per-share cost; prefer explicit price, fall back to total/qty
            per_share = price if price > 0 else (abs(total) / qty if qty else 0.0)
            buy_queues[ticker].append([qty, per_share])

        elif action == "SELL" and ticker and qty > 0:
            proceeds = abs(total) if total != 0 else max(qty * price - fees, 0.0)

            # FIFO cost lookup
            queue = buy_queues[ticker]
            remaining = qty
            cost = 0.0
            while remaining > 0.0001 and queue:
                lot_qty, lot_price = queue[0]
                used = min(lot_qty, remaining)
                cost += used * lot_price
                remaining -= used
                queue[0][0] -= used
                if queue[0][0] <= 0.0001:
                    queue.pop(0)

            gain = proceeds - cost

            if in_period and (not ticker_upper or ticker == ticker_upper):
                ticker_realized[ticker] += gain
                ticker_proceeds[ticker] += proceeds
                ticker_cost_used[ticker] += cost
                date_buckets[date_str]["realized"] += gain

        elif action == "DIVIDEND":
            div_amount = abs(total)
            key = ticker if ticker else "CASH"
            if in_period and div_amount > 0 and (not ticker_upper or ticker == ticker_upper or key == ticker_upper):
                ticker_dividends[key] += div_amount
                date_buckets[date_str]["dividend"] += div_amount

    # --- Cumulative timeline ---
    timeline = []
    cum_r = cum_d = 0.0
    for dt in sorted(date_buckets):
        cum_r += date_buckets[dt]["realized"]
        cum_d += date_buckets[dt]["dividend"]
        timeline.append({
            "date": dt,
            "realized": round(cum_r, 2),
            "dividends": round(cum_d, 2),
            "total": round(cum_r + cum_d, 2),
        })

    # --- Per-ticker summary ---
    all_tickers = set(ticker_realized) | set(ticker_dividends)
    by_ticker = []
    for t in sorted(all_tickers):
        r = ticker_realized.get(t, 0.0)
        d = ticker_dividends.get(t, 0.0)
        by_ticker.append({
            "ticker": t,
            "realized_gain": round(r, 2),
            "dividend_income": round(d, 2),
            "total_return": round(r + d, 2),
            "cost_basis": round(ticker_cost_used.get(t, 0.0), 2),
            "proceeds": round(ticker_proceeds.get(t, 0.0), 2),
        })
    by_ticker.sort(key=lambda x: abs(x["total_return"]), reverse=True)

    # --- Totals ---
    total_realized = sum(ticker_realized.values())
    total_dividends = sum(ticker_dividends.values())

    winners = [b for b in by_ticker if b["realized_gain"] > 0]
    losers = [b for b in by_ticker if b["realized_gain"] < 0]
    sell_count = len(winners) + len(losers)

    buys_in_period = [
        tx for tx in txs_sorted
        if tx.get("action") == "BUY"
        and (not period_start or tx.get("date", "") >= period_start)
    ]
    total_invested = sum(abs(_f(t.get("total_amount"))) for t in buys_in_period)

    return {
        "total_realized": round(total_realized, 2),
        "total_dividends": round(total_dividends, 2),
        "total_return": round(total_realized + total_dividends, 2),
        "total_invested": round(total_invested, 2),
        "win_count": len(winners),
        "loss_count": len(losers),
        "win_rate": round(len(winners) / sell_count * 100, 1) if sell_count else 0.0,
        "by_ticker": by_ticker[:50],
        "timeline": timeline,
    }


def validate_pnl(account_id: str = None) -> dict:
    """
    Walk all transactions with FIFO and detect sells whose entire cost basis
    is $0 — these occur when the matching BUY rows were silently dropped
    during import (unrecognised action codes, parse errors, etc.).
    Returns a list of affected tickers and an estimate of the inflated P&L.
    """
    txs = list_transactions(account_id=account_id, limit=50000)
    txs_sorted = sorted(txs, key=lambda x: x.get("date", ""))

    buy_queues: dict[str, list] = defaultdict(list)
    zero_basis: list[dict] = []

    for tx in txs_sorted:
        action = _s(tx.get("action"))
        if action not in _PNL_ACTIONS:
            continue
        ticker = _s(tx.get("ticker"))
        qty    = _f(tx.get("quantity"))
        price  = _f(tx.get("price"))
        total  = _f(tx.get("total_amount"))
        date_str = tx.get("date", "")

        if action == "BUY" and ticker and qty > 0:
            per_share = price if price > 0 else (abs(total) / qty if qty else 0.0)
            buy_queues[ticker].append([qty, per_share])

        elif action == "SELL" and ticker and qty > 0:
            proceeds = abs(total) if total != 0 else qty * price

            queue = buy_queues[ticker]
            remaining = qty
            cost = 0.0
            while remaining > 0.0001 and queue:
                lot_qty, lot_price = queue[0]
                used = min(lot_qty, remaining)
                cost += used * lot_price
                remaining -= used
                queue[0][0] -= used
                if queue[0][0] <= 0.0001:
                    queue.pop(0)

            # If we consumed nothing from the buy queue, cost basis = 0
            if cost == 0.0 and proceeds > 0:
                zero_basis.append({
                    "date":      date_str,
                    "ticker":    ticker,
                    "quantity":  qty,
                    "proceeds":  round(proceeds, 2),
                    "inflated_gain": round(proceeds, 2),
                    "account_id": tx.get("account_id", ""),
                })

    # Summarise by ticker
    by_ticker: dict[str, dict] = defaultdict(
        lambda: {"sell_count": 0, "inflated_gain": 0.0, "dates": []}
    )
    for s in zero_basis:
        t = s["ticker"]
        by_ticker[t]["sell_count"] += 1
        by_ticker[t]["inflated_gain"] += s["inflated_gain"]
        by_ticker[t]["dates"].append(s["date"])

    total_inflated = sum(d["inflated_gain"] for d in by_ticker.values())

    affected = sorted(
        [
            {
                "ticker":          t,
                "sell_count":      d["sell_count"],
                "inflated_gain":   round(d["inflated_gain"], 2),
                "first_sell_date": min(d["dates"]),
                "last_sell_date":  max(d["dates"]),
            }
            for t, d in by_ticker.items()
        ],
        key=lambda x: x["inflated_gain"],
        reverse=True,
    )

    return {
        "has_issues":            len(zero_basis) > 0,
        "zero_basis_sell_count": len(zero_basis),
        "total_inflated_gain":   round(total_inflated, 2),
        "affected_tickers":      affected,
        "sample_sells":          zero_basis[:30],
    }
