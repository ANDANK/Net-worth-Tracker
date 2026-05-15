"""E*TRADE CSV parser."""
import pandas as pd
from models.schemas import TransactionType
from parsers.base import BaseParser, ParsedTransaction, _is_blank

ACTION_MAP = {
    # ── Trades ──
    "Bought": TransactionType.BUY,
    "Sold":   TransactionType.SELL,
    # ── Options ──
    "Buy to Open":   TransactionType.OPTION_BUY,
    "Buy to Close":  TransactionType.OPTION_BUY,
    "Sell to Open":  TransactionType.OPTION_SELL,
    "Sell to Close": TransactionType.OPTION_SELL,
    # ── Income ──
    "Dividend":        TransactionType.DIVIDEND,
    "Interest":        TransactionType.INTEREST,
    "Margin Interest": TransactionType.INTEREST,
    # ── Cash movements ──
    "Contribution":    TransactionType.DEPOSIT,    # retirement contributions
    "ACH":             TransactionType.DEPOSIT,    # ACH bank transfer
    "Wire":            TransactionType.DEPOSIT,    # Wire in
    "Deposit":         TransactionType.DEPOSIT,
    "Withdrawal":      TransactionType.WITHDRAWAL,
    "Wire Out":        TransactionType.WITHDRAWAL,
    "Fee":             TransactionType.WITHDRAWAL,
    "Commission":      TransactionType.WITHDRAWAL,
    # ── Transfers / corporate ──
    "Transfer":   TransactionType.TRANSFER,
    "Stock Split": TransactionType.SPLIT,
}

_HEADER_VALUES = frozenset({"transaction type", "action", "date"})


class ETradeParser(BaseParser):
    broker_name = "E*TRADE"

    def parse(self, df: pd.DataFrame, account_id: str, filename: str) -> list[ParsedTransaction]:
        self.parse_errors = []
        df.columns = [str(c).strip() for c in df.columns]
        transactions = []

        for idx, row in df.iterrows():
            raw_action = ""
            try:
                raw_action = str(row.get("Transaction Type", row.get("Action", ""))).strip()

                if _is_blank(raw_action) or raw_action.lower() in _HEADER_VALUES:
                    continue

                action = self._map_action(raw_action)

                date   = self.normalize_date(row.get("Date", ""))
                ticker = str(row.get("Symbol", "")).strip() or None
                qty    = self.clean_qty(row.get("Quantity", ""))
                price  = self.clean_amount(row.get("Price", ""))
                fees   = self.clean_amount(row.get("Commission", row.get("Fees", 0)))
                amount = self.clean_amount(row.get("Amount", ""))

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
        return transactions

    def _map_action(self, raw: str) -> TransactionType:
        raw_lower = raw.lower()
        for key, val in ACTION_MAP.items():
            if key.lower() in raw_lower:
                return val
        return TransactionType.OTHER

    def diagnose(self, df: pd.DataFrame) -> dict:
        df.columns = [str(c).strip() for c in df.columns]
        col = next((c for c in ("Transaction Type", "Action") if c in df.columns), None)
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
            matched = any(k.lower() in raw.lower() for k in ACTION_MAP)
            if matched:
                recognised[raw] = recognised.get(raw, 0) + 1
            else:
                other[raw] = other.get(raw, 0) + 1

        return {
            "action_column": col, "total_rows": len(df),
            "recognised": recognised, "other": other,
            "skipped_blank": skipped_blank,
            "skipped_by_unrecognised_action": sum(other.values()),
        }
