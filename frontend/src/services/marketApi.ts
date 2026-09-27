import { apiGet } from './apiClient'
import type { BatchQuote, Quote } from '../types/api'

export interface Metric { label: string; value: string; tone?: 'positive' | 'negative' }
export interface MarketData { asset: string; name: string; status: string; metrics: Metric[]; points: number[]; updatedAt: string; isLive: boolean; isDemo?: boolean; source?: string }
export interface StockSearchResult { symbol: string; name: string }

export const indianStocks = [
  { symbol: 'RELIANCE', name: 'Reliance Industries' }, { symbol: 'TCS', name: 'Tata Consultancy Services' },
  { symbol: 'INFY', name: 'Infosys' }, { symbol: 'HDFCBANK', name: 'HDFC Bank' }, { symbol: 'ICICIBANK', name: 'ICICI Bank' },
]

const number = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 })
const volume = new Intl.NumberFormat('en-IN', { notation: 'compact', maximumFractionDigits: 1 })
const time = new Intl.DateTimeFormat('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })

// Shown when a quote cannot be loaded: no numbers and no chart points are invented.
export function fallback(symbol: string, name?: string): MarketData {
  const stock = indianStocks.find((item) => item.symbol === symbol) ?? { symbol, name: name ?? symbol }
  return { asset: stock.symbol, name: stock.name, status: 'MARKET DATA UNAVAILABLE', metrics: [{ label: 'Price', value: '—' }, { label: 'Daily Change', value: '—' }, { label: 'Volume', value: '—' }, { label: 'Market Status', value: 'Check source' }], points: [], updatedAt: 'Unable to connect', isLive: false }
}

export function toMarketData(quote: Quote, requestedName?: string): MarketData {
  const change = quote.change_pct
  const state = quote.market_state === 'OPEN' ? 'Open' : quote.market_state === 'DEMO' ? 'Demo data' : 'Closed'
  const status = quote.data_source.is_demo ? 'DEMO DATA · SYNTHETIC' : `LIVE QUOTE · NSE · ${state.toUpperCase()}`
  return {
    asset: quote.symbol, name: requestedName ?? quote.name, status,
    metrics: [
      { label: 'Price', value: `₹${number.format(quote.price)}` },
      { label: 'Daily Change', value: change === null ? '—' : `${change >= 0 ? '+' : ''}${change.toFixed(2)}%`, tone: change === null ? undefined : change >= 0 ? 'positive' : 'negative' },
      { label: 'Volume', value: quote.volume ? volume.format(quote.volume) : '—' },
      { label: 'Market Status', value: state },
    ],
    points: quote.intraday.map((point) => point.close), updatedAt: time.format(new Date(quote.data_source.fetched_at ?? Date.now())),
    isLive: !quote.data_source.is_demo, isDemo: quote.data_source.is_demo, source: quote.data_source.provider,
  }
}

export async function getMarketData(symbol = 'RELIANCE', requestedName?: string): Promise<MarketData> {
  return toMarketData(await apiGet<Quote>(`/api/market/${encodeURIComponent(symbol)}`), requestedName)
}

// One request for a whole watchlist; symbols the provider could not serve come back as explicit fallbacks.
export async function getWatchlist(symbols: string[]): Promise<MarketData[]> {
  const { quotes } = await apiGet<{ quotes: BatchQuote[] }>(`/api/market/quotes?symbols=${symbols.map(encodeURIComponent).join(',')}`)
  return quotes.map((item) => (item.status === 'ok' && item.quote ? toMarketData(item.quote, indianStocks.find((stock) => stock.symbol === item.symbol)?.name) : fallback(item.symbol)))
}

export async function searchStocks(query: string): Promise<StockSearchResult[]> {
  const cleanQuery = query.trim()
  if (cleanQuery.length < 2) return []
  const local = indianStocks.filter((stock) => `${stock.symbol} ${stock.name}`.toLowerCase().includes(cleanQuery.toLowerCase()))
  try {
    const { results } = await apiGet<{ results: StockSearchResult[] }>(`/api/market/search?q=${encodeURIComponent(cleanQuery)}`)
    return [...new Map([...local, ...results].map((stock) => [stock.symbol, { symbol: stock.symbol, name: stock.name }])).values()].slice(0, 8)
  } catch { return local }
}
