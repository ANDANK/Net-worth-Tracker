"""Google Sheets client — single source of truth for all sheet access."""
import os
import time
import uuid
from typing import Optional

# ── SSL fix for Windows ───────────────────────────────────────────────────────
# Python on Windows doesn't trust Google's CA by default.
# Point requests (used by gspread/google-auth) at certifi's bundle.
try:
    import certifi
    os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
    os.environ.setdefault("SSL_CERT_FILE",       certifi.where())
except ImportError:
    pass
# ─────────────────────────────────────────────────────────────────────────────

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
    "brokers": "Brokers",
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
    "brokers": [
        "broker_id", "broker_name", "active",
    ],
}

# Google Sheets API free tier: 60 write req/min per user.
# Small chunks + long pauses + retry-on-429 keeps us inside quota.
BATCH_CHUNK_SIZE = 100   # rows per append_rows call
BATCH_PAUSE_SEC  = 5.0   # pause between chunks
_MAX_RETRY       = 6     # max retry attempts on 429
_RETRY_BASE_SEC  = 15    # initial backoff (doubles each retry, caps at 120s)


class SheetsClient:
    def __init__(self):
        self._gc: Optional[gspread.Client] = None
        self._spreadsheet: Optional[gspread.Spreadsheet] = None

    # ------------------------------------------------------------------ #
    # Connection helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _in_streamlit() -> bool:
        """Return True only when code is actually running inside Streamlit."""
        try:
            from streamlit.runtime.scriptrunner import get_script_run_ctx
            return get_script_run_ctx() is not None
        except Exception:
            return False

    def _connect(self) -> gspread.Client:
        if self._gc is not None:
            return self._gc

        # ── Streamlit Cloud: credentials from st.secrets ─────────────────────
        # Use this path ONLY when genuinely running inside Streamlit so we
        # don't accidentally swallow errors and fall through to file-based creds.
        if self._in_streamlit():
            import streamlit as st
            try:
                creds_info = dict(st.secrets["gcp_service_account"])
            except KeyError:
                raise ValueError(
                    "Streamlit secrets are missing the [gcp_service_account] section.\n\n"
                    "Fix: go to  share.streamlit.io  → your app → "
                    "⋮ Menu → Settings → Secrets  and paste your service-account JSON.\n"
                    "See .streamlit/secrets.toml in the repo for the exact format."
                )
            try:
                self._st_spreadsheet_id = str(st.secrets["google"]["spreadsheet_id"])
            except KeyError:
                raise ValueError(
                    "Streamlit secrets are missing [google] spreadsheet_id.\n\n"
                    "Add this to your Streamlit Cloud secrets:\n"
                    "  [google]\n  spreadsheet_id = \"your-sheet-id\""
                )
            creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
            self._gc = gspread.authorize(creds)
            return self._gc
        # ─────────────────────────────────────────────────────────────────────

        # ── Local FastAPI dev: file-based credentials ─────────────────────────
        creds_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "credentials/service_account.json")
        if not os.path.exists(creds_file):
            raise FileNotFoundError(
                f"Google service account key not found at '{creds_file}'. "
                "Download it from Google Cloud Console → IAM & Admin → Service Accounts → Keys, "
                "then place it at backend/credentials/service_account.json"
            )
        spreadsheet_id = os.getenv("GOOGLE_SPREADSHEET_ID", "")
        if not spreadsheet_id:
            raise ValueError("GOOGLE_SPREADSHEET_ID is not set in backend/.env")
        creds = Credentials.from_service_account_file(creds_file, scopes=SCOPES)
        self._gc = gspread.authorize(creds)

        # ── Windows SSL fix (gspread 6.x) ────────────────────────────────
        # gspread 6 uses google.auth.transport.requests.AuthorizedSession
        # which lives at gc.http_client.session.  That session has TWO
        # internal sessions:
        #   1. The AuthorizedSession itself  → used for all API calls
        #   2. _auth_request_session         → used ONLY for OAuth token
        #      refresh (hits oauth2.googleapis.com/token)
        # On Windows, Python's SSL store can't verify Google's CA, so we
        # point both sessions at certifi's bundle.  Fall back to
        # verify=False when certifi is absent (safe for a local-only app).
        try:
            import certifi
            ca = certifi.where()
            auth_session = self._gc.http_client.session   # AuthorizedSession
            auth_session.verify = ca                      # main API calls
            if hasattr(auth_session, "_auth_request_session"):
                auth_session._auth_request_session.verify = ca  # token refresh
        except (ImportError, AttributeError):
            try:
                auth_session = self._gc.http_client.session
                auth_session.verify = False
                if hasattr(auth_session, "_auth_request_session"):
                    auth_session._auth_request_session.verify = False
            except AttributeError:
                pass
        # ─────────────────────────────────────────────────────────────────

        return self._gc

    def _get_spreadsheet(self) -> gspread.Spreadsheet:
        if self._spreadsheet is not None:
            return self._spreadsheet
        gc = self._connect()
        # _st_spreadsheet_id is set when using Streamlit secrets; fall back to .env
        spreadsheet_id = getattr(self, "_st_spreadsheet_id", None) or os.getenv("GOOGLE_SPREADSHEET_ID")
        self._spreadsheet = gc.open_by_key(spreadsheet_id)
        return self._spreadsheet

    def _get_or_create_sheet(self, sheet_key: str) -> gspread.Worksheet:
        ss = self._get_spreadsheet()
        sheet_name = SHEET_NAMES[sheet_key]
        try:
            ws = ss.worksheet(sheet_name)
        except gspread.WorksheetNotFound:
            ws = ss.add_worksheet(title=sheet_name, rows=5000, cols=20)
            ws.append_row(HEADERS[sheet_key])
        return ws

    # ------------------------------------------------------------------ #
    # Read helpers
    # ------------------------------------------------------------------ #

    def get_all_records(self, sheet_key: str) -> list[dict]:
        ws = self._get_or_create_sheet(sheet_key)
        return ws.get_all_records()

    def get_existing_transaction_ids(self) -> set[str]:
        """Single API call — returns all known transaction IDs as a set."""
        ws = self._get_or_create_sheet("transactions")
        # Read only the transaction_id column (col A) — much faster than get_all_records
        col_values = ws.col_values(1)           # 1 API call
        return set(col_values[1:])              # skip header row

    # ------------------------------------------------------------------ #
    # Write helpers
    # ------------------------------------------------------------------ #

    def append_row(self, sheet_key: str, row: list) -> None:
        """Single-row append — fine for accounts, manual entries, snapshots."""
        ws = self._get_or_create_sheet(sheet_key)
        ws.append_row(row, value_input_option="USER_ENTERED")

    @staticmethod
    def _append_chunk(ws: "gspread.Worksheet", chunk: list) -> None:
        """Append one chunk with exponential back-off on 429 quota errors."""
        delay = _RETRY_BASE_SEC
        for attempt in range(_MAX_RETRY):
            try:
                ws.append_rows(chunk, value_input_option="USER_ENTERED")
                return
            except gspread.exceptions.APIError as exc:
                status = getattr(getattr(exc, "response", None), "status_code", 0)
                if status == 429 and attempt < _MAX_RETRY - 1:
                    time.sleep(delay)
                    delay = min(delay * 2, 120)
                else:
                    raise

    def append_rows_batch(self, sheet_key: str, rows: list[list]) -> None:
        """Write many rows in chunks with quota-safe pauses and retry on 429."""
        if not rows:
            return
        ws = self._get_or_create_sheet(sheet_key)
        for i in range(0, len(rows), BATCH_CHUNK_SIZE):
            chunk = rows[i : i + BATCH_CHUNK_SIZE]
            self._append_chunk(ws, chunk)
            if i + BATCH_CHUNK_SIZE < len(rows):
                time.sleep(BATCH_PAUSE_SEC)

    def find_row_by_field(self, sheet_key: str, field: str, value: str) -> Optional[int]:
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

    def ensure_headers(self) -> None:
        for key in SHEET_NAMES:
            self._get_or_create_sheet(key)

    def generate_id(self) -> str:
        return str(uuid.uuid4())


sheets_client = SheetsClient()
