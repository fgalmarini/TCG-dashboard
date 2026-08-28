import { Link, useParams } from 'react-router-dom'
import { CardArt, ImageReferenceNote } from '@/components/collection/CardImage'
import { ErrorState } from '@/components/shared/ErrorState'
import { LoadingState } from '@/components/shared/LoadingState'
import { MarketPrice } from '@/components/shared/MarketPrice'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { fetchCatalogItem } from '@/lib/api'
import { useApi } from '@/lib/useApi'

export function CatalogDetailPage() {
  const id = Number(useParams().id)
  const { data, error, loading, reload } = useApi(() => fetchCatalogItem(id), [id])

  if (loading) return <LoadingState label="Cargando printing" />
  if (error || !data) return <ErrorState message={error ?? 'Printing no encontrado.'} onRetry={reload} />

  const item = data.printing
  const original = data.printings.find((printing) => printing.release_kind === 'original')
  return (
    <div className="space-y-6">
      <div>
        <Link to="/catalog" className="text-sm text-muted-foreground hover:underline">← Catalog</Link>
        <h1 className="mt-2 text-xl font-semibold">{item.name}</h1>
        <p className="text-sm text-muted-foreground">
          {[item.set_code?.toUpperCase(), item.card_number, item.language?.toUpperCase()].filter(Boolean).join(' · ')}
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[260px_1fr]">
        <Card><CardContent className="space-y-2 p-3"><CardArt image={item.image} alt={item.name} faceIndex={0} /><ImageReferenceNote image={item.image} /></CardContent></Card>
        <Card>
          <CardContent className="grid gap-4 p-5 sm:grid-cols-2">
            <Field label="Game" value={item.game_code} />
            <Field label="Release" value={item.expansion_name ?? item.set_code} />
            <Field label="Original release" value={original?.expansion_name ?? original?.set_code ?? 'Sin validar'} />
            <Field label="Language" value={item.language?.toUpperCase()} />
            <Field label="Release kind" value={item.release_kind} />
            <Field label="Art kind" value={item.art_kind} />
            <Field label="Printings" value={String(item.printing_count)} />
            <Field label="Reprints" value={String(item.reprint_count)} />
            <div>
              <p className="text-xs text-muted-foreground">Current price</p>
              <MarketPrice value={item.current_price} currency={item.price_currency} />
            </div>
            <Field label="Pricing source" value={item.price_source} />
            <Field label="Resolution" value={item.resolution_method} />
            <Field label="External ID evaluated" value={item.price_external_id} />
            <Field label="Sample size" value={String(item.price_sample_size)} />
            <Field label="Lowest price" value={item.lowest_price === null ? null : `${item.lowest_price} ${item.price_currency ?? ''}`} />
            <Field label="Median price" value={item.median_price === null ? null : `${item.median_price} ${item.price_currency ?? ''}`} />
            <Field label="Confidence" value={item.price_confidence} />
          </CardContent>
        </Card>
      </div>

      <div className="space-y-3">
        <h2 className="font-semibold">Known printings ({data.printings.length})</h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {data.printings.map((printing) => (
            <Link key={printing.id} to={`/catalog/${printing.id}`}>
              <Card className={printing.id === item.id ? 'border-primary' : ''}>
                <CardContent className="space-y-2 p-4">
                  <p className="font-medium">{printing.expansion_name ?? printing.set_code}</p>
                  <p className="text-xs text-muted-foreground">
                    {[printing.card_number, printing.language?.toUpperCase()].filter(Boolean).join(' · ')}
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {printing.release_kind && <Badge variant="outline">{printing.release_kind}</Badge>}
                    {printing.art_kind && <Badge variant="secondary">{printing.art_kind}</Badge>}
                  </div>
                  <MarketPrice value={printing.current_price} currency={printing.price_currency} />
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      </div>
    </div>
  )
}

function Field({ label, value }: { label: string; value: string | null | undefined }) {
  return <div><p className="text-xs text-muted-foreground">{label}</p><p className="text-sm">{value || '—'}</p></div>
}
