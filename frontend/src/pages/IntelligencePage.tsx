import { AnomalyPanel } from '../components/intelligence/AnomalyPanel'
import { CorrelationPanel } from '../components/intelligence/CorrelationPanel'
import { EvidencePanel } from '../components/intelligence/EvidencePanel'
import { FingerprintPanel } from '../components/intelligence/FingerprintPanel'
import { IntelligenceWorkspace } from '../components/intelligence/IntelligenceWorkspace'
import { NewsPanel } from '../components/intelligence/NewsPanel'
import { RiskPanel } from '../components/intelligence/RiskPanel'
import { fmtDate } from '../utils/format'

// Only sections the backend actually returns (no Financials tab: there is no fundamentals endpoint).
const SECTIONS = [{ id: 'overview', label: 'Overview' }, { id: 'behaviour', label: 'Behaviour' }, { id: 'anomaly', label: 'Price & anomaly' }, { id: 'news', label: 'News' }, { id: 'correlation', label: 'Correlation' }, { id: 'risk', label: 'Risk' }, { id: 'evidence', label: 'Evidence' }]

export function IntelligencePage() {
  return <main id="main" className="page page-intelligence"><div className="wrap">
    <header className="page-intro"><p className="eyebrow">AVENTRA INTELLIGENCE</p><h1 className="display-title">What changed, how unusual it is, and <em>what else was happening.</em></h1>
      <p className="section-intro">Market data, behavioural fingerprint, anomaly detection, news sentiment, cross-source correlation, risk and evidence, computed by the Aventra pipeline for the selected instrument.</p></header>
    <IntelligenceWorkspace sections={SECTIONS}>{({ data, focus, setFocus }) => <div className="ws-grid">
      <FingerprintPanel id="behaviour" fingerprint={data.fingerprint} />
      <AnomalyPanel id="anomaly" data={data} focus={focus} onFocus={setFocus} />
      <NewsPanel id="news" news={data.news} timeZone={data.asset.timezone} />
      <CorrelationPanel id="correlation" assessment={focus} timeZone={data.asset.timezone} />
      <RiskPanel id="risk" risk={focus.risk} title={`Risk signal · ${fmtDate(focus.trading_date)}`} />
      <EvidencePanel id="evidence" assessment={focus} timeZone={data.asset.timezone} />
    </div>}</IntelligenceWorkspace>
  </div></main>
}
