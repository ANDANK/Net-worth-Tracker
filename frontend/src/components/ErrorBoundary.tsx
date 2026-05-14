import { Component, ErrorInfo, ReactNode } from 'react'
import { AlertTriangle } from 'lucide-react'

interface Props { children: ReactNode }
interface State { error: Error | null }

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Page error:', error, info.componentStack)
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex flex-col items-center justify-center min-h-64 gap-4 text-center p-8">
          <AlertTriangle size={32} className="text-amber-400" />
          <div>
            <p className="text-slate-100 font-medium">Something went wrong on this page</p>
            <p className="text-sm text-slate-400 mt-1">{this.state.error.message}</p>
          </div>
          <button
            className="btn-secondary text-sm"
            onClick={() => this.setState({ error: null })}
          >
            Try again
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
