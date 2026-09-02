import { useState } from 'react'
import { ArrowLeft } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { CardArt, CardThumbnail, ImageReferenceNote } from '@/components/collection/CardImage'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { ErrorState } from '@/components/shared/ErrorState'
import { LoadingState } from '@/components/shared/LoadingState'
import { fetchCollectionItem, fetchMatchCandidates, resolveCollectionMatch } from '@/lib/api'
import { formatCurrency, formatDate, formatDateTime, formatPercent, formatSetCode } from '@/lib/format'
import { Input } from '@/components/ui/input'
import { useApi } from '@/lib/useApi'

type FieldValue = string | number | null | undefined

function hasMeaningfulValue(value: FieldValue): boolean {
  return value !== null && value !== undefined && (typeof value !== 'string' || value.trim() !== '')
}

function Field({ label, value }: { label: string; value: FieldValue }) {
  if (!hasMeaningfulValue(value)) return null

  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className="mt-0.5 text-sm">{typeof value === 'string' ? value.trim() : value}</dd>
    </div>
  )
}

function MatchResolver({ itemId, onResolved }: { itemId: number; onResolved: () => void }) {
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState<number | null>(null)
  const [pending, setPending] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)
  const { data, error, loading } = useApi(() => fetchMatchCandidates(itemId, search || undefined), [itemId, search])

  async function resolve() {
    if (selected === null || pending) return
    setPending(true)
    setActionError(null)
    try {
      await resolveCollectionMatch(itemId, selected)
      onResolved()
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Unable to resolve the match.')
    } finally {
      setPending(false)
    }
  }

  return (
    <Card>
      <CardHeader><CardTitle>Resolve catalog match</CardTitle></CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">This row has no canonical physical identity. Select a candidate explicitly from the local catalog.</p>
        {data && (
          <div className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
            <Field label="Name" value={data.name} />
            <Field label="Set" value={formatSetCode(data.set_code)} />
            <Field label="Collector number" value={data.card_number} />
            <Field label="Source" value={data.source} />
          </div>
        )}
        <Input placeholder="Search candidates..." value={search} onChange={(event) => setSearch(event.target.value)} />
        {loading && <LoadingState label="Searching candidates" />}
        {error && <p className="text-sm text-destructive">{error}</p>}
        {data && !loading && (
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {data.candidates.map((candidate) => (
              <button
                key={candidate.id}
                type="button"
                className={`flex items-center gap-3 rounded-lg border p-2 text-left transition-colors ${selected === candidate.id ? 'border-primary bg-primary/10' : 'hover:bg-muted'}`}
                aria-pressed={selected === candidate.id}
                onClick={() => setSelected(candidate.id)}
              >
                <CardThumbnail image={candidate.image} alt={candidate.name} />
                <span className="min-w-0 text-sm">
                  <span className="block truncate font-medium">{candidate.name}</span>
                  <span className="block text-xs text-muted-foreground">{[formatSetCode(candidate.set_code), candidate.card_number, candidate.finish, candidate.treatment].filter(Boolean).join(' · ')}</span>
                </span>
              </button>
            ))}
          </div>
        )}
        {actionError && <p className="text-sm text-destructive">{actionError}</p>}
        <Button type="button" disabled={selected === null || pending} onClick={resolve}>{pending ? 'Resolving…' : 'Confirm match'}</Button>
      </CardContent>
    </Card>
  )
}

