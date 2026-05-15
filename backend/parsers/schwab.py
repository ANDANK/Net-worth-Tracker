"""Charles Schwab CSV parser."""
import pandas as pd
from models.schemas import TransactionType
from parsers.base import BaseParser, ParsedTransaction, _is_blank

ACTION_MAP = {
    # ── Trades ──
    "Buy":  TransactionType.BUY,
    "Sell": TransactionType.SELL,
    # ── Options ──
    "Buy to Open":   TransactionType.OPTION_BUY,
    "Buy to Close":  TransactionType.OPTION_BUY,
    "Sell to Open":  TransactionType.OPTION_SELL,
    "Sell to Close": TransactionType.OPTION_SELL,
    # ── Income ──
    "Dividend":           TransactionType.DIVIDEND,
    "Qualified Dividend": TransactionType.DIVIDEND,
    "Div Reinvest":       TransactionType.DIVIDEND,
    "Capital Gain":       TransactionType.DIVIDEND,
    "Interest":           TransactionType.INTEREST,
    "Bank Interest":      TransactionType.INTEREST,
    "Margin Interest":    TransactionType.INTEREST,
    # ── Cash deposits ──
    "Wire Funds":                   TransactionType.DEPOSIT,
    "Wire Funds Received":          TransactionType.DEPOSIT,
    "Electronic Funds Transfer":    TransactionType.DEPOSIT,   # ACH equivalent
    "Funds Received":               TransactionType.DEPOSIT,
    "MoneyLink Transfer":           TransactionType.DEPOSIT,
    "Deposit":                      TransactionType.DEPOSIT,
    # ── Withdrawals / fees ──
    "Withdrawal":               TransactionType.WITHDRAWAL,
    "Wire Funds Sent":          TransactionType.WITHDRAWAL,
    "Electronic Funds Transfer - Sent": TransactionType.WITHDRAWAL,
    "Service Charges":          TransactionType.WITHDRAWAL,
    "Advisory Fees":            TransactionType.WITHDRAWAL,
    # ── Transfers / corporate ──
    "Journaled Shares":  TransactionType.TRANSFER,
    "Security Transfer": TransactionType.TRANSFER,
    "Stock Split":       TransactionType.SPLIT,
}

_HEADER_VALUES = frozenset({"action", "date"})


class SchwabParser(BaseParser):
    broker_name = "Schwab"

    def parse(self, df: pd.DataFrame, account_id: str, filename: str) -> list[ParsedTransaction]:
        self.parse_errors = []
        df = self._strip_preamble(df)
        df.columns = [str(c).strip() for c in df.columns]
        transactions = []

        for idx, row in df.iterrows():
            raw_action = ""
            try:
                raw_action = str(row.get("Action", "")).strip()

                if _is_blank(raw_action) or raw_action.lower() in _HEADER_VALUES:
                    continue

                action = self._map_action(raw_action)

                date_raw = row.get("Date", row.get("Settlement Date", ""))
                date   = self.normalize_date(str(date_raw).replace(" as of ", " ").split(" as")[0])
                ticker = str(row.get("Symbol", "")).strip() or None
                qty    = self.clean_qty(row.get("Quantity", ""))
                price  = self.clean_amount(row.get("Price", ""))
                fees   = self.clean_amount(row.get("Fees & Comm", row.get("Commission", 0)))
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

    def _strip_preamble(self, df: pd.DataFrame) -> pd.DataFrame:
        for i, row in df.iterrows():
            vals = [str(v).strip() for v in row.values]
            if "Date" in vals or "Action" in vals:
                new_df = df.iloc[i:].copy()
                new_df.columns = new_df.iloc[0]
                return new_df.iloc[1:].reset_index(drop=True)
        return df

    def diagnose(self, df: pd.DataFrame) -> dict:
        df = self._strip_preamble(df)
        df.columns = [str(c).strip() for c in df.columns]
        if "Action" not in df.columns:
            return {"action_column": None, "total_rows": len(df),
                    "recognised": {}, "other": {}, "skipped_blank": 0}

        recognised: dict[str, int] = {}
        other:      dict[str, int] = {}
        skipped_blank = 0

        for val in df["Action"]:
            raw = str(val).strip()
            if _is_blank(raw) or raw.lower() in _HEADER_VALUES:
                skipped_blank += 1
                continue
            matched = next((k for k in ACTION_MAP if k.lower() in raw.lower()), None)
            if matched:
                recognised[raw] = recognised.get(raw, 0) + 1
            else:
                other[raw] = other.get(raw, 0) + 1

        return {
            "action_column": "Action", "total_rows": len(df),
            "recognised": recognised, "other": other,
            "skipped_blank": skipped_blank,
            "skipped_by_unrecognised_action": sum(other.values()),
        }
