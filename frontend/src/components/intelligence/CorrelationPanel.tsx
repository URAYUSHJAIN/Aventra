import type { Assessment } from '../../types/api'
import { fmtDate, fmtDateTime, fmtScore, relationText } from '../../utils/format'

const COMPONENT_LABELS: Record<string, string> = { temporal_proximity: 'Temporal proximity', asset_match: 'Asset match', sentiment_strength: 'Sentiment strength', anomaly_strength: 'Anomaly strength' }

export function CorrelationPanel({ assessment }: { assessment: Assessment }) {
  const correlation = assessment.correlation
  return <section className="intel-panel" aria-labelledby="corr-title">
    <header className="intel-panel-head"><div><p className="eyebrow">CROSS-SOURCE EVENT CORRELATION</p><h2 id="corr-title">Signals aligned with {fmtDate(assessment.trading_date)}</h2></div>
      <div className="level-chip">best {fmtScore(correlation.best_score)}</div></header>
    {correlation.window.start && <p className="intel-note">Window: {fmtDateTime(correlation.window.start)} → {fmtDateTime(correlation.window.end)} (session {fmtDateTime(correlation.window.session_open)} – {fmtDateTime(correlation.window.session_close)}).</p>}
    {correlation.status === 'news_unavailable' && <p className="intel-state intel-error" role="alert">News context unavailable — correlation could not be assessed.</p>}
    {correlation.status === 'no_aligned_news' && <p className="intel-empty">No asset-linked news was published inside the analysis window. The anomaly is reported on market evidence only.</p>}
    {correlation.matches.map((m) => <article className="corr-match" key={m.news_id}>
      <div className="corr-head"><strong>{m.correlation_score.toFixed(2)}</strong><div>{m.url ? <a href={m.url} target="_blank" rel="noreferrer">{m.headline}</a> : <p>{m.headline}</p>}
        <small>{m.source ?? 'Unknown source'} · published {relationText(m.relation, m.hours_from_session)} · {m.category.category}{m.category.matched_keywords.length ? ` (${m.category.matched_keywords.slice(0, 3).join(', ')})` : ''}</small></div></div>
      <dl className="corr-components">{Object.entries(m.components).map(([key, value]) => <div key={key}><dt>{COMPONENT_LABELS[key] ?? key}</dt><dd><i><b style={{ width: `${value * 100}%` }} /></i>{value.toFixed(2)}</dd></div>)}
        <div><dt>Semantic relevance</dt><dd>{m.semantic_relevance === null ? 'unavailable' : m.semantic_relevance.toFixed(2)}</dd></div>
        <div><dt>Sentiment</dt><dd>{m.sentiment ? `${m.sentiment.label} (${m.sentiment.sentiment_score.toFixed(2)})` : 'unavailable'}</dd></div></dl>
    </article>)}
    <p className="intel-note">{correlation.interpretation ?? 'Correlation reflects temporal alignment and asset match; it does not establish causation.'}</p>
  </section>
}
