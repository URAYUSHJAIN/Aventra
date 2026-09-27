import type { Assessment, Intelligence } from '../../types/api'
import { fmtDate, fmtPrice, fmtScore } from '../../utils/format'
import { LineChart } from './LineChart'

const DETECTORS: Array<[keyof Assessment['anomaly']['scores'], string]> = [['statistical', 'Statistical z-score'], ['fingerprint', 'Behavioural fingerprint'], ['isolation_forest', 'Isolation Forest']]

export function AnomalyPanel({ data, focus, onFocus }: { data: Intelligence; focus: Assessment; onFocus?: (eventId: string) => void }) {
  const anomaly = focus.anomaly
  return <section className="intel-panel" aria-labelledby="anomaly-title">
    <header className="intel-panel-head"><div><p className="eyebrow">ANOMALY DETECTION</p><h2 id="anomaly-title">Price with detected anomalies</h2></div>
      <div className={`level-chip severity-${anomaly.severity.toLowerCase()}`}>{anomaly.severity}<small>{fmtDate(anomaly.trading_date)} · score {fmtScore(anomaly.anomaly_score)}</small></div></header>
    <LineChart ariaLabel={`${data.symbol} closing price over the scoring window with flagged anomalies marked`} format={fmtPrice}
      points={data.market.series.map((p) => ({ label: p.date, value: p.close, highlight: p.is_anomaly }))} />
    <div className="detector-grid">{DETECTORS.map(([key, label]) => <div key={key} className="detector"><span>{label}</span><strong>{fmtScore(anomaly.scores[key])}</strong><i><b style={{ width: `${(anomaly.scores[key] ?? 0) * 100}%` }} /></i></div>)}
      <div className="detector"><span>Detector agreement</span><strong>{fmtScore(anomaly.model_agreement)}</strong><i><b style={{ width: `${anomaly.model_agreement * 100}%` }} /></i></div></div>
    {anomaly.contributing_features.length > 0 ? <ul className="feature-list">{anomaly.contributing_features.map((f) => <li key={f.feature}><strong>{f.label}</strong> {f.explanation}</li>)}</ul>
      : <p className="intel-empty">No behavioural dimension deviated beyond 2 robust standard deviations in this session.</p>}
    <div className="flagged-list"><h3>Flagged sessions ({data.anomaly.flagged_count}) · threshold {data.anomaly.threshold}</h3>
      {data.events.length === 0 ? <p className="intel-empty">No session in the scoring window ({fmtDate(data.anomaly.window.start)} – {fmtDate(data.anomaly.window.end)}) reached the threshold.</p>
        : <div className="flagged-chips">{data.events.map((e) => <button type="button" key={e.event_id} className={e.event_id === focus.event_id ? 'active' : ''} aria-pressed={e.event_id === focus.event_id} onClick={() => onFocus?.(e.event_id)}>
          {fmtDate(e.trading_date)} <b className={`severity-${e.anomaly.severity.toLowerCase()}`}>{e.anomaly.severity}</b></button>)}</div>}
    </div>
    {data.anomaly.change_points.change_points.length > 0 && <p className="intel-note">Retrospective regime boundaries (PELT, uses the whole window): {data.anomaly.change_points.change_points.map(fmtDate).join(', ')}.</p>}
    <p className="intel-note">Isolation Forest is fitted only on sessions before {fmtDate(data.anomaly.window.start)}; thresholds are uncalibrated defaults.</p>
  </section>
}
