import type { RiskAssessment } from '../../types/api'
import { fmtRiskScore } from '../../utils/format'
import { Badge, riskTone } from '../common/Badge'
import { Panel } from '../common/Panel'

const BASIS_TEXT: Record<string, string> = {
  market_and_news: 'Market behaviour and aligned news',
  market_only_no_aligned_news: 'Market behaviour only: no aligned news found',
  market_only_news_unavailable: 'Market behaviour only: news context unavailable',
}

export function RiskPanel({ risk, title = 'Risk signal', id }: { risk: RiskAssessment; title?: string; id?: string }) {
  const max = Math.max(...risk.components.map((c) => c.weight * 100), 1)
  const parts = risk.components.map((c, index) => ({ ...c, index })).filter((c) => c.contribution > 0)
  return <Panel id={id} className="panel-risk" eyebrow="EXPLAINABLE RISK" titleId="risk-title" title={title} aside={<Badge tone={riskTone(risk.level)}>{risk.level}</Badge>}>
    <div className="risk-summary">
      <div className={`risk-score text-${riskTone(risk.level)}`} role="img" aria-label={`Risk ${fmtRiskScore(risk.score)} out of 100, ${risk.level}`}><strong>{fmtRiskScore(risk.score)}</strong><span>/ 100</span></div>
      <div><p className="risk-basis">{BASIS_TEXT[risk.basis] ?? risk.basis}</p><p className="risk-sub">The score is the sum of the contributions below. It is a transparent score, not a probability.</p></div>
    </div>
    <div className="risk-stack" aria-hidden="true">{parts.map((c) => <span key={c.name} className={`seg seg-${c.index % 6}`} style={{ width: `${c.contribution}%` }} title={`${c.name}: ${c.contribution.toFixed(1)}`} />)}</div>
    <table className="data-table risk-table"><caption className="sr-only">Contribution of each component to the risk score</caption>
      <thead><tr><th scope="col">Component</th><th scope="col">Value</th><th scope="col">Weight</th><th scope="col">Contribution</th></tr></thead>
      <tbody>{risk.components.map((c, index) => <tr key={c.name} className={c.available ? '' : 'is-unavailable'}><th scope="row" title={c.description}><i className={`swatch seg-${index % 6}`} aria-hidden="true" />{c.name}</th>
        <td>{c.available ? c.value?.toFixed(2) : 'n/a'}</td><td>{c.weight.toFixed(2)}{c.gate !== 1 ? ` × ${c.gate.toFixed(2)}` : ''}</td>
        <td><span className="contribution"><i aria-hidden="true"><b style={{ width: `${(c.contribution / max) * 100}%` }} /></i>{c.contribution.toFixed(1)}</span></td></tr>)}</tbody></table>
    <p className="note">Context terms are scaled by the anomaly score (× gate). Weights are uncalibrated defaults. {risk.disclaimer}</p>
  </Panel>
}
