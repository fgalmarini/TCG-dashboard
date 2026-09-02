import type { PriceSource } from '@/lib/types'
import { formatCurrency } from '@/lib/format'

function tcgplayerSource(sources: PriceSource[]) {
  return sources.find((source) => source.market === 'tcgplayer')
}

export function SecondaryMarketPrice({ sources, detail = false }: { sources: PriceSource[]; detail?: boolean }) {
  const source = tcgplayerSource(sources)
  if (!source) return null

  const metric = (name: string) => source.metrics[name]
  const entries = detail
    ? [
        ['Market', metric('market')],
        ['Low', metric('low')],
        ['Mid', metric('mid')],
        ['High', metric('high')],
        ['Direct Low', metric('direct_low')],
      ]
    : [['Market', metric('market')], ['Low', metric('low')]]
  const visible = entries.filter(([, value]) => value !== undefined && value !== null)
  if (!visible.length) return null

  return (
    <div className={detail ? 'rounded-md border p-3' : 'mt-2 text-xs'}>
      <p className="text-xs font-medium text-muted-foreground">Secondary market · TCGplayer · {source.currency}</p>
      <div className={detail ? 'mt-3 grid gap-3 sm:grid-cols-2' : 'mt-1 flex gap-3'}>
        {visible.map(([label, value]) => (
          <div key={label}>
            <p className="text-[11px] text-muted-foreground">{label}</p>
            <p className="font-medium">{formatCurrency(value as number, source.currency)}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
