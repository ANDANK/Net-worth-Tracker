"""Transaction import and query service."""
from datetime import datetime
from google_sheets.client import sheets_client
from parsers import get_parser
from parsers.base import ParsedTransaction
from models.schemas import ImportResult
import pandas as pd
import io


def import_file(
    file_bytes: bytes,
    filename: str,
    broker: str,
    account_id: str,
) -> ImportResult:
    parser = get_parser(broker)
    if parser is None:
        return ImportResult(imported=0, skipped_duplicates=0, errors=1,
                            error_details=[f"Unknown broker: {broker}"])

    try:
        if filename.endswith(".xlsx"):
            df = pd.read_excel(io.BytesIO(file_bytes))
        else:
            df = pd.read_csv(io.StringIO(file_bytes.decode("utf-8", errors="replace")))
    except Exception as e:
        return ImportResult(imported=0, skipped_duplicates=0, errors=1,
                            error_details=[f"Could not parse file: {str(e)}"])

    parsed = parser.parse(df, account_id, filename)
    existing_ids = sheets_client.get_existing_transaction_ids()

    imported = 0
    skipped = 0
    errors = 0
    error_details = []

    for tx in parsed:
        if tx.transaction_id in existing_ids:
            skipped += 1
            continue
        try:
            sheets_client.append_row("transactions", tx.to_row())
            existing_ids.add(tx.transaction_id)
            imported += 1
        except Exception as e:
            errors += 1
            error_details.append(str(e))

    return ImportResult(
        imported=imported,
        skipped_duplicates=skipped,
        errors=errors,
        error_details=error_details,
    )


def preview_file(file_bytes: bytes, filename: str, broker: str, account_id: str) -> list[dict]:
    """Parse and return rows without saving — used for the preview step."""
    parser = get_parser(broker)
    if parser is None:
        return []
    try:
        if filename.endswith(".xlsx"):
            df = pd.read_excel(io.BytesIO(file_bytes))
        else:
            df = pd.read_csv(io.StringIO(file_bytes.decode("utf-8", errors="replace")))
    except Exception:
        return []

    parsed = parser.parse(df, account_id, filename)
    return [tx.to_dict() for tx in parsed]


def list_transactions(
    account_id: str = None,
    broker: str = None,
    ticker: str = None,
    start_date: str = None,
    end_date: str = None,
    owner: str = None,
    limit: int = 500,
) -> list[dict]:
    records = sheets_client.get_all_records("transactions")

    if account_id:
        records = [r for r in records if r.get("account_id") == account_id]
    if broker:
        records = [r for r in records if r.get("broker", "").lower() == broker.lower()]
    if ticker:
        records = [r for r in records if r.get("ticker", "").upper() == ticker.upper()]
    if start_date:
        records = [r for r in records if r.get("date", "") >= start_date]
    if end_date:
        records = [r for r in records if r.get("date", "") <= end_date]

    records.sort(key=lambda r: r.get("date", ""), reverse=True)
    return records[:limit]
