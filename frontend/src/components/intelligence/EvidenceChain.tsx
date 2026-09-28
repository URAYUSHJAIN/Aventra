import type { Assessment, EvidenceItem } from '../../types/api'
import { fmtDateTime } from '../../utils/format'

// Signal → Context → Event/News → Interpretation → Risk, built only from the backend's evidence items for this assessment
// (ml/evidence/chain.py item types). A stage with no items says so; nothing is inferred.
const STAGES: Array<{ key: string; label: string; types: string[]; empty: string }> = [
  { key: 'signal', label: 'Signal', types: ['price', 'volume', 'volatility', 'rate', 'market'], empty: 'No dimension deviated beyond 2 robust σ.' },
  { key: 'context', label: 'Context', types: ['anomaly', 'regime'], empty: 'No detector context recorded.' },
  { key: 'news', label: 'Event / news', types: ['news', 'sentiment'], empty: 'No aligned news in the analysis window.' },
  { key: 'interpretation', label: 'Interpretation', types: ['correlation'], empty: 'No cross-source alignment to interpret.' },
  { key: 'risk', label: 'Risk', types: ['risk'], empty: 'No risk item recorded.' },
]

const stageOf = (item: EvidenceItem) => STAGES.find((s) => s.types.includes(item.type))?.key ?? 'signal'

export function EvidenceChain({ assessment, timeZone }: { assessment: Assessment; timeZone?: string | null }) {
  const grouped = STAGES.map((stage) => ({ stage, items: assessment.evidence.filter((item) => stageOf(item) === stage.key) }))
  const newsEmpty = assessment.correlation.status === 'news_unavailable' ? 'News context unavailable for this instrument.' : undefined
  return <ol className="evidence-chain" aria-label="Evidence chain from signal to risk">
    {grouped.map(({ stage, items }, index) => <li key={stage.key} className={`chain-stage stage-${stage.key}${items.length ? '' : ' is-empty'}`}>
      <div className="chain-head"><span className="chain-index">{String(index + 1).padStart(2, '0')}</span><strong>{stage.label}</strong><small>{items.length ? `${items.length} item${items.length === 1 ? '' : 's'}` : 'none'}</small></div>
      {items.length === 0 ? <p className="chain-empty">{stage.key === 'news' && newsEmpty ? newsEmpty : stage.empty}</p>
        : <ul className="chain-nodes">{items.map((item, i) => <li key={`${item.type}-${item.signal}-${i}`} className={`chain-node node-${item.type}`}>
          <span className="node-type">{item.type}</span>
          <p>{item.url ? <a href={item.url} target="_blank" rel="noreferrer">{item.description}</a> : item.description}</p>
          <small><time dateTime={item.timestamp}>{fmtDateTime(item.timestamp, timeZone)}</time> · {item.source}</small>
        </li>)}</ul>}
    </li>)}
  </ol>
}
