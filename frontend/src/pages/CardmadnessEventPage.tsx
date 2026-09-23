import { useMemo, useState } from 'react'
import { CardThumbnail } from '@/components/collection/CardImage'
import { ErrorState } from '@/components/shared/ErrorState'
import { LoadingState } from '@/components/shared/LoadingState'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { fetchEventWishlist } from '@/lib/api'
import { formatCurrency, formatSetCode } from '@/lib/format'
import { useApi } from '@/lib/useApi'

const EVENT_CODE = 'cardmadness-2026'
const dash = (value: number | null | undefined) => value == null ? '—' : formatCurrency(value, 'EUR')
const humanize = (value: string) => value.replace(/[_-]+/g, ' ').replace(/\b\w/g, letter => letter.toUpperCase())

export function CardmadnessEventPage() {
  const { data, error, loading, reload } = useApi(() => fetchEventWishlist(EVENT_CODE), [EVENT_CODE])
  const [search, setSearch] = useState('')
  const [set, setSet] = useState('all')
  const [status, setStatus] = useState('all')
  const filtered = useMemo(() => (data?.items ?? []).filter(({ wishlist_item: item }) =>
    item.name.toLocaleLowerCase().includes(search.toLocaleLowerCase()) &&
    (set === 'all' || item.set_code?.toUpperCase() === set) && (status === 'all' || item.status === status)), [data, search, set, status])

  if (loading && !data) return <LoadingState />
  if (error && !data) return <ErrorState message={error} onRetry={reload} />
  return <main className="mx-auto max-w-6xl space-y-5 px-4 py-6">
    <div><h1 className="text-2xl font-semibold">CARDMADNESS EVENT</h1><p className="text-sm text-muted-foreground">Event wishlist · {filtered.length} cards</p></div>
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      <Input aria-label="Search cards" placeholder="Search by name" value={search} onChange={e => setSearch(e.target.value)} />
      <Select value={set} onValueChange={setSet}><SelectTrigger aria-label="Filter by set"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="all">All sets</SelectItem><SelectItem value="HOB">HOB</SelectItem><SelectItem value="HOC">HOC</SelectItem></SelectContent></Select>
      <Select value={status} onValueChange={setStatus}><SelectTrigger aria-label="Filter by status"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="all">All statuses</SelectItem><SelectItem value="wanted">Wanted</SelectItem><SelectItem value="acquired">Acquired</SelectItem><SelectItem value="removed">Removed</SelectItem></SelectContent></Select>
    </div>
    {filtered.length === 0 ? <p className="rounded-lg border p-6 text-center text-muted-foreground">No linked wishlist cards.</p> : <div className="grid grid-cols-1 gap-3">
      {filtered.map(({ wishlist_item: item, target_prices: prices, traditional_foil: alternative }) => <Card key={item.id}>
        <CardContent className="flex min-w-0 flex-col gap-4 p-4 sm:flex-row">
          <CardThumbnail image={item.image} alt={item.name} />
          <div className="min-w-0 flex-1 space-y-3">
            <div className="flex flex-wrap items-center gap-2"><h2 className="font-semibold">{item.name}</h2><Badge variant="outline">{item.status}</Badge><Badge variant="secondary">{item.priority}</Badge></div>
            <p className="text-sm text-muted-foreground">{formatSetCode(item.set_code)} · #{item.card_number ?? '—'} · {humanize(item.treatment ?? item.finish ?? '—')}</p>
            <div className="flex flex-wrap gap-x-5 gap-y-2 text-sm"><span>Target: {dash(item.target_price)}</span><span>Max: {dash(item.max_price)}</span><span>Language: {item.language?.toUpperCase() ?? '—'}</span></div>
            {['hob', 'hoc'].includes((item.set_code ?? '').toLowerCase()) && item.treatment === 'surge_foil' && <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <section className="rounded-md border border-primary/40 bg-primary/5 p-3"><h3 className="mb-2 text-xs font-semibold uppercase tracking-wide">Surge Foil · Target</h3><div className="flex flex-wrap gap-x-4 gap-y-1 text-sm"><span>Low: {dash(prices.low)}</span><span>Avg30: {dash(prices.avg30)}</span></div></section>
              <section className="rounded-md border p-3"><h3 className="mb-2 text-xs font-semibold uppercase tracking-wide">Traditional Foil · Alternative</h3>{alternative ? <span className="text-sm">#{alternative.card_number} · Low: {dash(alternative.low)}</span> : <span className="text-sm text-muted-foreground">Unavailable · —</span>}</section>
            </div>}
            {['hob', 'hoc'].includes((item.set_code ?? '').toLowerCase()) && item.treatment === 'traditional_foil' && <section className="rounded-md border border-primary/40 bg-primary/5 p-3"><h3 className="mb-2 text-xs font-semibold uppercase tracking-wide">Traditional Foil · Target</h3><div className="flex flex-wrap gap-x-4 gap-y-1 text-sm"><span>Low: {dash(prices.low)}</span><span>Avg30: {dash(prices.avg30)}</span></div></section>}
          </div>
        </CardContent>
      </Card>)}
    </div>}
  </main>
}
