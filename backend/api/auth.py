"""Simple local password authentication."""
import os
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from dotenv import load_dotenv
from models.schemas import LoginRequest, TokenResponse

load_dotenv()

router = APIRouter(prefix="/auth", tags=["auth"])
bearer_scheme = HTTPBearer()

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
APP_PASSWORD = os.getenv("APP_PASSWORD", "changeme")


def create_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(minutes=EXPIRE_MINUTES)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest):
    if req.password != APP_PASSWORD:
        raise HTTPException(status_code=401, detail="Incorrect password")
    token = create_token({"sub": "local_user"})
    return TokenResponse(access_token=token)


@router.get("/verify")
def verify(user=Depends(verify_token)):
    return {"status": "ok", "user": user.get("sub")}
