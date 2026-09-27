import { useCallback, useEffect, useMemo, useState } from 'react'
import { BarChart3, Bell, Globe2, LayoutGrid, RefreshCw, Settings2 } from 'lucide-react'
import { SectionHeading } from '../common/SectionHeading'
import { GlobalSearch } from '../search/GlobalSearch'
import { getNews, getSnapshots, getWatchlist } from '../../services/intelligenceApi'
import { DATA_UNAVAILABLE } from '../../services/apiClient'
import type { NewsItem, SnapshotItem, Watchlist } from '../../types/api'
import { ASSET_CLASS_LABEL, fmtBp, fmtCompact, fmtDate, fmtLevel, fmtPct } from '../../utils/format'

const REFRESH_MS = 5 * 60_000

function chartPath(points: number[]) { if (points.length < 2) return ''; const low = Math.min(...points); const range = Math.max(...points) - low || 1; return points.map((point, index) => `${index ? 'L' : 'M'} ${(index / (points.length - 1)) * 100} ${86 - ((point - low) / range) * 66}`).join(' ') }
function ago(iso: string) { const minutes = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000)); return minutes < 60 ? `${minutes}m ago` : minutes < 1440 ? `${Math.round(minutes / 60)}h ago` : `${Math.round(minutes / 1440)}d ago` }
const shortCode = (id: string) => id.split(':').slice(1).join(':')

/** Signed daily change in the unit that fits the value kind: % for prices/NAV/rates, basis points for yields. */
function change(item: SnapshotItem): { value: number | null; text: string } {
  const s = item.snapshot
  if (!s) return { value: null, text: '—' }
  if (s.value_kind === 'yield') return { value: s.change_bp, text: fmtBp(s.change_bp) }
  return { value: s.change_pct === null ? null : s.change_pct / 100, text: fmtPct(s.change_pct === null ? null : s.change_pct / 100) }
}

type Load<T> = { state: 'loading' } | { state: 'ok'; data: T } | { state: 'error'; message: string }

