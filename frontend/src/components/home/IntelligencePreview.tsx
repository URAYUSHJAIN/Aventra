import { ArrowRight } from 'lucide-react'
import { useApiResource } from '../../hooks/useApiResource'
import { getIntelligence, getWatchlist } from '../../services/intelligenceApi'
import { ASSET_CLASS_LABEL, fmtBp, fmtDate, fmtLevel, fmtPct, fmtScore } from '../../utils/format'
import { SectionHeading } from '../common/SectionHeading'
import { GlobalSearch } from '../search/GlobalSearch'
import { LineChart } from '../intelligence/LineChart'
import { DataUnavailableState, LoadingState, SourceBadge } from '../intelligence/StateViews'

// Homepage preview of the pipeline output for the first watchlist instrument (configured server-side, never hard-coded).
export function IntelligencePreview() {
  const { state, reload } = useApiResource(async (signal) => {
    const watchlist = await getWatchlist(signal)
    const first = watchlist.items.find((i) => i.status !== 'not_in_master')
    return first ? getIntelligence(first.instrument_id, { signal }) : null
  }, [])
  const data = state.data
  const caps = data?.capabilities
  const level = (v: number) => fmtLevel(v, caps?.value_kind, data?.asset.currency)
  return <section className="section intel-preview" id="intelligence"><div className="container">
    <SectionHeading eyebrow="MARKET INTELLIGENCE" title="Behaviour, anomaly, sentiment and risk — for one instrument." intro="Aventra’s pipeline output for the first instrument in the configured watchlist, computed by the backend from real provider data." />
    <div className="preview-card">
      {state.status === 'error' && !data && <DataUnavailableState error={state.cause} message={state.error} onRetry={reload} />}
      {state.status === 'loading' && !data && <LoadingState message="Analysing the watchlist’s first instrument…" />}
      {state.status === 'success' && data === null && <div className="intel-empty-start"><p>No watchlist is configured on the server. Search any instrument to analyse it:</p><GlobalSearch /></div>}
      {data && caps && <>
        <div className="preview-head"><div><strong>{data.asset.name}</strong><span>{ASSET_CLASS_LABEL[data.asset.asset_class] ?? data.asset.asset_class} · {data.instrument_id} · {level(data.market.latest.close)} ({caps.value_kind === 'yield' ? fmtBp(data.market.latest.change_bp) : fmtPct(data.market.latest.return_1)}) · {fmtDate(data.market.latest.trading_date)}</span></div><SourceBadge source={data.data_source.market} /></div>
        <LineChart ariaLabel={`${data.instrument_id} daily series with flagged anomalies`} format={level} points={data.market.series.slice(-120).map((p) => ({ label: p.date, value: p.close, highlight: p.is_anomaly }))} />
        <div className="preview-stats">
          <div><span>Anomaly (latest observation)</span><strong>{data.anomaly.current.severity}</strong><small>score {fmtScore(data.anomaly.current.anomaly_score)} · {data.anomaly.flagged_count} flagged in window</small></div>
          <div><span>Behavioural fingerprint</span><strong>{data.fingerprint.level.replace('_', ' ')}</strong><small>deviation {fmtScore(data.fingerprint.score)}</small></div>
          <div><span>News sentiment (FinBERT)</span><strong>{data.news.sentiment_summary.mean_score === null ? (data.news.status === 'unavailable' ? 'unavailable' : 'no relevant news') : fmtScore(data.news.sentiment_summary.mean_score)}</strong><small>{data.news.sentiment_summary.scored} scored headlines</small></div>
          <div><span>Risk signal</span><strong className={`risk-text-${data.current_assessment.risk.level.toLowerCase()}`}>{Math.round(data.current_assessment.risk.score)} · {data.current_assessment.risk.level}</strong><small>{data.current_assessment.risk.basis.replace(/_/g, ' ')}</small></div>
        </div>
        <a className="button button-primary" href={`/intelligence?id=${encodeURIComponent(data.instrument_id)}`}>View Intelligence <ArrowRight size={15} /></a>
      </>}
    </div>
  </div></section>
}
