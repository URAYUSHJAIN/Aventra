// Central HTTP client for the Flask API: base URL, {success, data | error} envelope, timeouts, GET retry and typed errors.
// Components never call fetch() directly; they use the service functions built on this client.

export type ApiErrorKind = 'unavailable' | 'client' | 'server' | 'timeout'

export class ApiError extends Error {
  constructor(message: string, readonly kind: ApiErrorKind, readonly status?: number) { super(message) }
}

interface Envelope<T> { success: boolean; data?: T; error?: string }
interface RequestOptions { signal?: AbortSignal; timeoutMs?: number; retries?: number }

// Empty uses Vite's /api proxy locally (and the nginx proxy in Docker); set VITE_API_BASE_URL for a separately hosted API.
export const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')

const wait = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))

async function request<T>(path: string, init: RequestInit, { signal, timeoutMs = 30_000, retries = 0 }: RequestOptions): Promise<T> {
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
      if (response.ok && payload.success && payload.data !== undefined) return payload.data
      const kind: ApiErrorKind = response.status >= 500 ? (response.status === 502 || response.status === 503 ? 'unavailable' : 'server') : 'client'
      throw new ApiError(payload.error ?? `Request failed (HTTP ${response.status}).`, kind, response.status)
    } catch (error) {
      const retryable = error instanceof ApiError && (error.kind === 'unavailable' || error.kind === 'timeout' || error.kind === 'server')
      if (!retryable || attempt >= retries || signal?.aborted) throw error
      await wait(600 * (attempt + 1))
    } finally {
      clearTimeout(timer)
      signal?.removeEventListener('abort', onAbort)
    }
  }
}

export function apiGet<T>(path: string, options: RequestOptions = {}): Promise<T> {
  return request<T>(path, { method: 'GET' }, { retries: 1, ...options })
}

export function apiPost<T>(path: string, body: unknown, options: RequestOptions = {}): Promise<T> {
  return request<T>(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }, options)
}
