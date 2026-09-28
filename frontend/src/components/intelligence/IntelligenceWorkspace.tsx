import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { RefreshCw, Search } from 'lucide-react'
import { useApiResource } from '../../hooks/useApiResource'
import { useScrollSpy } from '../../hooks/useScrollSpy'
import { getIntelligence } from '../../services/intelligenceApi'
import type { AnalysisPending, Assessment, Intelligence } from '../../types/api'
import { ASSET_CLASS_LABEL, fmtBp, fmtCompact, fmtDate, fmtDateTime, fmtLevel, fmtPct, fmtPctAbs, fmtRiskScore, fmtScore } from '../../utils/format'
import { Badge, changeTone, fingerprintTone, riskTone, severityTone } from '../common/Badge'
import { Metric } from '../common/Metric'
import { GlobalSearch } from '../search/GlobalSearch'
import { DataUnavailableState, LoadingState, SourceBadge } from './StateViews'

const ID_PATTERN = /^[A-Za-z0-9:&^._-]{1,80}$/
const LEVEL_TEXT: Record<string, string> = { normal: 'Normal', mild_deviation: 'Mild deviation', elevated_deviation: 'Elevated', high_deviation: 'High deviation', insufficient_history: 'Insufficient history' }

function initialId(): string | null {
  const params = new URLSearchParams(window.location.search)
  const raw = params.get('id') ?? params.get('symbol')      // ?symbol= kept for v0.1 links (resolves to an NSE listing)
  return raw && ID_PATTERN.test(raw) ? raw : null
}

export interface WorkspaceContext { data: Intelligence; focus: Assessment; setFocus: (eventId: string) => void }
export interface WorkspaceSection { id: string; label: string }

