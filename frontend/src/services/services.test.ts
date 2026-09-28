import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, apiGet } from './apiClient'
import { getIntelligence, getSnapshots, searchInstruments } from './intelligenceApi'
import { analyzeNews } from './newsApi'
import { fail, mockFetch, ok } from '../test/fetchMock'
import { fmtBp, fmtLevel, fmtMoney } from '../utils/format'
import fixture from '../test/fixtures/intelligence-demo.json'

afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers() })

describe('apiClient', () => {
  it('unwraps the success envelope', async () => {
    mockFetch(() => ok({ value: 1 }))
    await expect(apiGet<{ value: number }>('/api/x')).resolves.toEqual({ value: 1 })
  })

  it('surfaces the server error message and code for client errors without retrying', async () => {
    const fetchMock = mockFetch(() => fail(404, 'XNAS:NOTREAL is not in the instrument master.', 'INSTRUMENT_NOT_FOUND'))
    await expect(apiGet('/api/intelligence/XNAS:NOTREAL')).rejects.toMatchObject({ kind: 'client', status: 404, code: 'INSTRUMENT_NOT_FOUND', message: expect.stringContaining('NOTREAL') })
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('does not retry typed data-availability states and keeps provider attempts', async () => {
    const attempts = [{ provider: 'alpha_vantage', status: 'unavailable', reason: 'ALPHAVANTAGE_API_KEY not set' }]
    const fetchMock = mockFetch(() => fail(503, 'No configured provider could supply data.', 'PROVIDER_UNAVAILABLE', attempts))
    const error = await apiGet('/api/intelligence/XNAS:AAPL').catch((reason: unknown) => reason) as ApiError
    expect(error.code).toBe('PROVIDER_UNAVAILABLE')
    expect(error.attempts).toEqual(attempts)
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
    mockFetch(() => (++calls === 1 ? fail(502, 'gateway') : ok('fine')))
    await expect(apiGet('/api/market/CRYPTO:BTC-USDT')).resolves.toBe('fine')
  })
})

describe('intelligenceApi', () => {
  it('searches with encoded query, filters and cursor', async () => {
    const fetchMock = mockFetch(() => ok({ items: [], next_cursor: null, query: 'S&P', master_size: 10, master_status: 'ok' }))
    await searchInstruments('S&P', { asset_class: 'etf' }, 'abc')
    const url = fetchMock.mock.calls[0][0] as string
    expect(url).toContain('/api/instruments/search?')
    expect(url).toContain('q=S%26P')
    expect(url).toContain('asset_class=etf')
    expect(url).toContain('cursor=abc')
  })

  it('requests snapshots by canonical IDs and keeps per-item states', async () => {
    const fetchMock = mockFetch(() => ok({ items: [{ instrument_id: 'XNAS:AAPL', status: 'PROVIDER_UNAVAILABLE', snapshot: null, error: 'key missing' }] }))
    const items = await getSnapshots(['XNAS:AAPL'])
    expect(fetchMock.mock.calls[0][0]).toContain('ids=XNAS%3AAAPL')
    expect(items[0].status).toBe('PROVIDER_UNAVAILABLE')
    expect(items[0].snapshot).toBeNull()
  })

  it('polls a queued analysis job until the result is ready', async () => {
    let intelligenceCalls = 0
    const pending = { status: 'queued', job: { id: 7, type: 'analyze', instrument_id: 'TEST:DEMO', status: 'queued', attempts: 0, error: null, updated_at: null }, previous_result: null, message: 'queued' }
    mockFetch((url) => {
      if (url.includes('/api/jobs/7')) return ok({ ...pending.job, status: 'done' })
      return ++intelligenceCalls === 1 ? { status: 202, body: { success: true, data: pending } } : ok(fixture)
    })
    const onPending = vi.fn()
    vi.useFakeTimers()
    const promise = getIntelligence('TEST:DEMO', { onPending })
    await vi.advanceTimersByTimeAsync(2_500)
    const result = await promise
    expect(result.instrument_id).toBe('TEST:DEMO')
    expect(onPending).toHaveBeenCalled()
    expect(intelligenceCalls).toBe(2)
  })
})

describe('format', () => {
  it('uses the instrument currency, never a hard-coded one', () => {
    expect(fmtMoney(1200, 'USD')).toContain('$')
    expect(fmtMoney(1200, 'INR')).toContain('₹')
    expect(fmtMoney(0.5, 'USDT')).toBe('0.5 USDT')
    expect(fmtMoney(null, 'USD')).toBe('n/a')
  })

  it('formats yields and basis points', () => {
    expect(fmtLevel(4.25, 'yield', 'USD')).toBe('4.250%')
    expect(fmtBp(-3.2)).toBe('-3.2 bp')
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

describe('risk score formatting', () => {
  it('rounds half to even like the backend explanation text, so the panel and the text agree', async () => {
    const { fmtRiskScore, fmtPctAbs } = await import('../utils/format')
    expect(fmtRiskScore(28.5)).toBe('28')
    expect(fmtRiskScore(29.5)).toBe('30')
    expect(fmtRiskScore(89.3)).toBe('89')
    expect(fmtRiskScore(6.7)).toBe('7')
    expect(fmtPctAbs(0.0228)).toBe('2.28%')
  })
})
