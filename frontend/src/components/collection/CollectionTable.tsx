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
import { MarketPrice } from '@/components/shared/MarketPrice'
import { formatCurrency } from '@/lib/format'
import type { CollectionItem } from '@/lib/types'
import { Button } from '@/components/ui/button'

export function CollectionTable({ items, onRemove }: { items: CollectionItem[]; onRemove: (id: number) => void }) {
  const navigate = useNavigate()

  if (items.length === 0) {
    return <p className="py-8 text-center text-sm text-muted-foreground">No hay cartas que coincidan con los filtros.</p>
  }

  return (
    <div className="overflow-x-auto rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-14">Img</TableHead>
            <TableHead>Carta</TableHead>
            <TableHead>Set</TableHead>
            <TableHead>#</TableHead>
            <TableHead>Cond.</TableHead>
            <TableHead className="text-right">Cant.</TableHead>
            <TableHead className="text-right">Costo</TableHead>
            <TableHead className="text-right">Valor de mercado</TableHead>
            <TableHead>Status</TableHead>
            <TableHead />
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
              <TableCell className="max-w-64 truncate font-medium">
                <div className="flex items-center gap-2">
                  <span className="truncate">{item.display_name}</span>
                  {item.manual_entry && (
                    <Badge variant="secondary" className="shrink-0">
                      Alta manual
                    </Badge>
                  )}
                  {item.reprint_count > 0 && <Badge variant="secondary" className="shrink-0">Reprints: {item.reprint_count}</Badge>}
                </div>
              </TableCell>
              <TableCell className="text-muted-foreground">{item.expansion_name ?? '—'}</TableCell>
              <TableCell className="text-muted-foreground">{[item.card_number, item.language?.toUpperCase()].filter(Boolean).join(' · ') || '—'}</TableCell>
              <TableCell className="text-muted-foreground">{item.condition ?? '—'}</TableCell>
              <TableCell className="text-right tabular-nums">{item.quantity}</TableCell>
              <TableCell className="text-right tabular-nums">{formatCurrency(item.purchase_price)}</TableCell>
              <TableCell className="text-right tabular-nums">
                <MarketPrice value={item.market_value} />
              </TableCell>
              <TableCell>
                <Badge variant="outline">{item.status}</Badge>
              </TableCell>
              <TableCell>
                <Button type="button" size="sm" variant="ghost" className="text-destructive" onClick={(event) => { event.stopPropagation(); onRemove(item.id) }}>Remove</Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
