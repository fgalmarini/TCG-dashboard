import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { CollectionTable } from './CollectionTable'
import { getCollectionMarketDisplay } from '@/lib/collectionPricing'
import type { CollectionItem } from '@/lib/types'

const navigateMock = vi.hoisted(() => vi.fn())
vi.mock('react-router-dom', () => ({ useNavigate: () => navigateMock }))

function makeItem(overrides: Partial<CollectionItem> = {}): CollectionItem {
  return {
    id: 1,
    display_name: 'Test Card',
    expansion_name: 'Test Set',
    expansion_set_code: 'test',
    card_number: '1',
    variant_label: null,
    game_code: 'pokemon',
    language: 'en',
    release_kind: null,
    art_kind: null,
    printing_count: 1,
    reprint_count: 0,
    price_sources: [],
    condition: null,
    quantity: 1,
    purchase_price: null,
    market_value: null,
    source_currency: 'EUR',
    manual_entry: false,
    catalog_matched: true,
    status: 'KEEP',
    purchase_date: null,
    image: null,
    ...overrides,
  }
}

describe('collection market display', () => {
  it('prefers Cardmarket over TCGplayer', () => {
    const display = getCollectionMarketDisplay(makeItem({
      market_value: 4.5,
      price_sources: [{ role: 'secondary', provider: 'pokemon_tcg_api', market: 'tcgplayer', currency: 'USD', source_variant: 'normal', metrics: { market: 8, low: 6 }, source_updated_at: null, observed_at: '2026-01-01', provenance: '{}', confidence: 'high' }],
    }))
    expect(display).toEqual({ value: 4.5, currency: 'EUR', label: null })
  })

  it('uses only TCGplayer Market when Cardmarket is null', () => {
    const display = getCollectionMarketDisplay(makeItem({
      price_sources: [{ role: 'secondary', provider: 'pokemon_tcg_api', market: 'tcgplayer', currency: 'USD', source_variant: 'normal', metrics: { market: 8, low: 6 }, source_updated_at: null, observed_at: '2026-01-01', provenance: '{}', confidence: 'high' }],
    }))
    expect(display).toEqual({ value: 8, currency: 'USD', label: 'TCGplayer · USD' })
  })

  it('returns no price when neither source exists', () => {
    expect(getCollectionMarketDisplay(makeItem())).toEqual({ value: null, currency: 'EUR', label: null })
  })
})

describe('CollectionTable', () => {
  beforeEach(() => navigateMock.mockReset())

  it('does not render Condition and shows one secondary market value', () => {
    render(<CollectionTable
      items={[makeItem({ price_sources: [{ role: 'secondary', provider: 'pokemon_tcg_api', market: 'tcgplayer', currency: 'USD', source_variant: 'normal', metrics: { market: 8, low: 6 }, source_updated_at: null, observed_at: '2026-01-01', provenance: '{}', confidence: 'high' }] })]}
      onRemove={vi.fn()}
      onEdit={vi.fn()}
    />)
    expect(screen.queryByRole('columnheader', { name: 'Condition' })).not.toBeInTheDocument()
    expect(screen.getByText('TCGplayer · USD')).toBeInTheDocument()
    expect(screen.queryByText('Market')).not.toBeInTheDocument()
    expect(screen.queryByText('Low')).not.toBeInTheDocument()
  })

  it('stops row navigation for Edit and keeps Remove available', () => {
    const onEdit = vi.fn()
    const onRemove = vi.fn()
    render(<CollectionTable items={[makeItem()]} onRemove={onRemove} onEdit={onEdit} />)

    fireEvent.click(screen.getByRole('button', { name: 'Edit' }))
    expect(onEdit).toHaveBeenCalledWith(1)
    expect(navigateMock).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: 'Remove' }))
    expect(onRemove).toHaveBeenCalledWith(1)
    expect(navigateMock).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('row', { name: /Test Card/ }))
    expect(navigateMock).toHaveBeenCalledWith('/collection/1')
  })
})
