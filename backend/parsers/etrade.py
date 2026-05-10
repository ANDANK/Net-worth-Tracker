"""E*TRADE CSV parser."""
import pandas as pd
from models.schemas import TransactionType
from parsers.base import BaseParser, ParsedTransaction

ACTION_MAP = {
    "Bought": TransactionType.BUY,
    "Sold": TransactionType.SELL,
    "Dividend": TransactionType.DIVIDEND,
    "Interest": TransactionType.INTEREST,
    "Contribution": TransactionType.DEPOSIT,
    "Withdrawal": TransactionType.WITHDRAWAL,
    "Transfer": TransactionType.TRANSFER,
    "Buy to Open": TransactionType.OPTION_BUY,
    "Sell to Close": TransactionType.OPTION_SELL,
}


class ETradeParser(BaseParser):
    broker_name = "E*TRADE"

    def parse(self, df: pd.DataFrame, account_id: str, filename: str) -> list[ParsedTransaction]:
        df.columns = [str(c).strip() for c in df.columns]
        transactions = []

        for _, row in df.iterrows():
            try:
                raw_action = str(row.get("Transaction Type", row.get("Action", ""))).strip()
                action = self._map_action(raw_action)
                if action is None:
                    continue

                date = self.normalize_date(row.get("Date", ""))
                ticker = str(row.get("Symbol", "")).strip() or None
                qty = self.clean_qty(row.get("Quantity", ""))
                price = self.clean_amount(row.get("Price", ""))
                fees = self.clean_amount(row.get("Commission", row.get("Fees", 0)))
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
