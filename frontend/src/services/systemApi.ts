import { apiGet } from './apiClient'
import type { Health } from '../types/api'

// One health request per page load, shared by every consumer (footer status, hero master size).
let health: Promise<Health> | null = null

export function getHealth(): Promise<Health> {
  health ??= apiGet<Health>('/api/health', { timeoutMs: 10_000, retries: 0 }).catch((reason: unknown) => { health = null; throw reason })
  return health
}
