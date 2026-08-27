// Tipos espejo de backend/api/schemas.py -- Fase 6 (solo lectura).

export interface CardsWithoutMarketValue {
  count: number
  ids: number[]
}

export interface TcgBucket {
  market_value: number
  unique_cards: number
  total_cards: number
}

export interface OverviewResponse {
  total_cost: number
  cost_basis_row_count: number
  rows_without_cost: number
  total_market_value: number
  market_value_row_count: number
  unrealized_pl: number
  /** Fraccion (ej. 0.631), no porcentaje -- formatPercent() hace el *100 una sola vez. */
  roi: number | null
  total_cards: number
  unique_cards: number
  cards_without_market_value: CardsWithoutMarketValue
  value_by_tcg: Record<string, TcgBucket>
}

export interface CollectionItem {
  id: number
  display_name: string
  expansion_name: string | null
  expansion_set_code: string | null
  card_number: string | null
  variant_label: string | null
  game_code: string | null
  condition: string | null
  quantity: number
  purchase_price: number | null
  /** Trend Price de Cardmarket, snapshot mas reciente. null = sin precio (nunca 0). */
  market_value: number | null
  manual_entry: boolean
  status: string
  purchase_date: string | null
  image: CardImage | null
}

export interface CollectionListResponse {
  items: CollectionItem[]
  total: number
  page: number
  page_size: number
}

export interface MarketPriceValue {
  trend: number
  avg: number | null
  low: number | null
  avg30: number | null
  observed_at: string
  source: string
}

export interface CardImageFace {
  face_index: number
  small_url: string | null
  large_url: string | null
}

export interface CardImage {
  source: string
  match_quality: string
  faces: CardImageFace[]
}

export interface CollectionItemDetail {
  id: number
  display_name: string
  card_name: string | null
  card_number: string | null
  printing_variant: string | null
  variant_label: string | null
  expansion_name: string | null
  expansion_set_code: string | null
  game_code: string | null
  game_name: string | null
  condition: string | null
  grading_company: string | null
  grade: number | null
  quantity: number
  purchase_price: number | null
  purchase_currency: string | null
  purchase_date: string | null
  trade_value: number | null
  status: string
  manual_entry: boolean
  manual_entry_note: string | null
  notes: string | null
  market_price: MarketPriceValue | null
  unrealized_pl: number | null
  roi: number | null
  image: CardImage | null
}

export type SortOption = 'nombre' | 'valor' | 'fecha'

export interface CollectionQueryParams {
  game?: string
  status?: string
  search?: string
  sort?: SortOption
  page?: number
  page_size?: number
}

export interface CatalogItem {
  id: number
  name: string
  set_code: string | null
  expansion_name: string | null
  card_number: string | null
  rarity: string | null
  finish: string | null
  treatment: string | null
  language: string | null
  current_price: number | null
  ownership_status: 'none' | 'owned' | 'wishlist' | 'owned_wishlist'
  owned: boolean
  wishlist: boolean
  wishlist_item_id: number | null
  image: CardImage | null
}

export interface CatalogListResponse {
  items: CatalogItem[]
  total: number
  page: number
  page_size: number
}

export interface CatalogQueryParams {
  game?: string
  sets?: string
  search?: string
  ownership?: 'owned' | 'not_owned' | 'wishlist'
  rarity?: string
  finish?: 'nonfoil' | 'foil' | 'etched'
  treatment?: string
  page?: number
  page_size?: number
}

export interface WishlistItem {
  id: number
  card_id: number
  name: string
  set_code: string | null
  expansion_name: string | null
  card_number: string | null
  rarity: string | null
  finish: string | null
  treatment: string | null
  quantity_wanted: number
  priority: 'low' | 'medium' | 'high'
  max_price: number | null
  currency: string | null
  notes: string | null
  status: 'wanted' | 'acquired' | 'removed'
  current_price: number | null
  image: CardImage | null
}

export interface WishlistListResponse {
  items: WishlistItem[]
}

export const GAME_OPTIONS = [
  { value: 'magic', label: 'Magic' },
  { value: 'pokemon', label: 'Pokemon' },
  { value: 'one_piece', label: 'One Piece' },
] as const

export const STATUS_OPTIONS = ['KEEP', 'HOLD', 'TRADE', 'SELL', 'WANT'] as const

export const GAME_LABELS: Record<string, string> = {
  magic: 'Magic',
  pokemon: 'Pokemon',
  one_piece: 'One Piece',
  sin_catalogar: 'Sin catalogar',
}