// Instrument selection (search) + pipeline loading, shared by the dashboard and the four capability pages.
export function IntelligenceWorkspace({ children, sections = [] }: { children: (context: WorkspaceContext) => ReactNode; sections?: WorkspaceSection[] }) {
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
  const active = useScrollSpy(sections.map((s) => s.id), Boolean(data))

  if (!instrumentId) {
    return <div className="workspace"><div className="ws-start">
      <Search size={20} aria-hidden="true" className="ws-start-icon" />
      <h2>Search for any instrument</h2>
      <p>Stocks, ETFs, REITs, bonds, indices, mutual funds, forex and crypto, analysed only when a legitimate data provider can supply real data.</p>
      <GlobalSearch autoFocus size="large" onSelect={(item) => setInstrumentId(item.instrument_id)} />
    </div></div>
  }

  const latest = data?.market.latest
  const caps = data?.capabilities
  const currency = data?.asset.currency
  const current = data?.current_assessment
  const valueLabel = caps?.value_kind === 'nav' ? 'NAV' : caps?.value_kind === 'yield' ? 'Yield' : caps?.value_kind === 'reference_rate' ? 'Reference rate' : 'Close'
  const change = caps?.value_kind === 'yield' ? { text: fmtBp(latest?.change_bp), value: latest?.change_bp } : { text: fmtPct(latest?.return_1), value: latest?.return_1 }
  return <div className="workspace">
    <div className="ws-toolbar">
      <GlobalSearch compact onSelect={(item) => setInstrumentId(item.instrument_id)} placeholder="Switch instrument…" />
      <button type="button" className="chip-button" onClick={refresh} disabled={state.status === 'loading'}><RefreshCw size={13} className={state.status === 'loading' ? 'spinning' : ''} aria-hidden="true" /> Re-run analysis</button>
      {data && <SourceBadge source={data.data_source.market} label="Data" />}
    </div>
    {state.status === 'error' && (state.error === 'no-instrument' ? null : <DataUnavailableState error={state.cause} message={state.error} onRetry={reload} />)}
    {state.status === 'loading' && !data && <LoadingState message={pending ? `Analysis ${pending.job.status} (job #${pending.job.id}): fetching real data and running the pipeline…` : 'Loading analysis…'} />}
    {data && focus && latest && caps && current && <>
      {state.status === 'loading' && <p className="note" role="status">{pending ? `Re-analysis ${pending.job.status} (job #${pending.job.id})…` : 'Refreshing analysis…'}</p>}
      <header className="ws-identity" id="overview">
        <div className="ws-id">
          <div className="ws-tags"><span className={`class-badge class-${data.asset.asset_class}`}>{ASSET_CLASS_LABEL[data.asset.asset_class] ?? data.asset.asset_class}</span>
            {data.asset.exchange && <span className="ws-tag">{data.asset.exchange}</span>}{currency && <span className="ws-tag">{currency}</span>}{data.asset.timezone && <span className="ws-tag">{data.asset.timezone}</span>}</div>
          <h2>{data.asset.name}</h2>
          <p className="ws-code">{data.instrument_id} · feature set <code>{data.feature_set}</code></p>
        </div>
        <div className="ws-quote">
          <span className="ws-quote-label">{valueLabel} · {fmtDate(latest.trading_date)}</span>
          <strong>{fmtLevel(latest.close, caps.value_kind, currency)}</strong>
          <span className={`ws-change text-${changeTone(change.value)}`}>{change.text}</span>
        </div>
      </header>
      {data.data_source.market.notes?.map((note) => <p className="note" key={note}>{note}</p>)}
      {data.data_source.market.attribution && <p className="note">{data.data_source.market.attribution}</p>}
      <div className="ws-state" aria-label="Instrument snapshot">
        {caps.has_volume ? <Metric label="Volume" value={fmtCompact(latest.volume)} sub={latest.volume_ratio ? `${latest.volume_ratio.toFixed(2)}× 20-period mean` : undefined} /> : <Metric label="Volume" value="n/a" sub="not provided for this asset class" />}
        <Metric label="20-period volatility" value={caps.value_kind === 'yield' ? 'n/a' : fmtPctAbs(latest.volatility_20)} />
        <Metric label="Behaviour" value={LEVEL_TEXT[data.fingerprint.level] ?? data.fingerprint.level} sub={`deviation ${fmtScore(data.fingerprint.score)}`} tone={fingerprintTone(data.fingerprint.level)} />
        <Metric label="Anomaly (latest)" value={current.anomaly.severity} sub={`score ${fmtScore(current.anomaly.anomaly_score)} · ${data.anomaly.flagged_count} flagged in window`} tone={severityTone(current.anomaly.severity)} />
        <Metric label="Current risk" value={<span className={`risk-text-${current.risk.level.toLowerCase()}`}>{fmtRiskScore(current.risk.score)} · {current.risk.level}</span>} sub="score / 100, not a probability" tone={riskTone(current.risk.level)} />
      </div>
      <section className="ws-insight" aria-label="Key insight">
        <p className="eyebrow">KEY INSIGHT · LATEST SESSION {fmtDate(current.trading_date)}</p>
        <p className="insight-lead">{current.explanation.what}</p>
        <p className="insight-body">{current.explanation.how_unusual} {current.explanation.why}</p>
      </section>
      {sections.length > 0 && <nav className="ws-tabs" aria-label="Analysis sections">
        <div className="ws-tabs-track">{sections.map((s) => <a key={s.id} href={`#${s.id}`} aria-current={active === s.id ? 'true' : undefined}>{s.label}</a>)}</div>
        <span className="ws-focus">Correlation, risk &amp; evidence for <b>{fmtDate(focus.trading_date)}</b> <Badge tone={severityTone(focus.anomaly.severity)}>{focus.anomaly.severity}</Badge></span>
      </nav>}
      {children({ data, focus, setFocus: setFocusId })}
      <p className="note ws-meta">Generated {fmtDateTime(data.generated_at, data.asset.timezone)} · pipeline v{data.pipeline_version} · versions {Object.entries(data.versions).filter(([, v]) => v).map(([k, v]) => `${k} ${v}`).join(' · ')} · {data.disclaimer}</p>
    </>}
  </div>
}
