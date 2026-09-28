import { ArrowRight } from 'lucide-react'
import { useState } from 'react'
import { useApiResource } from '../../hooks/useApiResource'
import { getIntelligence, getWatchlist } from '../../services/intelligenceApi'
import { ASSET_CLASS_LABEL, fmtBp, fmtDate, fmtLevel, fmtPct, fmtRiskScore, fmtScore } from '../../utils/format'
import { Badge, changeTone, fingerprintTone, riskTone, severityTone } from '../common/Badge'
import { SectionHeading } from '../common/SectionHeading'
import { GlobalSearch } from '../search/GlobalSearch'
import { LineChart } from '../intelligence/LineChart'
import { DataUnavailableState, LoadingState, SourceBadge } from '../intelligence/StateViews'

type Layer = 'state' | 'behaviour' | 'anomaly' | 'news' | 'events' | 'risk' | 'evidence'
const STORY: Array<[Layer, string, string]> = [
  ['state', 'Current state', 'The latest real observation, in the instrument’s own currency and timezone.'],
  ['behaviour', 'Behaviour', 'How today compares with the asset’s own learned normal.'],
  ['anomaly', 'Anomaly', 'Whether the session is unusual, and which dimensions moved.'],
  ['news', 'News', 'Linked financial news and the sentiment of its language.'],
  ['events', 'Events', 'What was published around the session, aligned in time.'],
  ['risk', 'Risk', 'A transparent score with every contribution shown.'],
  ['evidence', 'Evidence', 'The timestamped chain behind the flag.'],
]

// "Market intelligence, in one view": the story on the left, the pipeline's real output for the first watchlist instrument on the right.
export function IntelligencePreview() {
  const [layer, setLayer] = useState<Layer | null>(null)
  const { state, reload } = useApiResource(async (signal) => {
    const watchlist = await getWatchlist(signal)
    const first = watchlist.items.find((i) => i.status !== 'not_in_master')
    return first ? getIntelligence(first.instrument_id, { signal }) : null
  }, [])
  const data = state.data
  const caps = data?.capabilities
  const level = (v: number) => fmtLevel(v, caps?.value_kind, data?.asset.currency)
  const current = data?.current_assessment
  const lit = (...keys: Layer[]) => (layer && keys.includes(layer) ? ' is-lit' : layer ? ' is-dim' : '')
  return <section className="section intel-story" id="intelligence" aria-labelledby="story-title">
    <div className="wrap story-grid">
      <div className="story-copy">
        <SectionHeading id="story-title" eyebrow="MARKET INTELLIGENCE" title={<>Market intelligence, <em>in one view.</em></>} intro="Search one instrument and Aventra investigates it layer by layer, from what the market did to why it was flagged." />
        <ol className="story-steps">{STORY.map(([key, title, text], index) => <li key={key} onMouseEnter={() => setLayer(key)} onMouseLeave={() => setLayer(null)} className={layer === key ? 'is-active' : ''}>
          <span>{String(index + 1).padStart(2, '0')}</span><div><strong>{title}</strong><p>{text}</p></div></li>)}</ol>
      </div>
      <div className="story-product" aria-live="polite">
        {state.status === 'error' && !data && <DataUnavailableState error={state.cause} message={state.error} onRetry={reload} />}
        {state.status === 'loading' && !data && <LoadingState message="Analysing the watchlist’s first instrument…" />}
        {state.status === 'success' && data === null && <div className="product-empty"><p className="eyebrow">NO WATCHLIST CONFIGURED</p><p>This server has no default watchlist, so there is no instrument to preview. Search any instrument to run the full analysis:</p><GlobalSearch /></div>}
        {data && caps && current && <div className="product-view">
          <header className={`product-head${lit('state')}`}>
            <div><span className={`class-badge class-${data.asset.asset_class}`}>{ASSET_CLASS_LABEL[data.asset.asset_class] ?? data.asset.asset_class}</span><strong>{data.asset.name}</strong><small>{data.instrument_id} · {fmtDate(data.market.latest.trading_date)}</small></div>
            <div className="product-quote"><strong>{level(data.market.latest.close)}</strong><span className={`text-${changeTone(caps.value_kind === 'yield' ? data.market.latest.change_bp : data.market.latest.return_1)}`}>{caps.value_kind === 'yield' ? fmtBp(data.market.latest.change_bp) : fmtPct(data.market.latest.return_1)}</span></div>
          </header>
          <div className={`product-chart${lit('anomaly')}`}><LineChart ariaLabel={`${data.instrument_id} daily series with flagged anomalies`} format={level} height={170} points={data.market.series.slice(-120).map((p) => ({ label: p.date, value: p.close, highlight: p.is_anomaly }))} /></div>
          <div className="product-layers">
            <div className={lit('behaviour')}><span>Behaviour</span><Badge tone={fingerprintTone(data.fingerprint.level)}>{data.fingerprint.level.replace(/_/g, ' ')}</Badge><small>deviation {fmtScore(data.fingerprint.score)}</small></div>
            <div className={lit('anomaly')}><span>Anomaly · latest</span><Badge tone={severityTone(current.anomaly.severity)}>{current.anomaly.severity}</Badge><small>score {fmtScore(current.anomaly.anomaly_score)} · {data.anomaly.flagged_count} flagged</small></div>
            <div className={lit('news', 'events')}><span>News</span><Badge tone={data.news.status === 'unavailable' ? 'neutral' : 'info'}>{data.news.status === 'unavailable' ? 'unavailable' : `${data.news.sentiment_summary.scored} scored`}</Badge><small>{data.news.sentiment_summary.mean_score === null ? (data.news.status === 'unavailable' ? 'no permitted source' : 'no relevant news') : `mean sentiment ${fmtScore(data.news.sentiment_summary.mean_score)}`}</small></div>
            <div className={lit('risk')}><span>Risk</span><Badge tone={riskTone(current.risk.level)}>{fmtRiskScore(current.risk.score)} · {current.risk.level}</Badge><small>{current.risk.basis.replace(/_/g, ' ')}</small></div>
          </div>
          <p className={`product-insight${lit('evidence')}`}>{current.explanation.what}</p>
          <footer className="product-foot"><SourceBadge source={data.data_source.market} /><a className="text-link" href={`/intelligence?id=${encodeURIComponent(data.instrument_id)}`}>Open full analysis <ArrowRight size={14} aria-hidden="true" /></a></footer>
        </div>}
      </div>
    </div>
  </section>
}
