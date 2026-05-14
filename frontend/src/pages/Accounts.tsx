import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, XCircle, AlertCircle } from 'lucide-react'
import { accountsApi, manualApi, brokersApi } from '../services/api'
import { Account, AccountType, Owner, TaxStatus } from '../types'
import PageHeader from '../components/PageHeader'
import LoadingSpinner from '../components/LoadingSpinner'

const ACCOUNT_TYPES: { value: AccountType; label: string }[] = [
  { value: 'brokerage', label: 'Brokerage' },
  { value: 'roth_ira', label: 'Roth IRA' },
  { value: 'traditional_ira', label: 'Traditional IRA' },
  { value: '401k', label: '401(k)' },
  { value: 'solo_401k', label: 'Solo 401(k)' },
  { value: 'sep_ira', label: 'SEP IRA' },
  { value: 'hsa', label: 'HSA' },
  { value: 'fsa', label: 'FSA' },
  { value: 'crypto', label: 'Crypto' },
  { value: 'savings', label: 'Savings' },
  { value: 'checking', label: 'Checking' },
  { value: 'treasury', label: 'Treasury Bills' },
  { value: 'cd', label: 'CD' },
  { value: 'real_estate', label: 'Real Estate' },
]

const TAX_MAP: Record<AccountType, TaxStatus> = {
  brokerage: 'taxable',
  roth_ira: 'tax_free',
  traditional_ira: 'tax_deferred',
  '401k': 'tax_deferred',
  solo_401k: 'tax_deferred',
  sep_ira: 'tax_deferred',
  hsa: 'tax_free',
  fsa: 'tax_free',
  crypto: 'taxable',
  savings: 'taxable',
  checking: 'taxable',
  treasury: 'taxable',
  cd: 'taxable',
  real_estate: 'taxable',
}

function errorMessage(err: unknown): string {
  const e = err as any
  return e?.response?.data?.detail ?? e?.message ?? 'Unknown error'
}

function AddAccountModal({
  onClose,
  onSave,
  saving,
  error,
}: {
  onClose: () => void
  onSave: (d: object) => void
  saving: boolean
  error: string | null
}) {
  const [form, setForm] = useState({
    broker_name: '',
    account_name: '',
    account_type: 'brokerage' as AccountType,
    owner: 'self' as Owner,
    tax_status: 'taxable' as TaxStatus,
  })
  const [brokerOther, setBrokerOther] = useState(false)

  const { data: brokers = [] } = useQuery({
    queryKey: ['brokers'],
    queryFn: () => brokersApi.list().then((r) => r.data),
    retry: false,
  })

  const set = (k: string, v: string) => {
    const next = { ...form, [k]: v }
    if (k === 'account_type') next.tax_status = TAX_MAP[v as AccountType]
    setForm(next as typeof form)
  }

  const handleBrokerSelect = (v: string) => {
    if (v === '__other__') {
      setBrokerOther(true)
      set('broker_name', '')
    } else {
      setBrokerOther(false)
      set('broker_name', v)
    }
  }

  const canSave = form.broker_name.trim() && form.account_name.trim()

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="card w-full max-w-md">
        <h3 className="text-base font-semibold text-slate-100 mb-4">Add Account</h3>
        <div className="space-y-3">
          <div>
            <label className="label">Broker / Institution</label>
            {brokers.length > 0 ? (
              <>
                <select
                  className="select"
                  value={brokerOther ? '__other__' : form.broker_name}
                  onChange={(e) => handleBrokerSelect(e.target.value)}
                  autoFocus
                >
                  <option value="">Select broker…</option>
                  {brokers.map((b: any) => (
                    <option key={b.id} value={b.name}>{b.name}</option>
                  ))}
                  <option value="__other__">Other (type manually)…</option>
                </select>
                {brokerOther && (
                  <input
                    className="input mt-2"
                    value={form.broker_name}
                    onChange={(e) => set('broker_name', e.target.value)}
                    placeholder="Enter institution name"
                    autoFocus
                  />
                )}
              </>
            ) : (
              <input
                className="input"
                value={form.broker_name}
                onChange={(e) => set('broker_name', e.target.value)}
                placeholder="e.g. Fidelity"
                autoFocus
              />
            )}
          </div>
          <div>
            <label className="label">Account Name</label>
            <input
              className="input"
              value={form.account_name}
              onChange={(e) => set('account_name', e.target.value)}
              placeholder="e.g. My Roth IRA"
            />
          </div>
          <div>
            <label className="label">Account Type</label>
            <select className="select" value={form.account_type} onChange={(e) => set('account_type', e.target.value)}>
              {ACCOUNT_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Owner</label>
              <select className="select" value={form.owner} onChange={(e) => set('owner', e.target.value)}>
                <option value="self">Self</option>
                <option value="spouse">Spouse</option>
                <option value="joint">Joint</option>
              </select>
            </div>
            <div>
              <label className="label">Tax Status</label>
              <select className="select" value={form.tax_status} onChange={(e) => set('tax_status', e.target.value)}>
                <option value="taxable">Taxable</option>
                <option value="tax_deferred">Tax Deferred</option>
                <option value="tax_free">Tax Free</option>
              </select>
            </div>
          </div>
        </div>

        {error && (
          <div className="mt-3 flex items-start gap-2 p-3 bg-red-900/30 border border-red-700/40 rounded-lg">
            <AlertCircle size={14} className="text-red-400 mt-0.5 shrink-0" />
            <p className="text-sm text-red-300">{error}</p>
          </div>
        )}

        <div className="flex gap-2 mt-5">
          <button
            className="btn-primary flex-1"
            onClick={() => onSave(form)}
            disabled={saving || !canSave}
          >
            {saving ? 'Saving…' : 'Save'}
          </button>
          <button className="btn-secondary" onClick={onClose} disabled={saving}>Cancel</button>
        </div>
      </div>
    </div>
  )
}

