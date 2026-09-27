import { ArrowRight } from 'lucide-react'
import { useApiResource } from '../../hooks/useApiResource'
import { getIntelligence } from '../../services/intelligenceApi'
import { fmtDate, fmtPct, fmtPrice, fmtScore } from '../../utils/format'
import { SectionHeading } from '../common/SectionHeading'
import { LineChart } from '../intelligence/LineChart'
import { ErrorState, LoadingState, SourceBadge } from '../intelligence/StateViews'

const PREVIEW_SYMBOL = 'RELIANCE'

// Controlled homepage preview of the pipeline output (ML Pipeline §37); the full view lives at /intelligence.
export function IntelligencePreview() {
  const { state, reload } = useApiResource((signal) => getIntelligence(PREVIEW_SYMBOL, { signal }), [])
  const data = state.data
  return <section className="section intel-preview" id="intelligence"><div className="container">
    <SectionHeading eyebrow="MARKET INTELLIGENCE" title="Behaviour, anomaly, sentiment and risk — for one asset." intro="A preview of Aventra’s pipeline output for Reliance Industries, computed from provider data by the backend." />
    <div className="preview-card">
      {state.status === 'error' && !data && <ErrorState message={state.error} onRetry={reload} />}
      {state.status === 'loading' && !data && <LoadingState message="Analysing Reliance Industries…" />}
      {data && <>
        <div className="preview-head"><div><strong>{data.asset.name}</strong><span>{data.symbol} · close {fmtPrice(data.market.latest.close)} ({fmtPct(data.market.latest.return_1)}) · {fmtDate(data.market.latest.trading_date)}</span></div><SourceBadge source={data.data_source.market} /></div>
        <LineChart ariaLabel={`${data.symbol} closing price with flagged anomalies`} format={fmtPrice} points={data.market.series.slice(-120).map((p) => ({ label: p.date, value: p.close, highlight: p.is_anomaly }))} />
        <div className="preview-stats">
          <div><span>Anomaly (latest session)</span><strong>{data.anomaly.current.severity}</strong><small>score {fmtScore(data.anomaly.current.anomaly_score)} · {data.anomaly.flagged_count} flagged in window</small></div>
          <div><span>Behavioural fingerprint</span><strong>{data.fingerprint.level.replace('_', ' ')}</strong><small>deviation {fmtScore(data.fingerprint.score)}</small></div>
          <div><span>News sentiment (FinBERT)</span><strong>{data.news.sentiment_summary.mean_score === null ? 'unavailable' : fmtScore(data.news.sentiment_summary.mean_score)}</strong><small>{data.news.sentiment_summary.scored} scored headlines</small></div>
          <div><span>Risk signal</span><strong className={`risk-text-${data.current_assessment.risk.level.toLowerCase()}`}>{Math.round(data.current_assessment.risk.score)} · {data.current_assessment.risk.level}</strong><small>{data.current_assessment.risk.basis.replace(/_/g, ' ')}</small></div>
        </div>
        <a className="button button-primary" href={`/intelligence?symbol=${PREVIEW_SYMBOL}`}>View Intelligence <ArrowRight size={15} /></a>
      </>}
    </div>
  </div></section>
}
