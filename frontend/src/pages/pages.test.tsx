import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { IntelligencePage } from './IntelligencePage'
import { CapabilityPage } from './CapabilityPage'
import { NewsAnalysis } from '../components/news/NewsAnalysis'
import { fail, mockFetch, ok } from '../test/fetchMock'
import fixture from '../test/fixtures/intelligence-demo.json'

function routeIntelligence(url: string) {
  if (url.includes('/api/intelligence/TEST%3ADEMO')) return ok(fixture)
  return fail(404, 'not found', 'INSTRUMENT_NOT_FOUND')
}

afterEach(() => { cleanup(); vi.unstubAllGlobals(); window.history.replaceState(null, '', '/') })

describe('IntelligencePage', () => {
  it('shows a loading state, then renders every pipeline stage from the API', async () => {
    window.history.replaceState(null, '', '/intelligence?id=TEST:DEMO')
    mockFetch(routeIntelligence)
    render(<IntelligencePage />)
    expect(screen.getByRole('status').textContent).toMatch(/Loading analysis/)
    expect(await screen.findByRole('heading', { name: /Price with detected anomalies/ })).toBeTruthy()
    for (const name of [/Current vs normal behaviour/, /News sentiment/, /Signals aligned with/, /Why this was flagged/]) expect(screen.getByRole('heading', { name })).toBeTruthy()
    expect(screen.getAllByText(/DEMO · SYNTHETIC DATA/).length).toBeGreaterThan(0)
    expect(screen.getByRole('heading', { name: fixture.asset.name })).toBeTruthy()
    expect(screen.getAllByText(/TEST:DEMO/).length).toBeGreaterThan(0)
    const event = fixture.events[0]
    expect(screen.getByRole('img', { name: new RegExp(`Risk ${Math.round(event.risk.score)} out of 100`) })).toBeTruthy()
    expect(screen.getAllByText(/regulator opens investigation/).length).toBeGreaterThan(0)
  })

  it('asks for a search when no instrument is selected, without calling the analysis API', () => {
    window.history.replaceState(null, '', '/intelligence')
    const fetchMock = mockFetch(() => ok({}))
    render(<IntelligencePage />)
    expect(screen.getByRole('heading', { name: /Search for any instrument/ })).toBeTruthy()
    expect(screen.getByRole('combobox')).toBeTruthy()
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('shows the typed data-unavailable state with provider attempts', async () => {
    window.history.replaceState(null, '', '/intelligence?id=XNAS:AAPL')
    mockFetch(() => fail(503, 'No configured provider could supply XNAS:AAPL.', 'PROVIDER_UNAVAILABLE', [{ provider: 'alpha_vantage', status: 'unavailable', reason: 'ALPHAVANTAGE_API_KEY not set' }]))
    render(<IntelligencePage />)
    const alert = await screen.findByRole('alert')
    expect(alert.textContent).toContain('Data unavailable / insufficient source data')
    expect(alert.textContent).toMatch(/Data provider unavailable/)
    expect(alert.textContent).toMatch(/ALPHAVANTAGE_API_KEY not set/)
  })

  it('does not offer a retry for an instrument that does not exist', async () => {
    window.history.replaceState(null, '', '/intelligence?id=XNAS:NOTREAL')
    mockFetch(routeIntelligence)
    render(<IntelligencePage />)
    expect((await screen.findByRole('alert')).textContent).toMatch(/Instrument not found/)
    expect(screen.queryByRole('button', { name: /Try again/ })).toBeNull()
  })

  it('shows an error with retry when the backend is unavailable', async () => {
    window.history.replaceState(null, '', '/intelligence?id=TEST:DEMO')
    let calls = 0
    mockFetch(() => (++calls <= 2 ? 'network-error' : ok(fixture)))
    render(<IntelligencePage />)
    expect((await screen.findByRole('alert', {}, { timeout: 4000 })).textContent).toMatch(/backend is unavailable/)
    fireEvent.click(screen.getByRole('button', { name: /Try again/ }))
    expect(await screen.findByRole('heading', { name: /Price with detected anomalies/ })).toBeTruthy()
  })
})

describe('CapabilityPage', () => {
  it('renders only the capability-specific panels with real data', async () => {
    window.history.replaceState(null, '', '/risk-evidence?id=TEST:DEMO')
    mockFetch(routeIntelligence)
    render(<CapabilityPage capability='risk' />)
    expect(await screen.findByRole('heading', { name: /Risk signal/ })).toBeTruthy()
    expect(screen.getByRole('heading', { name: /Why this was flagged/ })).toBeTruthy()
    expect(screen.queryByRole('heading', { name: /Current vs normal behaviour/ })).toBeNull()
  })
})

describe('NewsAnalysis', () => {
  it('validates empty input without calling the API', () => {
    const fetchMock = mockFetch(() => ok({}))
    render(<NewsAnalysis />)
    fireEvent.click(screen.getByRole('button', { name: /Analyze News/ }))
    expect(screen.getByRole('alert').textContent).toContain('Enter financial news to begin analysis.')
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('renders the FinBERT result', async () => {
    mockFetch(() => ok({ label: 'negative', positive_probability: 0.05, neutral_probability: 0.1, negative_probability: 0.85, sentiment_score: -0.8 }))
    render(<NewsAnalysis />)
    fireEvent.change(screen.getByLabelText(/Financial news or text/), { target: { value: 'Profit fell.' } })
    fireEvent.click(screen.getByRole('button', { name: /Analyze News/ }))
    await waitFor(() => expect(screen.getByText('85%', { selector: '.result-summary strong' })).toBeTruthy())
    expect(screen.getByText('negative')).toBeTruthy()
  })
})
