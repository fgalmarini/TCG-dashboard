import { useState } from 'react'
import { CardThumbnail } from '@/components/collection/CardImage'
import { ErrorState } from '@/components/shared/ErrorState'
import { LoadingState } from '@/components/shared/LoadingState'
import { MarketPrice } from '@/components/shared/MarketPrice'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { fetchWishlist, moveWishlistToCollection, removeFromWishlist, updateWishlist } from '@/lib/api'
import { useApi } from '@/lib/useApi'

export function WishlistPage() {
  const [actionError, setActionError] = useState<string | null>(null)
  const { data, error, loading, reload } = useApi(fetchWishlist, [])

  async function runAction(action: () => Promise<unknown>) {
    setActionError(null)
    try {
      await action()
      reload()
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'No se pudo actualizar la wishlist.')
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Wishlist</h1>
        <p className="mt-1 text-sm text-muted-foreground">Cartas que quieres conseguir</p>
      </div>
      {actionError && <p className="text-sm text-destructive">{actionError}</p>}
      {loading && <LoadingState label="Cargando wishlist" />}
      {error && !loading && <ErrorState message={error} onRetry={reload} />}
      {data && !loading && !error && (
        data.items.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted-foreground">Tu wishlist está vacía.</p>
        ) : (
          <div className="space-y-3">
            {data.items.map((item) => (
              <Card key={item.id}>
                <CardContent className="flex flex-col gap-4 p-4 sm:flex-row sm:items-center">
                  <CardThumbnail image={item.image} alt={item.name} />
                  <div className="min-w-0 flex-1">
                    <h2 className="truncate font-medium">{item.name}</h2>
                    <p className="text-sm text-muted-foreground">{[item.set_code?.toUpperCase(), item.card_number, item.finish].filter(Boolean).join(' · ') || '—'}</p>
                    <div className="mt-2 flex flex-wrap items-center gap-2">
                      <Badge variant="outline">{item.quantity_wanted} wanted</Badge>
                      {item.treatment && <Badge variant="secondary">{item.treatment}</Badge>}
                      <MarketPrice value={item.current_price} />
                      <label className="flex items-center gap-2 text-sm text-muted-foreground">
                        Max price
                        <Input
                          aria-label={`Max price for ${item.name}`}
                          className="w-24"
                          type="number"
                          min="0"
                          step="0.01"
                          placeholder="—"
                          defaultValue={item.max_price ?? ''}
                          onBlur={(event) => {
                            const value = event.currentTarget.value.trim()
                            const maxPrice = value === '' ? null : Number(value)
                            if (maxPrice === null || Number.isFinite(maxPrice)) {
                              runAction(() => updateWishlist(item.id, { max_price: maxPrice }))
                            }
                          }}
                        />
                        {item.currency ?? 'EUR'}
                      </label>
                    </div>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <Select value={item.priority} onValueChange={(priority) => runAction(() => updateWishlist(item.id, { priority }))}>
                      <SelectTrigger className="w-28"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="low">Low</SelectItem>
                        <SelectItem value="medium">Medium</SelectItem>
                        <SelectItem value="high">High</SelectItem>
                      </SelectContent>
                    </Select>
                    <Button size="sm" onClick={() => runAction(() => moveWishlistToCollection(item.id))}>Move to Collection</Button>
                    <Button size="sm" variant="outline" onClick={() => runAction(() => removeFromWishlist(item.id))}>Remove</Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )
      )}
    </div>
  )
}
