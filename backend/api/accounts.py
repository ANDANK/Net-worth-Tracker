from fastapi import APIRouter, Depends, HTTPException
from models.schemas import AccountCreate
from services import accounts as svc
from api.auth import verify_token

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("/")
def list_accounts(user=Depends(verify_token)):
    return svc.list_accounts()


@router.post("/")
def create_account(data: AccountCreate, user=Depends(verify_token)):
    return svc.create_account(data)


@router.delete("/{account_id}")
def deactivate_account(account_id: str, user=Depends(verify_token)):
    ok = svc.deactivate_account(account_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Account not found")
    return {"status": "deactivated"}
