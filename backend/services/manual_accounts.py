"""Manual account entry service."""
from datetime import date as date_type, datetime
from models.schemas import ManualAccountCreate, Owner
from google_sheets.client import sheets_client


def list_manual_accounts(owner: str = None) -> list[dict]:
    records = sheets_client.get_all_records("manual")
    if owner:
        records = [r for r in records if r.get("owner", "").lower() == owner.lower()]
    return records


def add_manual_entry(data: ManualAccountCreate) -> dict:
    today = datetime.utcnow().strftime("%Y-%m-%d")
    row = [
        today,
        data.account_name,
        data.owner,
        data.value,
        data.notes or "",
    ]
    sheets_client.append_row("manual", row)
    return {
        "entry_date": today,
        "account_name": data.account_name,
        "owner": data.owner,
        "value": data.value,
        "notes": data.notes,
    }


def get_latest_manual_values() -> dict[str, float]:
    """Return the most recent value for each account_name."""
    records = sheets_client.get_all_records("manual")
    records.sort(key=lambda r: r.get("entry_date", ""), reverse=True)
    latest: dict[str, float] = {}
    for r in records:
        name = r.get("account_name", "")
        if name and name not in latest:
            try:
                latest[name] = float(r.get("value", 0))
            except (ValueError, TypeError):
                latest[name] = 0.0
    return latest
