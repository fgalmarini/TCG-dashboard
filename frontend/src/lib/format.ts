// Formateo centralizado -- regla unica "—" para valores nulos, y unico lugar donde
// roi (fraccion) se multiplica por 100 (fase6-dashboard-basico-sprint-contract.md).

import type { CardImage } from './types'

const dateFormatter = new Intl.DateTimeFormat('es-AR', { dateStyle: 'medium' })
const dateTimeFormatter = new Intl.DateTimeFormat('es-AR', { dateStyle: 'medium', timeStyle: 'short' })

export function formatCurrency(value: number | null | undefined, currency = 'EUR'): string {
  if (value === null || value === undefined) return '—'
  return new Intl.NumberFormat('de-DE', { style: 'currency', currency }).format(value)
}

/** value llega del backend como fraccion (ej. 0.631) -- el *100 pasa UNA sola vez, aca. */
export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—'
  return `${(value * 100).toFixed(1)}%`
}

export function formatPercentVariation(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—'
  const percent = (value * 100).toFixed(1)
  return value > 0 ? `+${percent}%` : `${percent}%`
}

export function formatSetCode(value: string | null | undefined): string | null {
  return value ? value.toUpperCase() : null
}

export function cardImageUrl(image: CardImage | null, faceIndex = 0): string | null {
  const face = image?.faces?.[faceIndex] ?? null
  return face?.large_url ?? face?.small_url ?? null
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return dateFormatter.format(date)
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return dateTimeFormatter.format(date)
}
