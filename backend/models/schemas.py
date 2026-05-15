from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from enum import Enum


class AccountType(str, Enum):
    BROKERAGE = "brokerage"
    ROTH_IRA = "roth_ira"
    TRADITIONAL_IRA = "traditional_ira"
    FOUR01K = "401k"
    SOLO_401K = "solo_401k"
    SEP_IRA = "sep_ira"
    HSA = "hsa"
    FSA = "fsa"
    CRYPTO = "crypto"
    SAVINGS = "savings"
    CHECKING = "checking"
    TREASURY = "treasury"
    CD = "cd"
    REAL_ESTATE = "real_estate"


class TaxStatus(str, Enum):
    TAXABLE = "taxable"
    TAX_DEFERRED = "tax_deferred"
    TAX_FREE = "tax_free"


class Owner(str, Enum):
    SELF = "self"
    SPOUSE = "spouse"
    JOINT = "joint"


class TransactionType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    DIVIDEND = "DIVIDEND"
    INTEREST = "INTEREST"
    OPTION_BUY = "OPTION_BUY"
    OPTION_SELL = "OPTION_SELL"
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    TRANSFER = "TRANSFER"
    SPLIT = "SPLIT"
    OTHER     = "OTHER"      # unrecognised code — uploaded for manual review, excluded from P&L
    DUPLICATE = "DUPLICATE"  # re-imported row — uploaded for audit trail, excluded from P&L


class Account(BaseModel):
    account_id: str
    broker_name: str
    account_name: str
    account_type: AccountType
    owner: Owner
    tax_status: TaxStatus
    active: bool = True


class AccountCreate(BaseModel):
    broker_name: str
    account_name: str
    account_type: AccountType
    owner: Owner
    tax_status: TaxStatus


class Transaction(BaseModel):
    transaction_id: str
    date: str
    ticker: Optional[str] = None
    action: TransactionType
    quantity: Optional[float] = None
    price: Optional[float] = None
    fees: Optional[float] = 0.0
    total_amount: float
    broker: str
    account_id: str
    imported_file: Optional[str] = None
    upload_timestamp: Optional[str] = None


class HoldingSnapshot(BaseModel):
    snapshot_date: str
    ticker: str
    quantity: float
    market_value: float
    cost_basis: Optional[float] = None
    unrealized_gain: Optional[float] = None
    account_id: str


class ManualAccount(BaseModel):
    entry_date: str
    account_name: str
    owner: Owner
    value: float
    notes: Optional[str] = ""


class ManualAccountCreate(BaseModel):
    account_name: str
    owner: Owner
    value: float
    notes: Optional[str] = ""


class NetWorthEntry(BaseModel):
    date: str
    total_assets: float
    total_liabilities: float
    net_worth: float
    investment_value: float
    retirement_value: float
    cash_value: float


class ProjectionScenario(BaseModel):
    scenario_name: str
    current_value: float
    annual_return: float
    inflation: float
    monthly_contribution: float
    target_age: int
    current_age: int


class ProjectionResult(BaseModel):
    scenario_name: str
    years: List[int]
    nominal_values: List[float]
    real_values: List[float]
    fire_age: Optional[int] = None
    coast_fire_value: Optional[float] = None
    target_value: Optional[float] = None


class ImportResult(BaseModel):
    imported: int
    skipped_duplicates: int = 0   # kept for compat; always 0 now (dups are uploaded)
    duplicate_uploaded: int = 0   # rows re-uploaded with action=DUPLICATE
    errors: int = 0
    error_details: List[str] = []


class LoginRequest(BaseModel):
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class DashboardSummary(BaseModel):
    total_net_worth: float
    investment_value: float
    retirement_value: float
    cash_value: float
    crypto_value: float
    real_estate_value: float
    monthly_change: float
    monthly_change_pct: float
    ytd_change: float
    ytd_change_pct: float
    last_updated: str
