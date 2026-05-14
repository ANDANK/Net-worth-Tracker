from fastapi import APIRouter, Depends, HTTPException
from models.schemas import AccountCreate
from services import accounts as svc
from api.auth import verify_token

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("/")
def list_accounts(user=Depends(verify_token)):
    try:
        return svc.list_accounts()
    except Exception:
        return []


@router.post("/")
def create_account(data: AccountCreate, user=Depends(verify_token)):
    try:
        return svc.create_account(data)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.delete("/{account_id}")
def deactivate_account(account_id: str, user=Depends(verify_token)):
    try:
        ok = svc.deactivate_account(account_id)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
    if not ok:
        raise HTTPException(status_code=404, detail="Account not found")
    return {"status": "deactivated"}
