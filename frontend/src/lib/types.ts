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

export interface TopCard {
  collection_item_id: number
  card_id: number | null
  name: string
  game_code: string | null
  expansion_name: string | null
  set_code: string | null
  card_number: string | null
  variant_label: string | null
  treatment: string | null
  source_variant: string | null
  finish: string | null
  language: string | null
  market_value: number
  price_currency: string | null
  price_variation: number | null
  image: CardImage | null
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
  top_cards: TopCard[]
}

export interface CollectionItem {
  id: number
  display_name: string
  expansion_name: string | null
  expansion_set_code: string | null
  card_number: string | null
  variant_label: string | null
  game_code: string | null
  language: string | null
  release_kind: string | null
  art_kind: string | null
  printing_count: number
  reprint_count: number
  condition: string | null
  quantity: number
  purchase_price: number | null
  /** Cardmarket Low vigente. null = sin resolución vigente (nunca 0). */
  market_value: number | null
  cardmarket_low?: number | null
  cardmarket_trend?: number | null
  source_currency?: string | null
  manual_entry: boolean
  catalog_matched: boolean
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
  trend: number | null
  avg: number | null
  low: number | null
  avg30: number | null
  avg1?: number | null
  avg7?: number | null
  cardmarket_low?: number | null
  cardmarket_trend?: number | null
  source_currency?: string | null
  observed_at: string | null
  source: string
  currency: string
  resolution_method: string | null
  estimated_dealer_cash?: number | null
  estimated_dealer_cash_min?: number | null
  estimated_dealer_cash_max?: number | null
  estimated_trade_value?: number | null
  estimated_trade_value_min?: number | null
  estimated_trade_value_max?: number | null
}

export interface CardImageFace {
  face_index: number
  small_url: string | null
  large_url: string | null
}

export interface CardImage {
  source: string
  actual_image_language: string | null
  requested_language: string | null
  is_language_fallback: boolean
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
  treatment?: string | null
  source_variant?: string | null
  finish?: string | null
  expansion_name: string | null
  expansion_set_code: string | null
  game_code: string | null
  game_name: string | null
  language: string | null
  canonical_card_id: number | null
  release_kind: string | null
  art_kind: string | null
  printing_count: number
  reprint_count: number
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
  catalog_matched: boolean
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
  language?: string
  status?: string
  search?: string
  sort?: SortOption
  page?: number
  page_size?: number
}

export interface CatalogItem {
  id: number
  canonical_card_id: number | null
  game_code: string
  name: string
  set_code: string | null
  expansion_name: string | null
  card_number: string | null
  rarity: string | null
  finish: string | null
  treatment: string | null
  language: string | null
  release_kind: string | null
  art_kind: string | null
  printing_count: number
  reprint_count: number
  current_price: number | null
  cardmarket_low?: number | null
  cardmarket_trend?: number | null
  cardmarket_avg1?: number | null
  cardmarket_avg7?: number | null
  cardmarket_avg30?: number | null
  source_currency?: string | null
  estimated_dealer_cash?: number | null
  estimated_dealer_cash_min?: number | null
  estimated_dealer_cash_max?: number | null
  estimated_trade_value?: number | null
  estimated_trade_value_min?: number | null
  estimated_trade_value_max?: number | null
  price_source: string | null
  resolution_method: string | null
  price_currency: string | null
  price_external_id: string | null
  price_sample_size: number
  lowest_price: number | null
  median_price: number | null
  price_confidence: string | null
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
  language?: string
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
  canonical_card_id: number | null
  game_code: string
  name: string
  set_code: string | null
  expansion_name: string | null
  card_number: string | null
  rarity: string | null
  finish: string | null
  treatment: string | null
  quantity_wanted: number
  priority: 'low' | 'medium' | 'high' | 'none'
  target_price: number | null
  max_price: number | null
  currency: string | null
  notes: string | null
  status: 'wanted' | 'acquired' | 'removed'
  acquired_at: string | null
  removed_at: string | null
  current_price: number | null
  cardmarket_low?: number | null
  cardmarket_trend?: number | null
  cardmarket_avg1?: number | null
  cardmarket_avg7?: number | null
  cardmarket_avg30?: number | null
  source_currency?: string | null
  language: string | null
  release_kind: string | null
  art_kind: string | null
  printing_count: number
  reprint_count: number
  source: string | null
  resolution_method: string | null
  price_currency: string | null
  matched: boolean
  image: CardImage | null
}

export interface WishlistSummary {
  wanted: number
  acquired: number
  missing_price: number
  unmatched: number
  estimated_total: number
}

export interface WishlistListResponse {
  items: WishlistItem[]
  total: number
  summary: WishlistSummary
}

export interface WishlistQueryParams {
  status?: 'wanted' | 'acquired' | 'removed' | 'all'
  priority?: string
  game?: string
  language?: string
  sets?: string
  finish?: 'nonfoil' | 'foil' | 'etched'
  has_price?: boolean
  matched?: boolean
  sort?: 'priority' | 'name' | 'current_price' | 'target_price' | 'max_price'
}

export interface MatchCandidate {
  id: number
  name: string
  set_code: string | null
  expansion_name: string | null
  card_number: string | null
  finish: string | null
  treatment: string | null
  language: string | null
  image: CardImage | null
}

export interface CollectionMatchContext {
  item_id: number
  name: string
  set_code: string | null
  card_number: string | null
  finish: string | null
  treatment: string | null
  language: string | null
  source: string
  source_note: string | null
  candidates: MatchCandidate[]
}

export const GAME_OPTIONS = [
  { value: 'magic', label: 'Magic' },
  { value: 'one_piece', label: 'One Piece' },
] as const

export const LANGUAGE_OPTIONS = [
  { value: 'en', label: 'English' },
  { value: 'jp', label: 'Japanese' },
] as const

export interface CatalogOption {
  value: string
  label: string
}

export interface CatalogOptionsResponse {
  games: CatalogOption[]
  languages: CatalogOption[]
  sets: CatalogOption[]
}

export interface CatalogDetailResponse {
  printing: CatalogItem
  printings: CatalogItem[]
}

export const STATUS_OPTIONS = ['KEEP', 'HOLD', 'TRADE', 'SELL', 'WANT'] as const

export const GAME_LABELS: Record<string, string> = {
  magic: 'Magic',
  pokemon: 'Pokemon',
  one_piece: 'One Piece',
  sin_catalogar: 'Sin catalogar',
}
