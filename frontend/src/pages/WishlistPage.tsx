import { useMemo, useState } from 'react'
import { CardThumbnail } from '@/components/collection/CardImage'
import { ErrorState } from '@/components/shared/ErrorState'
import { LoadingState } from '@/components/shared/LoadingState'
import { MarketPrice } from '@/components/shared/MarketPrice'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { exportWishlist, fetchCatalogOptions, fetchWishlist, markWishlistAcquired, removeFromWishlist, restoreWishlist, updateWishlist } from '@/lib/api'
import { formatCurrency, formatSetCode } from '@/lib/format'
import { GAME_OPTIONS, LANGUAGE_OPTIONS, type WishlistItem, type WishlistQueryParams } from '@/lib/types'
import { useApi } from '@/lib/useApi'

const ALL = '__all__'
const PRIORITIES = ['high', 'medium', 'low', 'none'] as const
const PRIORITY_LABELS: Record<string, string> = { high: 'High', medium: 'Medium', low: 'Low', none: 'None' }

function priceStatus(item: WishlistItem): { label: string; variant: 'default' | 'secondary' | 'destructive' } | null {
  if (item.current_price === null) return null
  if (item.target_price !== null && item.current_price <= item.target_price) return { label: 'GOOD BUY', variant: 'default' }
  if (item.target_price !== null && item.max_price !== null && item.current_price <= item.max_price) return { label: 'ACCEPTABLE', variant: 'secondary' }
  if (item.max_price !== null && item.current_price > item.max_price) return { label: 'ABOVE MAX', variant: 'destructive' }
  return null
}

function PriceField({ label, value, item, field, onSave }: {
  label: string
  value: number | null
  item: WishlistItem
  field: 'target_price' | 'max_price'
  onSave: (item: WishlistItem, field: 'target_price' | 'max_price', value: number | null) => void
}) {
  return (
    <label className="flex min-w-24 flex-1 flex-col gap-1 text-xs text-muted-foreground">
      {label}
      <Input
        key={`${item.id}-${field}-${value ?? ''}`}
        aria-label={`${label} for ${item.name}`}
        type="number"
        min="0"
        step="0.01"
        placeholder="—"
        defaultValue={value ?? ''}
        onBlur={(event) => {
          const raw = event.currentTarget.value.trim()
          const next = raw === '' ? null : Number(raw)
          if (next === null || Number.isFinite(next)) onSave(item, field, next)
        }}
      />
    </label>
  )
}

