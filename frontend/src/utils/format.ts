// Formatting helpers. Currency and timezone come from the instrument (API), never from hard-coded assumptions.
import type { DimensionUnit, ValueKind } from '../types/api'

const compact = new Intl.NumberFormat(undefined, { notation: 'compact', maximumFractionDigits: 1 })
const plain = new Intl.NumberFormat(undefined, { maximumFractionDigits: 6 })
const moneyFormatters = new Map<string, Intl.NumberFormat>()

function moneyFormatter(currency: string, value: number) {
  const digits = Math.abs(value) >= 1000 ? 2 : Math.abs(value) >= 1 ? 4 : 8
  const key = `${currency}:${digits}`
  if (!moneyFormatters.has(key)) {
    try { moneyFormatters.set(key, new Intl.NumberFormat(undefined, { style: 'currency', currency, maximumFractionDigits: digits })) }
    catch { return null }   // non-ISO quote assets (e.g. USDT) are shown as "1,234.5 USDT"
  }
  return moneyFormatters.get(key)!
}

/** Money in the instrument's own currency (ISO codes via Intl; crypto quote assets as a suffix). */
export function fmtMoney(value: number | null | undefined, currency: string | null | undefined) {
  if (value === null || value === undefined) return 'n/a'
  if (!currency) return plain.format(value)
  const formatter = moneyFormatter(currency, value)
  return formatter ? formatter.format(value) : `${plain.format(value)} ${currency}`
}

/** A level in the instrument's value kind: price/NAV/rate as money, yields as %, index levels as plain numbers. */
export function fmtLevel(value: number | null | undefined, valueKind: ValueKind | undefined, currency: string | null | undefined) {
  if (value === null || value === undefined) return 'n/a'
  if (valueKind === 'yield') return `${value.toFixed(3)}%`
  if (valueKind === 'index_level' || valueKind === 'reference_rate') return plain.format(Number(value.toFixed(6)))
  return fmtMoney(value, currency)
}

export const fmtCompact = (value: number | null | undefined) => (value === null || value === undefined ? 'n/a' : compact.format(value))
export const fmtPct = (fraction: number | null | undefined, digits = 2) => (fraction === null || fraction === undefined ? 'n/a' : `${fraction >= 0 ? '+' : ''}${(fraction * 100).toFixed(digits)}%`)
export const fmtBp = (bp: number | null | undefined) => (bp === null || bp === undefined ? 'n/a' : `${bp >= 0 ? '+' : ''}${bp.toFixed(1)} bp`)
export const fmtScore = (value: number | null | undefined, digits = 2) => (value === null || value === undefined ? 'n/a' : value.toFixed(digits))
/** Risk score as an integer, rounded half-to-even like the backend's explanation text (Python `:.0f`), so both always agree. */
export function fmtRiskScore(score: number) {
  const floor = Math.floor(score), diff = score - floor
  return String(Math.abs(diff - 0.5) < 1e-9 ? (floor % 2 === 0 ? floor : floor + 1) : Math.round(score))
}
/** Unsigned percentage for magnitudes such as volatility. */
export const fmtPctAbs = (fraction: number | null | undefined, digits = 2) => (fraction === null || fraction === undefined ? 'n/a' : `${(fraction * 100).toFixed(digits)}%`)
export const fmtSigned = (value: number | null | undefined, digits = 2) => (value === null || value === undefined ? 'n/a' : `${value >= 0 ? '+' : ''}${value.toFixed(digits)}`)

/** API timestamps are UTC; shown in the instrument's exchange timezone (or UTC for 24/7 markets). */
export function fmtDateTime(iso: string | null | undefined, timeZone: string | null | undefined = 'UTC') {
  if (!iso) return 'n/a'
  try {
    return new Intl.DateTimeFormat(undefined, { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', timeZone: timeZone || 'UTC', timeZoneName: 'short' }).format(new Date(iso))
  } catch { return new Date(iso).toISOString() }
}

/** Trading dates (YYYY-MM-DD) are already local exchange dates: format them without a timezone shift. */
export function fmtDate(isoDate: string | null | undefined) {
  if (!isoDate) return 'n/a'
  return new Intl.DateTimeFormat(undefined, { day: '2-digit', month: 'short', year: 'numeric', timeZone: 'UTC' }).format(new Date(`${isoDate}T00:00:00Z`))
}

export function fmtDimension(value: number | null | undefined, unit: DimensionUnit) {
  if (unit === 'shares') return fmtCompact(value)
  if (unit === 'bp') return value === null || value === undefined ? 'n/a' : `${value.toFixed(1)} bp`
  return fmtPct(value)
}

export function relationText(relation: string, hours: number) {
  if (relation === 'published_during_session') return 'during the session'
  if (relation === 'published_before_session') return `${Math.abs(hours).toFixed(1)} h before the open`
  return `${hours.toFixed(1)} h after the close`
}

export const ASSET_CLASS_LABEL: Record<string, string> = {
  equity: 'Equity', etf: 'ETF', reit: 'REIT', invit: 'InvIT', bond: 'Bond', index: 'Index', mutual_fund: 'Mutual fund', forex: 'Forex',
  crypto: 'Crypto', rate: 'Rate', commodity: 'Commodity',
}
