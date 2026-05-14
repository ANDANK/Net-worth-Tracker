from fastapi import APIRouter, Depends, Query, HTTPException
from services import pnl as svc
from api.auth import verify_token

router = APIRouter(prefix="/pnl", tags=["pnl"])

_EMPTY = {
    "total_realized": 0, "total_dividends": 0, "total_return": 0,
    "total_invested": 0, "win_count": 0, "loss_count": 0, "win_rate": 0,
    "by_ticker": [], "timeline": [],
}


@router.get("/")
def get_pnl(
    account_id: str = Query(None),
    period: str = Query("all", pattern="^(1m|3m|6m|1y|3y|5y|all)$"),
    ticker: str = Query(None),
    user=Depends(verify_token),
):
    try:
        return svc.compute_pnl(
            account_id=account_id or None,
            period=period,
            ticker=ticker or None,
        )
    except Exception as e:
        return {**_EMPTY, "_error": str(e)}


@router.get("/validate")
def validate_pnl(
    account_id: str = Query(None),
    user=Depends(verify_token),
):
    """
    Detect sells with zero cost basis — a sign that matching BUY rows
    were dropped during import (unrecognised action codes, parse errors).
    """
    try:
        return svc.validate_pnl(account_id=account_id or None)
    except Exception as e:
        return {
            "has_issues": False,
            "zero_basis_sell_count": 0,
            "total_inflated_gain": 0,
            "affected_tickers": [],
            "sample_sells": [],
            "_error": str(e),
        }
