import type { FingerprintDimension } from '../../types/api'
import { fmtSigned } from '../../utils/format'

// Radial signature of the behavioural fingerprint, drawn from the API's robust z-scores. Each spoke is one dimension; its distance
// from the centre is |robust z| against the asset's own baseline. The shaded band is the |z| < 2 envelope the fingerprint treats as normal.
const SIZE = 320, C = SIZE / 2, INNER = 24, OUTER = 118, MAX_Z = 8

const radius = (z: number) => INNER + (Math.min(Math.abs(z), MAX_Z) / MAX_Z) * (OUTER - INNER)
const zTone = (z: number) => { const a = Math.abs(z); return a >= 6 ? 'negative' : a >= 4 ? 'elevated' : a >= 2 ? 'warning' : 'positive' }

export function FingerprintGlyph({ dimensions, selected }: { dimensions: FingerprintDimension[]; selected?: string }) {
  const n = dimensions.length
  if (n < 3) return null
  const angle = (i: number) => -Math.PI / 2 + (i / n) * Math.PI * 2
  const ringAngle = angle(0) + Math.PI / n   // ring labels sit between the first two spokes, clear of dimension labels
  const at = (i: number, r: number) => [C + Math.cos(angle(i)) * r, C + Math.sin(angle(i)) * r] as const
  const measured = dimensions.map((d, i) => ({ d, i })).filter(({ d }) => typeof d.robust_z === 'number')
  const shape = measured.map(({ d, i }) => at(i, radius(d.robust_z as number)).join(',')).join(' ')
  const worst = Math.max(0, ...measured.map(({ d }) => Math.abs(d.robust_z as number)))
  const summary = dimensions.map((d) => `${d.label} ${d.robust_z === null ? 'unavailable' : `${fmtSigned(d.robust_z, 1)} robust z`}`).join('; ')

  return <figure className="fp-glyph">
    <svg viewBox={`-54 -14 ${SIZE + 108} ${SIZE + 28}`} role="img" aria-label={`Behavioural fingerprint signature. ${summary}. Values inside |z| < 2 are within the asset's normal range.`}>
      <circle className="fp-envelope" cx={C} cy={C} r={radius(2)} />
      {[2, 4, 6, 8].map((z) => <g key={z}><circle className={`fp-ring${z === 2 ? ' fp-ring-normal' : ''}`} cx={C} cy={C} r={radius(z)} /><text className="fp-ring-label" x={C + Math.cos(ringAngle) * radius(z)} y={C + Math.sin(ringAngle) * radius(z) - 3} textAnchor="middle">{z === 8 ? '≥8' : z}</text></g>)}
      {dimensions.map((d, i) => { const [x, y] = at(i, OUTER); return <line key={d.feature} className={`fp-spoke${d.feature === selected ? ' is-selected' : ''}`} x1={C} y1={C} x2={x} y2={y} /> })}
      {shape && <polygon className={`fp-shape tone-${zTone(worst)}`} points={shape} />}
      {measured.map(({ d, i }) => { const [x, y] = at(i, radius(d.robust_z as number)); return <circle key={d.feature} className={`fp-point tone-${zTone(d.robust_z as number)}${d.feature === selected ? ' is-selected' : ''}`} cx={x} cy={y} r={d.feature === selected ? 6 : 4.5} /> })}
      {dimensions.map((d, i) => {
        const [x, y] = at(i, OUTER + 18), cos = Math.cos(angle(i)), anchor = Math.abs(cos) < 0.2 ? 'middle' : cos > 0 ? 'start' : 'end'
        return <text key={d.feature} className={`fp-label${d.feature === selected ? ' is-selected' : ''}`} x={x} y={y} textAnchor={anchor} dominantBaseline="middle">
          <tspan x={x}>{d.label}</tspan><tspan x={x} dy="13" className={`fp-label-z tone-${d.robust_z === null ? 'neutral' : zTone(d.robust_z)}`}>{d.robust_z === null ? 'n/a' : `z ${fmtSigned(d.robust_z, 1)}`}</tspan></text>
      })}
    </svg>
    <figcaption>Distance from centre = |robust z| against this asset’s own baseline. Shaded band: |z| &lt; 2 (normal).</figcaption>
  </figure>
}
