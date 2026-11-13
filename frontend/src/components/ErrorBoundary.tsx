import { Component, type ErrorInfo, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { AlertTriangle } from 'lucide-react'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  message: string
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, message: '' }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, message: error.message }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('YOUR VIEWS render error', error, info)
  }

  render() {
    if (!this.state.hasError) return this.props.children
    return (
      <div className="flex min-h-screen items-center justify-center bg-paper px-6 text-ink">
        <div className="max-w-lg border-y-[3px] border-double border-rule py-12 text-center">
          <div className="mx-auto flex h-11 w-11 items-center justify-center border border-rule text-oxblood">
            <AlertTriangle size={20} strokeWidth={1.4} />
          </div>
          <p className="kicker mt-4">A Press Malfunction</p>
          <h1 className="mt-2 font-display text-3xl font-extrabold">This page failed to print</h1>
          <p className="mt-3 font-body text-[14px] leading-relaxed text-ink-soft">
            {this.state.message || 'An unexpected rendering error stopped the edition.'}
          </p>
          <div className="mt-6 flex items-center justify-center gap-3">
            <button type="button" className="paper-button" onClick={() => window.location.assign('/')}>
              Reload the edition
            </button>
            <Link to="/" className="underline-link">
              Front page
            </Link>
          </div>
        </div>
      </div>
    )
  }
}
