import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { networthApi } from '../services/api'
import PageHeader from '../components/PageHeader'
import { CheckCircle2 } from 'lucide-react'

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
