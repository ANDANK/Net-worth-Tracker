"""Robinhood CSV parser."""
import pandas as pd
from models.schemas import TransactionType
from parsers.base import BaseParser, ParsedTransaction

ACTION_MAP = {
    "Buy": TransactionType.BUY,
    "Sell": TransactionType.SELL,
    "BCSY": TransactionType.BUY,
    "STC": TransactionType.OPTION_SELL,
    "BTO": TransactionType.OPTION_BUY,
    "Dividend": TransactionType.DIVIDEND,
    "Cash Dividend": TransactionType.DIVIDEND,
    "Deposit": TransactionType.DEPOSIT,
    "Withdrawal": TransactionType.WITHDRAWAL,
    "Transfer": TransactionType.TRANSFER,
    "Interest": TransactionType.INTEREST,
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
