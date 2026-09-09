import { formatCurrency } from '@/lib/format'
import { Badge } from '@/components/ui/badge'

type ValuationStatus = 'EXACT' | 'ESTIMATED'

export function ValuationDisplay({
  status,
  method,
  value,
  currency,
  source,
  reason,
  compact = false,
}: {
  status?: ValuationStatus | string | null
  method?: string | null
  value?: number | null
  currency?: string | null
  source?: string | null
  reason?: string | null
  compact?: boolean
}) {
  const hasValue = value !== null && value !== undefined
  const methodLabel = method === 'CARDMARKET_AVG30' ? 'Cardmarket Avg30' : method
  const sourceLabel = source ? ` · ${source}` : ''

  return (
    <div className={`min-w-0 ${compact ? 'space-y-0.5' : 'space-y-1'}`} data-testid="valuation-display">
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="text-xs text-muted-foreground">{status === 'EXACT' ? 'Valuation' : 'Estimated valuation'}</span>
        {status && <Badge variant="secondary" className="text-[10px]">{status}</Badge>}
      </div>
      <div className="truncate tabular-nums">
        {hasValue ? formatCurrency(value, currency || 'EUR') : <span className="text-muted-foreground">—</span>}
      </div>
      {(methodLabel || source) && <div className="truncate text-[11px] text-muted-foreground">{methodLabel}{sourceLabel}</div>}
      {!hasValue && reason && <div className="truncate text-[11px] text-muted-foreground" title={reason}>Reason: {reason}</div>}
    </div>
  )
}
