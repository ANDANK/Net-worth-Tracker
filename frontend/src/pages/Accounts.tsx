import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Trash2, CheckCircle2, XCircle } from 'lucide-react'
import { accountsApi, manualApi } from '../services/api'
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

function AddAccountModal({ onClose, onSave }: { onClose: () => void; onSave: (d: object) => void }) {
  const [form, setForm] = useState({
    broker_name: '',
    account_name: '',
    account_type: 'brokerage' as AccountType,
    owner: 'self' as Owner,
    tax_status: 'taxable' as TaxStatus,
  })

  const set = (k: string, v: string) => {
    const next = { ...form, [k]: v }
    if (k === 'account_type') next.tax_status = TAX_MAP[v as AccountType]
    setForm(next as typeof form)
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="card w-full max-w-md">
        <h3 className="text-base font-semibold text-slate-100 mb-4">Add Account</h3>
        <div className="space-y-3">
          <div>
            <label className="label">Broker / Institution</label>
            <input className="input" value={form.broker_name} onChange={(e) => set('broker_name', e.target.value)} placeholder="e.g. Fidelity" />
          </div>
          <div>
            <label className="label">Account Name</label>
            <input className="input" value={form.account_name} onChange={(e) => set('account_name', e.target.value)} placeholder="e.g. My Roth IRA" />
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
        <div className="flex gap-2 mt-5">
          <button className="btn-primary flex-1" onClick={() => onSave(form)}>Save</button>
          <button className="btn-secondary" onClick={onClose}>Cancel</button>
        </div>
      </div>
    </div>
  )
}

function ManualEntryModal({ onClose, onSave }: { onClose: () => void; onSave: (d: object) => void }) {
  const [form, setForm] = useState({ account_name: '', owner: 'self' as Owner, value: '', notes: '' })
  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="card w-full max-w-md">
        <h3 className="text-base font-semibold text-slate-100 mb-4">Manual Account Entry</h3>
        <div className="space-y-3">
          <div>
            <label className="label">Account Name</label>
            <input className="input" value={form.account_name} onChange={(e) => setForm({ ...form, account_name: e.target.value })} placeholder="e.g. 401k at Work" />
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
              <input className="input" type="number" value={form.value} onChange={(e) => setForm({ ...form, value: e.target.value })} placeholder="0.00" />
            </div>
          </div>
          <div>
            <label className="label">Notes</label>
            <input className="input" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} placeholder="Optional" />
          </div>
        </div>
        <div className="flex gap-2 mt-5">
          <button className="btn-primary flex-1" onClick={() => onSave({ ...form, value: parseFloat(form.value) || 0 })}>Save</button>
          <button className="btn-secondary" onClick={onClose}>Cancel</button>
        </div>
      </div>
    </div>
  )
}

export default function Accounts() {
  const qc = useQueryClient()
  const [showAdd, setShowAdd] = useState(false)
  const [showManual, setShowManual] = useState(false)

  const { data: accounts = [], isLoading } = useQuery<Account[]>({
    queryKey: ['accounts'],
    queryFn: () => accountsApi.list().then((r) => r.data),
  })

  const { data: manualEntries = [] } = useQuery({
    queryKey: ['manual'],
    queryFn: () => manualApi.list().then((r) => r.data),
  })

  const createAccount = useMutation({
    mutationFn: (data: object) => accountsApi.create(data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['accounts'] }); setShowAdd(false) },
  })

  const addManual = useMutation({
    mutationFn: (data: object) => manualApi.add(data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['manual'] }); setShowManual(false) },
  })

  if (isLoading) return <LoadingSpinner />

  return (
    <div>
      <PageHeader
        title="Accounts"
        subtitle="Manage all your financial accounts"
        action={
          <div className="flex gap-2">
            <button className="btn-secondary text-sm" onClick={() => setShowManual(true)}>+ Manual Entry</button>
            <button className="btn-primary text-sm" onClick={() => setShowAdd(true)}>+ Add Account</button>
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
                </div>
                <p className="text-lg font-bold text-blue-400">${Number(e.value).toLocaleString()}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {showAdd && <AddAccountModal onClose={() => setShowAdd(false)} onSave={(d) => createAccount.mutate(d)} />}
      {showManual && <ManualEntryModal onClose={() => setShowManual(false)} onSave={(d) => addManual.mutate(d)} />}
    </div>
  )
}
