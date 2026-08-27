// Dark mode con el patron estandar shadcn (clase ".dark" en <html> + localStorage),
// desde el arranque -- no como retrofit (AGENTS.md seccion 26).

import { useEffect, useState } from 'react'

const STORAGE_KEY = 'tcg-dashboard-theme'

function getInitialIsDark(): boolean {
  if (typeof window === 'undefined') return false
  const stored = window.localStorage.getItem(STORAGE_KEY)
  if (stored === 'dark') return true
  if (stored === 'light') return false
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

export function useDarkMode(): [boolean, (value: boolean) => void] {
  const [isDark, setIsDark] = useState<boolean>(getInitialIsDark)

  useEffect(() => {
    document.documentElement.classList.toggle('dark', isDark)
    window.localStorage.setItem(STORAGE_KEY, isDark ? 'dark' : 'light')
  }, [isDark])

  return [isDark, setIsDark]
}
