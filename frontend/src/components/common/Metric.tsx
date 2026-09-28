import type { ReactNode } from 'react'
import type { Tone } from './Badge'
type Props = { label: string; value: ReactNode; sub?: ReactNode; tone?: Tone; className?: string }
export function Metric({ label, value, sub, tone, className = '' }: Props) { return <div className={`metric ${className}`.trim()}><span className="metric-label">{label}</span><strong className={`metric-value${tone ? ` text-${tone}` : ''}`}>{value}</strong>{sub && <small className="metric-sub">{sub}</small>}</div> }
