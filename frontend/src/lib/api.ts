// Cliente API tipado para backend/api/ (Fase 6, solo lectura).

import type {
  CollectionItemDetail,
  CollectionListResponse,
  CollectionQueryParams,
  CatalogListResponse,
  CatalogDetailResponse,
  CatalogOptionsResponse,
  CatalogQueryParams,
  OverviewResponse,
  WishlistItem,
  WishlistListResponse,
  WishlistQueryParams,
  CollectionMatchContext,
} from './types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, params?: Record<string, string | number | boolean | undefined>): Promise<T> {
  const url = new URL(`${API_BASE_URL}${path}`)
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== '') {
        url.searchParams.set(key, String(value))
      }
    }
  }

  let response: Response
  try {
    response = await fetch(url.toString())
  } catch {
    throw new ApiError('No se pudo conectar con la API (backend/api corriendo en :8000?).', 0)
  }

  if (!response.ok) {
    if (response.status === 404) {
      throw new ApiError('No encontrado.', 404)
    }
    throw new ApiError(`Error de la API (${response.status}).`, response.status)
  }

  return (await response.json()) as T
}

export function fetchOverview(): Promise<OverviewResponse> {
  return request<OverviewResponse>('/api/overview')
}

export function fetchCollection(params: CollectionQueryParams): Promise<CollectionListResponse> {
  return request<CollectionListResponse>('/api/collection', params as Record<string, string | number | undefined>)
}

export function fetchCollectionItem(id: number): Promise<CollectionItemDetail> {
  return request<CollectionItemDetail>(`/api/collection/${id}`)
}

export function removeFromCollection(id: number): Promise<void> {
  return mutate<void>(`/api/collection/${id}`, 'DELETE')
}

export function fetchCatalog(params: CatalogQueryParams): Promise<CatalogListResponse> {
  return request<CatalogListResponse>('/api/catalog', params as Record<string, string | number | undefined>)
}

export function fetchCatalogOptions(game?: string): Promise<CatalogOptionsResponse> {
  return request<CatalogOptionsResponse>('/api/catalog/options', game ? { game } : undefined)
}

export function fetchCatalogItem(id: number): Promise<CatalogDetailResponse> {
  return request<CatalogDetailResponse>(`/api/catalog/${id}`)
}

export function fetchWishlist(params: WishlistQueryParams = {}): Promise<WishlistListResponse> {
  return request<WishlistListResponse>('/api/wishlist', params as Record<string, string | number | boolean | undefined>)
}

async function mutate<T>(path: string, method: string, body?: unknown): Promise<T> {
  const url = `${API_BASE_URL}${path}`
  let response: Response
  try {
    response = await fetch(url, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new ApiError('No se pudo conectar con la API (backend/api corriendo en :8000?).', 0)
  }
  if (!response.ok) {
    throw new ApiError(`Error de la API (${response.status}).`, response.status)
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export function addToWishlist(card_id: number): Promise<WishlistItem> {
  return mutate<WishlistItem>('/api/wishlist', 'POST', { card_id })
}

export function addToCollection(card_id: number, quantity = 1, finish?: string | null, treatment?: string | null): Promise<CollectionItemDetail> {
  return mutate<CollectionItemDetail>('/api/collection', 'POST', { card_id, quantity, finish, treatment })
}

export function updateWishlist(id: number, payload: { priority?: string; quantity_wanted?: number; target_price?: number | null; max_price?: number | null; currency?: string | null; notes?: string | null }): Promise<WishlistItem> {
  return mutate<WishlistItem>(`/api/wishlist/${id}`, 'PATCH', payload)
}

export function removeFromWishlist(id: number): Promise<void> {
  return mutate<void>(`/api/wishlist/${id}`, 'DELETE')
}

export function markWishlistAcquired(id: number): Promise<WishlistItem> {
  return mutate<WishlistItem>(`/api/wishlist/${id}/mark-acquired`, 'POST')
}

export function restoreWishlist(id: number): Promise<WishlistItem> {
  return mutate<WishlistItem>(`/api/wishlist/${id}/restore`, 'POST')
}

export function fetchMatchCandidates(id: number, search?: string): Promise<CollectionMatchContext> {
  return request<CollectionMatchContext>(`/api/collection/${id}/match-candidates`, search ? { search } : undefined)
}

export function resolveCollectionMatch(id: number, card_id: number): Promise<CollectionItemDetail> {
  return mutate<CollectionItemDetail>(`/api/collection/${id}/resolve-match`, 'POST', { card_id })
}

export function exportWishlist(params: WishlistQueryParams = {}): string {
  const url = new URL(`${API_BASE_URL}/api/wishlist/export.csv`)
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== '') url.searchParams.set(key, String(value))
  }
  return url.toString()
}
