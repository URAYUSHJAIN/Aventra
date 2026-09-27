// Dependency-free SVG line chart with an optional baseline band and highlighted points.
export interface ChartPoint { label: string; value: number | null; lower?: number | null; upper?: number | null; highlight?: boolean }

const W = 800
const H = 220
const PAD = 8

export function LineChart({ points, ariaLabel, format = (v: number) => v.toFixed(2), bandLabel }: { points: ChartPoint[]; ariaLabel: string; format?: (value: number) => string; bandLabel?: string }) {
  const values = points.flatMap((p) => [p.value, p.lower, p.upper]).filter((v): v is number => typeof v === 'number' && Number.isFinite(v))
  if (points.length < 2 || values.length === 0) return <p className="intel-empty">Not enough data to draw this chart.</p>
  const low = Math.min(...values), high = Math.max(...values), range = high - low || 1
  const x = (i: number) => PAD + (i / (points.length - 1)) * (W - 2 * PAD)
  const y = (v: number) => H - PAD - ((v - low) / range) * (H - 2 * PAD)
  const line = (key: 'value' | 'lower' | 'upper') => points.map((p, i) => (typeof p[key] === 'number' ? `${x(i)},${y(p[key] as number)}` : null)).filter(Boolean).join(' ')
  const band = points.every((p) => typeof p.lower === 'number' && typeof p.upper === 'number')
    ? `M ${points.map((p, i) => `${x(i)},${y(p.upper as number)}`).join(' L ')} L ${[...points].reverse().map((p, i) => `${x(points.length - 1 - i)},${y(p.lower as number)}`).join(' L ')} Z` : null
  const highlighted = points.map((p, i) => ({ p, i })).filter(({ p }) => p.highlight && typeof p.value === 'number')
  return <figure className="line-chart">
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={ariaLabel}>
      {[0.25, 0.5, 0.75].map((f) => <line key={f} className="chart-grid" x1={0} x2={W} y1={H * f} y2={H * f} />)}
      {band && <path className="chart-band" d={band} />}
      <polyline className="chart-series" points={line('value')} />
      {highlighted.map(({ p, i }) => <circle key={i} className="chart-marker" cx={x(i)} cy={y(p.value as number)} r={6}><title>{`${p.label}: ${format(p.value as number)}`}</title></circle>)}
    </svg>
    <figcaption className="chart-caption"><span>{points[0].label}</span><span>{format(low)} – {format(high)}{band && bandLabel ? ` · shaded: ${bandLabel}` : ''}</span><span>{points[points.length - 1].label}</span></figcaption>
  </figure>
}