function ManualEntryModal({
  onClose,
  onSave,
  saving,
  error,
}: {
  onClose: () => void
  onSave: (d: object) => void
  saving: boolean
  error: string | null
}) {
  const [form, setForm] = useState({ account_name: '', owner: 'self' as Owner, value: '', notes: '' })
  const canSave = form.account_name.trim() && form.value

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="card w-full max-w-md">
        <h3 className="text-base font-semibold text-slate-100 mb-4">Manual Account Entry</h3>
        <div className="space-y-3">
          <div>
            <label className="label">Account Name</label>
            <input
              className="input"
              value={form.account_name}
              onChange={(e) => setForm({ ...form, account_name: e.target.value })}
              placeholder="e.g. 401k at Work"
              autoFocus
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Owner</label>
              <select className="select" value={form.owner} onChange={(e) => setForm({ ...form, owner: e.target.value as Owner })}>
                <option value="self">Self</option>
                <option value="spouse">Spouse</option>
                <option value="joint">Joint</option>
              </select>
            </div>
            <div>
              <label className="label">Current Value ($)</label>
              <input
                className="input"
                type="number"
                value={form.value}
                onChange={(e) => setForm({ ...form, value: e.target.value })}
                placeholder="0.00"
              />
            </div>
          </div>
          <div>
            <label className="label">Notes</label>
            <input
              className="input"
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
              placeholder="Optional"
            />
          </div>
        </div>

        {error && (
          <div className="mt-3 flex items-start gap-2 p-3 bg-red-900/30 border border-red-700/40 rounded-lg">
            <AlertCircle size={14} className="text-red-400 mt-0.5 shrink-0" />
            <p className="text-sm text-red-300">{error}</p>
          </div>
        )}

        <div className="flex gap-2 mt-5">
          <button
            className="btn-primary flex-1"
            onClick={() => onSave({ ...form, value: parseFloat(form.value) || 0 })}
            disabled={saving || !canSave}
          >
            {saving ? 'Saving…' : 'Save'}
          </button>
          <button className="btn-secondary" onClick={onClose} disabled={saving}>Cancel</button>
        </div>
      </div>
    </div>
  )
}

