"""Google Sheets client — single source of truth for all sheet access."""
import os
import json
import uuid
from datetime import datetime
from typing import Any, Optional
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SHEET_NAMES = {
    "accounts": "Accounts",
    "transactions": "Transactions",
    "holdings": "Holdings Snapshot",
    "manual": "Manual Accounts",
    "networth": "Net Worth History",
    "projections": "Projections",
}

HEADERS = {
    "accounts": [
        "account_id", "broker_name", "account_name", "account_type",
        "owner", "tax_status", "active",
    ],
    "transactions": [
        "transaction_id", "date", "ticker", "action", "quantity", "price",
        "fees", "total_amount", "broker", "account_id", "imported_file",
        "upload_timestamp",
    ],
    "holdings": [
        "snapshot_date", "ticker", "quantity", "market_value",
        "cost_basis", "unrealized_gain", "account_id",
    ],
    "manual": [
        "entry_date", "account_name", "owner", "value", "notes",
    ],
    "networth": [
        "date", "total_assets", "total_liabilities", "net_worth",
        "investment_value", "retirement_value", "cash_value",
    ],
    "projections": [
        "scenario_name", "annual_return", "inflation",
        "monthly_contribution", "target_age", "projected_value",
    ],
}


class SheetsClient:
    def __init__(self):
        self._gc: Optional[gspread.Client] = None
        self._spreadsheet: Optional[gspread.Spreadsheet] = None

    def _connect(self) -> gspread.Client:
        if self._gc is not None:
            return self._gc
        creds_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "credentials/service_account.json")
        creds = Credentials.from_service_account_file(creds_file, scopes=SCOPES)
        self._gc = gspread.authorize(creds)
        return self._gc

    def _get_spreadsheet(self) -> gspread.Spreadsheet:
        if self._spreadsheet is not None:
            return self._spreadsheet
        gc = self._connect()
        spreadsheet_id = os.getenv("GOOGLE_SPREADSHEET_ID")
        if not spreadsheet_id:
            raise ValueError("GOOGLE_SPREADSHEET_ID not set in environment")
        self._spreadsheet = gc.open_by_key(spreadsheet_id)
        return self._spreadsheet

    def _get_or_create_sheet(self, sheet_key: str) -> gspread.Worksheet:
        ss = self._get_spreadsheet()
        sheet_name = SHEET_NAMES[sheet_key]
        try:
            ws = ss.worksheet(sheet_name)
        except gspread.WorksheetNotFound:
            ws = ss.add_worksheet(title=sheet_name, rows=1000, cols=20)
            ws.append_row(HEADERS[sheet_key])
        return ws

    def get_all_records(self, sheet_key: str) -> list[dict]:
        ws = self._get_or_create_sheet(sheet_key)
        records = ws.get_all_records()
        return records

    def append_row(self, sheet_key: str, row: list) -> None:
        ws = self._get_or_create_sheet(sheet_key)
        ws.append_row(row, value_input_option="USER_ENTERED")

    def find_row_by_field(self, sheet_key: str, field: str, value: str) -> Optional[int]:
        """Return 1-based row index (including header) or None."""
        ws = self._get_or_create_sheet(sheet_key)
        headers = HEADERS[sheet_key]
        if field not in headers:
            return None
        col_idx = headers.index(field) + 1
        try:
            cell = ws.find(value, in_column=col_idx)
            return cell.row
        except gspread.CellNotFound:
            return None

    def update_row(self, sheet_key: str, row_idx: int, row: list) -> None:
        ws = self._get_or_create_sheet(sheet_key)
        ws.update(f"A{row_idx}", [row])

    def delete_row(self, sheet_key: str, row_idx: int) -> None:
        ws = self._get_or_create_sheet(sheet_key)
        ws.delete_rows(row_idx)

    def get_existing_transaction_ids(self) -> set[str]:
        records = self.get_all_records("transactions")
        return {r["transaction_id"] for r in records if r.get("transaction_id")}

    def ensure_headers(self) -> None:
        """Ensure all sheets exist with correct headers."""
        for key in SHEET_NAMES:
            self._get_or_create_sheet(key)

    def generate_id(self) -> str:
        return str(uuid.uuid4())


sheets_client = SheetsClient()
