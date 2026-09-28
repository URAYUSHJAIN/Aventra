import { ArrowLeft, ArrowRight } from 'lucide-react'
import { AnomalyPanel } from '../components/intelligence/AnomalyPanel'
import { CorrelationPanel } from '../components/intelligence/CorrelationPanel'
import { EvidencePanel } from '../components/intelligence/EvidencePanel'
import { FingerprintPanel } from '../components/intelligence/FingerprintPanel'
import { IntelligenceWorkspace } from '../components/intelligence/IntelligenceWorkspace'
import { NewsPanel } from '../components/intelligence/NewsPanel'
import { RiskPanel } from '../components/intelligence/RiskPanel'
import { services } from '../data/services'

export type Capability = 'fingerprint' | 'anomaly' | 'correlation' | 'risk'

const configurations = {
  fingerprint: { href: '/behavioural-fingerprint', title: <>Build an asset-specific <em>market baseline.</em></>, output: 'A deviation score per dimension, a behavioural level and the baseline series.', intro: 'Each behavioural dimension is compared with the asset’s own rolling median/MAD baseline. The baseline adapts over time, but extreme sessions enter it clipped so one event cannot redefine “normal”.' },
  anomaly: { href: '/anomaly-detection', title: <>Surface unusual movement <em>with context.</em></>, output: 'An ensemble score, a severity, the detectors’ agreement and the contributing features.', intro: 'A statistical z-score, the behavioural fingerprint and an Isolation Forest trained only on earlier sessions are combined into one anomaly score, with the contributing features listed.' },
  correlation: { href: '/event-correlation', title: <>Connect events across <em>time and sources.</em></>, output: 'Aligned articles with timing, asset match, sentiment and a correlation score.', intro: 'Flagged sessions are matched with asset-linked news published in a configurable window around the session, scored for temporal proximity, entity match, sentiment and anomaly strength.' },
  risk: { href: '/risk-evidence', title: <>Make the risk signal <em>explainable.</em></>, output: 'A score out of 100 with exact per-component contributions and a timestamped evidence chain.', intro: 'A transparent weighted risk score with its exact per-component contributions and a timestamped evidence chain. Analytical signal only: not investment advice or a market prediction.' },
} satisfies Record<Capability, { href: string; title: React.ReactNode; intro: string; output: string }>

export function CapabilityPage({ capability }: { capability: Capability }) {
  const config = configurations[capability]
  const service = services.find((s) => s.href === config.href)!
  const index = services.indexOf(service), next = services[(index + 1) % services.length]
  return <main id="main" className="page page-capability"><div className="wrap">
    <header className="capability-intro">
      <div><p className="eyebrow"><span className="capability-number">{service.number}</span> {service.title.toUpperCase()}</p><h1 className="display-title">{config.title}</h1></div>
      <div className="capability-facts">
        <p>{config.intro}</p>
        <dl><div><dt>Why it matters</dt><dd>{service.why}</dd></div><div><dt>Output</dt><dd>{config.output}</dd></div></dl>
        <p className="capability-links"><a className="text-link" href="/#services"><ArrowLeft size={14} aria-hidden="true" /> All capabilities</a><a className="text-link" href={`/intelligence${window.location.search}`}>Open the full intelligence dashboard <ArrowRight size={14} aria-hidden="true" /></a></p>
      </div>
    </header>
    <IntelligenceWorkspace>{({ data, focus, setFocus }) => <div className="ws-grid">
      {capability === 'fingerprint' && <div className="span-all"><FingerprintPanel fingerprint={data.fingerprint} /></div>}
      {capability === 'anomaly' && <div className="span-all"><AnomalyPanel data={data} focus={focus} onFocus={setFocus} /></div>}
      {capability === 'correlation' && <><CorrelationPanel assessment={focus} timeZone={data.asset.timezone} /><NewsPanel news={data.news} timeZone={data.asset.timezone} /></>}
      {capability === 'risk' && <><RiskPanel risk={focus.risk} /><EvidencePanel assessment={focus} timeZone={data.asset.timezone} /></>}
    </div>}</IntelligenceWorkspace>
    <a className="next-capability" href={next.href}><span>Next · {next.number}</span><strong>{next.title}</strong><ArrowRight size={18} aria-hidden="true" /></a>
  </div></main>
}
