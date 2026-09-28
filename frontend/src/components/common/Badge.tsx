import type { ReactNode } from 'react'

export type Tone = 'positive' | 'warning' | 'elevated' | 'negative' | 'info' | 'neutral'

// Status is always carried by text as well as colour.
export function Badge({ tone = 'neutral', children, title, className = '' }: { tone?: Tone; children: ReactNode; title?: string; className?: string }) {
  return <span className={`badge tone-${tone} ${className}`.trim()} title={title}><i aria-hidden="true" />{children}</span>
}

const SEVERITY: Record<string, Tone> = { LOW: 'neutral', MEDIUM: 'warning', HIGH: 'elevated', CRITICAL: 'negative' }
const RISK: Record<string, Tone> = { LOW: 'positive', MODERATE: 'warning', ELEVATED: 'elevated', HIGH: 'negative' }
const FINGERPRINT: Record<string, Tone> = { normal: 'positive', mild_deviation: 'warning', elevated_deviation: 'elevated', high_deviation: 'negative', insufficient_history: 'neutral' }
export const severityTone = (severity: string): Tone => SEVERITY[severity] ?? 'neutral'
export const riskTone = (level: string): Tone => RISK[level] ?? 'neutral'
export const fingerprintTone = (level: string): Tone => FINGERPRINT[level] ?? 'neutral'
export const changeTone = (value: number | null | undefined): Tone => (value === null || value === undefined ? 'neutral' : value >= 0 ? 'positive' : 'negative')
