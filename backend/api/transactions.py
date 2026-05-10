from fastapi import APIRouter, Depends, UploadFile, File, Form, Query
from models.schemas import ImportResult
from services import transactions as svc
from api.auth import verify_token

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
    return svc.list_transactions(
        account_id=account_id,
        broker=broker,
        ticker=ticker,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )


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
