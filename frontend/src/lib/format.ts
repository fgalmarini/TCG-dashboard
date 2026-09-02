// Formateo centralizado -- regla unica "—" para valores nulos, y unico lugar donde
// roi (fraccion) se multiplica por 100 (fase6-dashboard-basico-sprint-contract.md).

import type { CardImage } from './types'

const dateFormatter = new Intl.DateTimeFormat('es-AR', { dateStyle: 'medium' })
const dateTimeFormatter = new Intl.DateTimeFormat('es-AR', { dateStyle: 'medium', timeStyle: 'short' })
const TCGDEX_ASSET_HOST = 'https://assets.tcgdex.net/'
const IMAGE_EXTENSION_RE = /\.(?:png|jpe?g|webp)$/i
const TCGDEX_QUALITY_RE = /\/(?:low|high)\.(?:png|jpe?g|webp)$/i

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

export function normalizeImageAssetUrl(
  value: string | null | undefined,
  quality: 'low' | 'high' = 'high',
): string | null {
  if (!value) return null
  const url = value.trim()
  if (!url) return null
  if (!url.startsWith(TCGDEX_ASSET_HOST)) return url
  if (TCGDEX_QUALITY_RE.test(url) || IMAGE_EXTENSION_RE.test(url)) return url
  return `${url.replace(/\/+$/, '')}/${quality}.webp`
}

export function cardImageUrl(image: CardImage | null, faceIndex = 0): string | null {
  const face = image?.faces?.[faceIndex] ?? null
  return normalizeImageAssetUrl(face?.large_url ?? face?.small_url, 'high')
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