import type { CollectionItem } from './types'

export interface CollectionMarketDisplay {
  value: number | null
  currency: string
  label: string | null
}

export function getCollectionMarketDisplay(item: CollectionItem): CollectionMarketDisplay {
  if (item.market_value !== null) {
    return { value: item.market_value, currency: item.source_currency ?? 'EUR', label: null }
  }
  const source = item.price_sources.find((candidate) => candidate.market === 'tcgplayer' && candidate.metrics.market !== undefined && candidate.metrics.market !== null)
  if (source) {
    return { value: source.metrics.market, currency: source.currency || 'USD', label: `TCGplayer · ${source.currency || 'USD'}` }
  }
  return { value: null, currency: 'EUR', label: null }
}
