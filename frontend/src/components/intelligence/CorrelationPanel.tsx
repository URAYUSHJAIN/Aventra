import type { Assessment } from '../../types/api'
import { fmtDate, fmtDateTime, fmtScore, relationText } from '../../utils/format'
import { Panel } from '../common/Panel'

const COMPONENT_LABELS: Record<string, string> = { temporal_proximity: 'Temporal proximity', asset_match: 'Asset match', sentiment_strength: 'Sentiment strength', anomaly_strength: 'Anomaly strength' }

/** Position (0–100 %) of a timestamp inside the correlation window. */
function place(iso: string, start: number, end: number) { return Math.min(100, Math.max(0, ((new Date(iso).getTime() - start) / (end - start || 1)) * 100)) }

export function CorrelationPanel({ assessment, timeZone, id }: { assessment: Assessment; timeZone?: string | null; id?: string }) {
  const correlation = assessment.correlation
  const { window } = correlation
  const start = window.start ? new Date(window.start).getTime() : null, end = window.end ? new Date(window.end).getTime() : null
  return <Panel id={id} className="panel-correlation" eyebrow="CROSS-SOURCE CORRELATION" titleId="corr-title" title={`Signals aligned with ${fmtDate(assessment.trading_date)}`}
    aside={<span className="score-chip">best <b>{fmtScore(correlation.best_score)}</b></span>}>
    {window.start && <p className="note">Window: {fmtDateTime(window.start, timeZone)} → {fmtDateTime(window.end, timeZone)} (session {fmtDateTime(window.session_open, timeZone)} – {fmtDateTime(window.session_close, timeZone)}).</p>}
    {correlation.status === 'news_unavailable' && <p className="state-inline is-unavailable" role="alert">News context unavailable, so correlation could not be assessed.</p>}
    {correlation.status === 'no_aligned_news' && <p className="empty-note">No asset-linked news was published inside the analysis window. The anomaly is reported on market evidence only.</p>}
    {correlation.matches.map((m) => <article className="corr-match" key={m.news_id}>
      <div className="corr-head"><strong>{m.correlation_score.toFixed(2)}</strong><div>{m.url ? <a href={m.url} target="_blank" rel="noreferrer">{m.headline}</a> : <p>{m.headline}</p>}
        <small>{m.source ?? 'Unknown source'} · published {relationText(m.relation, m.hours_from_session)} · {m.category.category}{m.category.matched_keywords.length ? ` (${m.category.matched_keywords.slice(0, 3).join(', ')})` : ''}</small></div></div>
      {start !== null && end !== null && <div className="corr-timing" role="img" aria-label={`Published ${relationText(m.relation, m.hours_from_session)}, inside the analysis window`}>
        <span className="corr-session" style={{ left: `${place(window.session_open, start, end)}%`, width: `${place(window.session_close, start, end) - place(window.session_open, start, end)}%` }} />
        <span className="corr-published" style={{ left: `${place(m.published_at, start, end)}%` }} />
        <small className="corr-timing-label">window · <b>session</b> · ◆ article</small>
      </div>}
      <dl className="corr-components">{Object.entries(m.components).map(([key, value]) => <div key={key}><dt>{COMPONENT_LABELS[key] ?? key}</dt><dd><i aria-hidden="true"><b style={{ width: `${value * 100}%` }} /></i>{value.toFixed(2)}</dd></div>)}
        <div><dt>Semantic relevance</dt><dd>{m.semantic_relevance === null ? 'unavailable' : m.semantic_relevance.toFixed(2)}</dd></div>
        <div><dt>Sentiment</dt><dd>{m.sentiment ? `${m.sentiment.label} (${m.sentiment.sentiment_score.toFixed(2)})` : 'unavailable'}</dd></div></dl>
    </article>)}
    <p className="note">{correlation.interpretation ?? 'Correlation reflects temporal alignment and asset match; it does not establish causation.'}</p>
  </Panel>
}
