import { useCallback, useEffect, useMemo, useState } from 'react'
import { ArrowUpRight, RefreshCw } from 'lucide-react'
import { SectionHeading } from '../common/SectionHeading'
import { Badge, changeTone } from '../common/Badge'
import { GlobalSearch } from '../search/GlobalSearch'
import { getNews, getSnapshots, getWatchlist } from '../../services/intelligenceApi'
import { DATA_UNAVAILABLE } from '../../services/apiClient'
import type { NewsItem, SnapshotItem, Watchlist } from '../../types/api'
import { ASSET_CLASS_LABEL, fmtBp, fmtCompact, fmtDate, fmtLevel, fmtPct } from '../../utils/format'

const REFRESH_MS = 5 * 60_000

function chartPath(points: number[], top = 14, span = 72) { if (points.length < 2) return ''; const low = Math.min(...points); const range = Math.max(...points) - low || 1; return points.map((point, index) => `${index ? 'L' : 'M'} ${(index / (points.length - 1)) * 100} ${top + span - ((point - low) / range) * span}`).join(' ') }
function ago(iso: string) { const minutes = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000)); return minutes < 60 ? `${minutes}m ago` : minutes < 1440 ? `${Math.round(minutes / 60)}h ago` : `${Math.round(minutes / 1440)}d ago` }
const shortCode = (id: string) => id.split(':').slice(1).join(':')

