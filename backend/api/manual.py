from fastapi import APIRouter, Depends, Query, HTTPException
from models.schemas import ManualAccountCreate
from services import manual_accounts as svc
from api.auth import verify_token

router = APIRouter(prefix="/manual", tags=["manual"])


@router.get("/")
def list_manual(owner: str = Query(None), user=Depends(verify_token)):
    try:
        return svc.list_manual_accounts(owner=owner)
    except Exception:
        return []


@router.post("/")
def add_entry(data: ManualAccountCreate, user=Depends(verify_token)):
    try:
        return svc.add_manual_entry(data)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/latest")
def latest_values(user=Depends(verify_token)):
    try:
        return svc.get_latest_manual_values()
    except Exception:
        return {}
