import { useState } from 'react'
import { CardArt } from '@/components/collection/CardImage'
import { ErrorState } from '@/components/shared/ErrorState'
import { LoadingState } from '@/components/shared/LoadingState'
import { MarketPrice } from '@/components/shared/MarketPrice'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { addToWishlist, fetchCatalog, moveWishlistToCollection, removeFromWishlist } from '@/lib/api'
import type { CatalogQueryParams } from '@/lib/types'
import { useApi } from '@/lib/useApi'

const ALL = '__all__'

export function CatalogPage() {
  const [search, setSearch] = useState('')
  const [sets, setSets] = useState('')
  const [ownership, setOwnership] = useState<CatalogQueryParams['ownership']>()
  const [page, setPage] = useState(1)
  const [actionError, setActionError] = useState<string | null>(null)
  const { data, error, loading, reload } = useApi(
    () => fetchCatalog({ sets: sets || undefined, search: search || undefined, ownership, page, page_size: 24 }),
    [sets, search, ownership, page],
  )

  async function changeWishlist(cardId: number, wished: boolean) {
    setActionError(null)
    try {
      if (wished) {
        const item = data?.items.find((candidate) => candidate.id === cardId)
        if (item?.wishlist_item_id) await removeFromWishlist(item.wishlist_item_id)
      } else {
        await addToWishlist(cardId)
      }
      reload()
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'No se pudo actualizar la wishlist.')
    }
  }

  async function moveToCollection(cardId: number) {
    const item = data?.items.find((candidate) => candidate.id === cardId)
    if (!item) return
    setActionError(null)
    try {
      // Catalog only exposes Move when the card is already wished. The wishlist
      // endpoint owns the transition and preserves the acquired history.
      if (item.wishlist_item_id) await moveWishlistToCollection(item.wishlist_item_id)
      reload()
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'No se pudo mover la carta.')
    }
  }

  function resetPage<T>(setter: (value: T) => void) {
    return (value: T) => {
      setter(value)
      setPage(1)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Catalog</h1>
        <p className="mt-1 text-sm text-muted-foreground">Magic · The Lord of the Rings · LTR + LTC</p>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap">
        <Input placeholder="Buscar por nombre..." value={search} onChange={(event) => resetPage(setSearch)(event.target.value)} className="sm:w-64" />
        <Select value={sets || ALL} onValueChange={(value) => resetPage(setSets)(value === ALL ? '' : value)}>
          <SelectTrigger className="sm:w-40"><SelectValue placeholder="Set" /></SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>Todos los sets</SelectItem>
            <SelectItem value="ltr">LTR</SelectItem>
            <SelectItem value="ltc">LTC</SelectItem>
          </SelectContent>
        </Select>
        <Select value={ownership ?? ALL} onValueChange={(value) => resetPage(setOwnership)(value === ALL ? undefined : value as CatalogQueryParams['ownership'])}>
          <SelectTrigger className="sm:w-44"><SelectValue placeholder="Ownership" /></SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>Todas</SelectItem>
            <SelectItem value="owned">Owned</SelectItem>
            <SelectItem value="not_owned">Not owned</SelectItem>
            <SelectItem value="wishlist">Wishlist</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {actionError && <p className="text-sm text-destructive">{actionError}</p>}
      {loading && <LoadingState label="Cargando catálogo" />}
      {error && !loading && <ErrorState message={error} onRetry={reload} />}
      {data && !loading && !error && (
        <>
          {data.items.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">No hay cartas que coincidan con los filtros.</p>
          ) : (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
              {data.items.map((item) => (
                <Card key={item.id} className="overflow-hidden">
                  <CardContent className="space-y-3 p-3">
                    <CardArt image={item.image} alt={item.name} faceIndex={0} />
                    <div className="space-y-2">
                      <h2 className="line-clamp-2 text-sm font-medium">{item.name}</h2>
                      <p className="text-xs text-muted-foreground">{[item.set_code?.toUpperCase(), item.card_number].filter(Boolean).join(' · ') || '—'}</p>
                      <div className="flex flex-wrap gap-1">
                        {item.treatment && <Badge variant="secondary" className="text-[10px]">{item.treatment}</Badge>}
                        {item.finish && <Badge variant="outline" className="text-[10px]">{item.finish}</Badge>}
                        <Badge variant="outline" className="text-[10px]">{item.ownership_status}</Badge>
                      </div>
                      <MarketPrice value={item.current_price} />
                      <div className="flex flex-col gap-1">
                        <Button type="button" size="sm" variant={item.wishlist ? 'secondary' : 'outline'} onClick={() => changeWishlist(item.id, item.wishlist)}>
                          {item.wishlist ? 'Remove from Wishlist' : 'Add to Wishlist'}
                        </Button>
                        {item.wishlist && <Button type="button" size="sm" onClick={() => moveToCollection(item.id)}>Move to Collection</Button>}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">{data.total} cartas</span>
            <div className="flex gap-2">
              <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage(page - 1)}>Anterior</Button>
              <Button size="sm" variant="outline" disabled={page * data.page_size >= data.total} onClick={() => setPage(page + 1)}>Siguiente</Button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
