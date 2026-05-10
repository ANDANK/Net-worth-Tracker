from fastapi import APIRouter, Depends, Query
from services import networth as svc
from api.auth import verify_token

router = APIRouter(prefix="/networth", tags=["networth"])


@router.get("/dashboard")
def dashboard(user=Depends(verify_token)):
    return svc.get_dashboard_summary()


@router.get("/history")
def history(period: str = Query("all", regex="^(1m|3m|1y|5y|all)$"), user=Depends(verify_token)):
    return svc.get_networth_history(period)


@router.post("/snapshot")
def snapshot(
    investment_value: float = 0,
    retirement_value: float = 0,
    cash_value: float = 0,
    crypto_value: float = 0,
    real_estate_value: float = 0,
    liabilities: float = 0,
    user=Depends(verify_token),
):
    return svc.record_networth_snapshot(
        investment_value=investment_value,
        retirement_value=retirement_value,
        cash_value=cash_value,
        crypto_value=crypto_value,
        real_estate_value=real_estate_value,
        liabilities=liabilities,
    )
