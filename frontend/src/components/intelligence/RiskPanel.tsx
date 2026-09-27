import type { RiskAssessment } from '../../types/api'

const BASIS_TEXT: Record<string, string> = {
  market_and_news: 'Market behaviour and aligned news',
  market_only_no_aligned_news: 'Market behaviour only — no aligned news found',
  market_only_news_unavailable: 'Market behaviour only — news context unavailable',
}

export function RiskPanel({ risk, title = 'Risk signal' }: { risk: RiskAssessment; title?: string }) {
  const max = Math.max(...risk.components.map((c) => c.weight * 100), 1)
  return <section className="intel-panel" aria-labelledby="risk-title">
    <header className="intel-panel-head"><div><p className="eyebrow">RISK &amp; EVIDENCE</p><h2 id="risk-title">{title}</h2></div></header>
    <div className="risk-summary"><div className={`risk-dial risk-${risk.level.toLowerCase()}`} role="img" aria-label={`Risk ${Math.round(risk.score)} out of 100, ${risk.level}`}><strong>{Math.round(risk.score)}</strong><span>{risk.level}</span></div>
      <p>{BASIS_TEXT[risk.basis] ?? risk.basis}</p></div>
    <table className="risk-table"><caption className="sr-only">Contribution of each component to the risk score</caption>
      <thead><tr><th scope="col">Component</th><th scope="col">Value</th><th scope="col">Weight</th><th scope="col">Contribution</th></tr></thead>
      <tbody>{risk.components.map((c) => <tr key={c.name} className={c.available ? '' : 'unavailable'}><th scope="row" title={c.description}>{c.name}</th>
        <td>{c.available ? c.value?.toFixed(2) : 'n/a'}</td><td>{c.weight.toFixed(2)}{c.gate !== 1 ? ` × ${c.gate.toFixed(2)}` : ''}</td>
        <td><span className="contribution"><i><b style={{ width: `${(c.contribution / max) * 100}%` }} /></i>{c.contribution.toFixed(1)}</span></td></tr>)}</tbody></table>
    <p className="intel-note">Context terms are scaled by the anomaly score (× gate). Weights are uncalibrated defaults. {risk.disclaimer}</p>
  </section>
}
