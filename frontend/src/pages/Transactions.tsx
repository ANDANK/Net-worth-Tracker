import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Search, Filter } from 'lucide-react'
import { transactionsApi } from '../services/api'
import { Transaction } from '../types'
import PageHeader from '../components/PageHeader'
import LoadingSpinner from '../components/LoadingSpinner'

const ACTION_COLORS: Record<string, string> = {
  BUY: 'badge-green',
  SELL: 'badge-red',
  DIVIDEND: 'badge-blue',
  INTEREST: 'badge-blue',
  OPTION_BUY: 'badge-green',
  OPTION_SELL: 'badge-red',
  DEPOSIT: 'badge-green',
  WITHDRAWAL: 'badge-red',
  TRANSFER: 'badge-blue',
  SPLIT: 'badge-blue',
}

export default function Transactions() {
  const [ticker, setTicker] = useState('')
  const [broker, setBroker] = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [showFilters, setShowFilters] = useState(false)

  const params = {
    ticker: ticker || undefined,
    broker: broker || undefined,
    start_date: startDate || undefined,
    end_date: endDate || undefined,
    limit: 500,
  }

  const { data: transactions = [], isLoading } = useQuery<Transaction[]>({
    queryKey: ['transactions', params],
    queryFn: () => transactionsApi.list(params).then((r) => r.data),
  })

  return (
    <div>
      <PageHeader
        title="Transactions"
        subtitle={`${transactions.length} transactions`}
        action={
          <button
            className="btn-secondary text-sm flex items-center gap-2"
            onClick={() => setShowFilters(!showFilters)}
          >
            <Filter size={14} />
            Filters
          </button>
        }
      />

      {showFilters && (
        <div className="card mb-4 grid grid-cols-2 lg:grid-cols-4 gap-3">
          <div>
            <label className="label">Ticker</label>
            <input className="input" value={ticker} onChange={(e) => setTicker(e.target.value.toUpperCase())} placeholder="AAPL" />
          </div>
          <div>
            <label className="label">Broker</label>
            <input className="input" value={broker} onChange={(e) => setBroker(e.target.value)} placeholder="Fidelity" />
          </div>
          <div>
            <label className="label">From</label>
            <input className="input" type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
          </div>
          <div>
            <label className="label">To</label>
            <input className="input" type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
          </div>
        </div>
      )}

      {isLoading ? (
        <LoadingSpinner />
      ) : (
        <div className="card p-0 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-700">
                  {['Date', 'Type', 'Ticker', 'Qty', 'Price', 'Amount', 'Broker', 'Account'].map((h) => (
                    <th key={h} className="text-left px-4 py-3 text-xs font-medium text-slate-400 uppercase tracking-wider whitespace-nowrap">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/50">
                {transactions.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-10 text-center text-slate-500">
                      No transactions yet. Upload a broker file to import.
                    </td>
                  </tr>
                ) : (
                  transactions.map((tx) => (
                    <tr key={tx.transaction_id} className="hover:bg-slate-700/30 transition-colors">
                      <td className="px-4 py-3 text-slate-300 whitespace-nowrap font-mono text-xs">{tx.date}</td>
                      <td className="px-4 py-3">
                        <span className={ACTION_COLORS[tx.action] ?? 'badge-blue'}>{tx.action}</span>
                      </td>
                      <td className="px-4 py-3 font-mono font-medium text-slate-100">{tx.ticker || '—'}</td>
                      <td className="px-4 py-3 text-slate-300 tabular-nums">
                        {tx.quantity != null ? tx.quantity.toFixed(4) : '—'}
                      </td>
                      <td className="px-4 py-3 text-slate-300 tabular-nums">
                        {tx.price != null ? `$${tx.price.toFixed(2)}` : '—'}
                      </td>
                      <td className="px-4 py-3 font-medium text-slate-100 tabular-nums">
                        ${tx.total_amount.toFixed(2)}
                      </td>
                      <td className="px-4 py-3 text-slate-400 whitespace-nowrap">{tx.broker}</td>
                      <td className="px-4 py-3 text-slate-400 font-mono text-xs">{tx.account_id}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
