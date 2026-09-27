// Central HTTP client for the Flask API: base URL, {success, data | error, code} envelope, timeouts, GET retry and typed errors.
// Components never call fetch() directly; they use the service functions built on this client.
import type { ProviderAttempt } from '../types/api'

export type ApiErrorKind = 'unavailable' | 'client' | 'server' | 'timeout'

export class ApiError extends Error {
  constructor(message: string, readonly kind: ApiErrorKind, readonly status?: number, readonly code?: string, readonly attempts: ProviderAttempt[] = []) { super(message) }
}

interface Envelope<T> { success: boolean; data?: T; error?: string; code?: string; attempts?: ProviderAttempt[] }
interface RequestOptions { signal?: AbortSignal; timeoutMs?: number; retries?: number }
export interface ApiResponse<T> { status: number; data: T }

// Typed data-availability states are answers, not transient failures: never retried.
const DATA_STATES = new Set(['INSTRUMENT_NOT_FOUND', 'INVALID_INSTRUMENT_ID', 'NO_PROVIDER_FOR_ASSET', 'PROVIDER_UNAVAILABLE', 'RATE_LIMITED', 'INSUFFICIENT_HISTORY', 'INSUFFICIENT_SOURCE_DATA'])

// Empty uses Vite's /api proxy locally (and the nginx proxy in Docker); set VITE_API_BASE_URL for a separately hosted API.
export const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')

const wait = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))

async function request<T>(path: string, init: RequestInit, { signal, timeoutMs = 30_000, retries = 0 }: RequestOptions): Promise<ApiResponse<T>> {
  for (let attempt = 0; ; attempt++) {
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort('timeout'), timeoutMs)
    const onAbort = () => controller.abort('cancelled')
    signal?.addEventListener('abort', onAbort)
    try {
      let response: Response
      try {
        response = await fetch(`${apiBaseUrl}${path}`, { ...init, signal: controller.signal, headers: { Accept: 'application/json', ...(init.headers ?? {}) } })
      } catch (reason) {
        if (signal?.aborted) throw reason
        if (controller.signal.reason === 'timeout') throw new ApiError('The Aventra service took too long to respond.', 'timeout')
        throw new ApiError('The Aventra backend is unavailable. Check that the API server is running.', 'unavailable')
      }
      const payload = await response.json().catch(() => ({})) as Envelope<T>
      if (response.ok && payload.success && payload.data !== undefined) return { status: response.status, data: payload.data }
      const kind: ApiErrorKind = response.status >= 500 ? (response.status === 502 || response.status === 503 ? 'unavailable' : 'server') : 'client'
      throw new ApiError(payload.error ?? `Request failed (HTTP ${response.status}).`, kind, response.status, payload.code, payload.attempts ?? [])
    } catch (error) {
      const typed = error instanceof ApiError && error.code !== undefined && DATA_STATES.has(error.code)
      const retryable = error instanceof ApiError && !typed && (error.kind === 'unavailable' || error.kind === 'timeout' || error.kind === 'server')
      if (!retryable || attempt >= retries || signal?.aborted) throw error
      await wait(600 * (attempt + 1))
    } finally {
      clearTimeout(timer)
      signal?.removeEventListener('abort', onAbort)
    }
  }
}

export async function apiGet<T>(path: string, options: RequestOptions = {}): Promise<T> {
  return (await request<T>(path, { method: 'GET' }, { retries: 1, ...options })).data
}

export function apiGetWithStatus<T>(path: string, options: RequestOptions = {}): Promise<ApiResponse<T>> {
  return request<T>(path, { method: 'GET' }, { retries: 1, ...options })
}

export async function apiPost<T>(path: string, body: unknown, options: RequestOptions = {}): Promise<T> {
  return (await request<T>(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }, options)).data
}

export const DATA_UNAVAILABLE = 'Data unavailable / insufficient source data'