function WishlistCard({
  item,
  buyingMode,
  pending,
  onAction,
  onSavePrice,
  onSavePriority,
}: {
  item: WishlistItem
  buyingMode: boolean
  pending: boolean
  onAction: (item: WishlistItem, action: 'acquired' | 'removed' | 'restore') => void
  onSavePrice: (item: WishlistItem, field: 'target_price' | 'max_price', value: number | null) => void
  onSavePriority: (item: WishlistItem, priority: string) => void
}) {
  const status = priceStatus(item)
  const isWanted = item.status === 'wanted'
  return (
    <Card>
      <CardContent className="flex flex-col gap-3 p-3 sm:flex-row sm:items-center">
        <CardThumbnail image={item.image} alt={item.name} />
        <div className="min-w-0 flex-1 space-y-2">
          <div>
            <h2 className="truncate font-medium">{item.name}</h2>
            <p className="text-xs text-muted-foreground">
              {[formatSetCode(item.set_code), item.card_number, item.language?.toUpperCase(), item.treatment, item.finish].filter(Boolean).join(' · ') || '—'}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <Badge variant="outline">{item.quantity_wanted} wanted</Badge>
            <Badge variant="secondary">{PRIORITY_LABELS[item.priority]}</Badge>
            {item.reprint_count > 0 && <Badge variant="secondary">Reprints: {item.reprint_count}</Badge>}
            <span className="text-muted-foreground">Current</span>
            <MarketPrice value={item.current_price} currency={item.price_currency} />
            {status && <Badge variant={status.variant}>{status.label}</Badge>}
          </div>
          {buyingMode ? (
            <div className="flex flex-wrap gap-4 text-sm">
              <span><span className="text-xs text-muted-foreground">Target</span><br />{formatCurrency(item.target_price, item.currency ?? 'EUR')}</span>
              <span><span className="text-xs text-muted-foreground">Max</span><br />{formatCurrency(item.max_price, item.currency ?? 'EUR')}</span>
            </div>
          ) : (
            <div className="flex flex-wrap gap-2">
              {isWanted && <>
                <PriceField label="Target Price" value={item.target_price} item={item} field="target_price" onSave={onSavePrice} />
                <PriceField label="Max Price" value={item.max_price} item={item} field="max_price" onSave={onSavePrice} />
              </>}
              <label className="flex min-w-24 flex-1 flex-col gap-1 text-xs text-muted-foreground">
                Priority
                <Select value={item.priority} onValueChange={(priority) => onSavePriority(item, priority)}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {PRIORITIES.map((priority) => <SelectItem key={priority} value={priority}>{PRIORITY_LABELS[priority]}</SelectItem>)}
                  </SelectContent>
                </Select>
              </label>
            </div>
          )}
        </div>
        <div className="flex flex-wrap gap-2 sm:justify-end">
          {isWanted && (
            <>
              <Button type="button" size="sm" disabled={pending} onClick={() => onAction(item, 'acquired')}>
                {pending ? 'Saving…' : 'Mark acquired'}
              </Button>
              {!buyingMode && <Button type="button" size="sm" variant="outline" disabled={pending} onClick={() => onAction(item, 'removed')}>Remove</Button>}
            </>
          )}
          {!isWanted && <Button type="button" size="sm" variant="outline" disabled={pending} onClick={() => onAction(item, 'restore')}>{pending ? 'Saving…' : 'Restore'}</Button>}
        </div>
      </CardContent>
    </Card>
  )
}

