"""Transaction import and query service."""
from google_sheets.client import sheets_client
from parsers import get_parser
from models.schemas import ImportResult
import pandas as pd
import io


def _read_file(file_bytes: bytes, filename: str) -> pd.DataFrame:
    """Read CSV or XLSX tolerantly — skip malformed rows, try multiple encodings."""
    if filename.lower().endswith(".xlsx"):
        return pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl")

    for encoding in ("utf-8", "latin-1", "cp1252"):
        try:
            text = file_bytes.decode(encoding, errors="replace")
            break
        except Exception:
            continue

    lines = _strip_footer(text.splitlines())
    return pd.read_csv(
        io.StringIO("\n".join(lines)),
        on_bad_lines="skip",
        engine="python",
        skip_blank_lines=True,
    )


def _strip_footer(lines: list[str]) -> list[str]:
    """Remove trailing non-data lines brokers append (totals, disclaimers)."""
    if not lines:
        return lines
    for i in range(len(lines) - 1, 0, -1):
        if "," in lines[i] and not lines[i].strip().startswith("#"):
            return lines[: i + 1]
    return lines


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
        df = _read_file(file_bytes, filename)
    except Exception as e:
        return ImportResult(imported=0, skipped_duplicates=0, errors=1,
                            error_details=[f"Could not parse file: {str(e)}"])

    if df.empty:
        return ImportResult(imported=0, skipped_duplicates=0, errors=1,
                            error_details=["File parsed but contained no rows. Check broker selection."])

    parsed = parser.parse(df, account_id, filename)

    if not parsed:
        return ImportResult(imported=0, skipped_duplicates=0, errors=1,
                            error_details=[
                                f"File was read ({len(df)} rows) but no transactions could be extracted. "
                                "Verify you selected the correct broker."
                            ])

    # --- Duplicate check: 1 API call (reads transaction_id column only) ---
    try:
        existing_ids = sheets_client.get_existing_transaction_ids()
    except Exception as e:
        return ImportResult(imported=0, skipped_duplicates=0, errors=1,
                            error_details=[f"Could not reach Google Sheets: {str(e)}"])

    new_rows: list[list] = []
    skipped = 0

    for tx in parsed:
        if tx.transaction_id in existing_ids:
            skipped += 1
        else:
            new_rows.append(tx.to_row())
            existing_ids.add(tx.transaction_id)   # prevent intra-batch dupes

    if not new_rows:
        return ImportResult(imported=0, skipped_duplicates=skipped, errors=0)

    # --- Batch write: all rows in as few API calls as possible ---
    try:
        sheets_client.append_rows_batch("transactions", new_rows)
    except Exception as e:
        return ImportResult(imported=0, skipped_duplicates=skipped, errors=len(new_rows),
                            error_details=[f"Batch write failed: {str(e)}"])

    return ImportResult(
        imported=len(new_rows),
        skipped_duplicates=skipped,
        errors=0,
    )


def preview_file(file_bytes: bytes, filename: str, broker: str, account_id: str) -> list[dict]:
    """Parse and return rows without saving — used for the preview step."""
    parser = get_parser(broker)
    if parser is None:
        return []
    try:
        df = _read_file(file_bytes, filename)
    except Exception:
        return []
    parsed = parser.parse(df, account_id, filename)
    return [tx.to_dict() for tx in parsed]


def diagnose_file(file_bytes: bytes, filename: str, broker: str, account_id: str) -> dict:
    """
    Parse the file and return a full breakdown of what would be imported vs skipped,
    including unrecognised action codes and duplicate detection.
    """
    parser = get_parser(broker)
    if parser is None:
        return {"error": f"No parser for broker '{broker}'"}

    try:
        df = _read_file(file_bytes, filename)
    except Exception as e:
        return {"error": f"Could not read file: {e}"}

    parsed = parser.parse(df, account_id, filename)

    # Per-action breakdown from raw file
    diag = parser.diagnose(df) if hasattr(parser, "diagnose") else {}

    # Duplicate check against existing sheet
    try:
        existing_ids = sheets_client.get_existing_transaction_ids()
    except Exception as e:
        existing_ids = set()
        diag["sheets_error"] = str(e)

    new_count = 0
    dup_count = 0
    seen = set()
    for tx in parsed:
        if tx.transaction_id in existing_ids or tx.transaction_id in seen:
            dup_count += 1
        else:
            new_count += 1
        seen.add(tx.transaction_id)

    # Count by action type among parsed rows
    by_action: dict[str, int] = {}
    for tx in parsed:
        key = str(tx.action)
        by_action[key] = by_action.get(key, 0) + 1

    return {
        "total_rows_in_file":           len(df),
        "parsed_count":                 len(parsed),
        "would_import":                 new_count,
        "would_skip_duplicates":        dup_count,
        "skipped_unrecognised_action":  diag.get("skipped_by_unrecognised_action", 0),
        "recognised_actions":           diag.get("recognised", {}),
        "unrecognised_actions":         diag.get("unrecognised", {}),
        "parsed_by_action":             by_action,
    }


def list_transactions(
    account_id: str = None,
    broker: str = None,
    ticker: str = None,
    start_date: str = None,
    end_date: str = None,
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
