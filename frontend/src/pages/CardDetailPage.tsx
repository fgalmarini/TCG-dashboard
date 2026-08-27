import { useState } from 'react'
import { ArrowLeft } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { CardArt } from '@/components/collection/CardImage'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { ErrorState } from '@/components/shared/ErrorState'
import { LoadingState } from '@/components/shared/LoadingState'
import { fetchCollectionItem } from '@/lib/api'
import { formatCurrency, formatDate, formatDateTime, formatPercent } from '@/lib/format'
import { useApi } from '@/lib/useApi'

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className="mt-0.5 text-sm">{value}</dd>
    </div>
  )
}

export function CardDetailPage() {
  const { id } = useParams<{ id: string }>()
  const itemId = Number(id)
  const [selectedFace, setSelectedFace] = useState(0)

  const { data, error, loading, reload } = useApi(() => fetchCollectionItem(itemId), [itemId])
  const faces = data?.image?.faces ?? []
  const activeFace = faces[selectedFace] ? selectedFace : 0

  return (
    <div className="space-y-6">
      <Button variant="ghost" size="sm" asChild className="-ml-2">
        <Link to="/collection">
          <ArrowLeft className="mr-1 size-4" />
          Volver a Collection
        </Link>
      </Button>

      {loading && <LoadingState label="Cargando carta" />}
      {error && !loading && <ErrorState message={error} onRetry={reload} />}

      {data && !loading && !error && (
        <>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-xl font-semibold">{data.display_name}</h1>
            {data.manual_entry && <Badge variant="secondary">Alta manual</Badge>}
            <Badge variant="outline">{data.status}</Badge>
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(260px,360px)_1fr]">
            <Card>
              <CardHeader>
                <CardTitle>Imagen</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <CardArt image={data.image} alt={data.display_name} faceIndex={activeFace} />
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
                        Cara {index + 1}
                      </Button>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Datos de la carta</CardTitle>
              </CardHeader>
              <CardContent>
                <dl className="grid grid-cols-2 gap-4">
                  <Field label="Set" value={data.expansion_name ?? '—'} />
                  <Field label="Set code" value={data.expansion_set_code ?? '—'} />
                  <Field label="Numero" value={data.card_number ?? '—'} />
                  <Field label="TCG" value={data.game_name ?? '—'} />
                  <Field label="Variante" value={data.variant_label ?? data.printing_variant ?? '—'} />
                  <Field label="Condicion" value={data.condition ?? '—'} />
                  <Field label="Grading" value={data.grading_company ? `${data.grading_company} ${data.grade ?? ''}`.trim() : '—'} />
                  <Field label="Cantidad" value={String(data.quantity)} />
                </dl>

                {data.manual_entry && (
                  <>
                    <Separator className="my-4" />
                    <div>
                      <dt className="text-xs uppercase tracking-wide text-muted-foreground">
                        Nota de alta manual
                      </dt>
                      <dd className="mt-1 whitespace-pre-wrap break-words text-sm">
                        {data.manual_entry_note ?? data.notes ?? '—'}
                      </dd>
                    </div>
                  </>
                )}

                {!data.manual_entry && data.notes && (
                  <>
                    <Separator className="my-4" />
                    <Field label="Notas" value={data.notes} />
                  </>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Costo y precio de mercado</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <dl className="grid grid-cols-2 gap-4">
                  <Field label="Precio de compra" value={formatCurrency(data.purchase_price)} />
                  <Field label="Fecha de compra" value={formatDate(data.purchase_date)} />
                  <Field label="Trade value" value={formatCurrency(data.trade_value)} />
                  <Field label="P/L" value={formatCurrency(data.unrealized_pl)} />
                  <Field label="ROI" value={formatPercent(data.roi)} />
                </dl>

                <Separator />

                {data.market_price ? (
                  <div className="space-y-2">
                    <p className="text-sm font-medium">
                      Trend Price de Cardmarket · snapshot del {formatDateTime(data.market_price.observed_at)}
                    </p>
                    <p className="text-2xl font-semibold tabular-nums">{formatCurrency(data.market_price.trend)}</p>
                    <dl className="grid grid-cols-3 gap-3 text-sm">
                      <Field label="Avg" value={formatCurrency(data.market_price.avg)} />
                      <Field label="Low" value={formatCurrency(data.market_price.low)} />
                      <Field label="Avg 30d" value={formatCurrency(data.market_price.avg30)} />
                    </dl>
                    <p className="text-xs text-muted-foreground">
                      Estimacion de mercado (Cardmarket), no un precio de venta garantizado.
                    </p>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    — sin precio de mercado (alta manual o producto sin snapshot de Cardmarket todavia).
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
