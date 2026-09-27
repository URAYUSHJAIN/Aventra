import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, apiGet } from './apiClient'
import { fallback, getWatchlist, toMarketData } from './marketApi'
import { analyzeNews } from './newsApi'
import { fail, mockFetch, ok } from '../test/fetchMock'
import type { Quote } from '../types/api'

const quote: Quote = {
  symbol: 'RELIANCE', name: 'Reliance Industries', currency: 'INR', price: 1200, previous_close: 1190, change_pct: 0.84, volume: 1500000, day_high: 1210, day_low: 1180,
  market_time: '2026-09-25T10:00:00Z', intraday: [{ timestamp: 't1', close: 1190 }, { timestamp: 't2', close: 1200 }], interval: '5m', market_state: 'CLOSED',
  data_source: { provider: 'yahoo_finance_chart', is_demo: false, fetched_at: '2026-09-27T10:00:00Z' },
}

afterEach(() => vi.unstubAllGlobals())

describe('apiClient', () => {
  it('unwraps the success envelope', async () => {
    mockFetch(() => ok({ value: 1 }))
    await expect(apiGet<{ value: number }>('/api/x')).resolves.toEqual({ value: 1 })
  })

  it('surfaces the server error message for client errors without retrying', async () => {
    const fetchMock = mockFetch(() => fail(404, 'NOTREAL is not in Aventra\'s analysed asset universe.'))
    await expect(apiGet('/api/intelligence/NOTREAL')).rejects.toMatchObject({ kind: 'client', status: 404, message: expect.stringContaining('NOTREAL') })
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('reports an unavailable backend and retries GET once', async () => {
    const fetchMock = mockFetch(() => 'network-error')
    const error = await apiGet('/api/health').catch((reason: unknown) => reason)
    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).kind).toBe('unavailable')
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('recovers when a retried request succeeds', async () => {
    let calls = 0
    mockFetch(() => (++calls === 1 ? fail(502, 'provider down') : ok('fine')))
    await expect(apiGet('/api/market/TCS')).resolves.toBe('fine')
  })
})

describe('marketApi', () => {
  it('maps a live quote without inventing values', () => {
    const data = toMarketData(quote)
    expect(data.status).toBe('LIVE QUOTE · NSE · CLOSED')
    expect(data.metrics[1]).toMatchObject({ value: '+0.84%', tone: 'positive' })
    expect(data.points).toEqual([1190, 1200])
    expect(data.isDemo).toBe(false)
  })

  it('labels demo data as synthetic', () => {
    expect(toMarketData({ ...quote, market_state: 'DEMO', data_source: { ...quote.data_source, is_demo: true } }).status).toBe('DEMO DATA · SYNTHETIC')
  })

  it('fallback has no chart points or numbers', () => {
    const data = fallback('TCS')
    expect(data.points).toEqual([])
    expect(data.metrics.every((metric) => metric.value === '—' || metric.value === 'Check source')).toBe(true)
  })

  it('watchlist marks unavailable symbols explicitly', async () => {
    mockFetch(() => ok({ quotes: [{ symbol: 'RELIANCE', status: 'ok', quote }, { symbol: 'TCS', status: 'unavailable', quote: null, error: 'down' }] }))
    const [first, second] = await getWatchlist(['RELIANCE', 'TCS'])
    expect(first.metrics[0].value).toContain('1,200')
    expect(second.status).toBe('MARKET DATA UNAVAILABLE')
  })
})

describe('newsApi', () => {
  it('keeps the original unavailable message', async () => {
    mockFetch(() => 'network-error')
    await expect(analyzeNews({ text: 'x' })).rejects.toThrow('News analysis service is currently unavailable.')
  })

  it('passes validation messages through', async () => {
    mockFetch(() => fail(400, 'News text is required.'))
    await expect(analyzeNews({ text: ' ' })).rejects.toThrow('News text is required.')
  })
})
