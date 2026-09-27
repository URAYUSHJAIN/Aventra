import { useCallback, useEffect, useRef, useState } from 'react'

export type ResourceState<T> = { status: 'loading'; data?: T } | { status: 'success'; data: T } | { status: 'error'; error: string; data?: T }

// Loads an API resource with loading / success / error states, cancels stale requests and supports manual reloads.
export function useApiResource<T>(load: (signal: AbortSignal, refresh: boolean) => Promise<T>, deps: readonly unknown[]) {
  const [state, setState] = useState<ResourceState<T>>({ status: 'loading' })
  const controllerRef = useRef<AbortController | null>(null)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const loader = useCallback(load, deps)

  const run = useCallback((refresh: boolean) => {
    controllerRef.current?.abort()
    const controller = new AbortController()
    controllerRef.current = controller
    setState((previous) => ({ status: 'loading', data: previous.data }))
    loader(controller.signal, refresh)
      .then((data) => { if (!controller.signal.aborted) setState({ status: 'success', data }) })
      .catch((reason: unknown) => { if (!controller.signal.aborted) setState((previous) => ({ status: 'error', error: reason instanceof Error ? reason.message : 'Something went wrong.', data: previous.data })) })
  }, [loader])

  useEffect(() => { run(false); return () => controllerRef.current?.abort() }, [run])
  return { state, reload: () => run(false), refresh: () => run(true) }
}
