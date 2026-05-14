import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { networthApi, brokersApi } from '../services/api'
import PageHeader from '../components/PageHeader'
import { CheckCircle2, Plus, AlertTriangle, ToggleLeft, ToggleRight, Loader2, RefreshCw } from 'lucide-react'

// ─── Broker management card ──────────────────────────────────────────────────

function BrokerCard() {
  const qc = useQueryClient()
  const [showAdd, setShowAdd] = useState(false)
  const [newId, setNewId] = useState('')
  const [newName, setNewName] = useState('')
  const [addError, setAddError] = useState('')

  const { data: brokers = [], isLoading, refetch } = useQuery({
    queryKey: ['brokers-all'],
    queryFn: () => brokersApi.list(true).then(r => r.data),
    retry: false,
  })

  const addMutation = useMutation({
    mutationFn: () => brokersApi.add({ broker_id: newId.trim(), broker_name: newName.trim() }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['brokers-all'] })
      qc.invalidateQueries({ queryKey: ['brokers'] })
      setShowAdd(false)
      setNewId('')
      setNewName('')
      setAddError('')
    },
    onError: (e: any) => setAddError(e?.response?.data?.detail ?? 'Failed to add broker'),
  })

  const toggleMutation = useMutation({
    mutationFn: ({ id, active }: { id: string; active: boolean }) =>
      brokersApi.toggle(id, active),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['brokers-all'] })
      qc.invalidateQueries({ queryKey: ['brokers'] })
    },
  })

  const canAdd = newId.trim().length > 0 && newName.trim().length > 0

  return (
    <div className="card">
      <div className="flex items-start justify-between mb-1">
        <h3 className="text-sm font-semibold text-slate-100">Broker List</h3>
        <div className="flex items-center gap-2">
          <button
            onClick={() => refetch()}
            className="flex items-center gap-1 text-xs text-slate-400 hover:text-slate-200 transition-colors"
            title="Refresh from Google Sheets"
          >
            <RefreshCw size={12} className={isLoading ? 'animate-spin' : ''} />
            Sync
          </button>
          <button
            onClick={() => { setShowAdd(s => !s); setAddError('') }}
            className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 transition-colors"
          >
            <Plus size={13} />
            Add broker
          </button>
        </div>
      </div>
      <p className="text-xs text-slate-400 mb-4">
        Stored in the <span className="font-mono text-slate-300">Brokers</span> sheet in Google Sheets.
        Active brokers appear in the Upload and Add Account dropdowns.
        You can edit the sheet directly too — click Sync to reload.
      </p>

      {/* Add form */}
      {showAdd && (
        <div className="mb-4 p-3 rounded-lg bg-slate-800 border border-slate-700 space-y-2">
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="label">Broker ID</label>
              <input
                className="input text-sm"
                placeholder="e.g. tdameritrade"
                value={newId}
                onChange={e => setNewId(e.target.value.toLowerCase().replace(/\s+/g, '_'))}
              />
              <p className="text-xs text-slate-500 mt-1">Lowercase, no spaces. Must match parser key if used for import.</p>
            </div>
            <div>
              <label className="label">Display Name</label>
              <input
                className="input text-sm"
                placeholder="e.g. TD Ameritrade"
                value={newName}
                onChange={e => setNewName(e.target.value)}
              />
            </div>
          </div>
          {addError && <p className="text-xs text-red-400">{addError}</p>}
          <div className="flex gap-2">
            <button
              className="btn-primary text-sm py-1.5"
              disabled={!canAdd || addMutation.isPending}
              onClick={() => addMutation.mutate()}
            >
              {addMutation.isPending ? 'Saving…' : 'Add'}
            </button>
            <button className="btn-secondary text-sm py-1.5" onClick={() => setShowAdd(false)}>
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Broker list */}
      {isLoading ? (
        <div className="flex items-center gap-2 text-slate-500 text-sm py-2">
          <Loader2 size={14} className="animate-spin" /> Loading from Google Sheets…
        </div>
      ) : brokers.length === 0 ? (
        <p className="text-sm text-slate-500">No brokers found. The sheet will be seeded automatically on next load.</p>
      ) : (
        <div className="divide-y divide-slate-800">
          {brokers.map((b: any) => (
            <div key={b.id} className="flex items-center justify-between py-2.5">
              <div className="flex items-center gap-3 min-w-0">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className={`text-sm font-medium ${b.active ? 'text-slate-100' : 'text-slate-500'}`}>
                      {b.name}
                    </span>
                    {!b.has_parser && (
                      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs bg-amber-900/30 border border-amber-700/30 text-amber-400">
                        <AlertTriangle size={10} />
                        No parser
                      </span>
                    )}
                  </div>
                  <span className="text-xs font-mono text-slate-500">{b.id}</span>
                </div>
              </div>

              <button
                onClick={() => toggleMutation.mutate({ id: b.id, active: !b.active })}
                disabled={toggleMutation.isPending}
                className="text-slate-400 hover:text-slate-100 transition-colors flex-shrink-0"
                title={b.active ? 'Deactivate' : 'Activate'}
              >
                {b.active
                  ? <ToggleRight size={22} className="text-emerald-400" />
                  : <ToggleLeft size={22} className="text-slate-600" />
                }
              </button>
            </div>
          ))}
        </div>
      )}

      <p className="text-xs text-slate-600 mt-3 pt-3 border-t border-slate-800">
        "No parser" means the broker can be tracked manually but CSV import is not supported for it.
      </p>
    </div>
  )
}

