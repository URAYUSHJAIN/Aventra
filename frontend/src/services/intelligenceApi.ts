import { apiGet, apiGetWithStatus, apiPost } from './apiClient'
import type { AnalysisPending, Assessment, InstrumentSummary, Intelligence, Job, NewsItem, SearchResult, SnapshotItem, Watchlist } from '../types/api'

const encode = encodeURIComponent
const POLL_MS = 2_000
const MAX_WAIT_MS = 180_000

export interface SearchFilters { asset_class?: string; exchange?: string; country?: string }

export function searchInstruments(q: string, filters: SearchFilters = {}, cursor?: string | null, signal?: AbortSignal) {
  const params = new URLSearchParams({ q, limit: '12' })
  Object.entries(filters).forEach(([key, value]) => { if (value) params.set(key, value) })
  if (cursor) params.set('cursor', cursor)
  return apiGet<SearchResult>(`/api/instruments/search?${params}`, { signal, retries: 0 })
}

export const getInstrument = (id: string, signal?: AbortSignal) => apiGet<InstrumentSummary & { data_providers: Array<{ provider: string; configured: boolean; reason: string | null }> }>(`/api/instruments/${encode(id)}`, { signal })
export const getWatchlist = (signal?: AbortSignal) => apiGet<Watchlist>('/api/watchlists/default', { signal })
export const getSnapshots = (ids: string[], signal?: AbortSignal) => apiGet<{ items: SnapshotItem[] }>(`/api/market/snapshots?ids=${ids.map(encode).join(',')}`, { signal, timeoutMs: 90_000 }).then((d) => d.items)
export const getJob = (id: number, signal?: AbortSignal) => apiGet<Job>(`/api/jobs/${id}`, { signal })

const sleep = (ms: number, signal?: AbortSignal) => new Promise<void>((resolve, reject) => {
  const timer = setTimeout(resolve, ms)
  signal?.addEventListener('abort', () => { clearTimeout(timer); reject(new DOMException('Aborted', 'AbortError')) })
})

/** Resolves with a completed analysis. While the backend analyses in the background (202), polls the job and reports progress. */
export async function getIntelligence(id: string, { refresh = false, signal, onPending }: { refresh?: boolean; signal?: AbortSignal; onPending?: (pending: AnalysisPending) => void } = {}): Promise<Intelligence> {
  const path = `/api/intelligence/${encode(id)}`
  if (refresh) await apiPost(`${path}/runs`, {}, { signal })
  const started = Date.now()
  for (;;) {
    const response = await apiGetWithStatus<Intelligence | AnalysisPending>(path, { signal, timeoutMs: 60_000 })
    if (response.status !== 202) return response.data as Intelligence
    const pending = response.data as AnalysisPending
    onPending?.(pending)
    let job = pending.job
    while (job.status === 'queued' || job.status === 'running') {
      if (Date.now() - started > MAX_WAIT_MS) throw new Error('The analysis is taking longer than expected. It continues in the background; try again shortly.')
      await sleep(POLL_MS, signal)
      job = await getJob(job.id, signal)
      onPending?.({ ...pending, status: job.status === 'queued' ? 'queued' : 'running', job })
    }
  }
}

export const getNews = (id: string, limit = 8, signal?: AbortSignal) =>
  apiGet<{ instrument_id: string; items: NewsItem[]; data_source: { status: string; message: string | null; is_demo: boolean } }>(`/api/news?instrument=${encode(id)}&limit=${limit}`, { signal, timeoutMs: 90_000 })

export const getEvidence = (anomalyId: string, signal?: AbortSignal) =>
  apiGet<Pick<Assessment, 'evidence' | 'explanation' | 'risk'> & { event_id: string; anomaly_id: string; trading_date: string }>(`/api/evidence/${encode(anomalyId)}`, { signal })
