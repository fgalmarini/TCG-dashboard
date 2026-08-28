import { useNavigate } from 'react-router-dom'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { CardArt } from '@/components/collection/CardImage'
import { MarketPrice } from '@/components/shared/MarketPrice'
import type { CollectionItem } from '@/lib/types'
import { Button } from '@/components/ui/button'

export function CollectionGrid({ items, onRemove }: { items: CollectionItem[]; onRemove: (id: number) => void }) {
  const navigate = useNavigate()

  if (items.length === 0) {
    return <p className="py-8 text-center text-sm text-muted-foreground">No hay cartas que coincidan con los filtros.</p>
  }

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
      {items.map((item) => (
        <Card
          key={item.id}
          role="button"
          tabIndex={0}
          onClick={() => navigate(`/collection/${item.id}`)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' || event.key === ' ') navigate(`/collection/${item.id}`)
          }}
          className="cursor-pointer overflow-hidden"
        >
          <CardContent className="space-y-3 p-3">
            <CardArt image={item.image} alt={item.display_name} faceIndex={0} />
            <div className="min-h-24 space-y-2">
              <div>
                <h2 className="line-clamp-2 text-sm font-medium leading-snug">{item.display_name}</h2>
                <p className="mt-1 truncate text-xs text-muted-foreground">
                  {[item.expansion_set_code, item.card_number, item.language?.toUpperCase()].filter(Boolean).join(' · ') || '—'}
                </p>
              </div>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <MarketPrice value={item.market_value} />
                <Badge variant="outline" className="text-[10px]">
                  {item.status}
                </Badge>
                {item.reprint_count > 0 && <Badge variant="secondary" className="text-[10px]">Reprints: {item.reprint_count}</Badge>}
              </div>
              {item.variant_label && <p className="truncate text-xs text-muted-foreground">{item.variant_label}</p>}
              <Button type="button" size="sm" variant="ghost" className="w-full text-destructive" onClick={(event) => { event.stopPropagation(); onRemove(item.id) }}>Remove from Collection</Button>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