// Market monitor for the configured watchlist (AVENTRA_DEFAULT_WATCHLIST). Every value is a real provider observation or an explicit unavailable state.
export function LiveMarketData() {
  const [watchlist, setWatchlist] = useState<Load<Watchlist>>({ state: 'loading' })
  const [items, setItems] = useState<SnapshotItem[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [news, setNews] = useState<{ items: NewsItem[]; state: 'idle' | 'loading' | 'ok' | 'error'; message?: string }>({ items: [], state: 'idle' })

  useEffect(() => {
    const controller = new AbortController()
    getWatchlist(controller.signal).then((data) => setWatchlist({ state: 'ok', data }))
      .catch((reason: unknown) => { if (!controller.signal.aborted) setWatchlist({ state: 'error', message: reason instanceof Error ? reason.message : 'Watchlist unavailable.' }) })
    return () => controller.abort()
  }, [])

  const ids = useMemo(() => (watchlist.state === 'ok' ? watchlist.data.items.filter((i) => i.status !== 'not_in_master').map((i) => i.instrument_id) : []), [watchlist])
  const loadSnapshots = useCallback(async () => {
    if (ids.length === 0) return
    setLoading(true)
    try { setItems(await getSnapshots(ids)) }
    catch (reason) { setItems(ids.map((id) => ({ instrument_id: id, status: 'PROVIDER_UNAVAILABLE', snapshot: null, error: reason instanceof Error ? reason.message : DATA_UNAVAILABLE }))) }
    finally { setLoading(false) }
  }, [ids])
  useEffect(() => { void loadSnapshots(); const interval = window.setInterval(() => void loadSnapshots(), REFRESH_MS); return () => window.clearInterval(interval) }, [loadSnapshots])
  useEffect(() => { if (!selectedId && ids.length) setSelectedId(ids[0]) }, [ids, selectedId])

  useEffect(() => {
    if (!selectedId) return
    const controller = new AbortController()
    setNews({ items: [], state: 'loading' })
    getNews(selectedId, 5, controller.signal).then((data) => setNews({ items: data.items, state: 'ok', message: data.data_source.message ?? undefined }))
      .catch((reason: unknown) => { if (!controller.signal.aborted) setNews({ items: [], state: 'error', message: reason instanceof Error ? reason.message : 'News unavailable.' }) })
    return () => controller.abort()
  }, [selectedId])

  const selected = items.find((i) => i.instrument_id === selectedId)
  const snap = selected?.snapshot ?? null
  const meta = watchlist.state === 'ok' ? watchlist.data.items.find((i) => i.instrument_id === selectedId) : undefined
  const path = useMemo(() => chartPath(snap?.series.map((p) => p.close) ?? []), [snap])
  const gradientId = `market-gradient-${(selectedId ?? 'none').replace(/[^A-Za-z0-9]/g, '')}`
  const available = items.filter((i) => i.snapshot)
  const ordered = [...available].sort((a, b) => (change(b).value ?? 0) - (change(a).value ?? 0))
  const selectedChange = selected ? change(selected) : { value: null, text: '—' }
  const empty = watchlist.state === 'ok' && ids.length === 0

  return <section className="section market terminal-section" id="market"><div className="container">
    <div className="market-head terminal-heading"><SectionHeading eyebrow="MARKET MONITORING" title="Market intelligence, in one view." intro="A workspace for the configured watchlist — any mix of stocks, funds, forex and crypto, each shown in its own currency and only with real provider data." /></div>
    <div className="terminal">
      <aside className="terminal-rail" aria-label="Dashboard navigation"><div className="rail-mark">A</div><a className="rail-button active" href="#market" aria-label="Market overview"><Globe2 size={17} /></a><a className="rail-button" href="/intelligence" aria-label="Open the intelligence dashboard"><BarChart3 size={16} /></a><a className="rail-button" href="/anomaly-detection" aria-label="Anomaly detection"><LayoutGrid size={16} /></a><div className="rail-spacer" /><a className="rail-button" href="/risk-evidence" aria-label="Risk and evidence"><Settings2 size={16} /></a></aside>
      <div className="terminal-main">
        <div className="terminal-topbar">
          <div><span className={`live-label ${snap && !snap.quality.stale ? 'is-live' : ''}`}><i />{loading ? 'REFRESHING SNAPSHOTS' : snap ? (snap.quality.stale ? 'STORED DATA' : 'PROVIDER DATA') : 'NO DATA'}</span>
            <span className="quote-name">{snap ? `Latest observation ${fmtDate(snap.as_of.slice(0, 10))} · ${snap.data_source.provider} · refreshes every 5 minutes` : 'Daily observations from permitted providers'}</span></div>
          <div className="market-controls">
            {ids.length > 0 && <><label className="sr-only" htmlFor="watch-select">Choose a watchlist instrument</label>
              <select id="watch-select" className="asset-select" value={selectedId ?? ''} onChange={(event) => setSelectedId(event.target.value)}>
                {watchlist.state === 'ok' && watchlist.data.items.filter((i) => ids.includes(i.instrument_id)).map((i) => <option value={i.instrument_id} key={i.instrument_id}>{i.symbol ?? shortCode(i.instrument_id)}</option>)}</select></>}
            <button type="button" className="refresh-button" onClick={() => void loadSnapshots()} disabled={loading || ids.length === 0} aria-label="Refresh snapshots"><RefreshCw size={15} className={loading ? 'spinning' : ''} /></button>
          </div>
        </div>

        {watchlist.state === 'loading' && <p className="panel-state" role="status">Loading watchlist…</p>}
        {watchlist.state === 'error' && <p className="panel-state" role="alert">{watchlist.message}</p>}
        {empty && <div className="panel-state terminal-empty"><p>No watchlist is configured. Set <code>AVENTRA_DEFAULT_WATCHLIST</code> on the server (e.g. <code>CRYPTO:BTC-USDT,FX:USDINR</code>), or search any instrument:</p><GlobalSearch /></div>}

        {ids.length > 0 && <>
          <div className="terminal-overview">
            <section className="terminal-chart">
              <div className="terminal-card-title"><div><span>{selectedId}{meta?.asset_class ? ` · ${ASSET_CLASS_LABEL[meta.asset_class] ?? meta.asset_class}` : ''}</span><strong>{snap?.instrument.name ?? meta?.name ?? selectedId}</strong></div>
                <div className={(selectedChange.value ?? 0) >= 0 ? 'terminal-change gain' : 'terminal-change loss'}>{selectedChange.text}<small>{snap ? fmtLevel(snap.last, snap.value_kind, snap.instrument.currency) : '—'}</small></div></div>
              {path ? <svg viewBox="0 0 100 100" preserveAspectRatio="none" role="img" aria-label={`Daily trend for ${selectedId} over the last ${snap?.series.length ?? 0} observations`}><defs><linearGradient id={gradientId} x1="0" x2="0" y1="0" y2="1"><stop stopColor="#62d6d0" stopOpacity=".26" /><stop offset="1" stopColor="#62d6d0" stopOpacity="0" /></linearGradient></defs>{[18, 38, 58, 78].map((y) => <line className="chart-grid" x1="0" y1={y} x2="100" y2={y} key={y} />)}<path className="chart-fill" fill={`url(#${gradientId})`} d={`${path} L 100 100 L 0 100 Z`} /><path className="chart-line" d={path} /></svg>
                : <p className="chart-empty" role="status">{loading || !selected ? 'Loading daily series…' : `${DATA_UNAVAILABLE}${selected.error ? ` — ${selected.error}` : ''}`}</p>}
              {snap && <div className="chart-axis"><span>{fmtDate(snap.series[0]?.timestamp.slice(0, 10))}</span><span>{snap.series.length} daily observations</span><span>{fmtDate(snap.as_of.slice(0, 10))}</span></div>}
              {selectedId && <a className="source-link" href={`/intelligence?id=${encodeURIComponent(selectedId)}`}>OPEN INTELLIGENCE ↗</a>}
            </section>
            <section className="market-pulse"><div className="panel-heading"><span>MARKET PULSE</span><Bell size={14} /></div>
              <div className="pulse-orbit"><div className="orbit orbit-one" /><div className="orbit orbit-two" /><div className="pulse-core">WATCH<small>{ids.length}</small></div>
                {items.slice(0, 10).map((item, index) => { const c = change(item); return <button type="button" onClick={() => setSelectedId(item.instrument_id)} className={`pulse-node ${c.value === null ? '' : c.value >= 0 ? 'gain' : 'loss'}`} style={{ '--node': index } as React.CSSProperties} key={item.instrument_id} title={item.error}>{shortCode(item.instrument_id).split("-")[0].slice(0, 6)}<small>{c.text}</small></button> })}</div>
              <p>Latest daily change<br />across the configured watchlist.</p></section>
          </div>
          <div className="terminal-grid">
            <section className="terminal-panel heat-panel"><div className="panel-heading"><span>DAILY CHANGE HEAT MAP</span><span className="panel-action">WATCHLIST</span></div>
              <div className="heatmap">{items.map((item) => { const c = change(item); const scale = item.snapshot?.value_kind === 'yield' ? 20 : 0.04; return <button type="button" onClick={() => setSelectedId(item.instrument_id)} className={c.value === null ? 'heat-unknown' : c.value >= 0 ? 'heat-gain' : 'heat-loss'} style={{ '--heat': c.value === null ? 0 : Math.min(Math.abs(c.value) / scale, 1) } as React.CSSProperties} title={c.value === null ? `${item.instrument_id}: ${item.status.replace(/_/g, ' ').toLowerCase()}` : `${item.instrument_id} ${c.text}`} key={item.instrument_id}>{item.snapshot?.instrument.symbol ?? shortCode(item.instrument_id)}</button> })}</div></section>
            <section className="terminal-panel news-panel"><div className="panel-heading"><span>{selectedId ? shortCode(selectedId) : ''} NEWS</span><span className="panel-action">FINBERT</span></div>
              {news.state === 'loading' && <p className="panel-state" role="status">Loading linked news…</p>}
              {news.state === 'error' && <p className="panel-state" role="alert">News context unavailable — {news.message}</p>}
              {news.state === 'ok' && news.items.length === 0 && <p className="panel-state">{news.message ?? 'No relevant news found for this instrument.'}</p>}
              {news.items.map((item) => <a href={item.url ?? '#market'} target={item.url ? '_blank' : undefined} rel="noreferrer" className="news-item" key={item.news_id}><span>{item.sentiment && <b className={`news-sentiment sentiment-${item.sentiment.label}`}>{item.sentiment.label}</b>}{item.headline}</span><small>{ago(item.published_at)}</small></a>)}</section>
            <section className="terminal-panel gainers-panel"><div className="panel-heading"><span>TOP MOVERS</span><span className="panel-action">WATCHLIST</span></div>
              <div className="mover-labels"><span>SYMBOL</span><span>LAST</span><span>CHANGE</span></div>
              {ordered.length === 0 && !loading && <p className="panel-state">{DATA_UNAVAILABLE}</p>}
              {ordered.map((item) => { const c = change(item); const s = item.snapshot!; return <button type="button" className="mover" onClick={() => setSelectedId(item.instrument_id)} key={item.instrument_id}><span>{s.instrument.symbol}</span><span>{fmtLevel(s.last, s.value_kind, s.instrument.currency)}</span><strong className={(c.value ?? 0) >= 0 ? 'gain' : 'loss'}>{c.text}</strong></button> })}</section>
          </div>
          <p className="market-disclaimer">Daily observations from the provider shown for each instrument (Binance, CoinGecko, Frankfurter, AMFI/mfapi, Alpha Vantage, Upstox, FRED — whichever is permitted and configured). Grey cells had no data available; values are never estimated. Volume{snap?.volume !== null && snap?.volume !== undefined ? ` (latest ${fmtCompact(snap.volume)})` : ''} is shown only where the provider supplies it.</p>
        </>}
      </div>
    </div>
  </div></section>
}
