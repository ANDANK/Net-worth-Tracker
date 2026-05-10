"""Fidelity CSV parser."""
import pandas as pd
from models.schemas import TransactionType
from parsers.base import BaseParser, ParsedTransaction

ACTION_MAP = {
    "YOU BOUGHT": TransactionType.BUY,
    "YOU SOLD": TransactionType.SELL,
    "DIVIDEND RECEIVED": TransactionType.DIVIDEND,
    "REINVESTMENT": TransactionType.DIVIDEND,
    "INTEREST EARNED": TransactionType.INTEREST,
    "ELECTRONIC FUNDS TRANSFER RECEIVED": TransactionType.DEPOSIT,
    "DIRECT DEPOSIT": TransactionType.DEPOSIT,
    "TRANSFERRED FROM": TransactionType.TRANSFER,
    "TRANSFERRED TO": TransactionType.TRANSFER,
    "BOUGHT": TransactionType.BUY,
    "SOLD": TransactionType.SELL,
}


class FidelityParser(BaseParser):
    broker_name = "Fidelity"

    def parse(self, df: pd.DataFrame, account_id: str, filename: str) -> list[ParsedTransaction]:
        df.columns = [str(c).strip() for c in df.columns]
        transactions = []

        for _, row in df.iterrows():
            try:
                raw_action = str(row.get("Action", row.get("Transaction Type", ""))).strip().upper()
                action = self._map_action(raw_action)
                if action is None:
                    continue

                date = self.normalize_date(row.get("Run Date", row.get("Date", "")))
                ticker = str(row.get("Symbol", "")).strip() or None
                qty = self.clean_qty(row.get("Quantity", ""))
                price = self.clean_amount(row.get("Price ($)", row.get("Price", "")))
                fees = self.clean_amount(row.get("Commission ($)", row.get("Fees", 0)))
                amount = self.clean_amount(row.get("Amount ($)", row.get("Amount", "")))

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
            if key in raw:
                return val
        return None
