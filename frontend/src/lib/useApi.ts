// Hook minimo para llamadas a la API (fase6-dashboard-basico-sprint-contract.md
// seccion §28: sin React Query/SWR, sin retry automatico -- opcion mas simple
// razonable, documentada en el cierre del sprint).

import { useCallback, useEffect, useRef, useState } from 'react'

interface UseApiState<T> {
  data: T | null
  error: string | null
  loading: boolean
  refreshing: boolean
}

export function useApi<T>(fetcher: () => Promise<T>, deps: unknown[]): UseApiState<T> & { reload: () => void } {
  const [state, setState] = useState<UseApiState<T>>({ data: null, error: null, loading: true, refreshing: false })
  const [reloadKey, setReloadKey] = useState(0)
  const handledReloadKey = useRef(0)
  const hasData = useRef(false)

  useEffect(() => {
    let cancelled = false
    const explicitReload = reloadKey !== handledReloadKey.current
    handledReloadKey.current = reloadKey
    const backgroundRefresh = explicitReload && hasData.current
    if (!backgroundRefresh) hasData.current = false

    setState((prev) => backgroundRefresh
      ? { ...prev, error: null, loading: false, refreshing: true }
      : { data: null, error: null, loading: true, refreshing: false })

    fetcher()
      .then((data) => {
        if (!cancelled) {
          hasData.current = true
          setState({ data, error: null, loading: false, refreshing: false })
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : 'Unknown error.'
          setState((prev) => backgroundRefresh
            ? { ...prev, error: message, loading: false, refreshing: false }
            : { data: null, error: message, loading: false, refreshing: false })
        }
      })

    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, reloadKey])

  const reload = useCallback(() => setReloadKey((k) => k + 1), [])

  return { ...state, reload }
}
