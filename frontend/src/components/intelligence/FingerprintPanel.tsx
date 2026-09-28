import { useState } from 'react'
import type { Fingerprint } from '../../types/api'
import { fmtDimension, fmtScore, fmtSigned } from '../../utils/format'
import { Badge, fingerprintTone } from '../common/Badge'
import { Panel } from '../common/Panel'
import { FingerprintGlyph } from './FingerprintGlyph'
import { LineChart } from './LineChart'

const LEVEL_TEXT: Record<string, string> = { normal: 'Normal', mild_deviation: 'Mild deviation', elevated_deviation: 'Elevated deviation', high_deviation: 'High deviation', insufficient_history: 'Insufficient history' }

export function FingerprintPanel({ fingerprint, id }: { fingerprint: Fingerprint; id?: string }) {
  const [dim, setDim] = useState(fingerprint.dimensions.find((d) => d.feature === 'log_volume')?.feature ?? fingerprint.dimensions[0]?.feature)
  const selected = fingerprint.dimensions.find((d) => d.feature === dim)
  const series = dim ? fingerprint.series[dim] ?? [] : []
  const unit = selected?.unit ?? 'fraction'
  return <Panel id={id} className="panel-fingerprint" eyebrow="BEHAVIOURAL FINGERPRINT" titleId="fp-title" title="Current vs normal behaviour"
    aside={<><Badge tone={fingerprintTone(fingerprint.level)}>{LEVEL_TEXT[fingerprint.level] ?? fingerprint.level}</Badge><small className="panel-aside-note">deviation score {fmtScore(fingerprint.score)}</small></>}>
    {fingerprint.status === 'insufficient_history' ? <p className="empty-note">Not enough history to build a reliable fingerprint for this asset.</p> : <>
      <div className="fp-layout">
        <FingerprintGlyph dimensions={fingerprint.dimensions} selected={dim} />
        <div className="fp-detail">
          <table className="data-table fp-table"><caption className="sr-only">Behavioural dimensions compared with the asset's own baseline on {fingerprint.as_of}</caption>
            <thead><tr><th scope="col">Dimension</th><th scope="col">Current</th><th scope="col">Baseline median</th><th scope="col">Typical range (p5–p95)</th><th scope="col">Robust z</th></tr></thead>
            <tbody>{fingerprint.dimensions.map((d) => <tr key={d.feature} className={d.feature === dim ? 'is-selected' : ''}>
              <th scope="row"><button type="button" onClick={() => setDim(d.feature)} aria-pressed={d.feature === dim}>{d.label}</button></th>
              <td>{fmtDimension(d.value, d.unit)}</td><td>{fmtDimension(d.baseline_median, d.unit)}</td><td>{fmtDimension(d.p05, d.unit)} – {fmtDimension(d.p95, d.unit)}</td>
              <td><span className="z-bar" style={{ '--z': Math.min(Math.abs(d.robust_z ?? 0) / 6, 1) } as React.CSSProperties} data-dir={(d.robust_z ?? 0) >= 0 ? 'up' : 'down'}>{fmtSigned(d.robust_z, 1)}</span></td></tr>)}</tbody>
          </table>
          {selected && <div className="fp-series"><p className="chart-title">{selected.label} against its adaptive baseline</p><LineChart ariaLabel={`${selected.label} against its adaptive baseline`} bandLabel="baseline median ± 2 robust σ" height={180}
            points={series.map((p) => ({ label: p.date, value: p.value, lower: p.lower, upper: p.upper, highlight: Math.abs(p.robust_z ?? 0) >= 4 }))}
            format={(v) => fmtDimension(v, unit)} /></div>}
        </div>
      </div>
      <p className="note">Baseline: {fingerprint.method.baseline}, {fingerprint.method.window} prior sessions; extreme observations enter the baseline clipped at |z| = {fingerprint.method.guarded_update_z}. Markers show |z| ≥ 4.</p>
    </>}
  </Panel>
}
