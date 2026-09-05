import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { CollectionEditDialog } from './CollectionEditDialog'
import type { CollectionItemDetail } from '@/lib/types'

const fetchCollectionItemMock = vi.hoisted(() => vi.fn())
const updateCollectionItemMock = vi.hoisted(() => vi.fn())
vi.mock('@/lib/api', () => ({
  fetchCollectionItem: fetchCollectionItemMock,
  updateCollectionItem: updateCollectionItemMock,
}))

const detail: CollectionItemDetail = {
  id: 1,
  display_name: 'Test Card',
  card_name: 'Test Card',
  card_number: '1',
  printing_variant: 'normal',
  variant_label: null,
  treatment: null,
  source_variant: null,
  finish: 'normal',
  expansion_name: 'Test Set',
  expansion_set_code: 'test',
  game_code: 'pokemon',
  game_name: 'Pokémon',
  language: 'en',
  canonical_card_id: 1,
  release_kind: null,
  art_kind: null,
  printing_count: 1,
  reprint_count: 0,
  price_sources: [],
  condition: 'NM',
  grading_company: null,
  grade: null,
  quantity: 2,
  purchase_price: 5,
  purchase_currency: 'EUR',
  purchase_date: '2026-01-02',
  trade_value: null,
  status: 'KEEP',
  manual_entry: false,
  catalog_matched: true,
  manual_entry_note: null,
  notes: 'Original note',
  market_price: null,
  unrealized_pl: null,
  roi: null,
  image: null,
}

describe('CollectionEditDialog', () => {
  beforeEach(() => {
    fetchCollectionItemMock.mockReset()
    updateCollectionItemMock.mockReset()
    fetchCollectionItemMock.mockResolvedValue(detail)
    updateCollectionItemMock.mockResolvedValue({ ...detail, quantity: 3, notes: 'Updated note' })
  })

  it('loads current values and saves the ownership metadata', async () => {
    const onSaved = vi.fn()
    const onOpenChange = vi.fn()
    render(<CollectionEditDialog itemId={1} open onOpenChange={onOpenChange} onSaved={onSaved} />)

    expect(await screen.findByDisplayValue('2')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Original note')).toBeInTheDocument()
    fireEvent.change(screen.getByDisplayValue('2'), { target: { value: '3' } })
    fireEvent.change(screen.getByDisplayValue('Original note'), { target: { value: 'Updated note' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }))

    await waitFor(() => expect(updateCollectionItemMock).toHaveBeenCalledWith(1, expect.objectContaining({ quantity: 3, notes: 'Updated note', condition: 'NM' })))
    expect(onSaved).toHaveBeenCalled()
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })

  it('blocks duplicate submit and keeps the dialog open on error', async () => {
    let rejectUpdate: (error: Error) => void = () => undefined
    updateCollectionItemMock.mockReturnValue(new Promise((_, reject) => { rejectUpdate = reject }))
    const onOpenChange = vi.fn()
    render(<CollectionEditDialog itemId={1} open onOpenChange={onOpenChange} onSaved={vi.fn()} />)

    await screen.findByDisplayValue('2')
    const save = screen.getByRole('button', { name: 'Save changes' })
    fireEvent.click(save)
    fireEvent.click(save)
    expect(updateCollectionItemMock).toHaveBeenCalledTimes(1)
    expect(screen.getByRole('button', { name: 'Saving…' })).toBeDisabled()
    rejectUpdate(new Error('Save failed'))
    expect(await screen.findByRole('alert')).toHaveTextContent('Save failed')
    expect(onOpenChange).not.toHaveBeenCalledWith(false)
  })
})
