import { AnomalyPanel } from '../components/intelligence/AnomalyPanel'
import { CorrelationPanel } from '../components/intelligence/CorrelationPanel'
import { EvidencePanel } from '../components/intelligence/EvidencePanel'
import { FingerprintPanel } from '../components/intelligence/FingerprintPanel'
import { IntelligenceWorkspace } from '../components/intelligence/IntelligenceWorkspace'
import { NewsPanel } from '../components/intelligence/NewsPanel'
import { RiskPanel } from '../components/intelligence/RiskPanel'
import { fmtDate } from '../utils/format'

export function IntelligencePage() {
  return <main className="intel-page"><div className="container">
    <header className="intel-hero"><p className="eyebrow">AVENTRA INTELLIGENCE</p><h1 className="section-title">What changed, how unusual it is, and what else was happening.</h1>
      <p className="section-intro">Market data, behavioural fingerprint, anomaly detection, FinBERT news sentiment, cross-source correlation, risk and evidence — computed by the Aventra pipeline for the selected asset.</p></header>
    <IntelligenceWorkspace>{({ data, focus, setFocus }) => <div className="intel-grid">
      <div className="span-2"><AnomalyPanel data={data} focus={focus} onFocus={setFocus} /></div>
      <RiskPanel risk={focus.risk} title={`Risk signal · ${fmtDate(focus.trading_date)}`} />
      <FingerprintPanel fingerprint={data.fingerprint} />
      <NewsPanel news={data.news} timeZone={data.asset.timezone} />
      <CorrelationPanel assessment={focus} />
      <div className="span-2"><EvidencePanel assessment={focus} /></div>
    </div>}</IntelligenceWorkspace>
  </div></main>
}
