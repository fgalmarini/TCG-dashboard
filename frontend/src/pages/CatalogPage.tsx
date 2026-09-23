import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { CardArt } from '@/components/collection/CardImage'
import { ErrorState } from '@/components/shared/ErrorState'
import { LoadingState } from '@/components/shared/LoadingState'
import { MarketPrice } from '@/components/shared/MarketPrice'
import { Button } from '@/components/ui/button'
import { CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { addToCollection, addToWishlist, fetchCatalog, fetchCatalogOptions, removeFromWishlist } from '@/lib/api'
import { catalogCapabilities, GAME_OPTIONS, LANGUAGE_OPTIONS } from '@/lib/types'
import type { CatalogOptionsResponse, CatalogQueryParams } from '@/lib/types'
import { useApi } from '@/lib/useApi'
import { CardActions, CardIdentity, CardMetadata, CardPrice, TradingCard } from '@/components/shared/TradingCard'
import { SecondaryMarketPrice } from '@/components/shared/SecondaryMarketPrice'
import { cardImageUrl, formatSetCode } from '@/lib/format'

const ALL = '__all__'

function formatMetadataValue(value: string): string {
  const normalized = value.trim().toLowerCase()
  if (normalized === 'nonfoil') return 'Non-Foil'
  return normalized.replace(/[_-]+/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function formatFinishValue(treatment?: string | null, finish?: string | null): string | null {
  const normalizedTreatment = treatment?.trim().toLowerCase()
  if (normalizedTreatment === 'traditional_foil' || normalizedTreatment === 'surge_foil') {
    return formatMetadataValue(normalizedTreatment)
  }
  return finish ? formatMetadataValue(finish) : null
}

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
      setActionError(err instanceof Error ? err.message : 'Unable to update the wishlist.')
    }
  }

  async function changeCollection(cardId: number) {
    setActionError(null)
    try { await addToCollection(cardId); reload() }
    catch (err) { setActionError(err instanceof Error ? err.message : 'Unable to add the card to Collection.') }
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
        <p className="mt-1 text-sm text-muted-foreground">Physical printings by game, release, variant, and language</p>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap">
        <Input placeholder="Search by name or number..." value={search} onChange={(event) => resetPage(setSearch)(event.target.value)} className="sm:w-64" />
        <Select value={game} onValueChange={(value) => { setGame(value); setSets(''); setLanguage(''); setPage(1) }}>
          <SelectTrigger className="sm:w-40"><SelectValue placeholder="Game" /></SelectTrigger>
          <SelectContent>{GAME_OPTIONS.map((option) => <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>)}</SelectContent>
        </Select>
        <Select value={language || ALL} onValueChange={(value) => resetPage(setLanguage)(value === ALL ? '' : value)}>
          <SelectTrigger className="sm:w-40"><SelectValue placeholder="Language" /></SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>All languages</SelectItem>
            {(options?.languages.length ? options.languages : LANGUAGE_OPTIONS).map((option) => <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select value={sets || ALL} onValueChange={(value) => resetPage(setSets)(value === ALL ? '' : value)}>
          <SelectTrigger className="sm:w-40"><SelectValue placeholder="Set" /></SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>All sets</SelectItem>
            {(options?.sets ?? []).map((option) => <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select value={ownership ?? ALL} onValueChange={(value) => resetPage(setOwnership)(value === ALL ? undefined : value as CatalogQueryParams['ownership'])}>
          <SelectTrigger className="sm:w-44"><SelectValue placeholder="Ownership" /></SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>All</SelectItem>
            <SelectItem value="owned">Owned</SelectItem>
            <SelectItem value="not_owned">Not owned</SelectItem>
            <SelectItem value="wishlist">Wishlist</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {actionError && <p className="text-sm text-destructive">{actionError}</p>}
      {loading && !data && <LoadingState label="Loading catalog" />}
      {error && !data && <ErrorState message={error} onRetry={reload} />}
      {error && data && <ErrorState message={error} onRetry={reload} />}
      {data && !loading && (
        <>
          {data.items.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">No cards match the selected filters.</p>
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
                        <dl className="grid grid-cols-1 gap-x-2 gap-y-1 text-[10px] leading-tight sm:grid-cols-2">
                          {formatFinishValue(item.treatment, item.finish) && <div className="min-w-0"><dt className="text-muted-foreground">Finish</dt><dd className="truncate font-medium" title={formatFinishValue(item.treatment, item.finish) ?? undefined}>{formatFinishValue(item.treatment, item.finish)}</dd></div>}
                          {item.art_kind && item.art_kind !== 'unknown' && <div className="min-w-0"><dt className="text-muted-foreground">Variant</dt><dd className="truncate font-medium" title={formatMetadataValue(item.art_kind)}>{formatMetadataValue(item.art_kind)}</dd></div>}
                          {item.reprint_count > 0 && <div className="min-w-0"><dt className="text-muted-foreground">Reprints</dt><dd className="font-medium">{item.reprint_count}</dd></div>}
                          {item.ownership_status !== 'none' && <div className="min-w-0"><dt className="text-muted-foreground">Ownership</dt><dd className="truncate font-medium">{formatMetadataValue(item.ownership_status)}</dd></div>}
                        </dl>
                      </CardMetadata>
                      <CardPrice>
                        <MarketPrice value={item.current_price} currency={item.price_currency} />
                        <SecondaryMarketPrice sources={item.price_sources} />
                      </CardPrice>
                      {(catalogCapabilities(item.game_code).collection_enabled || catalogCapabilities(item.game_code).wishlist_enabled) && <CardActions>
                        <div className="flex flex-col gap-1">
                        {catalogCapabilities(item.game_code).collection_enabled && <Button type="button" size="sm" variant={item.owned ? 'secondary' : 'outline'} onClick={() => changeCollection(item.id)}>
                          {item.owned ? 'Add copy to Collection' : 'Add to Collection'}
                        </Button>}
                        {catalogCapabilities(item.game_code).wishlist_enabled && <Button type="button" size="sm" variant={item.wishlist ? 'secondary' : 'outline'} onClick={() => changeWishlist(item.id, item.wishlist)}>
                          {item.wishlist ? 'Remove from Wishlist' : 'Add to Wishlist'}
                        </Button>}
                        </div>
                      </CardActions>}
                    </div>
                  </CardContent>
                </TradingCard>
              ))}
            </div>
          )}
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">{data.identity_total ?? data.total} identities · {data.total} printings</span>
            <div className="flex gap-2">
              <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</Button>
              <Button size="sm" variant="outline" disabled={page * data.page_size >= data.total} onClick={() => setPage(page + 1)}>Next</Button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
