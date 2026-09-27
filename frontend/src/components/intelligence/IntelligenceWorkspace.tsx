import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { RefreshCw } from 'lucide-react'
import { useApiResource } from '../../hooks/useApiResource'

import { getIntelligence } from '../../services/intelligenceApi'
import type { AnalysisPending, Assessment, Intelligence } from '../../types/api'
import { ASSET_CLASS_LABEL, fmtBp, fmtCompact, fmtDate, fmtDateTime, fmtLevel, fmtPct } from '../../utils/format'
import { GlobalSearch } from '../search/GlobalSearch'
import { DataUnavailableState, LoadingState, SourceBadge } from './StateViews'

const ID_PATTERN = /^[A-Za-z0-9:&^._-]{1,80}$/

function initialId(): string | null {
  const params = new URLSearchParams(window.location.search)
  const raw = params.get('id') ?? params.get('symbol')      // ?symbol= kept for v0.1 links (resolves to an NSE listing)
  return raw && ID_PATTERN.test(raw) ? raw : null
}

export interface WorkspaceContext { data: Intelligence; focus: Assessment; setFocus: (eventId: string) => void }

// Instrument selection (search) + pipeline loading, shared by the dashboard and the four capability pages.
export function IntelligenceWorkspace({ children }: { children: (context: WorkspaceContext) => ReactNode }) {
  const [instrumentId, setInstrumentId] = useState<string | null>(initialId)
  const [focusId, setFocusId] = useState<string | null>(null)
  const [pending, setPending] = useState<AnalysisPending | null>(null)
  const { state, reload, refresh } = useApiResource(async (signal, force) => {
    if (!instrumentId) throw new Error('no-instrument')
    setPending(null)
    try { return await getIntelligence(instrumentId, { refresh: force, signal, onPending: setPending }) } finally { setPending(null) }
  }, [instrumentId])

  useEffect(() => {
    if (!instrumentId) return
    const url = new URL(window.location.href)
    url.searchParams.delete('symbol')
    url.searchParams.set('id', instrumentId)
    window.history.replaceState(null, '', url)
    setFocusId(null)
  }, [instrumentId])

  const data = state.data
  const focus = useMemo(() => (data ? data.events.find((e) => e.event_id === focusId) ?? data.events[0] ?? data.current_assessment : undefined), [data, focusId])

  if (!instrumentId) {
    return <div className="intel-workspace"><div className="intel-empty-start">
      <h2>Search for any instrument</h2>
      <p>Stocks, ETFs, REITs, bonds, indices, mutual funds, forex and crypto — analysed only when a legitimate data provider can supply real data.</p>
      <GlobalSearch autoFocus onSelect={(item) => setInstrumentId(item.instrument_id)} />
    </div></div>
  }

  const latest = data?.market.latest
  const caps = data?.capabilities
  const currency = data?.asset.currency
  return <div className="intel-workspace">
    <div className="intel-toolbar">
      <GlobalSearch compact onSelect={(item) => setInstrumentId(item.instrument_id)} placeholder="Switch instrument…" />
      <button type="button" className="intel-button" onClick={refresh} disabled={state.status === 'loading'}><RefreshCw size={13} className={state.status === 'loading' ? 'spinning' : ''} /> Re-run analysis</button>
      {data && <SourceBadge source={data.data_source.market} label="Data" />}
    </div>
    {state.status === 'error' && (state.error === 'no-instrument' ? null : <DataUnavailableState error={state.cause} message={state.error} onRetry={reload} />)}
    {state.status === 'loading' && !data && <LoadingState message={pending ? `Analysis ${pending.job.status} (job #${pending.job.id}) — fetching real data and running the pipeline…` : 'Loading analysis…'} />}
    {data && focus && latest && caps && <>
      {state.status === 'loading' && <p className="intel-note" role="status">{pending ? `Re-analysis ${pending.job.status} (job #${pending.job.id})…` : 'Refreshing analysis…'}</p>}
      <header className="instrument-header">
        <div><span className={`class-badge class-${data.asset.asset_class}`}>{ASSET_CLASS_LABEL[data.asset.asset_class] ?? data.asset.asset_class}</span>
          <h2>{data.asset.name}</h2>
          <p>{data.instrument_id}{data.asset.exchange ? ` · ${data.asset.exchange}` : ''}{currency ? ` · ${currency}` : ''}{data.asset.timezone ? ` · ${data.asset.timezone}` : ''} · feature set <code>{data.feature_set}</code></p></div>
      </header>
      {data.data_source.market.notes?.map((note) => <p className="intel-note" key={note}>{note}</p>)}
      {data.data_source.market.attribution && <p className="intel-note">{data.data_source.market.attribution}</p>}
      <div className="snapshot" aria-label="Instrument snapshot">
        <div><span>{caps.value_kind === 'nav' ? 'NAV' : caps.value_kind === 'yield' ? 'Yield' : caps.value_kind === 'reference_rate' ? 'Reference rate' : 'Close'}</span>
          <strong>{fmtLevel(latest.close, caps.value_kind, currency)}</strong><small>{fmtDate(latest.trading_date)}</small></div>
        <div><span>Change</span>{caps.value_kind === 'yield'
          ? <strong className={(latest.change_bp ?? 0) >= 0 ? 'gain' : 'loss'}>{fmtBp(latest.change_bp)}</strong>
          : <strong className={(latest.return_1 ?? 0) >= 0 ? 'gain' : 'loss'}>{fmtPct(latest.return_1)}</strong>}</div>
        <div><span>Volume</span>{caps.has_volume ? <><strong>{fmtCompact(latest.volume)}</strong><small>{latest.volume_ratio ? `${latest.volume_ratio.toFixed(2)}× 20-period mean` : ''}</small></>
          : <><strong>n/a</strong><small>not provided for this asset class</small></>}</div>
        <div><span>20-period volatility</span><strong>{caps.value_kind === 'yield' ? '—' : fmtPct(latest.volatility_20)}</strong></div>
        <div><span>Current risk</span><strong className={`risk-text-${data.current_assessment.risk.level.toLowerCase()}`}>{Math.round(data.current_assessment.risk.score)} · {data.current_assessment.risk.level}</strong></div>
      </div>
      {children({ data, focus, setFocus: setFocusId })}
      <p className="intel-note">Generated {fmtDateTime(data.generated_at, data.asset.timezone)} · pipeline v{data.pipeline_version} · versions {Object.entries(data.versions).filter(([, v]) => v).map(([k, v]) => `${k} ${v}`).join(' · ')} · {data.disclaimer}</p>
    </>}
  </div>
}


