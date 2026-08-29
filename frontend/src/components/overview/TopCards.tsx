import { Link } from 'react-router-dom'
import { Card, CardContent } from '@/components/ui/card'
import { CardArt } from '@/components/collection/CardImage'
import { formatCurrency, formatPercentVariation, formatSetCode } from '@/lib/format'
import type { TopCard } from '@/lib/types'

function variationClass(value: number | null): string {
  if (value === null) return 'text-muted-foreground'
  return value > 0 ? 'text-emerald-600 dark:text-emerald-400' : value < 0 ? 'text-red-600 dark:text-red-400' : 'text-muted-foreground'
}

export function TopCards({ cards, limit, onLimitChange }: { cards: TopCard[]; limit: 3 | 5 | 10; onLimitChange: (limit: 3 | 5 | 10) => void }) {
  const visibleCards = cards.slice(0, limit)

  return (
    <section className="space-y-3" aria-labelledby="top-cards-title">
      <div className="flex items-center justify-between gap-3">
        <h2 id="top-cards-title" className="text-lg font-semibold">Top Cards</h2>
        <div className="inline-flex rounded-md border bg-background p-1" aria-label="Cantidad de Top Cards">
          {[3, 5, 10].map((value) => (
            <button
              key={value}
              type="button"
              data-limit={value}
              className="rounded px-2 py-1 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground aria-pressed:bg-secondary aria-pressed:text-secondary-foreground"
              aria-pressed={limit === value}
              onClick={() => onLimitChange(value as 3 | 5 | 10)}
            >
              Top {value}
            </button>
          ))}
        </div>
      </div>
      {visibleCards.length === 0 ? (
        <Card><CardContent className="py-8 text-center text-sm text-muted-foreground">No hay cartas con precio actual.</CardContent></Card>
      ) : (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          {visibleCards.map((card) => (
            <Link key={card.collection_item_id} to={`/collection/${card.collection_item_id}`} className="block h-full">
              <Card className="h-full overflow-hidden transition-colors hover:border-primary">
                <CardContent className="flex h-full flex-col gap-3 p-3">
                  <CardArt image={card.image} alt={card.name} faceIndex={0} />
                  <div className="flex min-h-0 flex-1 flex-col">
                    <div className="min-h-14">
                      <h3 className="line-clamp-2 text-sm font-medium leading-snug">{card.name}</h3>
                      <p className="mt-1 truncate text-xs text-muted-foreground">
                        {[formatSetCode(card.set_code), card.card_number].filter(Boolean).join(' · ') || '—'}
                      </p>
                    </div>
                    <div className="mt-auto pt-3">
                      <p className="text-base font-semibold tabular-nums">{formatCurrency(card.market_value, card.price_currency ?? 'EUR')}</p>
                      <p className={`text-xs font-medium tabular-nums ${variationClass(card.price_variation)}`}>
                        {formatPercentVariation(card.price_variation)}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </section>
  )
}
