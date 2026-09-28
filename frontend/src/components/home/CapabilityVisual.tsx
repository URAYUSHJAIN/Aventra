import type { ServiceVisual } from '../../data/services'

// Schematic diagrams of how each capability reasons. They illustrate the method, not data (the section says so).
const RISK_SEGMENTS: Array<[number, number]> = [[0, 58], [58, 36], [94, 30], [124, 22], [146, 12]]
export function CapabilityVisual({ kind }: { kind: ServiceVisual }) {
  if (kind === 'fingerprint') return <svg className="cap-visual" viewBox="0 0 240 200" aria-hidden="true">
    <circle cx="120" cy="100" r="46" className="cv-band" />
    {[30, 46, 66, 86].map((r) => <circle key={r} cx="120" cy="100" r={r} className="cv-ring" />)}
    {[0, 1, 2, 3, 4, 5].map((i) => { const a = -Math.PI / 2 + (i / 6) * Math.PI * 2; return <line key={i} x1="120" y1="100" x2={120 + Math.cos(a) * 88} y2={100 + Math.sin(a) * 88} className="cv-ring" /> })}
    <polygon points="120,62 152,82 151,118 120,136 92,120 64,68" className="cv-shape" />
    <circle cx="64" cy="68" r="5" className="cv-alert" /><circle cx="120" cy="62" r="3.5" className="cv-dot" /><circle cx="152" cy="82" r="3.5" className="cv-dot" /><circle cx="151" cy="118" r="3.5" className="cv-dot" /><circle cx="120" cy="136" r="3.5" className="cv-dot" /><circle cx="92" cy="120" r="3.5" className="cv-dot" />
  </svg>
  if (kind === 'anomaly') return <svg className="cap-visual" viewBox="0 0 240 160" aria-hidden="true">
    <line x1="10" x2="230" y1="46" y2="46" className="cv-threshold" /><text x="230" y="40" textAnchor="end" className="cv-label">threshold</text>
    <polyline points="10,112 30,104 50,110 70,98 90,106 110,100 130,108 148,96 160,30 172,102 190,94 210,100 230,92" className="cv-line" />
    <circle cx="160" cy="30" r="6" className="cv-alert" />
    <g className="cv-bars">{[0, 1, 2].map((i) => <rect key={i} x={132 + i * 20} y={128} width="14" height={8 + i * 6} rx="2" />)}</g>
  </svg>
  if (kind === 'news') return <svg className="cap-visual" viewBox="0 0 240 160" aria-hidden="true">
    {[0, 1, 2, 3].map((i) => <g key={i} transform={`translate(12 ${18 + i * 34})`}><rect width={150 - i * 18} height="7" rx="3.5" className="cv-text" /><rect y="13" width={96 - i * 10} height="5" rx="2.5" className="cv-text dim" />
      <circle cx="206" cy="7" r="7" className={i === 1 ? 'cv-neg' : i === 3 ? 'cv-neutral' : 'cv-dot'} /></g>)}
  </svg>
  if (kind === 'correlation') return <svg className="cap-visual" viewBox="0 0 280 160" aria-hidden="true">
    <rect x="118" y="14" width="74" height="132" rx="4" className="cv-window" /><text x="155" y="156" textAnchor="middle" className="cv-label">window</text>
    <polyline points="10,58 40,52 70,60 100,54 130,58 150,20 166,56 200,50 230,56 270,52" className="cv-line" /><circle cx="150" cy="20" r="5" className="cv-alert" />
    <line x1="10" x2="270" y1="112" y2="112" className="cv-ring" />
    {[42, 138, 172, 238].map((x) => <rect key={x} x={x - 5} y="105" width="10" height="14" rx="2" className={x === 138 || x === 172 ? 'cv-doc is-in' : 'cv-doc'} />)}
    <line x1="150" y1="26" x2="138" y2="104" className="cv-link" /><line x1="150" y1="26" x2="172" y2="104" className="cv-link" />
  </svg>
  return <svg className="cap-visual" viewBox="0 0 240 150" aria-hidden="true">
    {RISK_SEGMENTS.map(([x, width], i) => <rect key={i} x={12 + x} y="54" width={width - 2} height="26" rx="3" className={`cv-s${i}`} />)}
    <line x1="170" x2="170" y1="40" y2="96" className="cv-threshold" />
    {[0, 1, 2, 3, 4].map((i) => <g key={i} transform={`translate(${12 + i * 44} 112)`}><rect width="8" height="8" rx="2" className={`cv-s${i}`} /><rect x="13" y="1.5" width="24" height="5" rx="2.5" className="cv-text dim" /></g>)}
  </svg>
}
