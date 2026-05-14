from fastapi import APIRouter, Depends, UploadFile, File, Form, Query, HTTPException
from models.schemas import ImportResult
from services import transactions as svc
from api.auth import verify_token
from parsers import get_parser
from services.transactions import _read_file

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("/")
def list_transactions(
    account_id: str = Query(None),
    broker: str = Query(None),
    ticker: str = Query(None),
    start_date: str = Query(None),
    end_date: str = Query(None),
    limit: int = Query(500, le=2000),
    user=Depends(verify_token),
):
    try:
        return svc.list_transactions(
            account_id=account_id,
            broker=broker,
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )
    except Exception:
        return []


@router.post("/preview")
async def preview_upload(
    file: UploadFile = File(...),
    broker: str = Form(...),
    account_id: str = Form(...),
    user=Depends(verify_token),
):
    data = await file.read()
    rows = svc.preview_file(data, file.filename, broker, account_id)
    return {"rows": rows, "count": len(rows)}


@router.post("/diagnose")
async def diagnose_file(
    file: UploadFile = File(...),
    broker: str = Form(...),
    account_id: str = Form(...),
    user=Depends(verify_token),
):
    """
    Parse a broker file in diagnostic mode.
    Returns how many rows were recognised vs silently dropped, broken down
    by action code so you can see exactly what was missed and why.
    """
    data = await file.read()

    try:
        df = _read_file(data, file.filename or "upload")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read file: {e}")

    parser = get_parser(broker)
    if parser is None:
        raise HTTPException(status_code=400, detail=f"Unknown broker: {broker}")

    parsed = parser.parse(df, account_id, file.filename or "upload")
    parsed_count = len(parsed)

    # Broker-specific diagnostic breakdown
    diag: dict = {}
    if hasattr(parser, "diagnose"):
        diag = parser.diagnose(df)

    # Action-level breakdown of what was imported
    from collections import Counter
    action_counter = Counter(str(tx.action) for tx in parsed)

    return {
        "filename": file.filename,
        "broker": broker,
        "total_rows_in_file": diag.get("total_rows", len(df)),
        "parsed_count": parsed_count,
        "skipped_by_unrecognised_action": diag.get("skipped_by_unrecognised_action", 0),
        "action_column_used": diag.get("action_column"),
        "recognised_actions": diag.get("recognised", {}),
        "unrecognised_actions": diag.get("unrecognised", {}),
        "imported_by_type": dict(action_counter),
    }


@router.post("/import", response_model=ImportResult)
async def import_file(
    file: UploadFile = File(...),
    broker: str = Form(...),
    account_id: str = Form(...),
    user=Depends(verify_token),
):
    data = await file.read()
    result = svc.import_file(data, file.filename, broker, account_id)
    return result
