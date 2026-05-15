"""Webull CSV parser."""
import pandas as pd
from models.schemas import TransactionType
from parsers.base import BaseParser, ParsedTransaction, _is_blank

ACTION_MAP = {
    # ── Trades ──
    "BUY":  TransactionType.BUY,
    "SELL": TransactionType.SELL,
    # ── Income ──
    "Dividend":        TransactionType.DIVIDEND,
    "Interest":        TransactionType.INTEREST,
    "Margin Interest": TransactionType.INTEREST,
    # ── Cash movements ──
    "Deposit":         TransactionType.DEPOSIT,
    "ACH Deposit":     TransactionType.DEPOSIT,
    "Wire Deposit":    TransactionType.DEPOSIT,
    "Withdrawal":      TransactionType.WITHDRAWAL,
    "ACH Withdrawal":  TransactionType.WITHDRAWAL,
    "Wire Withdrawal": TransactionType.WITHDRAWAL,
    "Fee":             TransactionType.WITHDRAWAL,
    # ── Transfers ──
    "Transfer":        TransactionType.TRANSFER,
    "Stock Split":     TransactionType.SPLIT,
}

_HEADER_VALUES = frozenset({"side", "type", "action"})


class WebullParser(BaseParser):
    broker_name = "Webull"

    def parse(self, df: pd.DataFrame, account_id: str, filename: str) -> list[ParsedTransaction]:
        self.parse_errors = []
        df.columns = [str(c).strip() for c in df.columns]
        transactions = []

        for idx, row in df.iterrows():
            raw_action = ""
            try:
                raw_action = str(row.get("Side", row.get("Type", ""))).strip()

                if _is_blank(raw_action) or raw_action.lower() in _HEADER_VALUES:
                    continue

                action = ACTION_MAP.get(raw_action, TransactionType.OTHER)

                date   = self.normalize_date(row.get("Time", row.get("Date", "")))
                ticker = self.clean_ticker(row.get("Symbol", ""))
                qty    = self.clean_qty(row.get("Filled Qty", row.get("Quantity", "")))
                price  = self.clean_amount(row.get("Avg Price", row.get("Price", "")))
                fees   = self.clean_amount(row.get("Commission", 0))
                amount = self.clean_amount(row.get("Filled Amount", row.get("Amount", "")))

                if amount == 0 and qty and price:
                    amount = qty * price

                transactions.append(ParsedTransaction(
                    date=date, action=action, total_amount=abs(amount),
                    broker=self.broker_name, account_id=account_id,
                    ticker=ticker, quantity=abs(qty) if qty else None,
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

    def diagnose(self, df: pd.DataFrame) -> dict:
        df.columns = [str(c).strip() for c in df.columns]
        col = next((c for c in ("Side", "Type") if c in df.columns), None)
        if col is None:
            return {"action_column": None, "total_rows": len(df),
                    "recognised": {}, "other": {}, "skipped_blank": 0}

        recognised: dict[str, int] = {}
        other:      dict[str, int] = {}
        skipped_blank = 0

        for val in df[col]:
            raw = str(val).strip()
            if _is_blank(raw) or raw.lower() in _HEADER_VALUES:
                skipped_blank += 1
                continue
            if raw in ACTION_MAP:
                recognised[raw] = recognised.get(raw, 0) + 1
            else:
                other[raw] = other.get(raw, 0) + 1

        return {
            "action_column": col, "total_rows": len(df),
            "recognised": recognised, "other": other,
            "skipped_blank": skipped_blank,
            "skipped_by_unrecognised_action": sum(other.values()),
        }
