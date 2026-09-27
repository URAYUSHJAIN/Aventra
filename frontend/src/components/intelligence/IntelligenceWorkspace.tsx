import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { RefreshCw } from 'lucide-react'
import { useApiResource } from '../../hooks/useApiResource'
import { getAssets, getIntelligence } from '../../services/intelligenceApi'
import type { Asset, Assessment, Intelligence } from '../../types/api'
import { fmtCompact, fmtDate, fmtDateTime, fmtPct, fmtPrice } from '../../utils/format'
import { ErrorState, LoadingState, SourceBadge } from './StateViews'

const FALLBACK_ASSETS: Asset[] = [
  { symbol: 'RELIANCE', name: 'Reliance Industries', exchange: 'NSE', sector: '', is_demo: false }, { symbol: 'TCS', name: 'Tata Consultancy Services', exchange: 'NSE', sector: '', is_demo: false },
  { symbol: 'INFY', name: 'Infosys', exchange: 'NSE', sector: '', is_demo: false }, { symbol: 'HDFCBANK', name: 'HDFC Bank', exchange: 'NSE', sector: '', is_demo: false },
  { symbol: 'ICICIBANK', name: 'ICICI Bank', exchange: 'NSE', sector: '', is_demo: false }, { symbol: 'DEMO', name: 'Aventra Synthetic Demo Asset', exchange: 'DEMO', sector: '', is_demo: true },
]

function initialSymbol() {
  const fromUrl = new URLSearchParams(window.location.search).get('symbol')?.toUpperCase()
  return fromUrl && /^[A-Z0-9&^.-]{1,20}$/.test(fromUrl) ? fromUrl : 'RELIANCE'
}

export interface WorkspaceContext { data: Intelligence; focus: Assessment; setFocus: (eventId: string) => void }

// Asset selection + pipeline loading shared by the dashboard and the four capability pages.
export function IntelligenceWorkspace({ children }: { children: (context: WorkspaceContext) => ReactNode }) {
  const [symbol, setSymbol] = useState(initialSymbol)
  const [assets, setAssets] = useState<Asset[]>(FALLBACK_ASSETS)
  const [focusId, setFocusId] = useState<string | null>(null)
  const { state, reload, refresh } = useApiResource((signal, force) => getIntelligence(symbol, { refresh: force, signal }), [symbol])

  useEffect(() => { const controller = new AbortController(); getAssets(controller.signal).then(setAssets).catch(() => undefined); return () => controller.abort() }, [])
  useEffect(() => { const url = new URL(window.location.href); url.searchParams.set('symbol', symbol); window.history.replaceState(null, '', url); setFocusId(null) }, [symbol])

  const data = state.data
  const focus = useMemo(() => (data ? data.events.find((e) => e.event_id === focusId) ?? data.events[0] ?? data.current_assessment : undefined), [data, focusId])

  return <div className="intel-workspace">
    <div className="intel-toolbar">
      <label htmlFor="intel-asset">Asset</label>
      <select id="intel-asset" className="asset-select" value={symbol} onChange={(event) => setSymbol(event.target.value)}>
        {assets.map((asset) => <option key={asset.symbol} value={asset.symbol}>{asset.symbol} · {asset.name}{asset.is_demo ? ' (synthetic demo)' : ''}</option>)}
      </select>
      <button type="button" className="intel-button" onClick={refresh} disabled={state.status === 'loading'}><RefreshCw size={13} className={state.status === 'loading' ? 'spinning' : ''} /> Re-run analysis</button>
      {data && <SourceBadge source={data.data_source.market} label="Market" />}
    </div>
    {state.status === 'error' && <ErrorState message={state.error} onRetry={reload} />}
    {state.status === 'loading' && !data && <LoadingState />}
    {data && focus && <>
      {state.status === 'loading' && <p className="intel-note" role="status">Refreshing analysis…</p>}
      {data.data_source.market.notes?.map((note) => <p className="intel-note" key={note}>{note}</p>)}
      <div className="snapshot" aria-label="Market snapshot">
        <div><span>{data.asset.name}</span><strong>{fmtPrice(data.market.latest.close)}</strong><small>close · {fmtDate(data.market.latest.trading_date)}</small></div>
        <div><span>Daily change</span><strong className={(data.market.latest.return_1 ?? 0) >= 0 ? 'gain' : 'loss'}>{fmtPct(data.market.latest.return_1)}</strong></div>
        <div><span>Volume</span><strong>{fmtCompact(data.market.latest.volume)}</strong><small>{data.market.latest.volume_ratio ? `${data.market.latest.volume_ratio.toFixed(2)}× 20-day mean` : ''}</small></div>
        <div><span>20-day volatility</span><strong>{fmtPct(data.market.latest.volatility_20)}</strong></div>
        <div><span>Current risk</span><strong className={`risk-text-${data.current_assessment.risk.level.toLowerCase()}`}>{Math.round(data.current_assessment.risk.score)} · {data.current_assessment.risk.level}</strong></div>
      </div>
      {children({ data, focus, setFocus: setFocusId })}
      <p className="intel-note">Generated {fmtDateTime(data.generated_at)} · pipeline v{data.pipeline_version} · {data.disclaimer}</p>
    </>}
  </div>
}