export function CardDetailPage() {
  const { id } = useParams<{ id: string }>()
  const itemId = Number(id)
  const [selectedFace, setSelectedFace] = useState(0)

  const { data, error, loading, reload } = useApi(() => fetchCollectionItem(itemId), [itemId])
  const faces = data?.image?.faces ?? []
  const activeFace = faces[selectedFace] ? selectedFace : 0
  const manualEntryNote = data && (hasMeaningfulValue(data.manual_entry_note) ? data.manual_entry_note : data.notes)

  return (
    <div className="space-y-6">
      <Button variant="ghost" size="sm" asChild className="-ml-2">
        <Link to="/collection">
          <ArrowLeft className="mr-1 size-4" />
          Back to Collection
        </Link>
      </Button>

      {loading && !data && <LoadingState label="Loading card" />}
      {error && !data && <ErrorState message={error} onRetry={reload} />}
      {error && data && <ErrorState message={error} onRetry={reload} />}

      {data && !loading && (
        <>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-xl font-semibold">{data.display_name}</h1>
            {data.manual_entry && <Badge variant="secondary">Manual entry</Badge>}
            {!data.catalog_matched && <Badge variant="destructive">Unmatched</Badge>}
            <Badge variant="outline">{data.status}</Badge>
            {data.reprint_count > 0 && <Badge variant="secondary">Reprints: {data.reprint_count}</Badge>}
          </div>

          {!data.catalog_matched && <MatchResolver itemId={itemId} onResolved={reload} />}

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(260px,360px)_1fr]">
            <Card>
              <CardHeader>
                <CardTitle>Image</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <CardArt image={data.image} alt={data.display_name} faceIndex={activeFace} />
                <ImageReferenceNote image={data.image} />
                {faces.length > 1 && (
                  <div className="inline-flex rounded-md border bg-background p-1">
                    {faces.map((face, index) => (
                      <Button
                        key={face.face_index}
                        type="button"
                        variant={activeFace === index ? 'secondary' : 'ghost'}
                        size="sm"
                        onClick={() => setSelectedFace(index)}
                      >
                        Face {index + 1}
                      </Button>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Card Data</CardTitle>
              </CardHeader>
              <CardContent>
                <dl className="grid grid-cols-2 gap-4">
                  <Field label="TCG" value={data.game_name} />
                  <Field label="Set" value={data.expansion_name} />
                  <Field label="Set Code" value={formatSetCode(data.expansion_set_code)} />
                  <Field label="Number" value={data.card_number} />
                  <Field label="Art Kind" value={data.art_kind} />
                  <Field label="Reprints" value={data.reprint_count} />
                  <Field label="Language" value={data.language?.toUpperCase()} />
                  <Field label="Release Kind" value={data.release_kind} />
                  <Field label="Printings" value={data.printing_count} />
                  <Field label="Treatment" value={data.treatment ?? data.variant_label ?? data.printing_variant} />
                  <Field label="Grading" value={data.grading_company ? `${data.grading_company} ${data.grade ?? ''}`.trim() : data.grade} />
                  <Field label="Quantity" value={data.quantity} />
                </dl>

                {data.manual_entry && hasMeaningfulValue(manualEntryNote) && (
                  <>
                    <Separator className="my-4" />
                    <div>
                      <dt className="text-xs uppercase tracking-wide text-muted-foreground">
                        Manual entry note
                      </dt>
                      <dd className="mt-1 whitespace-pre-wrap break-words text-sm">
                        {manualEntryNote}
                      </dd>
                    </div>
                  </>
                )}

                {!data.manual_entry && data.notes && (
                  <>
                    <Separator className="my-4" />
                    <Field label="Notes" value={data.notes} />
                  </>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Cost and market price</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <dl className="grid grid-cols-2 gap-4">
                  <Field label="Purchase price" value={formatCurrency(data.purchase_price)} />
                  <Field label="Purchase date" value={formatDate(data.purchase_date)} />
                  <Field label="Cardmarket Low" value={formatCurrency(data.market_price?.cardmarket_low ?? data.market_price?.low, data.market_price?.source_currency ?? data.market_price?.currency)} />
                  <Field label="P/L" value={formatCurrency(data.unrealized_pl)} />
                  <Field label="ROI" value={formatPercent(data.roi)} />
                </dl>

                <Separator />

                {data.market_price ? (
                  <div className="space-y-2">
                    <p className="text-sm font-medium">
                      {data.market_price.source} price · snapshot from {formatDateTime(data.market_price.observed_at)}
                    </p>
                    <p className="text-2xl font-semibold tabular-nums">{formatCurrency(data.market_price.cardmarket_low ?? data.market_price.low, data.market_price.source_currency ?? data.market_price.currency)}</p>
                    <dl className="grid grid-cols-3 gap-3 text-sm">
                      <Field label="Trend" value={formatCurrency(data.market_price.cardmarket_trend ?? data.market_price.trend, data.market_price.source_currency ?? data.market_price.currency)} />
                      <Field label="AVG7" value={formatCurrency(data.market_price.avg7, data.market_price.source_currency ?? data.market_price.currency)} />
                      <Field label="AVG30" value={formatCurrency(data.market_price.avg30, data.market_price.source_currency ?? data.market_price.currency)} />
                    </dl>
                    <p className="text-xs text-muted-foreground">
                      {data.market_price.resolution_method ?? 'Exact resolution'} · market estimate, not a guaranteed sale price.
                    </p>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    No market price (manual entry or product without a Cardmarket snapshot yet).
                  </p>
                )}
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  )
}
