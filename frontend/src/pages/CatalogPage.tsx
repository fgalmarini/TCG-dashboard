import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { CardArt } from '@/components/collection/CardImage'
import { ErrorState } from '@/components/shared/ErrorState'
import { LoadingState } from '@/components/shared/LoadingState'
import { MarketPrice } from '@/components/shared/MarketPrice'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { addToCollection, addToWishlist, fetchCatalog, fetchCatalogOptions, removeFromWishlist } from '@/lib/api'
import { GAME_OPTIONS, LANGUAGE_OPTIONS } from '@/lib/types'
import type { CatalogOptionsResponse, CatalogQueryParams } from '@/lib/types'
import { useApi } from '@/lib/useApi'
import { CardActions, CardIdentity, CardMetadata, CardPrice, TradingCard } from '@/components/shared/TradingCard'
import { cardImageUrl, formatSetCode } from '@/lib/format'

const ALL = '__all__'

export function CatalogPage() {
  const [game, setGame] = useState('magic')
  const [language, setLanguage] = useState('')
  const [search, setSearch] = useState('')
  const [sets, setSets] = useState('')
  const [ownership, setOwnership] = useState<CatalogQueryParams['ownership']>()
  const [page, setPage] = useState(1)
  const [actionError, setActionError] = useState<string | null>(null)
  const [options, setOptions] = useState<CatalogOptionsResponse | null>(null)
  const { data, error, loading, reload } = useApi(
    () => fetchCatalog({ game, language: language || undefined, sets: sets || undefined, search: search || undefined, ownership, page, page_size: 24 }),
    [game, language, sets, search, ownership, page],
  )

  useEffect(() => {
    if (loading || !data) return

    let cancelled = false
    setOptions(null)
    fetchCatalogOptions(game)
      .then((nextOptions) => {
        if (!cancelled) setOptions(nextOptions)
      })
      .catch(() => {
        if (!cancelled) setOptions(null)
      })

    return () => {
      cancelled = true
    }
  }, [data, game, loading])

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

  async function changeCollection(cardId: number) {
    setActionError(null)
    try { await addToCollection(cardId); reload() }
    catch (err) { setActionError(err instanceof Error ? err.message : 'No se pudo agregar a Collection.') }
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
        <p className="mt-1 text-sm text-muted-foreground">Printings físicos por juego, release, variante e idioma</p>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap">
        <Input placeholder="Buscar por nombre o número..." value={search} onChange={(event) => resetPage(setSearch)(event.target.value)} className="sm:w-64" />
        <Select value={game} onValueChange={(value) => { setGame(value); setSets(''); setLanguage(''); setPage(1) }}>
          <SelectTrigger className="sm:w-40"><SelectValue placeholder="Juego" /></SelectTrigger>
          <SelectContent>{GAME_OPTIONS.map((option) => <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>)}</SelectContent>
        </Select>
        <Select value={language || ALL} onValueChange={(value) => resetPage(setLanguage)(value === ALL ? '' : value)}>
          <SelectTrigger className="sm:w-40"><SelectValue placeholder="Idioma" /></SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>Todos los idiomas</SelectItem>
            {(options?.languages.length ? options.languages : LANGUAGE_OPTIONS).map((option) => <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select value={sets || ALL} onValueChange={(value) => resetPage(setSets)(value === ALL ? '' : value)}>
          <SelectTrigger className="sm:w-40"><SelectValue placeholder="Set" /></SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>Todos los sets</SelectItem>
            {(options?.sets ?? []).map((option) => <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>)}
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
                <TradingCard key={item.id} imageUrl={cardImageUrl(item.image)}>
                  <CardContent className="flex h-full flex-col gap-3 p-3">
                    <CardArt image={item.image} alt={item.name} faceIndex={0} />
                    <div className="flex min-h-0 flex-1 flex-col">
                      <CardIdentity>
                        <Link to={`/catalog/${item.id}`} className="line-clamp-2 text-sm font-medium hover:underline">{item.name}</Link>
                        <p className="mt-1 truncate text-xs text-muted-foreground">{[formatSetCode(item.set_code), item.card_number, item.language?.toUpperCase()].filter(Boolean).join(' · ') || '—'}</p>
                      </CardIdentity>
                      <CardMetadata>
                      <div className="flex flex-wrap gap-1">
                        {item.treatment && <Badge variant="secondary" className="text-[10px]">{item.treatment}</Badge>}
                        {item.finish && <Badge variant="outline" className="text-[10px]">{item.finish}</Badge>}
                        {item.art_kind && <Badge variant="secondary" className="text-[10px]">{item.art_kind}</Badge>}
                        {item.reprint_count > 0 && <Badge variant="secondary" className="text-[10px]">Reprints: {item.reprint_count}</Badge>}
                        <Badge variant="outline" className="text-[10px]">{item.ownership_status}</Badge>
                      </div>
                      </CardMetadata>
                      <CardPrice><MarketPrice value={item.current_price} currency={item.price_currency} /></CardPrice>
                      <CardActions>
                        <div className="flex flex-col gap-1">
                        <Button type="button" size="sm" variant={item.owned ? 'secondary' : 'outline'} onClick={() => changeCollection(item.id)}>
                          {item.owned ? 'Add copy to Collection' : 'Add to Collection'}
                        </Button>
                        <Button type="button" size="sm" variant={item.wishlist ? 'secondary' : 'outline'} onClick={() => changeWishlist(item.id, item.wishlist)}>
                          {item.wishlist ? 'Remove from Wishlist' : 'Add to Wishlist'}
                        </Button>
                        </div>
                      </CardActions>
                    </div>
                  </CardContent>
                </TradingCard>
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
