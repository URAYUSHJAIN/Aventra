import { useId } from 'react'

// Dependency-free SVG line chart with an optional baseline band, highlighted points and a focused point.
export interface ChartPoint { label: string; value: number | null; lower?: number | null; upper?: number | null; highlight?: boolean }

const W = 800
const PAD = 10

export function LineChart({ points, ariaLabel, format = (v: number) => v.toFixed(2), bandLabel, focusLabel, height = 220, compact = false }:
  { points: ChartPoint[]; ariaLabel: string; format?: (value: number) => string; bandLabel?: string; focusLabel?: string; height?: number; compact?: boolean }) {
  const gradient = `chart-fill-${useId().replace(/:/g, '')}`
  const H = height
  const values = points.flatMap((p) => [p.value, p.lower, p.upper]).filter((v): v is number => typeof v === 'number' && Number.isFinite(v))
  if (points.length < 2 || values.length === 0) return <p className="empty-note">Not enough data to draw this chart.</p>
  const low = Math.min(...values), high = Math.max(...values), range = high - low || 1
  const x = (i: number) => PAD + (i / (points.length - 1)) * (W - 2 * PAD)
  const y = (v: number) => H - PAD - ((v - low) / range) * (H - 2 * PAD)
  const coords = points.map((p, i) => (typeof p.value === 'number' ? [x(i), y(p.value)] as const : null)).filter((c): c is readonly [number, number] => c !== null)
  const line = coords.map(([cx, cy]) => `${cx},${cy}`).join(' ')
  const area = coords.length > 1 ? `M ${coords[0][0]},${H - PAD} L ${line.replace(/ /g, ' L ')} L ${coords[coords.length - 1][0]},${H - PAD} Z` : null
  const band = points.every((p) => typeof p.lower === 'number' && typeof p.upper === 'number')
    ? `M ${points.map((p, i) => `${x(i)},${y(p.upper as number)}`).join(' L ')} L ${[...points].reverse().map((p, i) => `${x(points.length - 1 - i)},${y(p.lower as number)}`).join(' L ')} Z` : null
  const highlighted = points.map((p, i) => ({ p, i })).filter(({ p }) => p.highlight && typeof p.value === 'number')
  const focusIndex = focusLabel ? points.findIndex((p) => p.label === focusLabel) : -1
  return <figure className={`line-chart${compact ? ' is-compact' : ''}`}>
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={ariaLabel}>
      <defs><linearGradient id={gradient} x1="0" x2="0" y1="0" y2="1"><stop offset="0" className="chart-fill-top" /><stop offset="1" className="chart-fill-bottom" /></linearGradient></defs>
      {[0.25, 0.5, 0.75].map((f) => <line key={f} className="chart-grid" x1={0} x2={W} y1={H * f} y2={H * f} />)}
      {band && <path className="chart-band" d={band} />}
      {area && !band && <path d={area} fill={`url(#${gradient})`} />}
      {focusIndex >= 0 && <line className="chart-focus" x1={x(focusIndex)} x2={x(focusIndex)} y1={0} y2={H} />}
      <polyline className="chart-series" points={line} />
      {highlighted.map(({ p, i }) => <circle key={i} className={`chart-marker${i === focusIndex ? ' is-focus' : ''}`} cx={x(i)} cy={y(p.value as number)} r={i === focusIndex ? 7 : 5}><title>{`${p.label}: ${format(p.value as number)}`}</title></circle>)}
    </svg>
    {!compact && <figcaption className="chart-caption"><span>{points[0].label}</span><span>{format(low)} – {format(high)}{band && bandLabel ? ` · shaded: ${bandLabel}` : ''}</span><span>{points[points.length - 1].label}</span></figcaption>}
  </figure>
}
