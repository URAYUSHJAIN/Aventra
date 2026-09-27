import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { GlobalSearch } from './GlobalSearch'
import { fail, mockFetch, ok } from '../../test/fetchMock'

const apple = { instrument_id: 'XNAS:AAPL', symbol: 'AAPL', name: 'Apple Inc', asset_class: 'equity', exchange: 'XNAS', country: 'US', currency: 'USD', timezone: 'America/New_York', status: 'active', capabilities: null }
const btc = { instrument_id: 'CRYPTO:BTC-USDT', symbol: 'BTC-USDT', name: 'Bitcoin / TetherUS', asset_class: 'crypto', exchange: 'BINANCE', country: null, currency: 'USDT', timezone: 'UTC', status: 'active', capabilities: null }

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

describe('GlobalSearch', () => {
  it('debounces, lists results with asset-class badges and selects by keyboard', async () => {
    const fetchMock = mockFetch(() => ok({ items: [apple, btc], next_cursor: null, query: 'a', master_size: 2, master_status: 'ok' }))
    const onSelect = vi.fn()
    render(<GlobalSearch onSelect={onSelect} />)
    const input = screen.getByRole('combobox')
    fireEvent.change(input, { target: { value: 'ap' } })
    fireEvent.change(input, { target: { value: 'app' } })
    expect(await screen.findByRole('option', { name: /Apple Inc/ })).toBeTruthy()
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(screen.getByText('Crypto')).toBeTruthy()
    fireEvent.keyDown(input, { key: 'ArrowDown' })
    fireEvent.keyDown(input, { key: 'Enter' })
    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ instrument_id: 'CRYPTO:BTC-USDT' }))
  })

  it('shows an explicit empty state and an empty-master state', async () => {
    mockFetch(() => ok({ items: [], next_cursor: null, query: 'zzz', master_size: 5, master_status: 'ok' }))
    render(<GlobalSearch />)
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'zzz' } })
    expect(await screen.findByText(/No instruments match/)).toBeTruthy()
    cleanup()
    mockFetch(() => ok({ items: [], next_cursor: null, query: 'x', master_size: 0, master_status: 'empty' }))
    render(<GlobalSearch />)
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'x' } })
    expect(await screen.findByText(/instrument master is empty/)).toBeTruthy()
  })

  it('reports search errors', async () => {
    mockFetch(() => fail(400, 'Query too long.'))
    render(<GlobalSearch />)
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'q' } })
    expect((await screen.findByRole('alert')).textContent).toContain('Query too long.')
  })
})
