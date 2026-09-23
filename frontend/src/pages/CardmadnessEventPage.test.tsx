import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { CardmadnessEventPage } from './CardmadnessEventPage'

vi.mock('@/lib/api', () => ({
  fetchEventWishlist: vi.fn().mockResolvedValue({
    event_code: 'cardmadness-2026',
    items: [{
      wishlist_item: {
        id: 1, card_id: 11, canonical_card_id: 4, game_code: 'magic', name: 'Smaug the Magnificent',
        set_code: 'hob', expansion_name: 'The Hobbit', card_number: '265', rarity: 'mythic', finish: 'foil',
        treatment: 'surge_foil', quantity_wanted: 1, priority: 'high', target_price: null, max_price: null,
        currency: 'EUR', notes: null, status: 'wanted', acquired_at: null, removed_at: null, current_price: null,
        language: 'en', release_kind: 'special', art_kind: 'parallel', printing_count: 2, reprint_count: 0,
        source: null, resolution_method: null, price_currency: null, matched: true,
        image: { source: 'scryfall', actual_image_language: 'en', requested_language: 'en', is_language_fallback: false,
          match_quality: 'exact', faces: [{ face_index: 0, small_url: 'https://cards.scryfall.io/small/hob/265.jpg', large_url: 'https://cards.scryfall.io/large/hob/265.jpg' }] },
      },
      target_prices: { low: 24999.99, avg30: 10100 },
      traditional_foil: { card_id: 10, card_number: '229', low: null },
    }],
  }),
}))

describe('CardmadnessEventPage', () => {
  beforeEach(() => vi.clearAllMocks())

  it('shows the Surge target and exact Traditional Foil alternative with null as a dash', async () => {
    render(<CardmadnessEventPage />)
    await waitFor(() => expect(screen.getByText('Smaug the Magnificent')).toBeInTheDocument())
    expect(screen.getByText('Surge Foil · Target')).toBeInTheDocument()
    expect(screen.getByText('Traditional Foil · Alternative')).toBeInTheDocument()
    expect(screen.getByAltText('Smaug the Magnificent')).toHaveAttribute('src', 'https://cards.scryfall.io/small/hob/265.jpg')
    expect(screen.getAllByText((_, node) => node?.textContent?.includes('24.999,99') ?? false).length).toBeGreaterThan(0)
    expect(screen.getAllByText((_, node) => node?.textContent?.includes('10.100,00') ?? false).length).toBeGreaterThan(0)
    expect(screen.getByText('#229 · Low: —')).toBeInTheDocument()
  })
})
