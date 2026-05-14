import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  AreaChart, Area, BarChart, Bar, Cell, PieChart, Pie,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts'
import { TrendingUp, TrendingDown, DollarSign, Trophy, Target, Activity, X, ChevronDown, AlertTriangle, ChevronRight } from 'lucide-react'
import { accountsApi, pnlApi, transactionsApi } from '../services/api'

// ─── Validation banner ───────────────────────────────────────────────────────

function ValidationBanner({ accountId }: { accountId: string }) {
  const [expanded, setExpanded] = useState(false)

  const { data } = useQuery({
    queryKey: ['pnl-validate', accountId],
    queryFn: () => pnlApi.validate(accountId || undefined).then(r => r.data),
    retry: false,
    staleTime: 60_000,
  })

  if (!data?.has_issues) return null

  return (
    <div className="rounded-xl border border-amber-600/40 bg-amber-500/10 p-4">
      <div className="flex items-start gap-3">
        <AlertTriangle size={18} className="text-amber-400 flex-shrink-0 mt-0.5" />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-amber-300">
            P&L may be inflated — {data.zero_basis_sell_count} sell{data.zero_basis_sell_count !== 1 ? 's' : ''} with $0 cost basis detected
          </p>
          <p className="text-xs text-amber-400/80 mt-1">
            Estimated inflation: <span className="font-bold text-amber-300">${data.total_inflated_gain.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>.
            {' '}This usually means matching BUY rows were dropped during import (unrecognised action codes).
            Re-uploading the file with the updated parser should fix it.
          </p>

          <button
            onClick={() => setExpanded(e => !e)}
            className="mt-2 flex items-center gap-1 text-xs text-amber-400 hover:text-amber-200 transition-colors"
          >
            <ChevronRight size={12} className={`transition-transform ${expanded ? 'rotate-90' : ''}`} />
            {expanded ? 'Hide' : 'Show'} affected tickers ({data.affected_tickers.length})
          </button>

          {expanded && (
            <div className="mt-3 overflow-x-auto">
              <table className="text-xs w-full">
                <thead>
                  <tr className="border-b border-amber-600/30">
                    {['Ticker', 'Sells w/ $0 basis', 'Inflated gain', 'Date range'].map(h => (
                      <th key={h} className="text-left pb-2 pr-4 text-amber-500 font-medium">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-amber-800/20">
                  {data.affected_tickers.map((t: any) => (
                    <tr key={t.ticker}>
                      <td className="py-1.5 pr-4 font-mono font-semibold text-amber-200">{t.ticker}</td>
                      <td className="py-1.5 pr-4 text-amber-300">{t.sell_count}</td>
                      <td className="py-1.5 pr-4 text-amber-300 font-medium">
                        ${t.inflated_gain.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                      </td>
                      <td className="py-1.5 text-amber-400/70">{t.first_sell_date} → {t.last_sell_date}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
import { Account } from '../types'
import PageHeader from '../components/PageHeader'
import LoadingSpinner from '../components/LoadingSpinner'

// ─── Helpers ────────────────────────────────────────────────────────────────

const PERIODS = [
  { label: '1M', value: '1m' }, { label: '3M', value: '3m' },
  { label: '6M', value: '6m' }, { label: '1Y', value: '1y' },
  { label: '3Y', value: '3y' }, { label: '5Y', value: '5y' },
  { label: 'All', value: 'all' },
]

function usd(n: number, compact = false): string {
  if (compact && Math.abs(n) >= 1000)
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', notation: 'compact', maximumFractionDigits: 1 }).format(n)
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(n)
}

function sign(n: number) { return n >= 0 ? '+' : '' }
function gainCls(n: number) { return n >= 0 ? 'text-emerald-400' : 'text-red-400' }
function gainColor(n: number) { return n >= 0 ? '#10b981' : '#f87171' }

const ACTION_COLORS: Record<string, string> = {
  BUY: '#60a5fa', SELL: '#f87171', DIVIDEND: '#34d399',
  INTEREST: '#34d399', DEPOSIT: '#a78bfa', WITHDRAWAL: '#fb923c',
}

// ─── Tooltips ────────────────────────────────────────────────────────────────

function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg p-3 shadow-xl text-xs space-y-1.5">
      <p className="text-slate-400 font-medium mb-2">{label}</p>
      {payload.map((p: any) => (
        <div key={p.dataKey} className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: p.color }} />
          <span className="text-slate-300">{p.name}:</span>
          <span className="font-semibold" style={{ color: p.color }}>{usd(p.value)}</span>
        </div>
      ))}
    </div>
  )
}

function BarTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  const val = payload[0]?.value ?? 0
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg p-3 shadow-xl text-xs">
      <p className="text-slate-300 font-semibold mb-1">{label}</p>
      <p style={{ color: gainColor(val) }}>{sign(val)}{usd(val)}</p>
    </div>
  )
}

// ─── KPI card ────────────────────────────────────────────────────────────────

function KpiCard({ label, value, sub, icon: Icon, positive }: {
  label: string; value: string; sub?: string
  icon: React.ElementType; positive?: boolean | null
}) {
  const accent = positive === true ? 'text-emerald-400' : positive === false ? 'text-red-400' : 'text-blue-400'
  const bg = positive === true ? 'bg-emerald-500/10 border-emerald-500/20' :
    positive === false ? 'bg-red-500/10 border-red-500/20' : 'bg-blue-500/10 border-blue-500/20'
  return (
    <div className="card flex items-start gap-4">
      <div className={`p-2.5 rounded-xl border flex-shrink-0 ${bg}`}>
        <Icon size={18} className={accent} />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">{label}</p>
        <p className={`text-xl font-bold ${accent} truncate`}>{value}</p>
        {sub && <p className="text-xs text-slate-500 mt-0.5">{sub}</p>}
      </div>
    </div>
  )
}

// ─── Ticker search ───────────────────────────────────────────────────────────

function TickerSearch({ tickers, value, onChange }: {
  tickers: string[]; value: string; onChange: (v: string) => void
}) {
  const [open, setOpen] = useState(false)
  const [input, setInput] = useState(value)

  const filtered = useMemo(() =>
    input
      ? tickers.filter(t => t.toLowerCase().includes(input.toLowerCase())).slice(0, 12)
      : tickers.slice(0, 12),
    [tickers, input]
  )

  function select(t: string) {
    setInput(t)
    onChange(t)
    setOpen(false)
  }

  function clear() {
    setInput('')
    onChange('')
    setOpen(false)
  }

  return (
    <div className="relative">
      <div className="relative flex items-center">
        <input
          className="input text-sm py-1.5 pr-8 min-w-[140px]"
          placeholder="Filter ticker…"
          value={input}
          onChange={e => { setInput(e.target.value); onChange(''); setOpen(true) }}
          onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 150)}
        />
        {input
          ? <button onClick={clear} className="absolute right-2 text-slate-500 hover:text-slate-300"><X size={14} /></button>
          : <ChevronDown size={14} className="absolute right-2 text-slate-500 pointer-events-none" />
        }
      </div>
      {open && filtered.length > 0 && (
        <div className="absolute top-full mt-1 left-0 w-full bg-slate-800 border border-slate-700 rounded-lg shadow-xl z-50 max-h-48 overflow-y-auto">
          {filtered.map(t => (
            <button
              key={t}
              onMouseDown={() => select(t)}
              className={`w-full text-left px-3 py-2 text-sm font-mono hover:bg-slate-700 transition-colors ${t === value ? 'text-blue-400 bg-slate-700/50' : 'text-slate-200'}`}
            >
              {t}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

// ─── Trade history panel ─────────────────────────────────────────────────────

function TradePanel({ ticker, accountId, period }: { ticker: string; accountId: string; period: string }) {
  const months: Record<string, number> = { '1m': 1, '3m': 3, '6m': 6, '1y': 12, '3y': 36, '5y': 60 }
  const startDate = useMemo(() => {
    const n = months[period]
    if (!n) return undefined
    const now = new Date()
    const total = now.getFullYear() * 12 + now.getMonth() - n
    const y = Math.floor(total / 12)
    const m = total % 12 + 1
    return `${y}-${String(m).padStart(2, '0')}-01`
  }, [period])

  const { data: trades = [], isLoading } = useQuery({
    queryKey: ['trades', ticker, accountId, period],
    queryFn: () => transactionsApi.list({
      ticker,
      account_id: accountId || undefined,
      start_date: startDate,
      limit: 200,
    }).then(r => r.data),
    enabled: !!ticker,
    retry: false,
  })

  if (isLoading) return <div className="card"><LoadingSpinner /></div>

  return (
    <div className="card">
      <h2 className="text-sm font-semibold text-slate-300 mb-4">
        Trade History — <span className="font-mono text-blue-400">{ticker}</span>
        <span className="ml-2 text-xs text-slate-500 font-normal">{trades.length} transactions</span>
      </h2>
      {trades.length === 0 ? (
        <p className="text-slate-500 text-sm text-center py-6">No transactions found for this ticker / period.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-700/60">
                {['Date', 'Action', 'Qty', 'Price', 'Fees', 'Total', 'Account'].map(h => (
                  <th key={h} className="text-left text-xs font-medium text-slate-500 uppercase tracking-wider pb-3 pr-4 last:pr-0">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {trades.map((t: any) => {
                const color = ACTION_COLORS[t.action] ?? '#94a3b8'
                return (
                  <tr key={t.transaction_id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="py-2.5 pr-4 text-slate-400 tabular-nums text-xs">{t.date}</td>
                    <td className="py-2.5 pr-4">
                      <span className="inline-block px-2 py-0.5 rounded text-xs font-semibold" style={{ color, background: color + '18' }}>
                        {t.action}
                      </span>
                    </td>
                    <td className="py-2.5 pr-4 tabular-nums text-slate-300">
                      {t.quantity != null ? Number(t.quantity).toLocaleString(undefined, { maximumFractionDigits: 4 }) : '—'}
                    </td>
                    <td className="py-2.5 pr-4 tabular-nums text-slate-300">
                      {t.price != null && t.price > 0 ? usd(t.price) : '—'}
                    </td>
                    <td className="py-2.5 pr-4 tabular-nums text-slate-500 text-xs">
                      {t.fees > 0 ? usd(t.fees) : '—'}
                    </td>
                    <td className={`py-2.5 pr-4 tabular-nums font-medium ${t.action === 'BUY' ? 'text-red-400' : 'text-emerald-400'}`}>
                      {t.total_amount != null ? `${t.action === 'BUY' ? '-' : '+'}${usd(Math.abs(t.total_amount))}` : '—'}
                    </td>
                    <td className="py-2.5 text-slate-500 text-xs truncate max-w-[120px]">{t.account_id}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

// ─── Main page ───────────────────────────────────────────────────────────────

export default function PnL() {
  const [period, setPeriod] = useState('all')
  const [accountId, setAccountId] = useState('')
  const [tickerFilter, setTickerFilter] = useState('')   // typed search
  const [selectedTicker, setSelectedTicker] = useState('') // committed (used for API + panel)

  const { data: accounts = [] } = useQuery<Account[]>({
    queryKey: ['accounts'],
    queryFn: () => accountsApi.list().then(r => r.data),
    retry: false,
  })

  // Fetch full summary (no ticker filter) — used for table + bar chart client-side filtering
  const { data, isLoading } = useQuery({
    queryKey: ['pnl', accountId, period],
    queryFn: () => pnlApi.get({ account_id: accountId || undefined, period }).then(r => r.data),
    retry: false,
  })

  // Fetch ticker-scoped data for timeline when a ticker is selected
  const { data: tickerData, isLoading: tickerLoading } = useQuery({
    queryKey: ['pnl', accountId, period, selectedTicker],
    queryFn: () => pnlApi.get({ account_id: accountId || undefined, period, ticker: selectedTicker }).then(r => r.data),
    enabled: !!selectedTicker,
    retry: false,
  })

  const summary = data ?? {
    total_realized: 0, total_dividends: 0, total_return: 0,
    total_invested: 0, win_count: 0, loss_count: 0, win_rate: 0,
    by_ticker: [], timeline: [],
  }

  // All known tickers for the search dropdown
  const allTickers: string[] = useMemo(() =>
    summary.by_ticker.map((t: any) => t.ticker).sort(),
    [summary.by_ticker]
  )

  // Client-side filtered ticker table + bar data
  const filteredTickers: any[] = useMemo(() => {
    if (!tickerFilter) return summary.by_ticker
    return summary.by_ticker.filter((t: any) =>
      t.ticker.toLowerCase().includes(tickerFilter.toLowerCase())
    )
  }, [summary.by_ticker, tickerFilter])

  // Active summary cards — use ticker-scoped data when selected
  const active = selectedTicker && tickerData ? tickerData : summary

  // Bar chart: top 20 by absolute realized, respecting client-side filter
  const barData = [...filteredTickers]
    .filter((t: any) => t.realized_gain !== 0)
    .sort((a: any, b: any) => Math.abs(b.realized_gain) - Math.abs(a.realized_gain))
    .slice(0, 20)
    .reverse()

  const pieData = [
    { name: 'Realized Gains', value: Math.max(active.total_realized, 0), fill: '#10b981' },
    { name: 'Realized Losses', value: Math.abs(Math.min(active.total_realized, 0)), fill: '#f87171' },
    { name: 'Dividends', value: active.total_dividends, fill: '#60a5fa' },
  ].filter(d => d.value > 0)

  const timelineData = selectedTicker ? (tickerData?.timeline ?? []) : summary.timeline
  const returnPositive = active.total_return >= 0

  function handleTickerChange(val: string) {
    setTickerFilter(val)
    // Only commit to API when the value exactly matches a known ticker
    if (allTickers.includes(val.toUpperCase())) {
      setSelectedTicker(val.toUpperCase())
    } else {
      setSelectedTicker('')
    }
  }

  function selectRow(ticker: string) {
    setTickerFilter(ticker)
    setSelectedTicker(ticker)
  }

  function clearTicker() {
    setTickerFilter('')
    setSelectedTicker('')
  }

  return (
    <div className="space-y-6 pb-10">
      {/* ── Header + filters ── */}
      <PageHeader
        title={selectedTicker ? `P&L — ${selectedTicker}` : 'Profit & Loss'}
        subtitle={selectedTicker
          ? 'Trade history, realized gains and dividends for this ticker'
          : 'Realized gains, losses and dividend income from your transactions'}
        action={
          <div className="flex items-center gap-3 flex-wrap justify-end">
            <select
              className="select text-sm py-1.5 min-w-[160px]"
              value={accountId}
              onChange={e => setAccountId(e.target.value)}
            >
              <option value="">All Accounts</option>
              {accounts.map((a: Account) => (
                <option key={a.account_id} value={a.account_id}>{a.account_name}</option>
              ))}
            </select>
            <TickerSearch tickers={allTickers} value={tickerFilter} onChange={handleTickerChange} />
            <div className="flex rounded-lg overflow-hidden border border-slate-700">
              {PERIODS.map(p => (
                <button
                  key={p.value}
                  onClick={() => setPeriod(p.value)}
                  className={`px-3 py-1.5 text-xs font-medium transition-colors ${period === p.value
                    ? 'bg-blue-600 text-white'
                    : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800'
                  }`}
                >{p.label}</button>
              ))}
            </div>
          </div>
        }
      />

      {/* Active ticker badge */}
      {selectedTicker && (
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500">Filtered to:</span>
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-blue-600/20 border border-blue-600/30 text-blue-400 text-sm font-mono font-semibold">
            {selectedTicker}
            <button onClick={clearTicker} className="hover:text-white transition-colors ml-1"><X size={12} /></button>
          </span>
          <span className="text-xs text-slate-500">— showing ticker-scoped metrics</span>
        </div>
      )}

      <ValidationBanner accountId={accountId} />

      {isLoading ? <LoadingSpinner /> : (
        <>
          {/* ── KPI Cards ── */}
          <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
            <KpiCard
              label="Total Return"
              value={`${sign(active.total_return)}${usd(active.total_return)}`}
              sub={selectedTicker ? selectedTicker : 'Realized + Dividends'}
              icon={returnPositive ? TrendingUp : TrendingDown}
              positive={active.total_return !== 0 ? returnPositive : null}
            />
            <KpiCard
              label="Realized P&L"
              value={`${sign(active.total_realized)}${usd(active.total_realized)}`}
              sub="From buy/sell trades"
              icon={Activity}
              positive={active.total_realized !== 0 ? active.total_realized >= 0 : null}
            />
            <KpiCard
              label="Dividend Income"
              value={usd(active.total_dividends)}
              sub="Cash distributions"
              icon={DollarSign}
              positive={null}
            />
            <KpiCard
              label="Total Invested"
              value={usd(active.total_invested, true)}
              sub={`${PERIODS.find(p => p.value === period)?.label ?? 'All'} period buys`}
              icon={Target}
              positive={null}
            />
            <KpiCard
              label="Win Rate"
              value={`${active.win_rate}%`}
              sub={`${active.win_count}W / ${active.loss_count}L`}
              icon={Trophy}
              positive={active.win_rate > 50 ? true : active.win_rate < 50 ? false : null}
            />
          </div>

          {/* ── Timeline ── */}
          {(tickerLoading && selectedTicker)
            ? <div className="card flex items-center justify-center py-10"><LoadingSpinner /></div>
            : timelineData.length > 0
            ? (
              <div className="card">
                <h2 className="text-sm font-semibold text-slate-300 mb-4">
                  Cumulative P&L Over Time
                  {selectedTicker && <span className="ml-2 font-mono text-blue-400">{selectedTicker}</span>}
                </h2>
                <ResponsiveContainer width="100%" height={280}>
                  <AreaChart data={timelineData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
                    <defs>
                      {[['gradR', '#10b981'], ['gradD', '#60a5fa'], ['gradT', '#a78bfa']].map(([id, c]) => (
                        <linearGradient key={id} id={id} x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor={c} stopOpacity={0.3} />
                          <stop offset="95%" stopColor={c} stopOpacity={0} />
                        </linearGradient>
                      ))}
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 11 }} tickLine={false} axisLine={false}
                      tickFormatter={d => d.slice(0, 7)} interval="preserveStartEnd" />
                    <YAxis tick={{ fill: '#64748b', fontSize: 11 }} tickLine={false} axisLine={false}
                      tickFormatter={v => usd(v, true)} width={70} />
                    <Tooltip content={<ChartTooltip />} />
                    <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }}
                      formatter={(v) => <span className="text-slate-400">{v}</span>} />
                    <Area type="monotone" dataKey="realized" name="Realized P&L" stroke="#10b981" strokeWidth={2} fill="url(#gradR)" />
                    <Area type="monotone" dataKey="dividends" name="Dividends" stroke="#60a5fa" strokeWidth={2} fill="url(#gradD)" />
                    <Area type="monotone" dataKey="total" name="Total Return" stroke="#a78bfa" strokeWidth={2} strokeDasharray="5 3" fill="url(#gradT)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            )
            : (
              <div className="card text-center py-10 text-slate-500">
                No realized transactions in this period.
              </div>
            )
          }

          {/* ── Trade history drill-down (when ticker selected) ── */}
          {selectedTicker && (
            <TradePanel ticker={selectedTicker} accountId={accountId} period={period} />
          )}

          {/* ── Bar + Pie ── */}
          <div className="grid lg:grid-cols-5 gap-4">
            <div className="card lg:col-span-3">
              <h2 className="text-sm font-semibold text-slate-300 mb-1">
                Realized P&L by Ticker
                <span className="ml-2 text-xs text-slate-500 font-normal">
                  {tickerFilter ? `filtered · ${filteredTickers.filter((t: any) => t.realized_gain !== 0).length} tickers` : 'top 20 by absolute value'}
                </span>
              </h2>
              {barData.length > 0
                ? (
                  <ResponsiveContainer width="100%" height={Math.max(barData.length * 32, 160)}>
                    <BarChart data={barData} layout="vertical" margin={{ top: 0, right: 60, left: 10, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
                      <XAxis type="number" tick={{ fill: '#64748b', fontSize: 11 }} tickLine={false} axisLine={false}
                        tickFormatter={v => usd(v, true)} />
                      <YAxis type="category" dataKey="ticker" tick={{ fill: '#94a3b8', fontSize: 12, fontWeight: 500 }}
                        tickLine={false} axisLine={false} width={55} />
                      <Tooltip content={<BarTooltip />} />
                      <Bar dataKey="realized_gain" name="Realized P&L" radius={[0, 4, 4, 0]} maxBarSize={20}
                        onClick={(d: any) => selectRow(d.ticker)} style={{ cursor: 'pointer' }}>
                        {barData.map((entry: any, i: number) => (
                          <Cell key={i}
                            fill={gainColor(entry.realized_gain)}
                            fillOpacity={selectedTicker && entry.ticker !== selectedTicker ? 0.35 : 0.9}
                            stroke={entry.ticker === selectedTicker ? gainColor(entry.realized_gain) : 'none'}
                            strokeWidth={2}
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                )
                : <div className="text-center py-10 text-slate-500 text-sm">No realized trades for this filter</div>
              }
            </div>

            <div className="card lg:col-span-2 flex flex-col">
              <h2 className="text-sm font-semibold text-slate-300 mb-4">Return Breakdown</h2>
              {pieData.length > 0
                ? (
                  <>
                    <ResponsiveContainer width="100%" height={200}>
                      <PieChart>
                        <Pie data={pieData} cx="50%" cy="50%" innerRadius={55} outerRadius={85} paddingAngle={3} dataKey="value">
                          {pieData.map((e, i) => <Cell key={i} fill={e.fill} />)}
                        </Pie>
                        <Tooltip
                          formatter={(v: number) => [usd(v), '']}
                          contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, fontSize: 12 }}
                          labelStyle={{ color: '#94a3b8' }} itemStyle={{ color: '#e2e8f0' }}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                    <div className="space-y-2 mt-2">
                      {pieData.map((d, i) => (
                        <div key={i} className="flex items-center justify-between text-sm">
                          <div className="flex items-center gap-2">
                            <span className="w-2.5 h-2.5 rounded-full" style={{ background: d.fill }} />
                            <span className="text-slate-400">{d.name}</span>
                          </div>
                          <span className="font-medium text-slate-200">{usd(d.value)}</span>
                        </div>
                      ))}
                    </div>
                  </>
                )
                : <div className="flex-1 flex items-center justify-center text-slate-500 text-sm">No data</div>
              }
            </div>
          </div>

          {/* ── Ticker table ── */}
          {filteredTickers.length > 0 && (
            <div className="card overflow-hidden">
              <h2 className="text-sm font-semibold text-slate-300 mb-4">
                Ticker Detail
                {tickerFilter && <span className="ml-2 text-xs text-slate-500 font-normal">({filteredTickers.length} of {summary.by_ticker.length})</span>}
              </h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-700/60">
                      {['Ticker', 'Realized P&L', 'Dividends', 'Total Return', 'Cost Basis', 'Proceeds', 'Status'].map(h => (
                        <th key={h} className="text-left text-xs font-medium text-slate-500 uppercase tracking-wider pb-3 pr-4 last:pr-0">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800">
                    {filteredTickers.map((t: any) => {
                      const isSelected = t.ticker === selectedTicker
                      return (
                        <tr
                          key={t.ticker}
                          onClick={() => isSelected ? clearTicker() : selectRow(t.ticker)}
                          className={`transition-colors cursor-pointer ${isSelected
                            ? 'bg-blue-600/10 border-l-2 border-blue-500'
                            : 'hover:bg-slate-800/40'
                          }`}
                        >
                          <td className="py-3 pr-4 font-mono font-semibold text-slate-200">{t.ticker}</td>
                          <td className={`py-3 pr-4 font-medium tabular-nums ${gainCls(t.realized_gain)}`}>
                            {t.realized_gain !== 0 ? `${sign(t.realized_gain)}${usd(t.realized_gain)}` : <span className="text-slate-600">—</span>}
                          </td>
                          <td className="py-3 pr-4 text-blue-400 tabular-nums">
                            {t.dividend_income > 0 ? usd(t.dividend_income) : <span className="text-slate-600">—</span>}
                          </td>
                          <td className={`py-3 pr-4 font-semibold tabular-nums ${gainCls(t.total_return)}`}>
                            {sign(t.total_return)}{usd(t.total_return)}
                          </td>
                          <td className="py-3 pr-4 text-slate-400 tabular-nums">
                            {t.cost_basis > 0 ? usd(t.cost_basis) : <span className="text-slate-600">—</span>}
                          </td>
                          <td className="py-3 pr-4 text-slate-400 tabular-nums">
                            {t.proceeds > 0 ? usd(t.proceeds) : <span className="text-slate-600">—</span>}
                          </td>
                          <td className="py-3">
                            {t.realized_gain > 0
                              ? <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-500/15 text-emerald-400">Winner</span>
                              : t.realized_gain < 0
                              ? <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-500/15 text-red-400">Loser</span>
                              : t.dividend_income > 0
                              ? <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-500/15 text-blue-400">Div only</span>
                              : null}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
