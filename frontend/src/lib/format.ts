// Formateo centralizado -- regla unica "—" para valores nulos, y unico lugar donde
// roi (fraccion) se multiplica por 100 (fase6-dashboard-basico-sprint-contract.md).

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
