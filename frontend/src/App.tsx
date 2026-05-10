import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './hooks/useAuth'
import Sidebar from './components/Sidebar'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Accounts from './pages/Accounts'
import Transactions from './pages/Transactions'
import Uploads from './pages/Uploads'
import Analytics from './pages/Analytics'
import Projections from './pages/Projections'
import Settings from './pages/Settings'
import LoadingSpinner from './components/LoadingSpinner'

function Layout({ onLogout }: { onLogout: () => void }) {
  return (
    <div className="flex min-h-screen">
      <Sidebar onLogout={onLogout} />
      <main className="flex-1 ml-56 p-6 min-h-screen overflow-auto">
        <div className="max-w-6xl mx-auto">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/accounts" element={<Accounts />} />
            <Route path="/transactions" element={<Transactions />} />
            <Route path="/uploads" element={<Uploads />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/projections" element={<Projections />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </main>
    </div>
  )
}

export default function App() {
  const { isAuthenticated, login, logout } = useAuth()

  if (isAuthenticated === null) return <LoadingSpinner />
  if (!isAuthenticated) return <Login onLogin={login} />

  return (
    <BrowserRouter>
      <Layout onLogout={logout} />
    </BrowserRouter>
  )
}
