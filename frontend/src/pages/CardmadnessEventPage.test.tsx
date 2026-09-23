import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { CardmadnessEventPage } from './CardmadnessEventPage'
import { fetchEventWishlist } from '@/lib/api'

vi.mock('@/lib/api', () => ({
  fetchEventWishlist: vi.fn().mockResolvedValue((() => {
    const item = {
      wishlist_item: {
        id: 1, card_id: 11, canonical_card_id: 4, game_code: 'magic', name: 'Smaug the Magnificent',
        set_code: 'hob', expansion_name: 'The Hobbit', card_number: '056', rarity: 'mythic', finish: 'foil',
        treatment: 'surge_foil', quantity_wanted: 1, priority: 'high', target_price: null, max_price: null,
        currency: 'EUR', notes: null, status: 'wanted', acquired_at: null, removed_at: null, current_price: null,
        language: 'en', release_kind: 'special', art_kind: 'parallel', printing_count: 2, reprint_count: 0,
        source: null, resolution_method: null, price_currency: null, matched: true,
        image: { source: 'scryfall', actual_image_language: 'en', requested_language: 'en', is_language_fallback: false,
          match_quality: 'exact', faces: [{ face_index: 0, small_url: 'https://cards.scryfall.io/small/hob/265.jpg', large_url: 'https://cards.scryfall.io/large/hob/265.jpg' }] },
      },
      target_prices: { low: 24999.99, avg30: 10100 },
      traditional_foil: { card_id: 10, card_number: '054', low: null },
    }
    return {
      event_code: 'cardmadness-2026',
      items: [item, {
        ...item,
        wishlist_item: { ...item.wishlist_item, id: 3, card_id: 13, name: 'Gandalf', card_number: '106' },
        traditional_foil: { card_id: 14, card_number: '100', low: null },
      }],
    }
  })()),
}))

describe('CardmadnessEventPage', () => {
  beforeEach(() => vi.clearAllMocks())

  it('shows the Surge target and exact Traditional Foil alternative with null as a dash', async () => {
    render(<CardmadnessEventPage />)
    await waitFor(() => expect(screen.getByText('Smaug the Magnificent')).toBeInTheDocument())
    expect(screen.getAllByText('Surge Foil · Target')).toHaveLength(2)
    expect(screen.getAllByText('Traditional Foil · Alternative')).toHaveLength(2)
    expect(screen.getByText('HOB · #056 · Surge Foil')).toBeInTheDocument()
    expect(screen.getByAltText('Smaug the Magnificent')).toHaveAttribute('src', 'https://cards.scryfall.io/small/hob/265.jpg')
    expect(screen.getAllByText((_, node) => node?.textContent?.includes('24.999,99') ?? false).length).toBeGreaterThan(0)
    expect(screen.getAllByText((_, node) => node?.textContent?.includes('10.100,00') ?? false).length).toBeGreaterThan(0)
    expect(screen.getByText('#054 · Low: —')).toBeInTheDocument()
  })

  it('finds an event item by its target or Traditional collector number, including without leading zeros', async () => {
    render(<CardmadnessEventPage />)
    await waitFor(() => expect(screen.getByText('Smaug the Magnificent')).toBeInTheDocument())
    const search = screen.getByRole('textbox', { name: 'Search cards' })

    for (const number of ['056', '56', '054']) {
      fireEvent.change(search, { target: { value: number } })
      expect(screen.getByText('Event wishlist · 1 cards')).toBeInTheDocument()
      expect(screen.getByText('Smaug the Magnificent')).toBeInTheDocument()
    }
    fireEvent.change(search, { target: { value: '106' } })
    expect(screen.getByText('Gandalf')).toBeInTheDocument()
    expect(screen.getByText('Event wishlist · 1 cards')).toBeInTheDocument()
    fireEvent.change(search, { target: { value: '100' } })
    expect(screen.getByText('Gandalf')).toBeInTheDocument()
    expect(screen.getByText('Event wishlist · 1 cards')).toBeInTheDocument()
    fireEvent.change(search, { target: { value: 'Smaug' } })
    expect(screen.getByText('Smaug the Magnificent')).toBeInTheDocument()
    expect(screen.getByText('Event wishlist · 1 cards')).toBeInTheDocument()
  })

  it('shows a Traditional Foil target without inventing a Surge comparison', async () => {
    vi.mocked(fetchEventWishlist).mockResolvedValueOnce({
      event_code: 'cardmadness-2026',
      items: [{
        wishlist_item: {
          id: 2, card_id: 12, canonical_card_id: 5, game_code: 'magic', name: 'Traditional Only Card',
          set_code: 'hoc', expansion_name: 'The Hobbit', card_number: '093', rarity: 'rare', finish: 'foil',
          treatment: 'traditional_foil', quantity_wanted: 1, priority: 'medium', target_price: null, max_price: null,
          currency: 'EUR', notes: null, status: 'wanted', acquired_at: null, removed_at: null, current_price: null,
          language: 'en', release_kind: 'special', art_kind: 'parallel', printing_count: 1, reprint_count: 0,
          source: null, resolution_method: null, price_currency: 'EUR', matched: true, image: null,
        },
        target_prices: {},
        traditional_foil: null,
      }],
    } as Awaited<ReturnType<typeof fetchEventWishlist>>)
    render(<CardmadnessEventPage />)
    await waitFor(() => expect(screen.getByText('Traditional Only Card')).toBeInTheDocument())
    expect(screen.getByText('HOC · #093 · Traditional Foil')).toBeInTheDocument()
    expect(screen.getByText('Traditional Foil · Target')).toBeInTheDocument()
    expect(screen.getAllByText('Low: —').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Avg30: —').length).toBeGreaterThan(0)
    expect(screen.queryByText('Surge Foil · Target')).not.toBeInTheDocument()
  })
})
