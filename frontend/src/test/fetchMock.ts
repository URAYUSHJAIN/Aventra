import { vi } from 'vitest'

type Route = (url: string, init?: RequestInit) => { status?: number; body: unknown } | Promise<{ status?: number; body: unknown }> | 'network-error'

// Replaces global fetch with a router; tests never reach a real backend.
export function mockFetch(route: Route) {
  const fn = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === 'string' ? input : input.toString()
    const result = await route(url, init)
    if (result === 'network-error') throw new TypeError('Failed to fetch')
    return new Response(JSON.stringify(result.body), { status: result.status ?? 200, headers: { 'Content-Type': 'application/json' } })
  })
  vi.stubGlobal('fetch', fn)
  return fn
}

export const ok = (data: unknown) => ({ status: 200, body: { success: true, data } })
export const fail = (status: number, error: string, code?: string, attempts?: unknown[]) => ({ status, body: { success: false, error, ...(code ? { code } : {}), ...(attempts ? { attempts } : {}) } })
