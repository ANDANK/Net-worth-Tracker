import clsx from 'clsx'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

interface StatCardProps {
  title: string
  value: number
  change?: number
  changePct?: number
  subtitle?: string
  color?: 'blue' | 'emerald' | 'violet' | 'amber' | 'rose' | 'cyan'
}

const colorMap = {
  blue: 'text-blue-400',
  emerald: 'text-emerald-400',
  violet: 'text-violet-400',
  amber: 'text-amber-400',
  rose: 'text-rose-400',
  cyan: 'text-cyan-400',
}

function fmt(n: number) {
  if (Math.abs(n) >= 1_000_000)
    return `$${(n / 1_000_000).toFixed(2)}M`
  if (Math.abs(n) >= 1_000)
    return `$${(n / 1_000).toFixed(1)}K`
  return `$${n.toFixed(2)}`
}

export default function StatCard({ title, value, change, changePct, subtitle, color = 'blue' }: StatCardProps) {
  const positive = (change ?? 0) >= 0

  return (
    <div className="card flex flex-col gap-3">
      <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">{title}</p>
      <p className={clsx('text-2xl font-bold tabular-nums', colorMap[color])}>
        {fmt(value)}
      </p>
      {(change !== undefined || subtitle) && (
        <div className="flex items-center gap-2">
          {change !== undefined && (
            <span className={clsx('flex items-center gap-1 text-xs font-medium', positive ? 'text-emerald-400' : 'text-red-400')}>
              {positive ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
              {positive ? '+' : ''}{fmt(change)}
              {changePct !== undefined && ` (${changePct > 0 ? '+' : ''}${changePct.toFixed(1)}%)`}
            </span>
          )}
          {subtitle && <span className="text-xs text-slate-500">{subtitle}</span>}
        </div>
      )}
    </div>
  )
}
