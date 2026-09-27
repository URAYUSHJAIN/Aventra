import { apiGet } from './apiClient'
import type { Asset, Assessment, Intelligence, NewsItem } from '../types/api'

// The full pipeline can take several seconds on a cold start (model loading, provider calls).
const PIPELINE_TIMEOUT = 120_000

export const getAssets = (signal?: AbortSignal) => apiGet<{ assets: Asset[] }>('/api/assets', { signal }).then(data => data.assets)

export const getIntelligence = (symbol: string, { refresh = false, signal }: { refresh?: boolean; signal?: AbortSignal } = {}) =>
  apiGet<Intelligence>(`/api/intelligence/${encodeURIComponent(symbol)}${refresh ? '?refresh=1' : ''}`, { signal, timeoutMs: PIPELINE_TIMEOUT })

export const getNews = (symbol: string, limit = 8, signal?: AbortSignal) =>
  apiGet<{ symbol: string; items: NewsItem[]; data_source: { status: string; message: string | null; is_demo: boolean } }>(`/api/news?symbol=${encodeURIComponent(symbol)}&limit=${limit}`, { signal, timeoutMs: PIPELINE_TIMEOUT })

export const getEvidence = (anomalyId: string, signal?: AbortSignal) =>
  apiGet<Pick<Assessment, 'evidence' | 'explanation' | 'risk'> & { event_id: string; anomaly_id: string; trading_date: string }>(`/api/evidence/${encodeURIComponent(anomalyId)}`, { signal })
