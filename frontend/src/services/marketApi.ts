export interface Metric { label: string; value: string; tone?: 'positive' | 'negative' }
export interface MarketData { asset: string; name: string; status: string; metrics: Metric[]; points: number[]; updatedAt: string; isLive: boolean }
export interface StockSearchResult { symbol: string; name: string }

export const indianStocks = [
  { symbol: 'RELIANCE', name: 'Reliance Industries' }, { symbol: 'TCS', name: 'Tata Consultancy Services' },
  { symbol: 'INFY', name: 'Infosys' }, { symbol: 'HDFCBANK', name: 'HDFC Bank' }, { symbol: 'ICICIBANK', name: 'ICICI Bank' },
]

type YahooChartResponse = { chart?: { result?: Array<{ meta?: { regularMarketPrice?: number; previousClose?: number; regularMarketVolume?: number; marketState?: string }; indicators?: { quote?: Array<{ close?: Array<number | null> }> } }> } }
const number = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 })
const volume = new Intl.NumberFormat('en-IN', { notation: 'compact', maximumFractionDigits: 1 })

export function fallback(symbol: string, name?: string): MarketData {
  const stock = indianStocks.find((item) => item.symbol === symbol) ?? { symbol, name: name ?? symbol }
  return { asset: stock.symbol, name: stock.name, status: 'MARKET DATA UNAVAILABLE', metrics: [{ label: 'Price', value: '—' }, { label: 'Daily Change', value: '—' }, { label: 'Volume', value: '—' }, { label: 'Market Status', value: 'Check source' }], points: [20, 24, 22, 30, 27, 35, 31, 40, 37, 46, 43, 50], updatedAt: 'Unable to connect', isLive: false }
}

export async function getMarketData(symbol = 'RELIANCE', requestedName?: string): Promise<MarketData> {
  const stock = indianStocks.find((item) => item.symbol === symbol) ?? { symbol: symbol.replace(/\.NS$/i, ''), name: requestedName ?? symbol }
  // Vite forwards this path in development. In production set VITE_MARKET_API_BASE_URL to a server-side quote proxy.
  const base = import.meta.env.VITE_MARKET_API_BASE_URL ?? '/market-api'
  const response = await fetch(`${base}/v8/finance/chart/${stock.symbol}.NS?range=1d&interval=5m`, { headers: { Accept: 'application/json' } })
  if (!response.ok) throw new Error('Quote service is unavailable')
  const payload = await response.json() as YahooChartResponse
  const quote = payload.chart?.result?.[0]
  const meta = quote?.meta
  const points = quote?.indicators?.quote?.[0]?.close?.filter((value): value is number => value !== null) ?? []
  if (!meta?.regularMarketPrice || points.length < 2) throw new Error('Quote is incomplete')
  const previousClose = meta.previousClose ?? meta.regularMarketPrice
  const change = ((meta.regularMarketPrice - previousClose) / previousClose) * 100
  const marketState = meta.marketState === 'REGULAR' ? 'Open' : meta.marketState === 'CLOSED' ? 'Closed' : meta.marketState ?? 'Unknown'
  return { asset: stock.symbol, name: stock.name, status: `LIVE QUOTE · NSE · ${marketState.toUpperCase()}`, metrics: [{ label: 'Price', value: `₹${number.format(meta.regularMarketPrice)}` }, { label: 'Daily Change', value: `${change >= 0 ? '+' : ''}${change.toFixed(2)}%`, tone: change >= 0 ? 'positive' : 'negative' }, { label: 'Volume', value: meta.regularMarketVolume ? volume.format(meta.regularMarketVolume) : '—' }, { label: 'Market Status', value: marketState }], points, updatedAt: new Intl.DateTimeFormat('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }).format(new Date()), isLive: true }
}

type YahooSearchResponse = { quotes?: Array<{ symbol?: string; shortname?: string; longname?: string; quoteType?: string }> }
export async function searchStocks(query: string): Promise<StockSearchResult[]> {
  const cleanQuery = query.trim()
  if (cleanQuery.length < 2) return []
  const local = indianStocks.filter((stock) => `${stock.symbol} ${stock.name}`.toLowerCase().includes(cleanQuery.toLowerCase()))
  const base = import.meta.env.VITE_MARKET_API_BASE_URL ?? '/market-api'
  try {
    const response = await fetch(`${base}/v1/finance/search?q=${encodeURIComponent(cleanQuery)}&quotesCount=8&newsCount=0`)
    if (!response.ok) return local
    const payload = await response.json() as YahooSearchResponse
    const remote = (payload.quotes ?? []).filter((quote) => quote.quoteType === 'EQUITY' && quote.symbol?.endsWith('.NS')).map((quote) => ({ symbol: quote.symbol!.replace(/\.NS$/i, ''), name: quote.longname ?? quote.shortname ?? quote.symbol!.replace(/\.NS$/i, '') }))
    return [...new Map([...local, ...remote].map((stock) => [stock.symbol, stock])).values()].slice(0, 8)
  } catch { return local }
}
