// Hook minimo para llamadas a la API (fase6-dashboard-basico-sprint-contract.md
// seccion §28: sin React Query/SWR, sin retry automatico -- opcion mas simple
// razonable, documentada en el cierre del sprint).

import { useCallback, useEffect, useState } from 'react'

interface UseApiState<T> {
  data: T | null
  error: string | null
  loading: boolean
}

export function useApi<T>(fetcher: () => Promise<T>, deps: unknown[]): UseApiState<T> & { reload: () => void } {
  const [state, setState] = useState<UseApiState<T>>({ data: null, error: null, loading: true })
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    let cancelled = false
    setState((prev) => ({ ...prev, loading: true, error: null }))

    fetcher()
      .then((data) => {
        if (!cancelled) setState({ data, error: null, loading: false })
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : 'Error desconocido.'
          setState({ data: null, error: message, loading: false })
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
