import type { Assessment, Intelligence } from '../../types/api'
import { fmtDate, fmtLevel, fmtScore } from '../../utils/format'
import { Badge, severityTone } from '../common/Badge'
import { Panel } from '../common/Panel'
import { LineChart } from './LineChart'

const DETECTORS: Array<[keyof Assessment['anomaly']['scores'], string]> = [['statistical', 'Statistical z-score'], ['fingerprint', 'Behavioural fingerprint'], ['isolation_forest', 'Isolation Forest']]

export function AnomalyPanel({ data, focus, onFocus, id }: { data: Intelligence; focus: Assessment; onFocus?: (eventId: string) => void; id?: string }) {
  const anomaly = focus.anomaly
  const kind = data.capabilities.value_kind === 'price' ? 'Price' : data.capabilities.value_kind === 'nav' ? 'NAV' : 'Series'
  return <Panel id={id} className="panel-anomaly" eyebrow="PRICE & ANOMALY DETECTION" titleId="anomaly-title" title={`${kind} with detected anomalies`}
    aside={<><Badge tone={severityTone(anomaly.severity)}>{anomaly.severity}</Badge><small className="panel-aside-note">{fmtDate(anomaly.trading_date)} · score {fmtScore(anomaly.anomaly_score)}</small></>}>
    <LineChart ariaLabel={`${data.symbol} daily series over the scoring window with flagged anomalies marked`} format={(v) => fmtLevel(v, data.capabilities.value_kind, data.asset.currency)}
      focusLabel={focus.trading_date} points={data.market.series.map((p) => ({ label: p.date, value: p.close, highlight: p.is_anomaly }))} />
    <div className="detectors">{DETECTORS.map(([key, label]) => <div key={key} className="detector"><span>{label}</span><strong>{fmtScore(anomaly.scores[key])}</strong><i aria-hidden="true"><b style={{ width: `${(anomaly.scores[key] ?? 0) * 100}%` }} /></i></div>)}
      <div className="detector"><span>Detector agreement</span><strong>{fmtScore(anomaly.model_agreement)}</strong><i aria-hidden="true"><b style={{ width: `${anomaly.model_agreement * 100}%` }} /></i></div></div>
    {anomaly.contributing_features.length > 0 ? <ul className="feature-list">{anomaly.contributing_features.map((f) => <li key={f.feature}><strong>{f.label}</strong> {f.explanation}</li>)}</ul>
      : <p className="empty-note">No behavioural dimension deviated beyond 2 robust standard deviations in this session.</p>}
    <div className="flagged"><h3>Flagged sessions ({data.anomaly.flagged_count}) · threshold {data.anomaly.threshold}</h3>
      {data.events.length === 0 ? <p className="empty-note">No session in the scoring window ({fmtDate(data.anomaly.window.start)} – {fmtDate(data.anomaly.window.end)}) reached the threshold.</p>
        : <div className="flagged-chips">{data.events.map((e) => <button type="button" key={e.event_id} className={e.event_id === focus.event_id ? 'is-active' : ''} aria-pressed={e.event_id === focus.event_id} onClick={() => onFocus?.(e.event_id)}>
          {fmtDate(e.trading_date)} <b className={`text-${severityTone(e.anomaly.severity)}`}>{e.anomaly.severity}</b></button>)}</div>}
    </div>
    {data.anomaly.change_points.change_points.length > 0 && <p className="note">Retrospective regime boundaries (PELT, uses the whole window): {data.anomaly.change_points.change_points.map(fmtDate).join(', ')}.</p>}
    <p className="note">Isolation Forest is fitted only on sessions before {fmtDate(data.anomaly.window.start)}; thresholds are uncalibrated defaults.</p>
  </Panel>
}
