import { Activity, BrainCircuit, ChartNoAxesCombined, Waypoints } from 'lucide-react'
import { AnomalyPanel } from '../components/intelligence/AnomalyPanel'
import { CorrelationPanel } from '../components/intelligence/CorrelationPanel'
import { EvidencePanel } from '../components/intelligence/EvidencePanel'
import { FingerprintPanel } from '../components/intelligence/FingerprintPanel'
import { IntelligenceWorkspace } from '../components/intelligence/IntelligenceWorkspace'
import { NewsPanel } from '../components/intelligence/NewsPanel'
import { RiskPanel } from '../components/intelligence/RiskPanel'

export type Capability = 'fingerprint' | 'anomaly' | 'correlation' | 'risk'

const configurations = {
  fingerprint: { eyebrow: 'ADAPTIVE BEHAVIOURAL FINGERPRINTING', title: 'Build an asset-specific market baseline.', intro: 'Each behavioural dimension is compared with the asset’s own rolling median/MAD baseline. The baseline adapts over time, but extreme sessions enter it clipped so one event cannot redefine “normal”.', icon: BrainCircuit },
  anomaly: { eyebrow: 'MULTI-SOURCE ANOMALY DETECTION', title: 'Surface unusual movement with context.', intro: 'A statistical z-score, the behavioural fingerprint and an Isolation Forest trained only on earlier sessions are combined into one anomaly score, with the contributing features listed.', icon: Activity },
  correlation: { eyebrow: 'CROSS-SOURCE EVENT CORRELATION', title: 'Connect events across time and sources.', intro: 'Flagged sessions are matched with asset-linked news published in a configurable window around the session, scored for temporal proximity, entity match, sentiment and anomaly strength.', icon: Waypoints },
  risk: { eyebrow: 'RISK SCORING & EVIDENCE CHAIN', title: 'Make the risk signal explainable.', intro: 'A transparent weighted risk score with its exact per-component contributions and a timestamped evidence chain. Analytical signal only — not investment advice or a market prediction.', icon: ChartNoAxesCombined },
} satisfies Record<Capability, { eyebrow: string; title: string; intro: string; icon: typeof BrainCircuit }>

export function CapabilityPage({ capability }: { capability: Capability }) {
  const config = configurations[capability]; const Icon = config.icon
  return <main className="intel-page"><div className="container">
    <header className="intel-hero"><p className="eyebrow"><Icon size={14} /> {config.eyebrow}</p><h1 className="section-title">{config.title}</h1><p className="section-intro">{config.intro}</p>
      <p className="intel-links"><a className="back-link" href="/#services">← Back to services</a> <a className="back-link" href={`/intelligence${window.location.search}`}>Open the full intelligence dashboard →</a></p></header>
    <IntelligenceWorkspace>{({ data, focus, setFocus }) => <div className="intel-grid">
      {capability === 'fingerprint' && <div className="span-2"><FingerprintPanel fingerprint={data.fingerprint} /></div>}
      {capability === 'anomaly' && <div className="span-2"><AnomalyPanel data={data} focus={focus} onFocus={setFocus} /></div>}
      {capability === 'correlation' && <><CorrelationPanel assessment={focus} /><NewsPanel news={data.news} timeZone={data.asset.timezone} /></>}
      {capability === 'risk' && <><RiskPanel risk={focus.risk} /><EvidencePanel assessment={focus} /></>}
    </div>}</IntelligenceWorkspace>
  </div></main>
}
