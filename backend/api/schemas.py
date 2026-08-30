"""Modelos Pydantic de backend/api/.

Collection remains read-only except for the explicit catalog match resolver; Wishlist
exposes the planning operations for this sprint.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from .queries import (
    CardImageData,
    CardImageFaceData,
    CatalogRow,
    CollectionMatchContext,
    CollectionRow,
    MatchCandidateRow,
    TcgBucketData,
    WishlistRow,
)

# --- /api/overview ---------------------------------------------------------------


class CardsWithoutMarketValue(BaseModel):
    count: int = Field(..., description="Cantidad de filas con market_trend IS NULL (altas manuales hoy, o producto sin snapshot todavia).")
    ids: list[int] = Field(..., description="collection_items.id de esas filas.")


class TcgBucket(BaseModel):
    market_value: float = Field(..., description="Suma de trend*quantity de las filas de este bucket con precio conocido. 0.0 si ninguna fila del bucket tiene precio todavia (nunca un precio inventado por carta).")
    unique_cards: int
    total_cards: int

    @classmethod
    def from_data(cls, data: TcgBucketData) -> "TcgBucket":
        return cls(
            market_value=round(data.market_value, 2),
            unique_cards=data.unique_cards,
            total_cards=data.total_cards,
        )


class OverviewResponse(BaseModel):
    total_cost: float = Field(..., description="SUM(purchase_price * quantity) sobre filas con purchase_price no nulo.")
    cost_basis_row_count: int = Field(..., description="Cantidad de filas (de unique_cards) que entran en total_cost.")
    rows_without_cost: int = Field(..., description="Cantidad de filas sin purchase_price -- no se asume 0.")
    total_market_value: float = Field(..., description="SUM(trend_mas_reciente * quantity) sobre filas con precio de mercado conocido (market_trend no nulo).")
    market_value_row_count: int = Field(..., description="Cantidad de filas (de unique_cards) que entran en total_market_value. Subconjunto distinto de cost_basis_row_count -- no asumir que son las mismas filas.")
    unrealized_pl: float = Field(..., description="total_market_value - total_cost.")
    roi: float | None = Field(
        None,
        description="unrealized_pl / total_cost, expresado como FRACCION (ej. 0.631, no 63.1). El frontend hace el *100 al formatear. None (nunca 0 ni excepcion) si total_cost == 0.",
    )
    total_cards: int = Field(..., description="SUM(quantity) sobre todas las filas.")
    unique_cards: int = Field(..., description="COUNT(*) de collection_items.")
    cards_without_market_value: CardsWithoutMarketValue
    value_by_tcg: dict[str, TcgBucket] = Field(
        ...,
        description="Agrupado por games.code. Bucket 'sin_catalogar' para filas sin game_id resoluble (card_id IS NULL) -- nunca descartado silenciosamente.",
    )
    top_cards: list[TopCardOut] = Field(..., max_length=10)


# --- /api/collection ---------------------------------------------------------------


class CardImageFaceOut(BaseModel):
    face_index: int
    small_url: str | None
    large_url: str | None

    @classmethod
    def from_data(cls, data: CardImageFaceData) -> "CardImageFaceOut":
        return cls(face_index=data.face_index, small_url=data.small_url, large_url=data.large_url)


class CardImageOut(BaseModel):
    source: str
    actual_image_language: str | None
    requested_language: str | None
    is_language_fallback: bool
    match_quality: str
    faces: list[CardImageFaceOut]

    @classmethod
    def from_data(cls, data: CardImageData | None) -> "CardImageOut | None":
        if data is None or not data.faces:
            return None
        return cls(
            source=data.source,
            actual_image_language=data.actual_image_language,
            requested_language=data.requested_language,
            is_language_fallback=data.is_language_fallback,
            match_quality=data.match_quality,
            faces=[CardImageFaceOut.from_data(face) for face in data.faces],
        )


class TopCardOut(BaseModel):
    collection_item_id: int
    card_id: int | None
    name: str
    game_code: str | None
    expansion_name: str | None
    set_code: str | None
    card_number: str | None
    variant_label: str | None
    treatment: str | None
    source_variant: str | None
    finish: str | None
    language: str | None
    market_value: float
    price_currency: str | None
    price_variation: float | None
    image: CardImageOut | None

    @classmethod
    def from_row(cls, row: CollectionRow) -> "TopCardOut":
        return cls(
            collection_item_id=row.id,
            card_id=row.card_id,
            name=row.display_name,
            game_code=row.game_code,
            expansion_name=row.expansion_name,
            set_code=row.expansion_set_code,
            card_number=row.card_number,
            variant_label=row.variant_label,
            treatment=row.treatment,
            source_variant=row.source_variant,
            finish=row.finish,
            language=row.language,
            market_value=row.market_trend,
            price_currency=row.price_currency,
            price_variation=row.price_variation,
            image=CardImageOut.from_data(row.image),
        )


class CollectionItemOut(BaseModel):
    id: int
    display_name: str = Field(..., description="card.name si existe; si no (alta manual), manual_entry_note o notes tal cual, sin parsear.")
    expansion_name: str | None
    expansion_set_code: str | None
    card_number: str | None
    variant_label: str | None
    game_code: str | None
    language: str | None
    release_kind: str | None
    art_kind: str | None
    printing_count: int
    reprint_count: int
    condition: str | None
    quantity: int
    purchase_price: float | None
    market_value: float | None = Field(None, description="Cardmarket Low vigente. None = sin resolución vigente/precio (nunca 0).")
    cardmarket_low: float | None = None
    cardmarket_trend: float | None = None
    cardmarket_avg1: float | None = None
    cardmarket_avg7: float | None = None
    cardmarket_avg30: float | None = None
    source_currency: str | None = None
    estimated_dealer_cash: float | None = None
    estimated_dealer_cash_min: float | None = None
    estimated_dealer_cash_max: float | None = None
    estimated_trade_value: float | None = None
    estimated_trade_value_min: float | None = None
    estimated_trade_value_max: float | None = None
    manual_entry: bool = Field(..., description="Como entro la carta a la coleccion -- senal independiente de si tiene precio de mercado hoy.")
    catalog_matched: bool
    match_status: str = "unmatched"
    match_quality: str | None = None
    match_reason: str | None = None
    status: str
    purchase_date: str | None
    image: CardImageOut | None = Field(
        None,
        description="Imagen normalizada desde card_images; puede ser fallback visual de otro idioma sin cambiar el idioma del printing.",
    )

    @classmethod
    def from_row(cls, row: CollectionRow) -> "CollectionItemOut":
        return cls(
            id=row.id,
            display_name=row.display_name,
            expansion_name=row.expansion_name,
            expansion_set_code=row.expansion_set_code,
            card_number=row.card_number,
            variant_label=row.variant_label,
            game_code=row.game_code,
            language=row.language,
            release_kind=row.release_kind,
            art_kind=row.art_kind,
            printing_count=row.printing_count,
            reprint_count=row.reprint_count,
            condition=row.condition,
            quantity=row.quantity,
            purchase_price=row.purchase_price,
            market_value=row.market_trend,
            cardmarket_low=row.cardmarket_low,
            cardmarket_trend=row.cardmarket_trend,
            source_currency=row.source_currency,
            estimated_dealer_cash=round(row.market_trend * .70, 2) if row.market_trend is not None else None,
            estimated_dealer_cash_min=round(row.market_trend * .60, 2) if row.market_trend is not None else None,
            estimated_dealer_cash_max=round(row.market_trend * .75, 2) if row.market_trend is not None else None,
            estimated_trade_value=round(row.market_trend * .80, 2) if row.market_trend is not None else None,
            estimated_trade_value_min=round(row.market_trend * .70, 2) if row.market_trend is not None else None,
            estimated_trade_value_max=round(row.market_trend * .85, 2) if row.market_trend is not None else None,
            manual_entry=row.manual_entry,
            catalog_matched=row.catalog_matched,
            match_status=row.match_status,
            match_quality=row.match_quality,
            match_reason=row.match_reason,
            status=row.status,
            purchase_date=row.purchase_date,
            image=CardImageOut.from_data(row.image),
        )


class CollectionListResponse(BaseModel):
    items: list[CollectionItemOut]
    total: int
    page: int
    page_size: int


class MarketPriceOut(BaseModel):
    trend: float | None
    avg: float | None
    low: float | None
    avg30: float | None
    avg1: float | None = None
    avg7: float | None = None
    cardmarket_low: float | None = None
    cardmarket_trend: float | None = None
    source_currency: str | None = None
    observed_at: str | None
    source: str = "cardmarket"
    currency: str = "EUR"
    resolution_method: str | None = None
    estimated_dealer_cash: float | None = None
    estimated_dealer_cash_min: float | None = None
    estimated_dealer_cash_max: float | None = None
    estimated_trade_value: float | None = None
    estimated_trade_value_min: float | None = None
    estimated_trade_value_max: float | None = None


class CollectionItemDetailOut(BaseModel):
    id: int
    display_name: str
    card_name: str | None
    card_number: str | None
    printing_variant: str | None
    variant_label: str | None
    treatment: str | None = None
    source_variant: str | None = None
    finish: str | None = None
    expansion_name: str | None
    expansion_set_code: str | None
    game_code: str | None
    game_name: str | None
    language: str | None
    canonical_card_id: int | None
    release_kind: str | None
    art_kind: str | None
    printing_count: int
    reprint_count: int
    condition: str | None
    grading_company: str | None
    grade: float | None
    quantity: int
    purchase_price: float | None
    purchase_currency: str | None
    purchase_date: str | None
    trade_value: float | None
    status: str
    manual_entry: bool
    catalog_matched: bool
    manual_entry_note: str | None
    notes: str | None
    market_price: MarketPriceOut | None = Field(
        None,
        description="Bloque separado y explicito -- None si no hay snapshot de precio, nunca un objeto con campos en 0 (AGENTS.md seccion 25).",
    )
    unrealized_pl: float | None = Field(None, description="(market_price.trend - purchase_price) * quantity, o None si falta costo/precio.")
    roi: float | None = Field(None, description="unrealized_pl / (purchase_price * quantity), o None si falta costo/precio o costo es 0.")
    image: CardImageOut | None = Field(
        None,
        description="Imagen normalizada desde card_images; el metadata indica si es fallback visual.",
    )

    @classmethod
    def from_row(cls, row: CollectionRow) -> "CollectionItemDetailOut":
        market_price = None
        if row.has_market_value and row.price_observed_at is not None:
            market_price = MarketPriceOut(
                trend=row.cardmarket_trend,
                avg=row.market_avg,
                low=row.market_low,
                avg30=row.market_avg30,
                avg1=row.cardmarket_avg1,
                avg7=row.cardmarket_avg7,
                cardmarket_low=row.cardmarket_low,
                cardmarket_trend=row.cardmarket_trend,
                source_currency=row.source_currency,
                observed_at=row.price_observed_at,
                source=row.price_source or "cardmarket",
                currency=row.price_currency or "EUR",
                resolution_method=row.resolution_method,
                estimated_dealer_cash=round(row.market_trend * .70, 2) if row.market_trend is not None else None,
                estimated_dealer_cash_min=round(row.market_trend * .60, 2) if row.market_trend is not None else None,
                estimated_dealer_cash_max=round(row.market_trend * .75, 2) if row.market_trend is not None else None,
                estimated_trade_value=round(row.market_trend * .80, 2) if row.market_trend is not None else None,
                estimated_trade_value_min=round(row.market_trend * .70, 2) if row.market_trend is not None else None,
                estimated_trade_value_max=round(row.market_trend * .85, 2) if row.market_trend is not None else None,
            )
        unrealized_pl = None
        roi = None
        if row.market_trend is not None and row.purchase_price is not None:
            cost_basis = row.purchase_price * row.quantity
            unrealized_pl = round((row.market_trend * row.quantity) - cost_basis, 2)
            roi = (unrealized_pl / cost_basis) if cost_basis > 0 else None
        return cls(
            id=row.id,
            display_name=row.display_name,
            card_name=row.card_name,
            card_number=row.card_number,
            printing_variant=row.printing_variant,
            variant_label=row.variant_label,
            treatment=row.treatment,
            source_variant=row.source_variant,
            finish=row.finish,
            expansion_name=row.expansion_name,
            expansion_set_code=row.expansion_set_code,
            game_code=row.game_code,
            game_name=row.game_name,
            language=row.language,
            canonical_card_id=row.canonical_card_id,
            release_kind=row.release_kind,
            art_kind=row.art_kind,
            printing_count=row.printing_count,
            reprint_count=row.reprint_count,
            condition=row.condition,
            grading_company=row.grading_company,
            grade=row.grade,
            quantity=row.quantity,
            purchase_price=row.purchase_price,
            purchase_currency=row.purchase_currency,
            purchase_date=row.purchase_date,
            trade_value=row.trade_value,
            status=row.status,
            manual_entry=row.manual_entry,
            catalog_matched=row.catalog_matched,
            manual_entry_note=row.manual_entry_note,
            notes=row.notes,
            market_price=market_price,
            unrealized_pl=unrealized_pl,
            roi=roi,
            image=CardImageOut.from_data(row.image),
        )


# --- /api/catalog -------------------------------------------------------------------


class CatalogItemOut(BaseModel):
    id: int
    canonical_card_id: int | None
    game_code: str
    name: str
    set_code: str | None
    expansion_name: str | None
    card_number: str | None
    rarity: str | None
    finish: str | None
    treatment: str | None
    language: str | None
    release_kind: str | None
    art_kind: str | None
    printing_count: int
    reprint_count: int
    current_price: float | None
    cardmarket_low: float | None = None
    cardmarket_trend: float | None = None
    cardmarket_avg1: float | None = None
    cardmarket_avg7: float | None = None
    cardmarket_avg30: float | None = None
    source_currency: str | None = None
    estimated_dealer_cash: float | None = None
    estimated_dealer_cash_min: float | None = None
    estimated_dealer_cash_max: float | None = None
    estimated_trade_value: float | None = None
    estimated_trade_value_min: float | None = None
    estimated_trade_value_max: float | None = None
    price_source: str | None
    resolution_method: str | None
    price_currency: str | None
    price_external_id: str | None
    price_sample_size: int
    lowest_price: float | None
    median_price: float | None
    price_confidence: str | None
    ownership_status: str
    owned: bool
    wishlist: bool
    wishlist_item_id: int | None
    image: CardImageOut | None

    @classmethod
    def from_row(cls, row: CatalogRow) -> "CatalogItemOut":
        return cls(
            id=row.id, canonical_card_id=row.canonical_card_id, game_code=row.game_code,
            name=row.name, set_code=row.set_code,
            expansion_name=row.expansion_name, card_number=row.card_number,
            rarity=row.rarity, finish=row.finish, treatment=row.treatment,
            language=row.language, release_kind=row.release_kind, art_kind=row.art_kind,
            printing_count=row.printing_count, reprint_count=row.reprint_count,
            current_price=row.current_price, price_source=row.price_source,
            cardmarket_low=row.cardmarket_low, cardmarket_trend=row.cardmarket_trend,
            cardmarket_avg1=row.cardmarket_avg1, cardmarket_avg7=row.cardmarket_avg7,
            cardmarket_avg30=row.cardmarket_avg30, source_currency=row.source_currency,
            estimated_dealer_cash=round(row.current_price * .70, 2) if row.current_price is not None else None,
            estimated_dealer_cash_min=round(row.current_price * .60, 2) if row.current_price is not None else None,
            estimated_dealer_cash_max=round(row.current_price * .75, 2) if row.current_price is not None else None,
            estimated_trade_value=round(row.current_price * .80, 2) if row.current_price is not None else None,
            estimated_trade_value_min=round(row.current_price * .70, 2) if row.current_price is not None else None,
            estimated_trade_value_max=round(row.current_price * .85, 2) if row.current_price is not None else None,
            resolution_method=row.resolution_method,
            price_currency=row.price_currency, price_external_id=row.price_external_id,
            price_sample_size=row.price_sample_size, lowest_price=row.lowest_price,
            median_price=row.median_price, price_confidence=row.price_confidence,
            ownership_status=row.ownership_status, owned=row.owned,
            wishlist=row.wishlist, wishlist_item_id=row.wishlist_item_id,
            image=CardImageOut.from_data(row.image),
        )


class CatalogListResponse(BaseModel):
    items: list[CatalogItemOut]
    total: int
    page: int
    page_size: int


class CatalogDetailResponse(BaseModel):
    printing: CatalogItemOut
    printings: list[CatalogItemOut]


class CatalogOptionOut(BaseModel):
    value: str
    label: str


class CatalogOptionsResponse(BaseModel):
    games: list[CatalogOptionOut]
    languages: list[CatalogOptionOut]
    sets: list[CatalogOptionOut]


# --- /api/wishlist ------------------------------------------------------------------


class WishlistItemOut(BaseModel):
    id: int
    card_id: int
    canonical_card_id: int | None
    game_code: str
    name: str
    set_code: str | None
    expansion_name: str | None
    card_number: str | None
    rarity: str | None
    finish: str | None
    treatment: str | None
    quantity_wanted: int
    priority: str
    target_price: float | None
    max_price: float | None
    currency: str | None
    notes: str | None
    status: str
    acquired_at: str | None
    removed_at: str | None
    current_price: float | None
    cardmarket_low: float | None = None
    cardmarket_trend: float | None = None
    cardmarket_avg1: float | None = None
    cardmarket_avg7: float | None = None
    cardmarket_avg30: float | None = None
    source_currency: str | None = None
    estimated_dealer_cash: float | None = None
    estimated_dealer_cash_min: float | None = None
    estimated_dealer_cash_max: float | None = None
    estimated_trade_value: float | None = None
    estimated_trade_value_min: float | None = None
    estimated_trade_value_max: float | None = None
    language: str | None
    release_kind: str | None
    art_kind: str | None
    printing_count: int
    reprint_count: int
    source: str | None
    resolution_method: str | None
    price_currency: str | None
    matched: bool
    image: CardImageOut | None

    @classmethod
    def from_row(cls, row: WishlistRow) -> "WishlistItemOut":
        return cls(
            id=row.id, card_id=row.card_id, canonical_card_id=row.canonical_card_id,
            game_code=row.game_code, name=row.name, set_code=row.set_code,
            expansion_name=row.expansion_name, card_number=row.card_number,
            rarity=row.rarity, finish=row.finish, treatment=row.treatment,
            quantity_wanted=row.quantity_wanted, priority=row.priority,
            target_price=row.target_price,
            max_price=row.max_price, currency=row.currency, notes=row.notes,
            status=row.status, acquired_at=row.acquired_at, removed_at=row.removed_at,
            current_price=row.current_price, language=row.language,
            cardmarket_low=row.cardmarket_low, cardmarket_trend=row.cardmarket_trend,
            cardmarket_avg1=row.cardmarket_avg1, cardmarket_avg7=row.cardmarket_avg7,
            cardmarket_avg30=row.cardmarket_avg30,
            source_currency=row.source_currency,
            estimated_dealer_cash=round(row.current_price * .70, 2) if row.current_price is not None else None,
            estimated_dealer_cash_min=round(row.current_price * .60, 2) if row.current_price is not None else None,
            estimated_dealer_cash_max=round(row.current_price * .75, 2) if row.current_price is not None else None,
            estimated_trade_value=round(row.current_price * .80, 2) if row.current_price is not None else None,
            estimated_trade_value_min=round(row.current_price * .70, 2) if row.current_price is not None else None,
            estimated_trade_value_max=round(row.current_price * .85, 2) if row.current_price is not None else None,
            release_kind=row.release_kind, art_kind=row.art_kind,
            printing_count=row.printing_count, reprint_count=row.reprint_count,
            source=row.source, resolution_method=row.resolution_method,
            price_currency=row.price_currency,
            matched=row.matched,
            image=CardImageOut.from_data(row.image),
        )


class WishlistSummaryOut(BaseModel):
    wanted: int
    acquired: int
    missing_price: int
    unmatched: int
    estimated_total: float


class WishlistListResponse(BaseModel):
    items: list[WishlistItemOut]
    total: int
    summary: WishlistSummaryOut


class WishlistCreateIn(BaseModel):
    card_id: int
    quantity_wanted: int = Field(1, gt=0)
    priority: str = Field("medium", pattern="^(low|medium|high|none)$")
    target_price: float | None = Field(None, ge=0)
    max_price: float | None = Field(None, ge=0)
    currency: str | None = "EUR"
    notes: str | None = None

    @model_validator(mode="after")
    def validate_price_order(self):
        if self.target_price is not None and self.max_price is not None and self.target_price > self.max_price:
            raise ValueError("target_price no puede ser mayor que max_price")
        return self


class WishlistUpdateIn(BaseModel):
    quantity_wanted: int | None = Field(None, gt=0)
    priority: str | None = Field(None, pattern="^(low|medium|high|none)$")
    target_price: float | None = Field(None, ge=0)
    max_price: float | None = Field(None, ge=0)
    currency: str | None = None
    notes: str | None = None


class MatchCandidateOut(BaseModel):
    id: int
    name: str
    set_code: str | None
    expansion_name: str | None
    card_number: str | None
    finish: str | None
    treatment: str | None
    language: str | None
    image: CardImageOut | None

    @classmethod
    def from_row(cls, row: MatchCandidateRow) -> "MatchCandidateOut":
        return cls(
            id=row.id, name=row.name, set_code=row.set_code,
            expansion_name=row.expansion_name, card_number=row.card_number,
            finish=row.finish, treatment=row.treatment, language=row.language,
            image=CardImageOut.from_data(row.image),
        )


class CollectionMatchContextOut(BaseModel):
    item_id: int
    name: str
    set_code: str | None
    card_number: str | None
    finish: str | None
    treatment: str | None
    language: str | None
    source: str
    source_note: str | None
    candidates: list[MatchCandidateOut]

    @classmethod
    def from_data(cls, data: CollectionMatchContext) -> "CollectionMatchContextOut":
        return cls(
            item_id=data.item_id, name=data.name, set_code=data.set_code,
            card_number=data.card_number, finish=data.finish, treatment=data.treatment,
            language=data.language, source=data.source, source_note=data.source_note,
            candidates=[MatchCandidateOut.from_row(row) for row in data.candidates],
        )


class ResolveMatchIn(BaseModel):
    card_id: int
    finish: str | None = None
    treatment: str | None = None

class AddToCollectionIn(BaseModel):
    card_id: int
    quantity: int = Field(1, ge=1)
    finish: str | None = None
    treatment: str | None = None


OverviewResponse.model_rebuild()
