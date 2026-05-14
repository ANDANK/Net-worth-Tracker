"""Robinhood CSV parser."""
import pandas as pd
from models.schemas import TransactionType
from parsers.base import BaseParser, ParsedTransaction

# ── All known Robinhood action codes ─────────────────────────────────────────
# Codes that were NOT here before are the ones that caused silent data loss
# and therefore inflated P&L (sells kept, matching buys dropped).
ACTION_MAP = {
    # ── Stock trades ──
    "Buy":          TransactionType.BUY,
    "Sell":         TransactionType.SELL,
    "BCSY":         TransactionType.BUY,    # Buy Cash Security
    "SCSY":         TransactionType.SELL,   # Sell Cash Security  ← was missing
    "MKT BUY":      TransactionType.BUY,
    "MKT SELL":     TransactionType.SELL,
    "LIMIT BUY":    TransactionType.BUY,
    "LIMIT SELL":   TransactionType.SELL,

    # ── Options ──
    "BTO":  TransactionType.OPTION_BUY,    # Buy to Open
    "STC":  TransactionType.OPTION_SELL,   # Sell to Close
    "BTC":  TransactionType.OPTION_BUY,    # Buy to Close    ← was missing
    "STO":  TransactionType.OPTION_SELL,   # Sell to Open    ← was missing
    "OCA":  TransactionType.OPTION_SELL,   # Option Cash Assignment (exercised)

    # ── Income ──
    "Dividend":       TransactionType.DIVIDEND,
    "Cash Dividend":  TransactionType.DIVIDEND,
    "CDIV":           TransactionType.DIVIDEND,  # Cash Dividend alt code  ← was missing
    "JDIV":           TransactionType.DIVIDEND,  # Journal Dividend        ← was missing
    "Interest":       TransactionType.INTEREST,
    "Misc Credit":    TransactionType.INTEREST,

    # ── Cash movements ──
    "Deposit":    TransactionType.DEPOSIT,
    "Withdrawal": TransactionType.WITHDRAWAL,
    "FEE":        TransactionType.WITHDRAWAL,   # Account fee  ← was missing

    # ── Transfers / corporate actions ──
    "Transfer":     TransactionType.TRANSFER,
    "JTRANSFER":    TransactionType.TRANSFER,   # Journal Transfer  ← was missing
    "ACATC":        TransactionType.TRANSFER,   # ACATS Cash        ← was missing
    "ACATS":        TransactionType.TRANSFER,   # ACATS Securities  ← was missing
    "SPC":          TransactionType.TRANSFER,   # Stock Position Correction
    "CONV":         TransactionType.TRANSFER,   # Conversion
    "OEXP":         TransactionType.TRANSFER,   # Option Expiration (worthless, $0)
    "SPL":          TransactionType.SPLIT,      # Stock Split       ← was missing
    "RECSPL":       TransactionType.SPLIT,      # Reverse Split     ← was missing
}


class RobinhoodParser(BaseParser):
    broker_name = "Robinhood"

    def parse(self, df: pd.DataFrame, account_id: str, filename: str) -> list[ParsedTransaction]:
        transactions = []
        df.columns = [c.strip() for c in df.columns]

        for _, row in df.iterrows():
            try:
                raw_action = str(row.get("Trans Code", row.get("Activity Type", ""))).strip()
                action = ACTION_MAP.get(raw_action)
                if action is None:
                    continue

                date = self.normalize_date(row.get("Date", row.get("Process Date", "")))
                ticker = str(row.get("Instrument", row.get("Symbol", ""))).strip() or None
                qty = self.clean_qty(row.get("Quantity", row.get("Shares", "")))
                price = self.clean_amount(row.get("Price", ""))
                fees = self.clean_amount(row.get("Fees & Comm", row.get("Fees", 0)))
                amount = self.clean_amount(row.get("Amount", ""))

                if amount == 0 and qty and price:
                    amount = qty * price

                transactions.append(ParsedTransaction(
                    date=date,
                    action=action,
                    total_amount=amount,
                    broker=self.broker_name,
                    account_id=account_id,
                    ticker=ticker,
                    quantity=qty,
                    price=price if price else None,
                    fees=fees,
                    imported_file=filename,
                ))
            except Exception:
                continue

        return transactions

    @classmethod
    def diagnose(cls, df: pd.DataFrame) -> dict:
        """
        Inspect a raw DataFrame without importing it.
        Returns every action code found in the file, split into
        'recognised' (would be imported) and 'unrecognised' (would be silently dropped).
        """
        df.columns = [c.strip() for c in df.columns]
        action_col = next(
            (c for c in ("Trans Code", "Activity Type") if c in df.columns),
            None,
        )
        if action_col is None:
            return {
                "action_column": None,
                "total_rows": len(df),
                "recognised": {},
                "unrecognised": {},
                "skipped_by_unrecognised_action": 0,
            }

        counts: dict[str, int] = {}
        for val in df[action_col]:
            raw = str(val).strip()
            if raw and raw.lower() not in ("nan", "trans code", "activity type", ""):
                counts[raw] = counts.get(raw, 0) + 1

        recognised   = {k: v for k, v in counts.items() if k in ACTION_MAP}
        unrecognised = {k: v for k, v in counts.items() if k not in ACTION_MAP}

        return {
            "action_column": action_col,
            "total_rows": len(df),
            "recognised": recognised,
            "unrecognised": unrecognised,
            "skipped_by_unrecognised_action": sum(unrecognised.values()),
        }
