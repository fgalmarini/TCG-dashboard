// Unico lugar donde se decide "—" vs valor formateado para precios de mercado --
// nunca un valor artificial para "sin dato" (AGENTS.md seccion 20/25).

import { formatCurrency } from '@/lib/format'

export function MarketPrice({ value, currency = 'EUR', className }: { value: number | null; currency?: string | null; className?: string }) {
  if (value === null) {
    return <span className={`text-muted-foreground ${className ?? ''}`}>— no price</span>
  }
  return <span className={className}>{formatCurrency(value, currency || 'EUR')}</span>
}
