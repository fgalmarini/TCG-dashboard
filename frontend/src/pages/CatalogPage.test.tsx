import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { CatalogPage } from './CatalogPage'

const { mockData } = vi.hoisted(() => ({
  mockData: {
    items: [
      { id: 1, game_code: 'magic', name: 'Belladonna Took', set_code: 'hob', card_number: '214', language: 'en', treatment: 'traditional_foil', finish: 'foil', art_kind: 'parallel', reprint_count: 0, ownership_status: 'none', owned: false, wishlist: false, wishlist_item_id: null, current_price: null, price_currency: null, price_sources: [], image: null },
      { id: 2, game_code: 'magic', name: 'Belladonna Took', set_code: 'hob', card_number: '250', language: 'en', treatment: 'surge_foil', finish: 'foil', art_kind: 'parallel', reprint_count: 0, ownership_status: 'none', owned: false, wishlist: false, wishlist_item_id: null, current_price: null, price_currency: null, price_sources: [], image: null },
      { id: 3, game_code: 'magic', name: 'Beorn the Fierce', set_code: 'hob', card_number: '230', language: 'en', treatment: 'traditional_foil', finish: 'foil', art_kind: 'parallel', reprint_count: 0, ownership_status: 'none', owned: false, wishlist: false, wishlist_item_id: null, current_price: null, price_currency: null, price_sources: [], image: null },
      { id: 4, game_code: 'magic', name: 'Beorn the Fierce', set_code: 'hob', card_number: '266', language: 'en', treatment: 'surge_foil', finish: 'foil', art_kind: 'parallel', reprint_count: 0, ownership_status: 'none', owned: false, wishlist: false, wishlist_item_id: null, current_price: null, price_currency: null, price_sources: [], image: null },
    ],
    total: 4,
    identity_total: 2,
    page_size: 24,
  },
}))

vi.mock('@/lib/useApi', () => ({
  useApi: () => ({ data: mockData, error: null, loading: false, reload: vi.fn() }),
}))

vi.mock('@/lib/api', () => ({
  addToCollection: vi.fn(),
  addToWishlist: vi.fn(),
  fetchCatalog: vi.fn(),
  fetchCatalogOptions: vi.fn().mockResolvedValue({ languages: [], sets: [] }),
  removeFromWishlist: vi.fn(),
}))

vi.mock('@/components/collection/CardImage', () => ({
  CardArt: () => <div aria-hidden="true" />,
}))

vi.mock('@/components/shared/MarketPrice', () => ({
  MarketPrice: () => null,
}))

vi.mock('@/components/shared/SecondaryMarketPrice', () => ({
  SecondaryMarketPrice: () => null,
}))

describe('CatalogPage metadata', () => {
  beforeEach(() => vi.clearAllMocks())

  it('labels and formats treatment, finish, and variant without empty ownership state', () => {
    render(<MemoryRouter><CatalogPage /></MemoryRouter>)

    expect(screen.getAllByText('Traditional Foil')).toHaveLength(2)
    expect(screen.getAllByText('Surge Foil')).toHaveLength(2)
    expect(screen.getAllByText('Foil')).toHaveLength(4)
    expect(screen.getAllByText('Parallel')).toHaveLength(4)
    expect(screen.getAllByText('Treatment')).toHaveLength(4)
    expect(screen.getAllByText('Finish')).toHaveLength(4)
    expect(screen.getAllByText('Variant')).toHaveLength(4)
    expect(screen.queryByText('Serialized')).not.toBeInTheDocument()
    expect(screen.queryByText('none')).not.toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'Add to Collection' })).toHaveLength(4)
    expect(screen.getAllByRole('button', { name: 'Add to Wishlist' })).toHaveLength(4)
  })
})
