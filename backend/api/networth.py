from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException
from services import networth as svc
from api.auth import verify_token

router = APIRouter(prefix="/networth", tags=["networth"])

EMPTY_DASHBOARD = {
    "total_net_worth": 0,
    "investment_value": 0,
    "retirement_value": 0,
    "cash_value": 0,
    "crypto_value": 0,
    "real_estate_value": 0,
    "monthly_change": 0,
    "monthly_change_pct": 0,
    "ytd_change": 0,
    "ytd_change_pct": 0,
    "last_updated": datetime.utcnow().strftime("%Y-%m-%d"),
}


@router.get("/dashboard")
def dashboard(user=Depends(verify_token)):
    try:
        return svc.get_dashboard_summary()
    except Exception as e:
        return {**EMPTY_DASHBOARD, "_error": str(e)}


@router.get("/history")
def history(period: str = Query("all", pattern="^(1m|3m|1y|5y|all)$"), user=Depends(verify_token)):
    try:
        return svc.get_networth_history(period)
    except Exception:
        return []


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
    try:
        return svc.record_networth_snapshot(
            investment_value=investment_value,
            retirement_value=retirement_value,
            cash_value=cash_value,
            crypto_value=crypto_value,
            real_estate_value=real_estate_value,
            liabilities=liabilities,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
