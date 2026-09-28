import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import App from './App'
import { EvidenceChain } from './components/intelligence/EvidenceChain'
import { FingerprintGlyph } from './components/intelligence/FingerprintGlyph'
import { fail, mockFetch, ok } from './test/fetchMock'
import fixture from './test/fixtures/intelligence-demo.json'
import type { Assessment, FingerprintDimension } from './types/api'

const health = { status: 'ok', database: 'ok', database_backend: 'sqlite', instrument_master_size: 68612, finbert_model_files: 'present', synthetic_test_data: false, pipeline_version: '0.2.0', job_mode: 'inline' }

function routeSite(url: string) {
  if (url.includes('/api/health')) return ok(health)
  if (url.includes('/api/watchlists/default')) return ok({ name: 'default', items: [] })
  if (url.includes('/api/instruments/search')) return ok({ items: [], next_cursor: null, query: 'x', master_size: 10, master_status: 'ok' })
  return fail(404, 'not found')
}

function visit(path: string) { window.history.replaceState(null, '', path); return render(<App />) }

afterEach(() => { cleanup(); vi.unstubAllGlobals(); window.history.replaceState(null, '', '/') })

describe('site shell', () => {
  it('reports an unreachable API in the footer instead of a healthy status', async () => {
    mockFetch(() => 'network-error')
    visit('/about')
    expect(await screen.findByText('API unreachable')).toBeTruthy()
  })

  it('shows the live API status and pipeline version from /api/health', async () => {
    mockFetch(routeSite)
    visit('/about')
    expect(await screen.findByText(/API online · pipeline v0\.2\.0/)).toBeTruthy()
  })

  it.each([
    ['/about', /Financial data is abundant/, 'About | Aventra'],
    ['/research', /research-first approach/, 'Research & Methodology | Aventra'],
    ['/doc', /Documentation/, 'Documentation | Aventra'],
    ['/contact', /Get in/, 'Contact | Aventra'],
    ['/nowhere', /outside our coverage/, 'Page not found | Aventra'],
  ])('routes %s to its page with its own title', (path, heading, title) => {
    mockFetch(routeSite)
    visit(path)
    expect(screen.getByRole('heading', { level: 1, name: heading })).toBeTruthy()
    expect(document.title).toBe(title)
  })

  it('opens and closes the mobile navigation with the keyboard', () => {
    mockFetch(routeSite)
    visit('/about')
    const toggle = screen.getByRole('button', { name: 'Open navigation' })
    fireEvent.click(toggle)
    expect(toggle.getAttribute('aria-expanded')).toBe('true')
    expect(document.getElementById('mobile-nav')?.hidden).toBe(false)
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(document.getElementById('mobile-nav')?.hidden).toBe(true)
  })

  it('marks the current page in the navigation', () => {
    mockFetch(routeSite)
    visit('/research')
    const nav = screen.getByRole('navigation', { name: 'Main navigation' })
    expect(within(nav).getByRole('link', { name: 'Research' }).getAttribute('aria-current')).toBe('page')
  })
})

describe('home page', () => {
  it('renders the hero, real master size and explicit no-watchlist states without inventing data', async () => {
    mockFetch(routeSite)
    visit('/')
    expect(screen.getByRole('heading', { level: 1, name: /Understand what the market is really doing/ })).toBeTruthy()
    expect(await screen.findByText('68,612')).toBeTruthy()
    expect(await screen.findByText(/NO WATCHLIST CONFIGURED/)).toBeTruthy()
    expect(await screen.findByText(/No watchlist is configured/)).toBeTruthy()
    expect(screen.getByText(/Illustrative/)).toBeTruthy()
  })

  it('fills the hero search with an example query instead of showing a value', async () => {
    const fetchMock = mockFetch(routeSite)
    visit('/')
    fireEvent.click(screen.getByRole('button', { name: 'Search for RELIANCE' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).includes('/api/instruments/search?q=RELIANCE'))).toBe(true))
  })
})

describe('documentation page', () => {
  it('marks every unpublished publication as Coming Soon and links only to real engineering docs', () => {
    mockFetch(routeSite)
    visit('/doc')
    for (const kind of ['PATENT', 'RESEARCH PAPER', 'REVIEW PAPER']) expect(screen.getByText(kind)).toBeTruthy()
    expect(screen.getAllByText('Coming Soon')).toHaveLength(3)
    const docLinks = screen.getAllByRole('link').map((a) => a.getAttribute('href') ?? '').filter((href) => href.includes('/docs/'))
    expect(docLinks.length).toBeGreaterThan(0)
    docLinks.forEach((href) => expect(href).toMatch(/^https:\/\/github\.com\/URAYUSHJAIN\/Aventra\/blob\/main\/docs\/\d\d_[A-Z_]+\.md$/))
  })
})

describe('intelligence visuals', () => {
  const event = fixture.events[0] as unknown as Assessment

  it('groups the backend evidence items into the five chain stages', () => {
    render(<EvidenceChain assessment={event} />)
    const stages = screen.getAllByRole('listitem').filter((li) => li.classList.contains('chain-stage'))
    expect(stages.map((s) => s.querySelector('strong')?.textContent)).toEqual(['Signal', 'Context', 'Event / news', 'Interpretation', 'Risk'])
    const count = (type: string) => event.evidence.filter((e) => e.type === type).length
    expect(stages[0].querySelectorAll('.chain-node')).toHaveLength(count('price') + count('volume') + count('volatility'))
    expect(stages[2].querySelectorAll('.chain-node')).toHaveLength(count('news') + count('sentiment'))
    expect(stages[4].querySelectorAll('.chain-node')).toHaveLength(count('risk'))
  })

  it('says news context is unavailable rather than leaving the news stage blank', () => {
    const noNews = { ...event, evidence: event.evidence.filter((e) => e.type !== 'news' && e.type !== 'sentiment' && e.type !== 'correlation'), correlation: { ...event.correlation, status: 'news_unavailable', matches: [] } } as Assessment
    render(<EvidenceChain assessment={noNews} />)
    expect(screen.getByText('News context unavailable for this instrument.')).toBeTruthy()
  })

  it('draws the fingerprint signature from the API robust z-scores with a text alternative', () => {
    const dimensions = fixture.fingerprint.dimensions as FingerprintDimension[]
    render(<FingerprintGlyph dimensions={dimensions} />)
    const glyph = screen.getByRole('img', { name: /Behavioural fingerprint signature/ })
    for (const d of dimensions) expect(glyph.getAttribute('aria-label')).toContain(d.label)
    expect(glyph.querySelectorAll('.fp-point')).toHaveLength(dimensions.filter((d) => d.robust_z !== null).length)
  })
})
