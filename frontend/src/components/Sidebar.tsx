import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Wallet, ArrowLeftRight, Upload,
  BarChart2, TrendingUp, Settings, LogOut,
} from 'lucide-react'
import clsx from 'clsx'

const nav = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/accounts', icon: Wallet, label: 'Accounts' },
  { to: '/transactions', icon: ArrowLeftRight, label: 'Transactions' },
  { to: '/uploads', icon: Upload, label: 'Uploads' },
  { to: '/analytics', icon: BarChart2, label: 'Analytics' },
  { to: '/projections', icon: TrendingUp, label: 'Projections' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

interface SidebarProps {
  onLogout: () => void
}

export default function Sidebar({ onLogout }: SidebarProps) {
  return (
    <aside className="fixed inset-y-0 left-0 w-56 bg-slate-900 border-r border-slate-700/50 flex flex-col z-30">
      <div className="px-5 py-6 border-b border-slate-700/50">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 bg-blue-600 rounded-lg flex items-center justify-center">
            <TrendingUp size={14} className="text-white" />
          </div>
          <span className="font-semibold text-slate-100 text-sm">NetWorth</span>
        </div>
      </div>

      <nav className="flex-1 py-4 px-3 space-y-0.5 overflow-y-auto">
        {nav.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                isActive
                  ? 'bg-blue-600/20 text-blue-400'
                  : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800',
              )
            }
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="p-3 border-t border-slate-700/50">
        <button
          onClick={onLogout}
          className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors w-full"
        >
          <LogOut size={16} />
          Sign out
        </button>
      </div>
    </aside>
  )
}
