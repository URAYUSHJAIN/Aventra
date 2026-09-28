import { AlertTriangle, Database, Inbox, Loader2, RefreshCw } from 'lucide-react'
import type { DataSource } from '../../types/api'
import { ApiError, DATA_UNAVAILABLE } from '../../services/apiClient'
import { fmtDateTime } from '../../utils/format'

export function LoadingState({ message = 'Running the Aventra pipeline…', hint = 'First analysis of an asset can take up to a minute while models load.' }: { message?: string; hint?: string | null }) {
  return <div className="state state-loading" role="status"><Loader2 size={18} className="spinning" aria-hidden="true" /><span>{message}</span>{hint && <small>{hint}</small>}<i className="state-scan" aria-hidden="true" /></div>
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return <div className="state state-error" role="alert"><AlertTriangle size={18} aria-hidden="true" /><span>{message}</span>{onRetry && <button type="button" className="chip-button" onClick={onRetry}><RefreshCw size={13} aria-hidden="true" /> Try again</button>}</div>
}

export function EmptyState({ message }: { message: string }) {
  return <p className="empty-note"><Inbox size={14} aria-hidden="true" /> {message}</p>
}

export function SourceBadge({ source, label }: { source: DataSource; label?: string }) {
  const kind = source.is_demo ? 'demo' : source.stale ? 'stale' : 'live'
  const text = source.is_demo ? 'DEMO · SYNTHETIC DATA' : source.stale ? 'STORED DATA · PROVIDER UNAVAILABLE' : 'LIVE PROVIDER DATA'
  return <span className={`source-badge source-${kind}`} title={`${source.provider} · fetched ${fmtDateTime(source.fetched_at)}`}><Database size={11} aria-hidden="true" /> {label ? `${label}: ` : ''}{text}</span>
}

const STATE_TITLES: Record<string, string> = {
  INSTRUMENT_NOT_FOUND: 'Instrument not found',
  INVALID_INSTRUMENT_ID: 'Invalid instrument ID',
  NO_PROVIDER_FOR_ASSET: 'No supported data provider for this asset',
  PROVIDER_UNAVAILABLE: 'Data provider unavailable',
  RATE_LIMITED: 'Data provider rate limit reached',
  INSUFFICIENT_HISTORY: 'Insufficient history for analysis',
  INSUFFICIENT_SOURCE_DATA: 'Insufficient source data',
  ANALYSIS_FAILED: 'Analysis failed',
}

// Typed data-availability answer: Aventra never substitutes synthetic or guessed values.
export function DataUnavailableState({ error, message, onRetry }: { error?: unknown; message: string; onRetry?: () => void }) {
  const typed = error instanceof ApiError && error.code ? error : null
  if (!typed || !(typed.code! in STATE_TITLES)) return <ErrorState message={message} onRetry={onRetry} />
  return <div className="state state-unavailable" role="alert" data-code={typed.code}>
    <AlertTriangle size={18} aria-hidden="true" />
    <strong>{DATA_UNAVAILABLE}</strong>
    <span>{STATE_TITLES[typed.code!]}: {message.replace(/^Data unavailable \/ insufficient source data[.:]?\s*/i, '')}</span>
    {typed.attempts.length > 0 && <ul className="provider-attempts">{typed.attempts.map((a) => <li key={`${a.provider}-${a.status}`}><code>{a.provider}</code>: {a.status}{a.reason ? ` (${a.reason})` : ''}{a.detail ? `: ${a.detail}` : ''}</li>)}</ul>}
    {onRetry && typed.code !== 'INSTRUMENT_NOT_FOUND' && typed.code !== 'INVALID_INSTRUMENT_ID' && typed.code !== 'NO_PROVIDER_FOR_ASSET' && <button type="button" className="chip-button" onClick={onRetry}><RefreshCw size={13} aria-hidden="true" /> Try again</button>}
  </div>
}
