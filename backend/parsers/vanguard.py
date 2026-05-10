"""Vanguard CSV parser."""
import pandas as pd
from models.schemas import TransactionType
from parsers.base import BaseParser, ParsedTransaction

ACTION_MAP = {
    "Buy": TransactionType.BUY,
    "Sell": TransactionType.SELL,
    "Dividend": TransactionType.DIVIDEND,
    "Capital gain (LT)": TransactionType.DIVIDEND,
    "Capital gain (ST)": TransactionType.DIVIDEND,
    "Reinvestment": TransactionType.DIVIDEND,
    "Interest": TransactionType.INTEREST,
    "Contribution": TransactionType.DEPOSIT,
    "Distribution": TransactionType.WITHDRAWAL,
    "Transfer (incoming)": TransactionType.TRANSFER,
    "Transfer (outgoing)": TransactionType.TRANSFER,
}


class VanguardParser(BaseParser):
    broker_name = "Vanguard"

    def parse(self, df: pd.DataFrame, account_id: str, filename: str) -> list[ParsedTransaction]:
        df.columns = [str(c).strip() for c in df.columns]
        transactions = []

        for _, row in df.iterrows():
            try:
                raw_action = str(row.get("Transaction type", row.get("Type", ""))).strip()
                action = ACTION_MAP.get(raw_action)
                if action is None:
                    continue

                date = self.normalize_date(row.get("Trade date", row.get("Date", "")))
                ticker = str(row.get("Symbol", row.get("Ticker symbol", ""))).strip() or None
                qty = self.clean_qty(row.get("Shares", row.get("Quantity", "")))
                price = self.clean_amount(row.get("Share price", row.get("Price", "")))
                fees = self.clean_amount(row.get("Commission", 0))
                amount = self.clean_amount(row.get("Principal amount", row.get("Amount", "")))

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