// ─── Main page ───────────────────────────────────────────────────────────────

export default function Settings() {
  const [snapshot, setSnapshot] = useState({
    investment_value: '',
    retirement_value: '',
    cash_value: '',
    crypto_value: '',
    real_estate_value: '',
    liabilities: '',
  })
  const [saved, setSaved] = useState(false)

  const snapshotMutation = useMutation({
    mutationFn: () =>
      networthApi.snapshot(Object.fromEntries(
        Object.entries(snapshot).map(([k, v]) => [k, parseFloat(v) || 0])
      )),
    onSuccess: () => setSaved(true),
  })

  return (
    <div>
      <PageHeader title="Settings" subtitle="Configuration and utilities" />

      <div className="max-w-xl space-y-5">
        {/* Broker management */}
        <BrokerCard />

        {/* Net worth snapshot */}
        <div className="card">
          <h3 className="text-sm font-semibold text-slate-100 mb-1">Record Net Worth Snapshot</h3>
          <p className="text-xs text-slate-400 mb-4">Manually record today's values to build your net worth history chart.</p>
          <div className="grid grid-cols-2 gap-3">
            {[
              { key: 'investment_value', label: 'Investments ($)' },
              { key: 'retirement_value', label: 'Retirement ($)' },
              { key: 'cash_value', label: 'Cash ($)' },
              { key: 'crypto_value', label: 'Crypto ($)' },
              { key: 'real_estate_value', label: 'Real Estate ($)' },
              { key: 'liabilities', label: 'Liabilities ($)' },
            ].map(({ key, label }) => (
              <div key={key}>
                <label className="label">{label}</label>
                <input
                  className="input"
                  type="number"
                  value={snapshot[key as keyof typeof snapshot]}
                  onChange={(e) => setSnapshot({ ...snapshot, [key]: e.target.value })}
                  placeholder="0"
                />
              </div>
            ))}
          </div>
          <div className="flex items-center gap-3 mt-4">
            <button
              className="btn-primary"
              onClick={() => { setSaved(false); snapshotMutation.mutate() }}
              disabled={snapshotMutation.isPending}
            >
              {snapshotMutation.isPending ? 'Saving…' : 'Save Snapshot'}
            </button>
            {saved && (
              <span className="flex items-center gap-1 text-sm text-emerald-400">
                <CheckCircle2 size={14} /> Saved to Google Sheets
              </span>
            )}
          </div>
        </div>

        {/* About */}
        <div className="card">
          <h3 className="text-sm font-semibold text-slate-100 mb-2">About</h3>
          <div className="space-y-1 text-sm text-slate-400">
            <p>NetWorth Tracker v1.0</p>
            <p>Data stored in Google Sheets · Runs locally</p>
            <p className="text-xs text-slate-500 mt-2">
              API credentials stored in <code className="font-mono text-slate-400">.env</code> file — never committed to git.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