/** Signed daily change in the unit that fits the value kind: % for prices/NAV/rates, basis points for yields. */
function change(item: SnapshotItem): { value: number | null; text: string } {
  const s = item.snapshot
  if (!s) return { value: null, text: 'n/a' }
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
  const selectedChange = selected ? change(selected) : { value: null, text: 'n/a' }
  const empty = watchlist.state === 'ok' && ids.length === 0
  const rows = ids.map((id) => ({ id, item: items.find((i) => i.instrument_id === id), meta: watchlist.state === 'ok' ? watchlist.data.items.find((i) => i.instrument_id === id) : undefined }))

  return <section className="section monitor" id="market" aria-labelledby="monitor-title">
    <div className="wrap">
      <div className="monitor-head">
        <SectionHeading id="monitor-title" eyebrow="WATCHLIST MONITOR" title="Observed daily. Never estimated." intro="The configured watchlist can mix stocks, funds, forex and crypto. Each is shown in its own currency, with real provider observations only." />
        <div className="monitor-status">
          <span className={`live-label${snap && !snap.quality.stale ? ' is-live' : ''}`}><i aria-hidden="true" />{loading ? 'REFRESHING' : snap ? (snap.quality.stale ? 'STORED DATA' : 'PROVIDER DATA') : 'NO DATA'}</span>
          <button type="button" className="chip-button" onClick={() => void loadSnapshots()} disabled={loading || ids.length === 0} aria-label="Refresh snapshots"><RefreshCw size={14} className={loading ? 'spinning' : ''} aria-hidden="true" /> Refresh</button>
        </div>
      </div>

      {watchlist.state === 'loading' && <p className="state state-loading" role="status">Loading watchlist…</p>}
      {watchlist.state === 'error' && <p className="state state-error" role="alert">{watchlist.message}</p>}
      {empty && <div className="monitor-empty"><p>No watchlist is configured. Set <code>AVENTRA_DEFAULT_WATCHLIST</code> on the server (e.g. <code>CRYPTO:BTC-USDT,FX:USDINR</code>), or search any instrument:</p><GlobalSearch /></div>}

      {ids.length > 0 && <div className="monitor-grid">
        <ul className="monitor-list" aria-label="Watchlist instruments">{rows.map(({ id, item, meta: m }) => { const c = item ? change(item) : { value: null, text: 'n/a' }; const s = item?.snapshot; const spark = s ? chartPath(s.series.map((p) => p.close), 10, 80) : ''
          return <li key={id}><button type="button" className={id === selectedId ? 'is-selected' : ''} aria-pressed={id === selectedId} onClick={() => setSelectedId(id)} title={item?.error}>
            <span className="row-id"><b>{s?.instrument.symbol ?? m?.symbol ?? shortCode(id)}</b><small>{s?.instrument.name ?? m?.name ?? id}</small></span>
            {spark ? <svg className={`row-spark text-${changeTone(c.value)}`} viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true"><path d={spark} /></svg> : <span className="row-spark" aria-hidden="true" />}
            <span className="row-value"><b>{s ? fmtLevel(s.last, s.value_kind, s.instrument.currency) : item ? 'unavailable' : '…'}</b><small className={`text-${changeTone(c.value)}`}>{c.text}</small></span>
          </button></li> })}</ul>

        <div className="monitor-detail">
          <div className="detail-head"><div><span className="mono-meta">{selectedId}{meta?.asset_class ? ` · ${ASSET_CLASS_LABEL[meta.asset_class] ?? meta.asset_class}` : ''}</span><strong>{snap?.instrument.name ?? meta?.name ?? selectedId}</strong></div>
            <div className="detail-quote"><strong>{snap ? fmtLevel(snap.last, snap.value_kind, snap.instrument.currency) : 'n/a'}</strong><span className={`text-${changeTone(selectedChange.value)}`}>{selectedChange.text}</span></div></div>
          {path ? <svg className="detail-chart" viewBox="0 0 100 100" preserveAspectRatio="none" role="img" aria-label={`Daily trend for ${selectedId} over the last ${snap?.series.length ?? 0} observations`}><defs><linearGradient id={gradientId} x1="0" x2="0" y1="0" y2="1"><stop offset="0" className="chart-fill-top" /><stop offset="1" className="chart-fill-bottom" /></linearGradient></defs>{[20, 45, 70].map((y) => <line className="chart-grid" x1="0" y1={y} x2="100" y2={y} key={y} />)}<path fill={`url(#${gradientId})`} d={`${path} L 100 100 L 0 100 Z`} /><path className="chart-series" d={path} /></svg>
            : <p className="chart-empty" role="status">{loading || !selected ? 'Loading daily series…' : `${DATA_UNAVAILABLE}${selected.error ? `: ${selected.error}` : ''}`}</p>}
          {snap && <div className="chart-caption"><span>{fmtDate(snap.series[0]?.timestamp.slice(0, 10))}</span><span>{snap.series.length} daily observations · {snap.data_source.provider} · refreshes every 5 min</span><span>{fmtDate(snap.as_of.slice(0, 10))}</span></div>}
          <div className="detail-news"><p className="eyebrow">LINKED NEWS{selectedId ? ` · ${shortCode(selectedId)}` : ''}</p>
            {news.state === 'loading' && <p className="empty-note" role="status">Loading linked news…</p>}
            {news.state === 'error' && <p className="state-inline is-unavailable" role="alert">News context unavailable: {news.message}</p>}
            {news.state === 'ok' && news.items.length === 0 && <p className="empty-note">{news.message ?? 'No relevant news found for this instrument.'}</p>}
            {news.items.length > 0 && <ul className="detail-news-list">{news.items.map((item) => <li key={item.news_id}>{item.sentiment && <Badge tone={item.sentiment.label === 'positive' ? 'positive' : item.sentiment.label === 'negative' ? 'negative' : 'neutral'}>{item.sentiment.label}</Badge>}
              {item.url ? <a href={item.url} target="_blank" rel="noreferrer">{item.headline}</a> : <span>{item.headline}</span>}<small>{ago(item.published_at)}</small></li>)}</ul>}
          </div>
          {selectedId && <a className="text-link" href={`/intelligence?id=${encodeURIComponent(selectedId)}`}>Open intelligence <ArrowUpRight size={14} aria-hidden="true" /></a>}
        </div>
      </div>}
      {ids.length > 0 && <p className="fine-print">Daily observations from the provider shown for each instrument (Binance, CoinGecko, Frankfurter, AMFI/mfapi, Alpha Vantage, Upstox, FRED: whichever is permitted and configured). Instruments without data say so; values are never estimated.{snap?.volume !== null && snap?.volume !== undefined ? ` Latest volume ${fmtCompact(snap.volume)}.` : ''}</p>}
    </div>
  </section>
}
