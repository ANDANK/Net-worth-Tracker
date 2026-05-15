"""Robinhood CSV parser."""
import re
import pandas as pd
from models.schemas import TransactionType
from parsers.base import BaseParser, ParsedTransaction, _is_blank

_OPT_UNDERLYING_RE = re.compile(r"^([A-Z]{1,6}(?:\.[A-Z])?)\s+\d", re.IGNORECASE)

def _opt_underlying(ticker: str | None) -> str | None:
    """
    Normalize Robinhood option contract descriptions to just the underlying ticker.
    Robinhood sometimes puts the full contract in the Instrument column for BTC/BTO:
      "AVGO 01/20/2025 200.00 C"  →  "AVGO"
    Simple tickers are returned unchanged.
    """
    if not ticker or " " not in ticker:
        return ticker
    m = _OPT_UNDERLYING_RE.match(ticker.strip())
    return m.group(1).upper() if m else ticker

ACTION_MAP = {
    # ── Stock trades ──
    "Buy":          TransactionType.BUY,
    "Sell":         TransactionType.SELL,
    "BCSY":         TransactionType.BUY,   # Buy Cash Security
    "SCSY":         TransactionType.SELL,  # Sell Cash Security
    "MKT BUY":      TransactionType.BUY,
    "MKT SELL":     TransactionType.SELL,
    "LIMIT BUY":    TransactionType.BUY,
    "LIMIT SELL":   TransactionType.SELL,
    # ── Options ──
    "BTO":  TransactionType.OPTION_BUY,    # Buy to Open
    "STC":  TransactionType.OPTION_SELL,   # Sell to Close
    "BTC":  TransactionType.OPTION_BUY,    # Buy to Close
    "STO":  TransactionType.OPTION_SELL,   # Sell to Open
    "OCA":  TransactionType.OPTION_SELL,   # Option Cash Assignment
    # ── Income / interest ──
    "Dividend":       TransactionType.DIVIDEND,
    "Cash Dividend":  TransactionType.DIVIDEND,
    "CDIV":           TransactionType.DIVIDEND,  # Cash Dividend
    "JDIV":           TransactionType.DIVIDEND,  # Journal Dividend
    "Interest":       TransactionType.INTEREST,
    "Misc Credit":    TransactionType.INTEREST,
    "INT":            TransactionType.INTEREST,  # Interest (short code)
    "MINT":           TransactionType.INTEREST,  # Margin Interest
    # ── Cash deposits ──
    "Deposit":        TransactionType.DEPOSIT,
    "ACH":            TransactionType.DEPOSIT,   # ACH bank transfer (cash in)
    "ACH_CANCEL":     TransactionType.WITHDRAWAL, # ACH reversal/cancellation
    "RTP":            TransactionType.DEPOSIT,   # Real-Time Payment (instant deposit)
    "WIRE":           TransactionType.DEPOSIT,   # Wire transfer in
    # ── Withdrawals / fees ──
    "Withdrawal":     TransactionType.WITHDRAWAL,
    "FEE":            TransactionType.WITHDRAWAL, # Generic fee
    "GOLD":           TransactionType.WITHDRAWAL, # Robinhood Gold subscription fee
    "MARGIN":         TransactionType.WITHDRAWAL, # Margin interest charge
    # ── Transfers / corporate actions ──
    "Transfer":    TransactionType.TRANSFER,
    "JTRANSFER":   TransactionType.TRANSFER,  # Journal Transfer
    "ACATC":       TransactionType.TRANSFER,  # ACATS Cash
    "ACATS":       TransactionType.TRANSFER,  # ACATS Securities
    "SPC":         TransactionType.TRANSFER,  # Stock Position Correction
    "CONV":        TransactionType.TRANSFER,  # Conversion
    "OEXP":        TransactionType.TRANSFER,  # Option Expiration (worthless)
    "OASGN":       TransactionType.TRANSFER,  # Option Assignment (shares delivered at strike)
    "OEXCS":       TransactionType.TRANSFER,  # Option Exercise (you exercise your long option)
    "SPL":         TransactionType.SPLIT,     # Stock Split
    "RECSPL":      TransactionType.SPLIT,     # Reverse Split
}

# Column names that look like action codes — skip them (repeated header rows)
_HEADER_VALUES = frozenset({"trans code", "activity type", "action"})


class RobinhoodParser(BaseParser):
    broker_name = "Robinhood"

    def parse(self, df: pd.DataFrame, account_id: str, filename: str) -> list[ParsedTransaction]:
        self.parse_errors = []
        transactions = []
        df.columns = [c.strip() for c in df.columns]

        for idx, row in df.iterrows():
            raw_action = ""
            try:
                raw_action = str(row.get("Trans Code", row.get("Activity Type", ""))).strip()

                # Skip blank rows and repeated header rows
                if _is_blank(raw_action) or raw_action.lower() in _HEADER_VALUES:
                    continue

                action = ACTION_MAP.get(raw_action, TransactionType.OTHER)

                date   = self.normalize_date(row.get("Date", row.get("Process Date", "")))
                ticker = _opt_underlying(
                    self.clean_ticker(row.get("Instrument", row.get("Symbol", "")))
                )
                qty    = self.clean_qty(row.get("Quantity", row.get("Shares", "")))
                price  = self.clean_amount(row.get("Price", ""))
                fees   = self.clean_amount(row.get("Fees & Comm", row.get("Fees", 0)))
                amount = self.clean_amount(row.get("Amount", ""))

                if amount == 0 and qty and price:
                    amount = qty * price

                transactions.append(ParsedTransaction(
                    date=date, action=action, total_amount=abs(amount),
                    broker=self.broker_name, account_id=account_id,
                    ticker=ticker, quantity=qty,
                    price=price if price else None,
                    fees=fees, imported_file=filename,
                ))
            except Exception as e:
                self.parse_errors.append({
                    "row": int(idx) + 2,
                    "raw_action": raw_action,
                    "error": str(e)[:200],
                })
        return self._ensure_unique_ids(transactions)

    @classmethod
    def diagnose(cls, df: pd.DataFrame) -> dict:
        df.columns = [c.strip() for c in df.columns]
        action_col = next(
            (c for c in ("Trans Code", "Activity Type") if c in df.columns), None
        )
        if action_col is None:
            return {"action_column": None, "total_rows": len(df),
                    "recognised": {}, "other": {}, "skipped_blank": 0}

        recognised: dict[str, int] = {}
        other:      dict[str, int] = {}
        skipped_blank = 0

        for val in df[action_col]:
            raw = str(val).strip()
            if _is_blank(raw) or raw.lower() in _HEADER_VALUES:
                skipped_blank += 1
                continue
            if raw in ACTION_MAP:
                recognised[raw] = recognised.get(raw, 0) + 1
            else:
                other[raw] = other.get(raw, 0) + 1

        return {
            "action_column": action_col,
            "total_rows": len(df),
            "recognised": recognised,
            "other": other,
            "skipped_blank": skipped_blank,
            # legacy key kept for compatibility
            "skipped_by_unrecognised_action": sum(other.values()),
        }
