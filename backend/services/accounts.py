"""Account CRUD operations against Google Sheets."""
import uuid
from datetime import datetime
from models.schemas import AccountCreate, Account, AccountType, Owner, TaxStatus
from google_sheets.client import sheets_client


def list_accounts() -> list[dict]:
    return sheets_client.get_all_records("accounts")


def create_account(data: AccountCreate) -> dict:
    account_id = f"acc_{uuid.uuid4().hex[:12]}"
    row = [
        account_id,
        data.broker_name,
        data.account_name,
        data.account_type,
        data.owner,
        data.tax_status,
        True,
    ]
    sheets_client.append_row("accounts", row)
    return {
        "account_id": account_id,
        "broker_name": data.broker_name,
        "account_name": data.account_name,
        "account_type": data.account_type,
        "owner": data.owner,
        "tax_status": data.tax_status,
        "active": True,
    }


def deactivate_account(account_id: str) -> bool:
    row_idx = sheets_client.find_row_by_field("accounts", "account_id", account_id)
    if row_idx is None:
        return False
    records = sheets_client.get_all_records("accounts")
    record = next((r for r in records if r["account_id"] == account_id), None)
    if not record:
        return False
    updated = [
        record["account_id"],
        record["broker_name"],
        record["account_name"],
        record["account_type"],
        record["owner"],
        record["tax_status"],
        False,
    ]
    sheets_client.update_row("accounts", row_idx, updated)
    return True
