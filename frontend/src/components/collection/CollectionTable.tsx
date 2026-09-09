// Dos indicadores independientes por fila, ninguno derivado del otro: el badge
// "Alta manual" sale de item.manual_entry tal cual viene de la API; el "—"/"sin
// precio" sale de item.market_value === null (via MarketPrice). No derivar uno del
// otro -- en Fase 7 una fila normal puede quedar temporalmente sin snapshot fresco,
// y mostrarle "Alta manual" seria incorrecto (fase6-dashboard-basico-sprint-contract.md,
// correccion explicita de Facundo sobre una version anterior del plan).

import { useNavigate } from 'react-router-dom'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { CardThumbnail } from '@/components/collection/CardImage'
import { formatCurrency } from '@/lib/format'
import type { CollectionItem } from '@/lib/types'
import { getCollectionMarketDisplay } from '@/lib/collectionPricing'
import { Button } from '@/components/ui/button'
import { ValuationDisplay } from '@/components/shared/ValuationDisplay'

export function CollectionTable({ items, onRemove, onEdit }: { items: CollectionItem[]; onRemove: (id: number) => void; onEdit: (id: number) => void }) {
  const navigate = useNavigate()

  if (items.length === 0) {
    return <p className="py-8 text-center text-sm text-muted-foreground">No cards match the selected filters.</p>
  }

  return (
    <div className="overflow-x-auto rounded-md border">
      <Table className="min-w-[940px] table-fixed">
        <TableHeader>
          <TableRow>
            <TableHead className="w-14 text-center">Image</TableHead>
            <TableHead className="w-[25%] text-center">Card</TableHead>
            <TableHead className="w-[16%] text-center">Set</TableHead>
            <TableHead className="w-[11%] text-center">#</TableHead>
            <TableHead className="w-16 text-center">Qty.</TableHead>
            <TableHead className="w-24 text-center">Cost</TableHead>
            <TableHead className="w-36 text-center">Market value</TableHead>
            <TableHead className="w-36 text-center">Estimated valuation</TableHead>
            <TableHead className="w-24 text-center">Status</TableHead>
            <TableHead className="w-36 text-center">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.map((item) => (
            <TableRow
              key={item.id}
              className="cursor-pointer"
              onClick={() => navigate(`/collection/${item.id}`)}
            >
              <TableCell>
                <CardThumbnail image={item.image} alt={item.display_name} />
              </TableCell>
              <TableCell className="truncate font-medium">
                <div className="flex items-center gap-2">
                  <span className="truncate">{item.display_name}</span>
                  {item.manual_entry && (
                    <Badge variant="secondary" className="shrink-0">
                      Manual entry
                    </Badge>
                  )}
                  {item.reprint_count > 0 && <Badge variant="secondary" className="shrink-0">Reprints: {item.reprint_count}</Badge>}
                </div>
              </TableCell>
              <TableCell className="truncate text-muted-foreground">{item.expansion_name ?? '—'}</TableCell>
              <TableCell className="truncate text-muted-foreground">{[item.card_number, item.language?.toUpperCase()].filter(Boolean).join(' · ') || '—'}</TableCell>
              <TableCell className="text-right tabular-nums">{item.quantity}</TableCell>
              <TableCell className="text-right tabular-nums">{formatCurrency(item.purchase_price)}</TableCell>
              <TableCell className="text-right tabular-nums">
                {(() => {
                  const display = getCollectionMarketDisplay(item)
                  return (
                    <div className="min-w-0 truncate">
                      <div>{display.value === null ? <span className="text-muted-foreground">—</span> : formatCurrency(display.value, display.currency)}</div>
                      {display.label && <div className="truncate text-[11px] font-normal text-muted-foreground">{display.label}</div>}
                    </div>
                  )
                })()}
              </TableCell>
              <TableCell className="text-right">
                <ValuationDisplay
                  status={item.valuation_status}
                  method={item.valuation_method}
                  value={item.valuation_value}
                  currency={item.valuation_currency}
                  source={item.valuation_source}
                  reason={item.valuation_reason}
                  compact
                />
              </TableCell>
              <TableCell className="text-center">
                <Badge variant="outline">{item.status}</Badge>
              </TableCell>
              <TableCell>
                <div className="flex justify-center gap-1">
                  <Button type="button" size="sm" variant="ghost" onClick={(event) => { event.stopPropagation(); onEdit(item.id) }}>Edit</Button>
                  <Button type="button" size="sm" variant="ghost" className="text-destructive" onClick={(event) => { event.stopPropagation(); onRemove(item.id) }}>Remove</Button>
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
