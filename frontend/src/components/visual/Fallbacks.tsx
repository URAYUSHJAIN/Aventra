// Static SVG stand-ins for the WebGL scenes (no WebGL, jsdom, or while the scene module loads).
export function FieldFallback() {
  return <svg className="scene-fallback" viewBox="0 0 400 400" aria-hidden="true">
    <g fill="none" stroke="var(--scene-line)" strokeWidth="1">
      <circle cx="200" cy="200" r="120" />
      {[20, 45, 70, 95].map((ry) => <ellipse key={`h${ry}`} cx="200" cy="200" rx="120" ry={ry} />)}
      {[25, 55, 85, 110].map((rx) => <ellipse key={`v${rx}`} cx="200" cy="200" rx={rx} ry="120" />)}
      <ellipse cx="200" cy="200" rx="178" ry="62" transform="rotate(-18 200 200)" opacity=".6" />
    </g>
    <circle cx="258" cy="150" r="5" fill="var(--scene-signal)" />
  </svg>
}

export function GlobeFallback() {
  return <svg className="scene-fallback" viewBox="0 0 400 400" aria-hidden="true">
    <circle cx="200" cy="200" r="140" fill="var(--scene-core)" stroke="var(--scene-line)" />
    <g fill="none" stroke="var(--scene-line)" strokeWidth="1" opacity=".7">
      {[40, 80, 120].map((ry) => <ellipse key={ry} cx="200" cy="200" rx="140" ry={ry} />)}
      {[35, 75, 115].map((rx) => <ellipse key={rx} cx="200" cy="200" rx={rx} ry="140" />)}
    </g>
    <path d="M232 168 Q 180 90 120 150" fill="none" stroke="var(--scene-signal)" strokeWidth="1.2" opacity=".8" />
    <circle cx="232" cy="168" r="4" fill="var(--scene-signal)" /><circle cx="120" cy="150" r="3" fill="var(--scene-signal)" />
  </svg>
}

export function MountainFallback() {
  const ridge = (row: number) => {
    const depth = 1 - row / 8, base = 250 + row * 12
    return Array.from({ length: 41 }, (_, i) => { const x = i * 10, d = (x - 200) / (70 + row * 12); return `${x},${(base - (Math.exp(-d * d) * 150 + Math.exp(-(((x - 262) / 40) ** 2)) * 50) * depth).toFixed(1)}` }).join(' ')
  }
  return <svg className="scene-fallback" viewBox="0 0 400 360" aria-hidden="true">
    <g fill="none" stroke="var(--scene-line)" strokeWidth="1">{Array.from({ length: 8 }, (_, row) => <polyline key={row} points={ridge(row)} opacity={0.35 + row * 0.08} />)}</g>
    <circle cx="200" cy="100" r="4" fill="var(--scene-signal)" />
  </svg>
}

export function TerrainFallback() {
  const ridge = (offset: number, amp: number) => Array.from({ length: 41 }, (_, i) => `${i * 10},${60 + offset - Math.sin(i * 0.45 + offset) * amp - (i % 13 === 5 ? amp : 0)}`).join(' ')
  return <svg className="scene-fallback" viewBox="0 0 400 160" preserveAspectRatio="none" aria-hidden="true">
    <g fill="none" stroke="var(--scene-line)" strokeWidth="1">{[0, 16, 32, 48, 64, 80].map((o, i) => <polyline key={o} points={ridge(o, 10 + i * 2)} opacity={0.3 + i * 0.1} />)}</g>
  </svg>
}
