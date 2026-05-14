"""Base parser — all broker parsers inherit from this."""
import hashlib
import math
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional
import pandas as pd

from models.schemas import TransactionType


class ParsedTransaction:
    __slots__ = (
        "date", "ticker", "action", "quantity", "price",
        "fees", "total_amount", "broker", "account_id",
        "imported_file", "upload_timestamp", "transaction_id",
    )

    def __init__(
        self,
        date: str,
        action: TransactionType,
        total_amount: float,
        broker: str,
        account_id: str,
        ticker: Optional[str] = None,
        quantity: Optional[float] = None,
        price: Optional[float] = None,
        fees: float = 0.0,
        imported_file: str = "",
    ):
        self.date = date
        self.ticker = ticker
        self.action = action
        self.quantity = quantity
        self.price = price
        self.fees = fees
        self.total_amount = total_amount
        self.broker = broker
        self.account_id = account_id
        self.imported_file = imported_file
        self.upload_timestamp = datetime.utcnow().isoformat()
        self.transaction_id = self._make_id()

    def _make_id(self) -> str:
        key = f"{self.date}|{self.ticker}|{self.action}|{self.quantity}|{self.total_amount}"
        return hashlib.sha256(key.encode()).hexdigest()[:32]

    @staticmethod
    def _safe_num(val, default=""):
        """Return val if it's a real number; default if None/NaN/inf."""
        if val is None:
            return default
        try:
            f = float(val)
            return default if (math.isnan(f) or math.isinf(f)) else f
        except (TypeError, ValueError):
            return default

    def to_row(self) -> list:
        return [
            self.transaction_id,
            self.date,
            self.ticker or "",
            self.action,
            self._safe_num(self.quantity, ""),
            self._safe_num(self.price, ""),
            self._safe_num(self.fees, 0.0),
            self._safe_num(self.total_amount, 0.0),
            self.broker,
            self.account_id,
            self.imported_file,
            self.upload_timestamp,
        ]

    def to_dict(self) -> dict:
        return {
            "transaction_id": self.transaction_id,
            "date": self.date,
            "ticker": self.ticker,
            "action": self.action,
            "quantity": self.quantity,
            "price": self.price,
            "fees": self.fees,
            "total_amount": self.total_amount,
            "broker": self.broker,
            "account_id": self.account_id,
            "imported_file": self.imported_file,
            "upload_timestamp": self.upload_timestamp,
        }


class BaseParser(ABC):
    broker_name: str = "Unknown"

    @abstractmethod
    def parse(self, df: pd.DataFrame, account_id: str, filename: str) -> list[ParsedTransaction]:
        ...

    @staticmethod
    def clean_amount(val) -> float:
        if val is None or val == "":
            return 0.0
        s = str(val).replace("$", "").replace(",", "").strip()
        if s in ("", "-", "N/A"):
            return 0.0
        try:
            return float(s)
        except ValueError:
            return 0.0

    @staticmethod
    def clean_qty(val) -> Optional[float]:
        if val is None or val == "":
            return None
        s = str(val).replace(",", "").strip()
        try:
            return float(s)
        except ValueError:
            return None

    @staticmethod
    def normalize_date(val) -> str:
        if isinstance(val, datetime):
            return val.strftime("%Y-%m-%d")
        s = str(val).strip()
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%Y/%m/%d", "%d-%b-%Y"):
            try:
                return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return s
