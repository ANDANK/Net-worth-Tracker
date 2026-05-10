"""Charles Schwab CSV parser."""
import pandas as pd
from models.schemas import TransactionType
from parsers.base import BaseParser, ParsedTransaction

ACTION_MAP = {
    "Buy": TransactionType.BUY,
    "Sell": TransactionType.SELL,
    "Div Reinvest": TransactionType.DIVIDEND,
    "Dividend": TransactionType.DIVIDEND,
    "Qualified Dividend": TransactionType.DIVIDEND,
    "Interest": TransactionType.INTEREST,
    "Bank Interest": TransactionType.INTEREST,
    "Wire Funds": TransactionType.DEPOSIT,
    "Wire Funds Received": TransactionType.DEPOSIT,
    "Electronic Funds Transfer": TransactionType.DEPOSIT,
    "Funds Received": TransactionType.DEPOSIT,
    "Journaled Shares": TransactionType.TRANSFER,
    "Stock Split": TransactionType.SPLIT,
    "Buy to Open": TransactionType.OPTION_BUY,
    "Sell to Close": TransactionType.OPTION_SELL,
    "Sell to Open": TransactionType.OPTION_SELL,
    "Buy to Close": TransactionType.OPTION_BUY,
}


class SchwabParser(BaseParser):
    broker_name = "Schwab"

    def parse(self, df: pd.DataFrame, account_id: str, filename: str) -> list[ParsedTransaction]:
        # Schwab files often have header rows to skip
        df = self._strip_preamble(df)
        df.columns = [str(c).strip() for c in df.columns]
        transactions = []

        for _, row in df.iterrows():
            try:
                raw_action = str(row.get("Action", "")).strip()
                action = self._map_action(raw_action)
                if action is None:
                    continue

                date_raw = row.get("Date", row.get("Settlement Date", ""))
                date = self.normalize_date(str(date_raw).replace(" as of ", " ").split(" as")[0])
                ticker = str(row.get("Symbol", "")).strip() or None
                qty = self.clean_qty(row.get("Quantity", ""))
                price = self.clean_amount(row.get("Price", ""))
                fees = self.clean_amount(row.get("Fees & Comm", row.get("Commission", 0)))
                amount = self.clean_amount(row.get("Amount", ""))

                if amount == 0 and qty and price:
                    amount = qty * price

                transactions.append(ParsedTransaction(
                    date=date,
                    action=action,
                    total_amount=abs(amount),
                    broker=self.broker_name,
                    account_id=account_id,
                    ticker=ticker,
                    quantity=abs(qty) if qty else None,
                    price=price if price else None,
                    fees=fees,
                    imported_file=filename,
                ))
            except Exception:
                continue

        return transactions

    def _map_action(self, raw: str):
        for key, val in ACTION_MAP.items():
            if key.lower() in raw.lower():
                return val
        return None

    def _strip_preamble(self, df: pd.DataFrame) -> pd.DataFrame:
        """Schwab exports sometimes have account info rows before the header."""
        for i, row in df.iterrows():
            vals = [str(v).strip() for v in row.values]
            if "Date" in vals or "Action" in vals:
                new_df = df.iloc[i:].copy()
                new_df.columns = new_df.iloc[0]
                return new_df.iloc[1:].reset_index(drop=True)
        return df
