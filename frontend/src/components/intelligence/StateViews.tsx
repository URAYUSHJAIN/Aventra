import { AlertTriangle, Database, Loader2, RefreshCw } from 'lucide-react'
import type { DataSource } from '../../types/api'
import { fmtDateTime } from '../../utils/format'

export function LoadingState({ message = 'Running the Aventra pipeline…' }: { message?: string }) {
  return <div className="intel-state" role="status"><Loader2 size={18} className="spinning" /><span>{message}</span><small>First analysis of an asset can take up to a minute while models load.</small></div>
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return <div className="intel-state intel-error" role="alert"><AlertTriangle size={18} /><span>{message}</span>{onRetry && <button type="button" className="intel-button" onClick={onRetry}><RefreshCw size={13} /> Try again</button>}</div>
}

export function EmptyState({ message }: { message: string }) {
  return <p className="intel-empty">{message}</p>
}

export function SourceBadge({ source, label }: { source: DataSource; label?: string }) {
  const kind = source.is_demo ? 'demo' : source.stale ? 'stale' : 'live'
  const text = source.is_demo ? 'DEMO · SYNTHETIC DATA' : source.stale ? 'STORED DATA · PROVIDER UNAVAILABLE' : 'LIVE PROVIDER DATA'
  return <span className={`source-badge source-${kind}`} title={`${source.provider} · fetched ${fmtDateTime(source.fetched_at)}`}><Database size={11} /> {label ? `${label}: ` : ''}{text}</span>
}
