from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from services import brokers as svc
from api.auth import verify_token

router = APIRouter(prefix="/brokers", tags=["brokers"])

_FALLBACK = [
    {"id": "robinhood", "name": "Robinhood",       "active": True, "has_parser": True},
    {"id": "schwab",    "name": "Charles Schwab",   "active": True, "has_parser": True},
    {"id": "fidelity",  "name": "Fidelity",         "active": True, "has_parser": True},
    {"id": "vanguard",  "name": "Vanguard",          "active": True, "has_parser": True},
    {"id": "webull",    "name": "Webull",            "active": True, "has_parser": True},
    {"id": "etrade",    "name": "E*TRADE",           "active": True, "has_parser": True},
]


class BrokerCreate(BaseModel):
    broker_id: str
    broker_name: str


class BrokerToggle(BaseModel):
    active: bool


@router.get("/")
def list_brokers(include_inactive: bool = False, user=Depends(verify_token)):
    try:
        return svc.list_brokers(include_inactive=include_inactive)
    except Exception:
        return [b for b in _FALLBACK if include_inactive or b["active"]]


@router.post("/")
def add_broker(data: BrokerCreate, user=Depends(verify_token)):
    try:
        return svc.add_broker(data.broker_id, data.broker_name)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.patch("/{broker_id}")
def toggle_broker(broker_id: str, data: BrokerToggle, user=Depends(verify_token)):
    try:
        return svc.set_active(broker_id, data.active)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
