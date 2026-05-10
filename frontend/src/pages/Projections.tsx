import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import {
  LineChart, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, Legend,
} from 'recharts'
import { projectionsApi } from '../services/api'
import { ProjectionResult } from '../types'
import PageHeader from '../components/PageHeader'

function fmt(n: number) {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`
  return `$${n.toFixed(0)}`
}

const TOOLTIP_STYLE = {
  contentStyle: { background: '#1e293b', border: '1px solid #334155', borderRadius: 8 },
  labelStyle: { color: '#94a3b8', fontSize: 12 },
}

export default function Projections() {
  const [form, setForm] = useState({
    scenario_name: 'Base Case',
    current_value: 100000,
    annual_return: 7,
    inflation: 3,
    monthly_contribution: 2000,
    target_age: 65,
    current_age: 35,
  })
  const [result, setResult] = useState<ProjectionResult | null>(null)
  const [saved, setSaved] = useState(false)

  const runMutation = useMutation({
    mutationFn: () => projectionsApi.run(form).then((r) => r.data),
    onSuccess: (data) => { setResult(data); setSaved(false) },
  })

  const saveMutation = useMutation({
    mutationFn: () => projectionsApi.save(form).then((r) => r.data),
    onSuccess: () => setSaved(true),
  })

  const chartData = result
    ? result.years.map((year, i) => ({
        age: year,
        nominal: result.nominal_values[i],
        real: result.real_values[i],
      }))
    : []

  const set = (k: string, v: number | string) => setForm({ ...form, [k]: typeof v === 'string' ? parseFloat(v) || 0 : v })

  return (
    <div>
      <PageHeader title="Projections" subtitle="Retirement and wealth modeling" />

      <div className="grid xl:grid-cols-3 gap-6">
        <div className="space-y-4">
          <div className="card">
            <h3 className="text-sm font-semibold text-slate-100 mb-4">Scenario Settings</h3>
            <div className="space-y-3">
              <div>
                <label className="label">Scenario Name</label>
                <input className="input" value={form.scenario_name} onChange={(e) => setForm({ ...form, scenario_name: e.target.value })} />
              </div>
              <div>
                <label className="label">Current Portfolio Value ($)</label>
                <input className="input" type="number" value={form.current_value} onChange={(e) => set('current_value', e.target.value)} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label">Current Age</label>
                  <input className="input" type="number" value={form.current_age} onChange={(e) => set('current_age', e.target.value)} />
                </div>
                <div>
                  <label className="label">Target Age</label>
                  <input className="input" type="number" value={form.target_age} onChange={(e) => set('target_age', e.target.value)} />
                </div>
              </div>
              <div>
                <label className="label">Monthly Contribution ($)</label>
                <input className="input" type="number" value={form.monthly_contribution} onChange={(e) => set('monthly_contribution', e.target.value)} />
              </div>
              <div>
                <label className="label">Annual Return ({form.annual_return}%)</label>
                <input type="range" min="1" max="15" step="0.5" value={form.annual_return}
                  onChange={(e) => set('annual_return', e.target.value)}
                  className="w-full accent-blue-500" />
                <div className="flex justify-between text-xs text-slate-500 mt-0.5">
                  <span>1%</span><span>Conservative 5%</span><span>Market 7%</span><span>15%</span>
                </div>
              </div>
              <div>
                <label className="label">Inflation ({form.inflation}%)</label>
                <input type="range" min="1" max="8" step="0.5" value={form.inflation}
                  onChange={(e) => set('inflation', e.target.value)}
                  className="w-full accent-violet-500" />
                <div className="flex justify-between text-xs text-slate-500 mt-0.5">
                  <span>1%</span><span>Target 2%</span><span>High 5%</span><span>8%</span>
                </div>
              </div>
            </div>
            <div className="flex gap-2 mt-5">
              <button className="btn-primary flex-1" onClick={() => runMutation.mutate()} disabled={runMutation.isPending}>
                {runMutation.isPending ? 'Calculating…' : 'Run Projection'}
              </button>
              {result && (
                <button className="btn-secondary" onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending || saved}>
                  {saved ? '✓ Saved' : 'Save'}
                </button>
              )}
            </div>
          </div>

          {result && (
            <div className="card space-y-3">
              <h3 className="text-sm font-semibold text-slate-100">Key Metrics</h3>
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-slate-400">Portfolio at {form.target_age}</span>
                  <span className="text-base font-bold text-blue-400">{fmt(result.target_value ?? 0)}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-slate-400">Inflation-adjusted</span>
                  <span className="text-base font-bold text-violet-400">{fmt(result.real_values.at(-1) ?? 0)}</span>
                </div>
                {result.fire_age && (
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-slate-400">FIRE Age</span>
                    <span className="text-base font-bold text-emerald-400">Age {result.fire_age}</span>
                  </div>
                )}
                {result.coast_fire_value && (
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-slate-400">Coast FIRE today</span>
                    <span className="text-base font-bold text-amber-400">{fmt(result.coast_fire_value)}</span>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        <div className="xl:col-span-2">
          <div className="card h-full min-h-[400px]">
            <h3 className="text-sm font-semibold text-slate-100 mb-4">Projection Chart</h3>
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={380}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis
                    dataKey="age"
                    tick={{ fill: '#64748b', fontSize: 11 }}
                    axisLine={false}
                    tickLine={false}
                    label={{ value: 'Age', position: 'insideBottom', offset: -4, fill: '#64748b', fontSize: 11 }}
                  />
                  <YAxis
                    tickFormatter={fmt}
                    tick={{ fill: '#64748b', fontSize: 11 }}
                    axisLine={false}
                    tickLine={false}
                    width={75}
                  />
                  <Tooltip {...TOOLTIP_STYLE} formatter={(v: number) => [fmt(v)]} />
                  <Legend iconType="line" formatter={(v) => <span className="text-xs text-slate-400">{v}</span>} />
                  <Line type="monotone" dataKey="nominal" stroke="#3b82f6" strokeWidth={2} dot={false} name="Nominal Value" />
                  <Line type="monotone" dataKey="real" stroke="#8b5cf6" strokeWidth={2} dot={false} name="Real (Inflation-adj)" strokeDasharray="5 3" />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-64 text-slate-500 text-sm">
                Configure your scenario and click "Run Projection"
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
