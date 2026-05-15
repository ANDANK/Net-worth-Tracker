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

        # ------------------------------------------------------------------
        # Effective quantity: if Quantity field is blank/zero in Sheets,
        # infer from total_amount / price.  This handles rows where the
        # broker CSV had no Quantity column (those rows contribute to the
        # pivot total_amount sum but were silently skipped in FIFO).
        # ------------------------------------------------------------------
        qty_eff = qty if qty > 0 else (
            abs(total) / price if (price > 0 and total != 0) else 0.0
        )

        if action == "BUY" and ticker and qty_eff > 0:
            per_share = price if price > 0 else (abs(total) / qty_eff)
            buy_queues[ticker].append([qty_eff, per_share])

        elif action == "SELL" and ticker and qty_eff > 0:
            proceeds = abs(total) if total != 0 else max(qty_eff * price - fees, 0.0)

            queue = buy_queues[ticker]
            remaining = qty_eff
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

        elif action == "OPTION_BUY" and ticker:
            # Premium paid for opening/closing an option — direct expense.
            # Options don't use stock FIFO; BTO/BTC cost is a realised loss
            # regardless of whether a matching close or expiry exists.
            opt_cost = abs(total)
            if in_period and opt_cost > 0 and (not ticker_upper or ticker == ticker_upper):
                ticker_realized[ticker] -= opt_cost
                ticker_cost_used[ticker] += opt_cost
                date_buckets[date_str]["realized"] -= opt_cost

        elif action == "OPTION_SELL" and ticker:
            # Premium received from STO / STC / OCA — direct income.
            # No matching BUY required; expired/assigned options are
            # already fully settled at this point.
            opt_income = abs(total)
            if in_period and opt_income > 0 and (not ticker_upper or ticker == ticker_upper):
                ticker_realized[ticker] += opt_income
                ticker_proceeds[ticker] += opt_income
                date_buckets[date_str]["realized"] += opt_income

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
    is $0.  Also counts BUY vs SELL rows per ticker so the caller can show
    the user exactly WHY the cost basis is missing:
      - fewer BUY rows than SELL rows  → history gap (pre-file or ACATS transfer)
      - equal rows but still $0 cost  → data/parsing issue
    """
    txs = list_transactions(account_id=account_id, limit=50000)
    txs_sorted = sorted(txs, key=lambda x: x.get("date", ""))

    buy_queues: dict[str, list] = defaultdict(list)
    zero_basis: list[dict] = []

    # Per-ticker buy/sell accounting (all rows, not FIFO-filtered)
    ticker_buy_rows:   dict[str, int]   = defaultdict(int)
    ticker_sell_rows:  dict[str, int]   = defaultdict(int)
    ticker_buy_qty:    dict[str, float] = defaultdict(float)
    ticker_sell_qty:   dict[str, float] = defaultdict(float)
    ticker_buy_value:  dict[str, float] = defaultdict(float)
    ticker_sell_value: dict[str, float] = defaultdict(float)

    for tx in txs_sorted:
        action = _s(tx.get("action"))
        if action not in _PNL_ACTIONS:
            continue
        ticker = _s(tx.get("ticker"))
        qty    = _f(tx.get("quantity"))
        price  = _f(tx.get("price"))
        total  = _f(tx.get("total_amount"))
        date_str = tx.get("date", "")

        qty_eff = qty if qty > 0 else (
            abs(total) / price if (price > 0 and total != 0) else 0.0
        )

        if action == "BUY" and ticker and qty_eff > 0:
            per_share = price if price > 0 else (abs(total) / qty_eff)
            buy_queues[ticker].append([qty_eff, per_share])
            ticker_buy_rows[ticker]  += 1
            ticker_buy_qty[ticker]   += qty_eff
            ticker_buy_value[ticker] += qty_eff * per_share

        elif action == "SELL" and ticker and qty_eff > 0:
            proceeds = abs(total) if total != 0 else qty_eff * price
            ticker_sell_rows[ticker]  += 1
            ticker_sell_qty[ticker]   += qty_eff
            ticker_sell_value[ticker] += proceeds

            queue = buy_queues[ticker]
            remaining = qty_eff
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
                    "date":          date_str,
                    "ticker":        ticker,
                    "quantity":      qty_eff,
                    "proceeds":      round(proceeds, 2),
                    "inflated_gain": round(proceeds, 2),
                    "account_id":    tx.get("account_id", ""),
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
                # Buy vs sell row counts — key for diagnosing WHY cost is $0
                "buy_rows":        ticker_buy_rows.get(t, 0),
                "sell_rows":       ticker_sell_rows.get(t, 0),
                "buy_qty":         round(ticker_buy_qty.get(t, 0), 4),
                "sell_qty":        round(ticker_sell_qty.get(t, 0), 4),
                "buy_value":       round(ticker_buy_value.get(t, 0), 2),
                "sell_value":      round(ticker_sell_value.get(t, 0), 2),
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


def trace_ticker_fifo(ticker: str, account_id: str = None) -> dict:
    """
    Step-by-step FIFO trace for one ticker — returns every relevant transaction
    in date order, showing whether each BUY entered the queue or was skipped,
    and for each SELL how much cost was matched vs how many shares had no buy.

    Use this to diagnose why cost basis looks wrong for a specific ticker.
    """
    ticker_upper = ticker.upper().strip()
    txs = list_transactions(account_id=account_id, limit=50000)

    relevant = sorted(
        [tx for tx in txs
         if _s(tx.get("ticker")).upper() == ticker_upper
         and _s(tx.get("action")) in _PNL_ACTIONS],
        key=lambda x: x.get("date", ""),
    )

    buy_queue: list = []
    events:    list = []
    total_buy_value   = 0.0
    total_proceeds    = 0.0
    total_cost_used   = 0.0
    total_opt_pl      = 0.0
    skipped_zero_qty  = 0

    for tx in relevant:
        action   = _s(tx.get("action"))
        date_str = tx.get("date", "")
        qty      = _f(tx.get("quantity"))
        price    = _f(tx.get("price"))
        total    = _f(tx.get("total_amount"))
        fees     = _f(tx.get("fees"))

        qty_eff = qty if qty > 0 else (
            abs(total) / price if (price > 0 and total != 0) else 0.0
        )

        q_len  = len(buy_queue)
        q_qty  = round(sum(r[0] for r in buy_queue), 4)
        q_val  = round(sum(r[0] * r[1] for r in buy_queue), 2)

        if action == "BUY":
            if qty_eff > 0:
                per_share = price if price > 0 else abs(total) / qty_eff
                buy_queue.append([qty_eff, per_share])
                total_buy_value += qty_eff * per_share
                events.append({
                    "date": date_str, "action": "BUY",
                    "qty": round(qty_eff, 4),
                    "price": round(per_share, 4),
                    "amount": round(abs(total), 2),
                    "note": "queued" + (" [qty inferred]" if qty <= 0 else ""),
                    "queue_qty_after": round(q_qty + qty_eff, 4),
                    "queue_value_after": round(q_val + qty_eff * per_share, 2),
                })
            else:
                skipped_zero_qty += 1
                events.append({
                    "date": date_str, "action": "BUY",
                    "qty": 0, "price": round(price, 4),
                    "amount": round(abs(total), 2),
                    "note": "⚠️ SKIPPED — qty=0, cannot infer (price and total both 0?)",
                    "queue_qty_after": q_qty,
                    "queue_value_after": q_val,
                })

        elif action == "SELL" and qty_eff > 0:
            proceeds  = abs(total) if total != 0 else qty_eff * price
            remaining = qty_eff
            cost      = 0.0
            while remaining > 0.0001 and buy_queue:
                lot_qty, lot_price = buy_queue[0]
                used = min(lot_qty, remaining)
                cost += used * lot_price
                remaining -= used
                buy_queue[0][0] -= used
                if buy_queue[0][0] <= 0.0001:
                    buy_queue.pop(0)
            gain = proceeds - cost
            total_proceeds  += proceeds
            total_cost_used += cost
            note = f"gain {gain:+,.2f}"
            if remaining > 0.001:
                note += f"  ⚠️ {remaining:.4f} shares had NO matching BUY (missing history?)"
            events.append({
                "date": date_str, "action": "SELL",
                "qty": round(qty_eff, 4),
                "price": round(price, 4),
                "amount": round(proceeds, 2),
                "cost_matched": round(cost, 2),
                "gain": round(gain, 2),
                "unmatched_qty": round(remaining, 4),
                "note": note,
                "queue_qty_after": round(sum(r[0] for r in buy_queue), 4),
                "queue_value_after": round(sum(r[0]*r[1] for r in buy_queue), 2),
            })

        elif action in ("OPTION_BUY", "OPTION_SELL"):
            opt_pl = abs(total) * (1 if action == "OPTION_SELL" else -1)
            total_opt_pl += opt_pl
            events.append({
                "date": date_str, "action": action,
                "qty": round(qty_eff, 4),
                "price": round(price, 4),
                "amount": round(abs(total), 2),
                "note": f"option P&L {opt_pl:+,.2f} (direct, no FIFO)",
                "queue_qty_after": q_qty,
                "queue_value_after": q_val,
            })

    remaining_lots = [
        {"qty": round(r[0], 4), "cost_per_share": round(r[1], 4),
         "lot_value": round(r[0] * r[1], 2)}
        for r in buy_queue
    ]

    return {
        "ticker":            ticker_upper,
        "total_transactions": len(relevant),
        "skipped_zero_qty":  skipped_zero_qty,
        "total_buy_value":   round(total_buy_value, 2),
        "total_proceeds":    round(total_proceeds, 2),
        "total_cost_used":   round(total_cost_used, 2),
        "stock_gain":        round(total_proceeds - total_cost_used, 2),
        "option_pl":         round(total_opt_pl, 2),
        "total_pl":          round(total_proceeds - total_cost_used + total_opt_pl, 2),
        "remaining_lots":    remaining_lots,
        "remaining_qty":     round(sum(r[0] for r in buy_queue), 4),
        "remaining_value":   round(sum(r[0]*r[1] for r in buy_queue), 2),
        "events":            events,
    }
