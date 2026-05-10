import { useState, useCallback } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { useDropzone } from 'react-dropzone'
import { Upload, CheckCircle2, AlertCircle, FileText, X } from 'lucide-react'
import { transactionsApi, accountsApi, brokersApi } from '../services/api'
import { Account, ImportResult } from '../types'
import PageHeader from '../components/PageHeader'

type Step = 'select' | 'preview' | 'done'

interface PreviewRow {
  date: string
  action: string
  ticker?: string
  quantity?: number
  price?: number
  total_amount: number
}

export default function Uploads() {
  const [file, setFile] = useState<File | null>(null)
  const [broker, setBroker] = useState('')
  const [accountId, setAccountId] = useState('')
  const [step, setStep] = useState<Step>('select')
  const [previewRows, setPreviewRows] = useState<PreviewRow[]>([])
  const [result, setResult] = useState<ImportResult | null>(null)

  const { data: accounts = [] } = useQuery<Account[]>({
    queryKey: ['accounts'],
    queryFn: () => accountsApi.list().then((r) => r.data),
  })

  const { data: brokers = [] } = useQuery({
    queryKey: ['brokers'],
    queryFn: () => brokersApi.list().then((r) => r.data),
  })

  const onDrop = useCallback((files: File[]) => {
    if (files[0]) setFile(files[0])
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'text/csv': ['.csv'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'] },
    maxFiles: 1,
  })

  const previewMutation = useMutation({
    mutationFn: async () => {
      const fd = new FormData()
      fd.append('file', file!)
      fd.append('broker', broker)
      fd.append('account_id', accountId)
      return transactionsApi.preview(fd).then((r) => r.data)
    },
    onSuccess: (data) => {
      setPreviewRows(data.rows)
      setStep('preview')
    },
  })

  const importMutation = useMutation({
    mutationFn: async () => {
      const fd = new FormData()
      fd.append('file', file!)
      fd.append('broker', broker)
      fd.append('account_id', accountId)
      return transactionsApi.import(fd).then((r) => r.data)
    },
    onSuccess: (data) => {
      setResult(data)
      setStep('done')
    },
  })

  const reset = () => {
    setFile(null)
    setBroker('')
    setAccountId('')
    setStep('select')
    setPreviewRows([])
    setResult(null)
  }

  const canPreview = file && broker && accountId

  return (
    <div>
      <PageHeader
        title="Upload Transactions"
        subtitle="Import broker CSV or XLSX files"
      />

      {step === 'select' && (
        <div className="max-w-2xl space-y-5">
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors ${
              isDragActive ? 'border-blue-500 bg-blue-500/5' : 'border-slate-600 hover:border-slate-500'
            }`}
          >
            <input {...getInputProps()} />
            <Upload size={32} className="mx-auto mb-3 text-slate-400" />
            {file ? (
              <div className="flex items-center justify-center gap-2">
                <FileText size={16} className="text-blue-400" />
                <span className="text-slate-100 font-medium">{file.name}</span>
                <button onClick={(e) => { e.stopPropagation(); setFile(null) }}>
                  <X size={14} className="text-slate-400 hover:text-slate-100" />
                </button>
              </div>
            ) : (
              <>
                <p className="text-slate-100 font-medium">Drop your broker file here</p>
                <p className="text-sm text-slate-400 mt-1">Supports CSV and XLSX · Click to browse</p>
              </>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">Broker</label>
              <select className="select" value={broker} onChange={(e) => setBroker(e.target.value)}>
                <option value="">Select broker…</option>
                {brokers.map((b: any) => (
                  <option key={b.id} value={b.id}>{b.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">Account</label>
              <select className="select" value={accountId} onChange={(e) => setAccountId(e.target.value)}>
                <option value="">Select account…</option>
                {accounts.filter((a) => a.active).map((a) => (
                  <option key={a.account_id} value={a.account_id}>
                    {a.account_name} ({a.broker_name})
                  </option>
                ))}
              </select>
            </div>
          </div>

          <button
            className="btn-primary w-full"
            disabled={!canPreview || previewMutation.isPending}
            onClick={() => previewMutation.mutate()}
          >
            {previewMutation.isPending ? 'Parsing…' : 'Preview Import'}
          </button>

          {previewMutation.isError && (
            <p className="text-sm text-red-400">Failed to parse file. Check the broker and file format.</p>
          )}
        </div>
      )}

      {step === 'preview' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-100 font-medium">{previewRows.length} transactions found in {file?.name}</p>
              <p className="text-sm text-slate-400">Review before importing. Duplicates will be skipped automatically.</p>
            </div>
            <button className="btn-secondary text-sm" onClick={reset}>Start over</button>
          </div>

          <div className="card p-0 overflow-hidden max-h-96 overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-slate-800 border-b border-slate-700">
                <tr>
                  {['Date', 'Type', 'Ticker', 'Qty', 'Price', 'Amount'].map((h) => (
                    <th key={h} className="text-left px-4 py-3 text-xs font-medium text-slate-400 uppercase tracking-wider">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/50">
                {previewRows.map((row, i) => (
                  <tr key={i} className="hover:bg-slate-700/20">
                    <td className="px-4 py-2 text-slate-300 font-mono text-xs">{row.date}</td>
                    <td className="px-4 py-2"><span className="badge-blue">{row.action}</span></td>
                    <td className="px-4 py-2 font-mono text-slate-100">{row.ticker || '—'}</td>
                    <td className="px-4 py-2 text-slate-300 tabular-nums">
                      {row.quantity != null ? row.quantity.toFixed(4) : '—'}
                    </td>
                    <td className="px-4 py-2 text-slate-300 tabular-nums">
                      {row.price != null ? `$${row.price.toFixed(2)}` : '—'}
                    </td>
                    <td className="px-4 py-2 font-medium text-slate-100 tabular-nums">${row.total_amount.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex gap-3">
            <button
              className="btn-primary flex-1"
              disabled={importMutation.isPending}
              onClick={() => importMutation.mutate()}
            >
              {importMutation.isPending ? 'Importing…' : `Import ${previewRows.length} Transactions`}
            </button>
            <button className="btn-secondary" onClick={() => setStep('select')}>Back</button>
          </div>
        </div>
      )}

      {step === 'done' && result && (
        <div className="max-w-md space-y-4">
          <div className="card">
            <div className="flex items-center gap-3 mb-4">
              <CheckCircle2 size={24} className="text-emerald-400" />
              <h3 className="text-base font-semibold text-slate-100">Import Complete</h3>
            </div>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-slate-400">Imported</span>
                <span className="text-emerald-400 font-medium">{result.imported}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-slate-400">Skipped (duplicates)</span>
                <span className="text-slate-300 font-medium">{result.skipped_duplicates}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-slate-400">Errors</span>
                <span className={result.errors > 0 ? 'text-red-400 font-medium' : 'text-slate-300 font-medium'}>
                  {result.errors}
                </span>
              </div>
            </div>
            {result.error_details.length > 0 && (
              <div className="mt-3 p-3 bg-red-900/20 rounded-lg">
                {result.error_details.slice(0, 3).map((e, i) => (
                  <p key={i} className="text-xs text-red-400">{e}</p>
                ))}
              </div>
            )}
          </div>
          <button className="btn-primary w-full" onClick={reset}>Import Another File</button>
        </div>
      )}
    </div>
  )
}
