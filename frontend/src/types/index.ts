export type AccountType =
  | 'brokerage' | 'roth_ira' | 'traditional_ira' | '401k'
  | 'solo_401k' | 'sep_ira' | 'hsa' | 'fsa' | 'crypto'
  | 'savings' | 'checking' | 'treasury' | 'cd' | 'real_estate'

export type TaxStatus = 'taxable' | 'tax_deferred' | 'tax_free'
export type Owner = 'self' | 'spouse' | 'joint'

export type TransactionType =
  | 'BUY' | 'SELL' | 'DIVIDEND' | 'INTEREST'
  | 'OPTION_BUY' | 'OPTION_SELL' | 'DEPOSIT' | 'WITHDRAWAL'
  | 'TRANSFER' | 'SPLIT'

export interface Account {
  account_id: string
  broker_name: string
  account_name: string
  account_type: AccountType
  owner: Owner
  tax_status: TaxStatus
  active: boolean
}

export interface Transaction {
  transaction_id: string
  date: string
  ticker?: string
  action: TransactionType
  quantity?: number
  price?: number
  fees?: number
  total_amount: number
  broker: string
  account_id: string
  imported_file?: string
  upload_timestamp?: string
}

export interface ManualEntry {
  entry_date: string
  account_name: string
  owner: Owner
  value: number
  notes?: string
}

export interface NetWorthPoint {
  date: string
  total_assets: number
  total_liabilities: number
  net_worth: number
  investment_value: number
  retirement_value: number
  cash_value: number
}

export interface DashboardSummary {
  total_net_worth: number
  investment_value: number
  retirement_value: number
  cash_value: number
  crypto_value: number
  real_estate_value: number
  monthly_change: number
  monthly_change_pct: number
  ytd_change: number
  ytd_change_pct: number
  last_updated: string
}

export interface ImportResult {
  imported: number
  skipped_duplicates: number
  errors: number
  error_details: string[]
}

export interface ProjectionScenario {
  scenario_name: string
  current_value: number
  annual_return: number
  inflation: number
  monthly_contribution: number
  target_age: number
  current_age: number
}

export interface ProjectionResult {
  scenario_name: string
  years: number[]
  nominal_values: number[]
  real_values: number[]
  fire_age?: number
  coast_fire_value?: number
  target_value?: number
}
