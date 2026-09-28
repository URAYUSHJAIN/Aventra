import { useEffect, useState } from 'react'
import { getHealth } from '../services/systemApi'
import type { Health } from '../types/api'

export type HealthState = { status: 'loading' } | { status: 'ok'; data: Health } | { status: 'unreachable' }

export function useHealth(): HealthState {
  const [state, setState] = useState<HealthState>({ status: 'loading' })
  useEffect(() => {
    let active = true
    getHealth().then((data) => { if (active) setState({ status: 'ok', data }) }).catch(() => { if (active) setState({ status: 'unreachable' }) })
    return () => { active = false }
  }, [])
  return state
}