export default function Accounts() {
  const qc = useQueryClient()
  const [showAdd, setShowAdd] = useState(false)
  const [showManual, setShowManual] = useState(false)
  const [addError, setAddError] = useState<string | null>(null)
  const [manualError, setManualError] = useState<string | null>(null)

  const { data: accounts = [], isLoading } = useQuery<Account[]>({
    queryKey: ['accounts'],
    queryFn: () => accountsApi.list().then((r) => r.data),
    retry: false,
  })

  const { data: manualEntries = [] } = useQuery({
    queryKey: ['manual'],
    queryFn: () => manualApi.list().then((r) => r.data),
    retry: false,
  })

  const createAccount = useMutation({
    mutationFn: (data: object) => accountsApi.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['accounts'] })
      setShowAdd(false)
      setAddError(null)
    },
    onError: (err) => setAddError(errorMessage(err)),
  })

  const addManual = useMutation({
    mutationFn: (data: object) => manualApi.add(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['manual'] })
      setShowManual(false)
      setManualError(null)
    },
    onError: (err) => setManualError(errorMessage(err)),
  })

  if (isLoading) return <LoadingSpinner />

  return (
    <div>
      <PageHeader
        title="Accounts"
        subtitle="Manage all your financial accounts"
        action={
          <div className="flex gap-2">
            <button
              className="btn-secondary text-sm"
              onClick={() => { setManualError(null); setShowManual(true) }}
            >
              + Manual Entry
            </button>
            <button
              className="btn-primary text-sm"
              onClick={() => { setAddError(null); setShowAdd(true) }}
            >
              + Add Account
            </button>
          </div>
        }
      />

      <div className="grid gap-4">
        {accounts.length === 0 && (
          <div className="card text-center py-12 text-slate-500">
            No accounts yet. Add your first account to get started.
          </div>
        )}
        {accounts.map((acc) => (
          <div key={acc.account_id} className="card flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className={`w-2 h-10 rounded-full ${acc.active ? 'bg-emerald-500' : 'bg-slate-600'}`} />
              <div>
                <p className="font-medium text-slate-100">{acc.account_name}</p>
                <p className="text-sm text-slate-400">{acc.broker_name} · {acc.account_type} · {acc.owner}</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <span className={`badge-${acc.tax_status === 'taxable' ? 'blue' : 'green'}`}>
                {acc.tax_status.replace('_', ' ')}
              </span>
              {acc.active
                ? <CheckCircle2 size={16} className="text-emerald-400" />
                : <XCircle size={16} className="text-slate-500" />}
            </div>
          </div>
        ))}
      </div>

      {manualEntries.length > 0 && (
        <div className="mt-6">
          <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">Manual Entries</h2>
          <div className="grid gap-3">
            {manualEntries.map((e: any, i: number) => (
              <div key={i} className="card flex items-center justify-between">
                <div>
                  <p className="font-medium text-slate-100">{e.account_name}</p>
                  <p className="text-sm text-slate-400">{e.owner} · {e.entry_date}</p>
                  {e.notes && <p className="text-xs text-slate-500 mt-0.5">{e.notes}</p>}
                </div>
                <p className="text-lg font-bold text-blue-400">${Number(e.value).toLocaleString()}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {showAdd && (
        <AddAccountModal
          onClose={() => { setShowAdd(false); setAddError(null) }}
          onSave={(d) => { setAddError(null); createAccount.mutate(d) }}
          saving={createAccount.isPending}
          error={addError}
        />
      )}
      {showManual && (
        <ManualEntryModal
          onClose={() => { setShowManual(false); setManualError(null) }}
          onSave={(d) => { setManualError(null); addManual.mutate(d) }}
          saving={addManual.isPending}
          error={manualError}
        />
      )}
    </div>
  )
}