export function WishlistPage() {
  const [status, setStatus] = useState<WishlistQueryParams['status']>('wanted')
  const [priorities, setPriorities] = useState<string[]>([])
  const [sets, setSets] = useState('')
  const [game, setGame] = useState('')
  const [language, setLanguage] = useState('')
  const [finish, setFinish] = useState<WishlistQueryParams['finish']>()
  const [hasPrice, setHasPrice] = useState<boolean | undefined>()
  const [matched, setMatched] = useState<boolean | undefined>()
  const [sort, setSort] = useState<NonNullable<WishlistQueryParams['sort']>>('priority')
  const [buyingMode, setBuyingMode] = useState(false)
  const [pendingIds, setPendingIds] = useState<Set<number>>(new Set())
  const [actionError, setActionError] = useState<string | null>(null)
  const query = useMemo<WishlistQueryParams>(() => ({
    status,
    priority: priorities.length ? priorities.join(',') : undefined,
    sets: sets || undefined,
    game: game || undefined,
    language: language || undefined,
    finish,
    has_price: hasPrice,
    matched,
    sort,
  }), [status, priorities, sets, game, language, finish, hasPrice, matched, sort])
  const { data, error, loading, reload } = useApi(() => fetchWishlist(query), [query])
  const { data: options } = useApi(() => fetchCatalogOptions(game || undefined), [game])

  async function runAction(item: WishlistItem, action: 'acquired' | 'removed' | 'restore') {
    if (pendingIds.has(item.id)) return
    setPendingIds((ids) => new Set(ids).add(item.id))
    setActionError(null)
    try {
      if (action === 'acquired') await markWishlistAcquired(item.id)
      if (action === 'removed') await removeFromWishlist(item.id)
      if (action === 'restore') await restoreWishlist(item.id)
      reload()
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'No se pudo actualizar la wishlist.')
    } finally {
      setPendingIds((ids) => {
        const next = new Set(ids)
        next.delete(item.id)
        return next
      })
    }
  }

  async function savePrice(item: WishlistItem, field: 'target_price' | 'max_price', value: number | null) {
    if (field === 'target_price' || field === 'max_price') {
      const target = field === 'target_price' ? value : item.target_price
      const max = field === 'max_price' ? value : item.max_price
      if (target !== null && max !== null && target > max) {
        setActionError('Target Price no puede ser mayor que Max Price.')
        return
      }
      await saveItem(item.id, { [field]: value })
    }
  }

  async function saveItem(id: number, payload: { target_price?: number | null; max_price?: number | null; priority?: string }) {
    setActionError(null)
    try {
      await updateWishlist(id, payload)
      reload()
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'No se pudo guardar el item.')
    }
  }

  function onSavePrice(item: WishlistItem, field: 'target_price' | 'max_price', value: number | null) {
    void savePrice(item, field, value)
  }

  function onSavePriority(item: WishlistItem, priority: string) {
    void saveItem(item.id, { priority })
  }

  function togglePriority(priority: string) {
    setPriorities((current) => current.includes(priority) ? current.filter((value) => value !== priority) : [...current, priority])
  }

  const visibleItems = data?.items ?? []
  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-xl font-semibold">Wishlist</h1>
          <p className="mt-1 text-sm text-muted-foreground">Planificación de compras Multi-TCG por printing e idioma</p>
        </div>
        <div className="inline-flex w-fit rounded-md border bg-background p-1">
          <Button type="button" size="sm" variant={!buyingMode ? 'secondary' : 'ghost'} onClick={() => setBuyingMode(false)}>Wishlist</Button>
          <Button type="button" size="sm" variant={buyingMode ? 'secondary' : 'ghost'} onClick={() => setBuyingMode(true)}>Buying Mode</Button>
        </div>
      </div>

      {data && (
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
          <Card><CardContent className="p-3"><p className="text-xs text-muted-foreground">Wanted</p><p className="text-lg font-semibold">{data.summary.wanted}</p></CardContent></Card>
          <Card><CardContent className="p-3"><p className="text-xs text-muted-foreground">Estimated (EUR)</p><p className="text-lg font-semibold">{formatCurrency(data.summary.estimated_total, 'EUR')}</p></CardContent></Card>
          <Card><CardContent className="p-3"><p className="text-xs text-muted-foreground">Missing price</p><p className="text-lg font-semibold">{data.summary.missing_price}</p></CardContent></Card>
          <Card><CardContent className="p-3"><p className="text-xs text-muted-foreground">Unmatched</p><p className="text-lg font-semibold">{data.summary.unmatched}</p></CardContent></Card>
          <Card><CardContent className="p-3"><p className="text-xs text-muted-foreground">Acquired</p><p className="text-lg font-semibold">{data.summary.acquired}</p></CardContent></Card>
        </div>
      )}

      <div className="flex flex-col gap-3 rounded-xl border p-3 sm:flex-row sm:flex-wrap sm:items-center">
        <Select value={status ?? 'wanted'} onValueChange={(value) => setStatus(value as WishlistQueryParams['status'])}>
          <SelectTrigger className="sm:w-36"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="wanted">Wanted</SelectItem><SelectItem value="acquired">Acquired</SelectItem><SelectItem value="removed">Removed</SelectItem><SelectItem value="all">All statuses</SelectItem>
          </SelectContent>
        </Select>
        <div className="flex flex-wrap gap-1">
          {PRIORITIES.map((priority) => <Button key={priority} type="button" size="sm" variant={priorities.includes(priority) ? 'secondary' : 'outline'} aria-pressed={priorities.includes(priority)} onClick={() => togglePriority(priority)}>{PRIORITY_LABELS[priority]}</Button>)}
        </div>
        <Select value={game || ALL} onValueChange={(value) => { setGame(value === ALL ? '' : value); setSets('') }}>
          <SelectTrigger className="sm:w-36"><SelectValue placeholder="Juego" /></SelectTrigger>
          <SelectContent><SelectItem value={ALL}>All games</SelectItem>{GAME_OPTIONS.map((option) => <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>)}</SelectContent>
        </Select>
        <Select value={language || ALL} onValueChange={(value) => setLanguage(value === ALL ? '' : value)}>
          <SelectTrigger className="sm:w-36"><SelectValue placeholder="Idioma" /></SelectTrigger>
          <SelectContent><SelectItem value={ALL}>All languages</SelectItem>{(options?.languages.length ? options.languages : LANGUAGE_OPTIONS).map((option) => <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>)}</SelectContent>
        </Select>
        <Select value={sets || ALL} onValueChange={(value) => setSets(value === ALL ? '' : value)}>
          <SelectTrigger className="sm:w-32"><SelectValue placeholder="Set" /></SelectTrigger>
          <SelectContent><SelectItem value={ALL}>All sets</SelectItem>{(options?.sets ?? []).map((option) => <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>)}</SelectContent>
        </Select>
        <Select value={finish ?? ALL} onValueChange={(value) => setFinish(value === ALL ? undefined : value as WishlistQueryParams['finish'])}>
          <SelectTrigger className="sm:w-32"><SelectValue placeholder="Finish" /></SelectTrigger>
          <SelectContent><SelectItem value={ALL}>All finishes</SelectItem><SelectItem value="nonfoil">Nonfoil</SelectItem><SelectItem value="foil">Foil</SelectItem><SelectItem value="etched">Etched</SelectItem></SelectContent>
        </Select>
        <Select value={hasPrice === undefined ? ALL : String(hasPrice)} onValueChange={(value) => setHasPrice(value === ALL ? undefined : value === 'true')}>
          <SelectTrigger className="sm:w-36"><SelectValue placeholder="Price" /></SelectTrigger>
          <SelectContent><SelectItem value={ALL}>All prices</SelectItem><SelectItem value="true">Has price</SelectItem><SelectItem value="false">Missing price</SelectItem></SelectContent>
        </Select>
        <Select value={matched === undefined ? ALL : String(matched)} onValueChange={(value) => setMatched(value === ALL ? undefined : value === 'true')}>
          <SelectTrigger className="sm:w-36"><SelectValue placeholder="Match" /></SelectTrigger>
          <SelectContent><SelectItem value={ALL}>All matches</SelectItem><SelectItem value="true">Matched</SelectItem><SelectItem value="false">Unmatched</SelectItem></SelectContent>
        </Select>
        <Select value={sort} onValueChange={(value) => setSort(value as NonNullable<WishlistQueryParams['sort']>)}>
          <SelectTrigger className="sm:w-40"><SelectValue /></SelectTrigger>
          <SelectContent><SelectItem value="priority">Sort: Priority</SelectItem><SelectItem value="name">Sort: Name</SelectItem><SelectItem value="current_price">Sort: Current Price</SelectItem><SelectItem value="target_price">Sort: Target Price</SelectItem><SelectItem value="max_price">Sort: Max Price</SelectItem></SelectContent>
        </Select>
        <Button type="button" variant="outline" onClick={() => { window.location.href = exportWishlist(query) }}>Export CSV</Button>
      </div>

      {actionError && <p className="text-sm text-destructive">{actionError}</p>}
      {loading && <LoadingState label="Cargando wishlist" />}
      {error && !loading && <ErrorState message={error} onRetry={reload} />}
      {data && !loading && !error && (
        visibleItems.length === 0 ? <p className="py-8 text-center text-sm text-muted-foreground">No hay items que coincidan con los filtros.</p> :
          <div className="space-y-3">
            {visibleItems.map((item) => <WishlistCard key={item.id} item={item} buyingMode={buyingMode} pending={pendingIds.has(item.id)} onAction={runAction} onSavePrice={onSavePrice} onSavePriority={onSavePriority} />)}
          </div>
      )}
    </div>
  )
}
