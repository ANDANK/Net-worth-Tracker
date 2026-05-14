"""Broker list service — reads from Google Sheets, auto-seeds on first run."""
from google_sheets.client import sheets_client

# Parsers that actually exist in parsers/
KNOWN_PARSERS = {"robinhood", "schwab", "fidelity", "vanguard", "webull", "etrade"}

# Seeded into the sheet on first load if it is empty
_DEFAULTS: list[tuple[str, str]] = [
    ("robinhood", "Robinhood"),
    ("schwab",    "Charles Schwab"),
    ("fidelity",  "Fidelity"),
    ("vanguard",  "Vanguard"),
    ("webull",    "Webull"),
    ("etrade",    "E*TRADE"),
]


def _is_active(val) -> bool:
    return str(val).strip().upper() not in ("FALSE", "0", "NO", "")


def _seed() -> None:
    rows = [[bid, bname, "TRUE"] for bid, bname in _DEFAULTS]
    sheets_client.append_rows_batch("brokers", rows)


def list_brokers(include_inactive: bool = False) -> list[dict]:
    records = sheets_client.get_all_records("brokers")

    if not records:
        _seed()
        records = [
            {"broker_id": bid, "broker_name": bname, "active": "TRUE"}
            for bid, bname in _DEFAULTS
        ]

    result = []
    for r in records:
        bid = str(r.get("broker_id", "")).strip()
        if not bid:
            continue
        result.append({
            "id":         bid,
            "name":       str(r.get("broker_name", bid)),
            "active":     _is_active(r.get("active", "TRUE")),
            "has_parser": bid in KNOWN_PARSERS,
        })

    if not include_inactive:
        result = [b for b in result if b["active"]]

    return result


def add_broker(broker_id: str, broker_name: str) -> dict:
    bid = broker_id.lower().strip().replace(" ", "_")
    sheets_client.append_row("brokers", [bid, broker_name.strip(), "TRUE"])
    return {"id": bid, "name": broker_name.strip(), "active": True, "has_parser": bid in KNOWN_PARSERS}


def set_active(broker_id: str, active: bool) -> dict:
    """Toggle a broker active/inactive by rewriting its row."""
    row_idx = sheets_client.find_row_by_field("brokers", "broker_id", broker_id)
    if row_idx is None:
        raise ValueError(f"Broker '{broker_id}' not found in Brokers sheet")

    records = sheets_client.get_all_records("brokers")
    broker = next((r for r in records if str(r.get("broker_id", "")).strip() == broker_id), None)
    if broker is None:
        raise ValueError(f"Broker '{broker_id}' not found")

    sheets_client.update_row("brokers", row_idx, [
        broker["broker_id"],
        broker["broker_name"],
        "TRUE" if active else "FALSE",
    ])
    return {
        "id":         broker_id,
        "name":       broker["broker_name"],
        "active":     active,
        "has_parser": broker_id in KNOWN_PARSERS,
    }
