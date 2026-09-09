import { useNavigate } from 'react-router-dom'
import { Badge } from '@/components/ui/badge'
import { CardContent } from '@/components/ui/card'
import { CardArt } from '@/components/collection/CardImage'
import { MarketPrice } from '@/components/shared/MarketPrice'
import { SecondaryMarketPrice } from '@/components/shared/SecondaryMarketPrice'
import { CardActions, CardIdentity, CardMetadata, CardPrice, TradingCard } from '@/components/shared/TradingCard'
import { cardImageUrl, formatSetCode } from '@/lib/format'
import type { CollectionItem } from '@/lib/types'
import { Button } from '@/components/ui/button'
import { ValuationDisplay } from '@/components/shared/ValuationDisplay'

export function CollectionGrid({ items, onRemove, onEdit }: { items: CollectionItem[]; onRemove: (id: number) => void; onEdit: (id: number) => void }) {
  const navigate = useNavigate()

  if (items.length === 0) {
    return <p className="py-8 text-center text-sm text-muted-foreground">No cards match the selected filters.</p>
  }

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
      {items.map((item) => (
        <TradingCard
          key={item.id}
          imageUrl={cardImageUrl(item.image)}
          onClick={() => navigate(`/collection/${item.id}`)}
        >
          <CardContent className="flex h-full flex-col gap-3 p-3">
            <CardArt image={item.image} alt={item.display_name} faceIndex={0} />
            <div className="flex min-h-0 flex-1 flex-col">
              <CardIdentity>
                <h2 className="line-clamp-2 text-sm font-medium leading-snug">{item.display_name}</h2>
                <p className="mt-1 truncate text-xs text-muted-foreground">
                  {[formatSetCode(item.expansion_set_code), item.card_number, item.language?.toUpperCase()].filter(Boolean).join(' · ') || '—'}
                </p>
              </CardIdentity>
              <CardMetadata>
                <div className="flex flex-wrap gap-1">
                  {item.variant_label && <Badge variant="secondary" className="text-[10px]">{item.variant_label}</Badge>}
                  {item.reprint_count > 0 && <Badge variant="secondary" className="text-[10px]">Reprints: {item.reprint_count}</Badge>}
                </div>
              </CardMetadata>
              <CardPrice>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="text-xs text-muted-foreground">Market price</p>
                    <MarketPrice value={item.market_value} />
                  </div>
                  <Badge variant="outline" className="text-[10px]">{item.status}</Badge>
                </div>
                <ValuationDisplay
                  status={item.valuation_status}
                  method={item.valuation_method}
                  value={item.valuation_value}
                  currency={item.valuation_currency}
                  source={item.valuation_source}
                  reason={item.valuation_reason}
                  compact
                />
                <SecondaryMarketPrice sources={item.price_sources} />
              </CardPrice>
              <CardActions>
                <div className="flex gap-1">
                  <Button type="button" size="sm" variant="ghost" className="flex-1" onClick={(event) => { event.stopPropagation(); onEdit(item.id) }}>Edit</Button>
                  <Button type="button" size="sm" variant="ghost" className="flex-1 text-destructive" onClick={(event) => { event.stopPropagation(); onRemove(item.id) }}>Remove</Button>
                </div>
              </CardActions>
            </div>
          </CardContent>
        </TradingCard>
      ))}
    </div>
  )
}
