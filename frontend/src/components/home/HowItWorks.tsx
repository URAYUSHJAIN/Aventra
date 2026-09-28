import { SectionHeading } from '../common/SectionHeading'

// The actual request path through the implemented system (docs/04, docs/05). Nothing here describes planned components.
const steps: Array<{ key: string; label: string; text: string; detail?: string[] }> = [
  { key: 'user', label: 'You', text: 'Ask about one instrument.' },
  { key: 'search', label: 'Instrument search', text: 'Search the Instrument Master, synced from permitted listings (exchanges, SEC, Binance, AMFI and others).' },
  { key: 'resolve', label: 'Instrument resolution', text: 'Resolve a canonical ID with asset class, exchange, currency, timezone, calendar and a capability profile.' },
  { key: 'router', label: 'Provider router', text: 'Try only the permitted providers that cover this asset, with rate limits, retries and a circuit breaker. No hidden fallback.' },
  { key: 'data', label: 'Real data', text: 'Daily observations with provenance: provider, retrieval time, currency and adjustment. Unavailable data is reported, never invented.' },
  { key: 'validate', label: 'Validation', text: 'Remove duplicates and impossible values, keep extreme but valid moves, align to UTC and the instrument’s own sessions.' },
  { key: 'features', label: 'Feature engineering', text: 'Past-only features chosen from what the data supports: returns, volume, volatility, range, gaps, drawdown.' },
  { key: 'ml', label: 'ML intelligence', text: 'Four analyses run on the same features.', detail: ['Behavioural fingerprint: rolling median/MAD baseline', 'Anomaly ensemble: statistical, fingerprint, Isolation Forest', 'News: linked articles, FinBERT sentiment', 'Correlation: news aligned to the session window'] },
  { key: 'risk', label: 'Risk + evidence', text: 'A transparent weighted risk score and a timestamped evidence chain with provenance.' },
  { key: 'back', label: 'You', text: 'Read what happened, how unusual it was, what else happened at the same time, and why it was flagged.' },
]

export function HowItWorks() {
  return <section className="section how" id="how-it-works" aria-labelledby="how-title">
    <div className="wrap how-grid">
      <div className="how-copy">
        <SectionHeading id="how-title" eyebrow="HOW IT WORKS" title={<>From a search <em>to evidence.</em></>} intro="The path a request actually takes through Aventra. Every stage is implemented; each hands a typed result (or an explicit “unavailable”) to the next." />
        <p className="how-principle"><span>Signal</span><span>Context</span><span>Explanation</span><span>Evidence</span></p>
      </div>
      <ol className="pipeline">{steps.map((step, index) => <li key={step.key} className={`pipeline-step step-${step.key} reveal`}>
        <span className="pipeline-index">{String(index + 1).padStart(2, '0')}</span>
        <div><strong>{step.label}</strong><p>{step.text}</p>{step.detail && <ul>{step.detail.map((d) => <li key={d}>{d}</li>)}</ul>}</div>
      </li>)}</ol>
    </div>
  </section>
}
