"""NetWorth Tracker — FastAPI backend entry point."""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from api.auth import router as auth_router
from api.accounts import router as accounts_router
from api.transactions import router as transactions_router
from api.manual import router as manual_router
from api.networth import router as networth_router
from api.projections import router as projections_router
from api.pnl import router as pnl_router
from api.brokers import router as brokers_router

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """On startup: ensure all Google Sheets tabs exist and seed Brokers if empty."""
    try:
        from google_sheets.client import sheets_client
        sheets_client.ensure_headers()          # creates any missing tabs
        from services.brokers import list_brokers
        list_brokers()                          # seeds Brokers tab if empty
    except Exception as e:
        print(f"[startup] Google Sheets init skipped: {e}")
    yield  # app runs here


app = FastAPI(
    lifespan=lifespan,
    title="NetWorth Tracker API",
    description="Personal finance dashboard backend",
    version="1.0.0",
)

allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api")
app.include_router(accounts_router, prefix="/api")
app.include_router(transactions_router, prefix="/api")
app.include_router(manual_router, prefix="/api")
app.include_router(networth_router, prefix="/api")
app.include_router(projections_router, prefix="/api")
app.include_router(pnl_router, prefix="/api")
app.include_router(brokers_router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}


