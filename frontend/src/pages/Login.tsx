import { useState } from 'react'
import { TrendingUp } from 'lucide-react'

interface LoginProps {
  onLogin: (password: string) => Promise<boolean>
}

export default function Login({ onLogin }: LoginProps) {
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    const ok = await onLogin(password)
    if (!ok) setError('Incorrect password')
    setLoading(false)
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-900">
      <div className="w-full max-w-sm">
        <div className="flex justify-center mb-8">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center">
              <TrendingUp size={20} className="text-white" />
            </div>
            <span className="text-xl font-bold text-slate-100">NetWorth Tracker</span>
          </div>
        </div>

        <div className="card">
          <h2 className="text-lg font-semibold text-slate-100 mb-5">Sign in</h2>
          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="label">Password</label>
              <input
                type="password"
                className="input"
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoFocus
              />
            </div>
            {error && (
              <p className="text-sm text-red-400">{error}</p>
            )}
            <button type="submit" className="btn-primary w-full" disabled={loading}>
              {loading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>
        </div>

        <p className="text-center text-xs text-slate-500 mt-6">
          Personal use only · Data stored in Google Sheets
        </p>
      </div>
    </div>
  )
}
