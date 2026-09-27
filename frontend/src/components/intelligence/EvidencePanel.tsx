import type { Assessment } from '../../types/api'
import { fmtDateTime } from '../../utils/format'

export function EvidencePanel({ assessment }: { assessment: Assessment }) {
  const { explanation, evidence } = assessment
  return <section className="intel-panel" aria-labelledby="evidence-title">
    <header className="intel-panel-head"><div><p className="eyebrow">EVIDENCE CHAIN</p><h2 id="evidence-title">Why this was flagged</h2></div></header>
    <dl className="explanation">
      <div><dt>What happened</dt><dd>{explanation.what}</dd></div>
      <div><dt>When</dt><dd>{explanation.when}</dd></div>
      <div><dt>How unusual</dt><dd>{explanation.how_unusual}</dd></div>
      <div><dt>Associated news</dt><dd>{explanation.news}</dd></div>
      <div><dt>Timing</dt><dd>{explanation.timing}</dd></div>
      <div><dt>Why this risk level</dt><dd>{explanation.why}</dd></div>
    </dl>
    <ol className="evidence-timeline">{evidence.map((item, index) => <li key={index} className={`evidence-${item.type}`}>
      <div className="evidence-time"><time dateTime={item.timestamp}>{fmtDateTime(item.timestamp)}</time>{item.gap_minutes_from_previous ? <small>+{Math.round(item.gap_minutes_from_previous)} min</small> : null}</div>
      <div className="evidence-body"><span className="evidence-type">{item.type}</span><p>{item.url ? <a href={item.url} target="_blank" rel="noreferrer">{item.description}</a> : item.description}</p><small>source: {item.source}</small></div>
    </li>)}</ol>
    <p className="intel-note">{explanation.caveat}</p>
  </section>
}
