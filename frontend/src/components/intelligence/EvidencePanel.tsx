import type { Assessment } from '../../types/api'
import { fmtDateTime } from '../../utils/format'
import { Panel } from '../common/Panel'
import { EvidenceChain } from './EvidenceChain'

export function EvidencePanel({ assessment, timeZone, id }: { assessment: Assessment; timeZone?: string | null; id?: string }) {
  const { explanation, evidence } = assessment
  return <Panel id={id} className="panel-evidence" eyebrow="EVIDENCE CHAIN" titleId="evidence-title" title="Why this was flagged">
    <dl className="explanation">
      <div><dt>What happened</dt><dd>{explanation.what}</dd></div>
      <div><dt>When</dt><dd>{explanation.when}</dd></div>
      <div><dt>How unusual</dt><dd>{explanation.how_unusual}</dd></div>
      <div><dt>Associated news</dt><dd>{explanation.news}</dd></div>
      <div><dt>Timing</dt><dd>{explanation.timing}</dd></div>
      <div><dt>Why this risk level</dt><dd>{explanation.why}</dd></div>
    </dl>
    <EvidenceChain assessment={assessment} timeZone={timeZone} />
    <details className="disclosure">
      <summary>Timestamped record ({evidence.length} items)</summary>
      <ol className="evidence-timeline">{evidence.map((item, index) => <li key={index} className={`evidence-${item.type}`}>
        <div className="evidence-time"><time dateTime={item.timestamp}>{fmtDateTime(item.timestamp, timeZone)}</time>{item.gap_minutes_from_previous ? <small>+{Math.round(item.gap_minutes_from_previous)} min</small> : null}</div>
        <div className="evidence-body"><span className="evidence-type">{item.type}</span><p>{item.url ? <a href={item.url} target="_blank" rel="noreferrer">{item.description}</a> : item.description}</p><small>source: {item.source}</small></div>
      </li>)}</ol>
    </details>
    <p className="note caveat">{explanation.caveat}</p>
  </Panel>
}
