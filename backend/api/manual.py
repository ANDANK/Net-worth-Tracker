from fastapi import APIRouter, Depends, Query
from models.schemas import ManualAccountCreate
from services import manual_accounts as svc
from api.auth import verify_token

router = APIRouter(prefix="/manual", tags=["manual"])


@router.get("/")
def list_manual(owner: str = Query(None), user=Depends(verify_token)):
    return svc.list_manual_accounts(owner=owner)


@router.post("/")
def add_entry(data: ManualAccountCreate, user=Depends(verify_token)):
    return svc.add_manual_entry(data)


@router.get("/latest")
def latest_values(user=Depends(verify_token)):
    return svc.get_latest_manual_values()
