import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, Legend,
} from 'recharts'
import { networthApi } from '../services/api'
import { NetWorthPoint } from '../types'
import PageHeader from '../components/PageHeader'
import LoadingSpinner from '../components/LoadingSpinner'

const PERIODS = ['1m', '3m', '1y', '5y', 'all'] as const

function fmt(n: number) {
  if (Math.abs(n) >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`
  if (Math.abs(n) >= 1_000) return `$${(n / 1_000).toFixed(0)}K`
  return `$${n.toFixed(0)}`
}

function fmtDate(d: string) {
  return new Date(d).toLocaleDateString('en-US', { month: 'short', year: '2-digit' })
}

const TOOLTIP_STYLE = {
  contentStyle: { background: '#1e293b', border: '1px solid #334155', borderRadius: 8 },
  labelStyle: { color: '#94a3b8', fontSize: 12 },
}

export default function Analytics() {
  const [period, setPeriod] = useState<string>('1y')

  const { data: history = [], isLoading } = useQuery<NetWorthPoint[]>({
    queryKey: ['networth-history', period],
    queryFn: () => networthApi.history(period).then((r) => r.data),
    retry: false,
  })

  const stackedData = history.map((h) => ({
    ...h,
    date: h.date,
  }))

  return (
    <div>
      <PageHeader title="Analytics" subtitle="Portfolio performance over time" />

      <div className="flex gap-1 mb-6">
        {PERIODS.map((p) => (
          <button
            key={p}
            onClick={() => setPeriod(p)}
            className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
              period === p ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-slate-100 hover:bg-slate-700'
            }`}
          >
            {p.toUpperCase()}
          </button>
        ))}
      </div>

      {isLoading ? <LoadingSpinner /> : (
        <div className="grid gap-4">
          <div className="card">
            <h2 className="text-sm font-semibold text-slate-100 mb-4">Net Worth Trend</h2>
            {history.length > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <LineChart data={history}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="date" tickFormatter={fmtDate} tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis tickFormatter={fmt} tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} width={70} />
                  <Tooltip {...TOOLTIP_STYLE} formatter={(v: number) => [fmt(v)]} labelFormatter={fmtDate} />
                  <Line type="monotone" dataKey="net_worth" stroke="#3b82f6" strokeWidth={2} dot={false} name="Net Worth" />
                  <Line type="monotone" dataKey="investment_value" stroke="#10b981" strokeWidth={1.5} dot={false} name="Investments" strokeDasharray="4 2" />
                  <Line type="monotone" dataKey="retirement_value" stroke="#8b5cf6" strokeWidth={1.5} dot={false} name="Retirement" strokeDasharray="4 2" />
                  <Legend iconType="line" formatter={(v) => <span className="text-xs text-slate-400">{v}</span>} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-48 text-slate-500 text-sm">
                No history snapshots yet. Record your first net worth snapshot.
              </div>
            )}
          </div>

          <div className="card">
            <h2 className="text-sm font-semibold text-slate-100 mb-4">Portfolio Composition Over Time</h2>
            {history.length > 0 ? (
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={stackedData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="date" tickFormatter={fmtDate} tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis tickFormatter={fmt} tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} width={70} />
                  <Tooltip {...TOOLTIP_STYLE} formatter={(v: number) => [fmt(v)]} labelFormatter={fmtDate} />
                  <Legend iconType="square" formatter={(v) => <span className="text-xs text-slate-400">{v}</span>} />
                  <Bar dataKey="investment_value" name="Investments" fill="#10b981" stackId="a" />
                  <Bar dataKey="retirement_value" name="Retirement" fill="#8b5cf6" stackId="a" />
                  <Bar dataKey="cash_value" name="Cash" fill="#06b6d4" stackId="a" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-48 text-slate-500 text-sm">
                No composition data yet.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
