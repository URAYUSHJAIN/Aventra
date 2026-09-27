const compact = new Intl.NumberFormat('en-IN', { notation: 'compact', maximumFractionDigits: 1 })
const price = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 })
const dateTime = new Intl.DateTimeFormat('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Kolkata' })
const date = new Intl.DateTimeFormat('en-IN', { day: '2-digit', month: 'short', year: 'numeric', timeZone: 'Asia/Kolkata' })

export const fmtPrice = (value: number | null | undefined) => (value === null || value === undefined ? '—' : `₹${price.format(value)}`)
export const fmtCompact = (value: number | null | undefined) => (value === null || value === undefined ? '—' : compact.format(value))
export const fmtPct = (fraction: number | null | undefined, digits = 2) => (fraction === null || fraction === undefined ? '—' : `${fraction >= 0 ? '+' : ''}${(fraction * 100).toFixed(digits)}%`)
export const fmtScore = (value: number | null | undefined, digits = 2) => (value === null || value === undefined ? '—' : value.toFixed(digits))
export const fmtSigned = (value: number | null | undefined, digits = 2) => (value === null || value === undefined ? '—' : `${value >= 0 ? '+' : ''}${value.toFixed(digits)}`)
// Timestamps are UTC in the API; they are displayed in exchange time (IST).
export const fmtDateTime = (iso: string | null | undefined) => (iso ? `${dateTime.format(new Date(iso))} IST` : '—')
export const fmtDate = (isoDate: string | null | undefined) => (isoDate ? date.format(new Date(`${isoDate}T00:00:00+05:30`)) : '—')

export function fmtDimension(value: number | null | undefined, unit: 'shares' | 'fraction') {
  return unit === 'shares' ? fmtCompact(value) : fmtPct(value)
}

export function relationText(relation: string, hours: number) {
  if (relation === 'published_during_session') return 'during the session'
  if (relation === 'published_before_session') return `${Math.abs(hours).toFixed(1)} h before the open`
  return `${hours.toFixed(1)} h after the close`
}
