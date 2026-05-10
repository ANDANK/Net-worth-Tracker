import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from 'recharts'
import { networthApi } from '../services/api'
import { DashboardSummary, NetWorthPoint } from '../types'
import StatCard from '../components/StatCard'
import LoadingSpinner from '../components/LoadingSpinner'
import PageHeader from '../components/PageHeader'

const PERIODS = ['1m', '3m', '1y', '5y', 'all'] as const
type Period = typeof PERIODS[number]

const PIE_COLORS = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444', '#06b6d4']

function fmt(n: number) {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`
  return `$${n.toFixed(0)}`
}

function fmtDate(d: string) {
  return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: '2-digit' })
}

export default function Dashboard() {
  const [period, setPeriod] = useState<Period>('1y')

  const { data: summary, isLoading: summaryLoading } = useQuery<DashboardSummary>({
    queryKey: ['dashboard'],
    queryFn: () => networthApi.dashboard().then((r) => r.data),
  })

  const { data: history, isLoading: historyLoading } = useQuery<NetWorthPoint[]>({
    queryKey: ['networth-history', period],
    queryFn: () => networthApi.history(period).then((r) => r.data),
  })

  if (summaryLoading) return <LoadingSpinner />

  const s = summary!

  const pieData = [
    { name: 'Investments', value: s.investment_value },
    { name: 'Retirement', value: s.retirement_value },
    { name: 'Cash', value: s.cash_value },
    { name: 'Crypto', value: s.crypto_value },
    { name: 'Real Estate', value: s.real_estate_value },
  ].filter((d) => d.value > 0)

  return (
    <div>
      <PageHeader
        title="Dashboard"
        subtitle={`Last updated ${s.last_updated}`}
      />

      <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 mb-6">
        <div className="col-span-2">
          <StatCard
            title="Total Net Worth"
            value={s.total_net_worth}
            change={s.monthly_change}
            changePct={s.monthly_change_pct}
            subtitle="vs last month"
            color="blue"
          />
        </div>
        <StatCard title="Investments" value={s.investment_value} color="emerald" />
        <StatCard title="Retirement" value={s.retirement_value} color="violet" />
        <StatCard title="Cash" value={s.cash_value} color="cyan" />
        <StatCard title="Crypto" value={s.crypto_value} color="amber" />
        <StatCard title="Real Estate" value={s.real_estate_value} color="rose" />
        <StatCard
          title="YTD Change"
          value={s.ytd_change}
          changePct={s.ytd_change_pct}
          subtitle="year to date"
          color="blue"
        />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <div className="xl:col-span-2 card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-slate-100">Net Worth Over Time</h2>
            <div className="flex gap-1">
              {PERIODS.map((p) => (
                <button
                  key={p}
                  onClick={() => setPeriod(p)}
                  className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                    period === p
                      ? 'bg-blue-600 text-white'
                      : 'text-slate-400 hover:text-slate-100 hover:bg-slate-700'
                  }`}
                >
                  {p.toUpperCase()}
                </button>
              ))}
            </div>
          </div>
          {historyLoading ? (
            <LoadingSpinner size={20} />
          ) : history && history.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={history}>
                <XAxis
                  dataKey="date"
                  tickFormatter={fmtDate}
                  tick={{ fill: '#64748b', fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tickFormatter={fmt}
                  tick={{ fill: '#64748b', fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  width={70}
                />
                <Tooltip
                  contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
                  labelStyle={{ color: '#94a3b8', fontSize: 12 }}
                  formatter={(val: number) => [fmt(val), 'Net Worth']}
                  labelFormatter={fmtDate}
                />
                <Line
                  type="monotone"
                  dataKey="net_worth"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-48 text-slate-500 text-sm">
              No history yet — add a net worth snapshot to get started
            </div>
          )}
        </div>

        <div className="card">
          <h2 className="text-sm font-semibold text-slate-100 mb-4">Asset Allocation</h2>
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="45%"
                  innerRadius={60}
                  outerRadius={90}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {pieData.map((_, i) => (
                    <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
                  formatter={(val: number) => [fmt(val)]}
                />
                <Legend
                  iconType="circle"
                  iconSize={8}
                  formatter={(v) => <span className="text-xs text-slate-400">{v}</span>}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-48 text-slate-500 text-sm">
              No allocation data yet
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
