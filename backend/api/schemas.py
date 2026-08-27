"""Modelos Pydantic de backend/api/.

Collection remains read-only; Catalog/Wishlist expose the explicitly scoped write
operations for this sprint.
"""

from pydantic import BaseModel, Field

from .queries import CardImageData, CardImageFaceData, CatalogRow, CollectionRow, TcgBucketData, WishlistRow

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
    match_quality: str
    faces: list[CardImageFaceOut]

    @classmethod
    def from_data(cls, data: CardImageData | None) -> "CardImageOut | None":
        if data is None or not data.faces:
            return None
        return cls(
            source=data.source,
            match_quality=data.match_quality,
            faces=[CardImageFaceOut.from_data(face) for face in data.faces],
        )


class CollectionItemOut(BaseModel):
    id: int
    display_name: str = Field(..., description="card.name si existe; si no (alta manual), manual_entry_note o notes tal cual, sin parsear.")
    expansion_name: str | None
    expansion_set_code: str | None
    card_number: str | None
    variant_label: str | None
    game_code: str | None
    condition: str | None
    quantity: int
    purchase_price: float | None
    market_value: float | None = Field(None, description="Trend Price de Cardmarket, snapshot mas reciente. None = sin precio de mercado (nunca 0).")
    manual_entry: bool = Field(..., description="Como entro la carta a la coleccion -- senal independiente de si tiene precio de mercado hoy.")
    status: str
    purchase_date: str | None
    image: CardImageOut | None = Field(
        None,
        description="Imagen exacta normalizada desde card_images. None = sin imagen exacta visible.",
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
            condition=row.condition,
            quantity=row.quantity,
            purchase_price=row.purchase_price,
            market_value=row.market_trend,
            manual_entry=row.manual_entry,
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
    trend: float
    avg: float | None
    low: float | None
    avg30: float | None
    observed_at: str
    source: str = "cardmarket"


class CollectionItemDetailOut(BaseModel):
    id: int
    display_name: str
    card_name: str | None
    card_number: str | None
    printing_variant: str | None
    variant_label: str | None
    expansion_name: str | None
    expansion_set_code: str | None
    game_code: str | None
    game_name: str | None
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
        description="Imagen exacta normalizada desde card_images. Representative no se muestra como imagen visible en este sprint.",
    )

    @classmethod
    def from_row(cls, row: CollectionRow) -> "CollectionItemDetailOut":
        market_price = None
        if row.has_market_value and row.price_observed_at is not None:
            market_price = MarketPriceOut(
                trend=row.market_trend,
                avg=row.market_avg,
                low=row.market_low,
                avg30=row.market_avg30,
                observed_at=row.price_observed_at,
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
            expansion_name=row.expansion_name,
            expansion_set_code=row.expansion_set_code,
            game_code=row.game_code,
            game_name=row.game_name,
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
    name: str
    set_code: str | None
    expansion_name: str | None
    card_number: str | None
    rarity: str | None
    finish: str | None
    treatment: str | None
    language: str | None
    current_price: float | None
    ownership_status: str
    owned: bool
    wishlist: bool
    wishlist_item_id: int | None
    image: CardImageOut | None

    @classmethod
    def from_row(cls, row: CatalogRow) -> "CatalogItemOut":
        return cls(
            id=row.id, name=row.name, set_code=row.set_code,
            expansion_name=row.expansion_name, card_number=row.card_number,
            rarity=row.rarity, finish=row.finish, treatment=row.treatment,
            language=row.language, current_price=row.current_price,
            ownership_status=row.ownership_status, owned=row.owned,
            wishlist=row.wishlist, wishlist_item_id=row.wishlist_item_id,
            image=CardImageOut.from_data(row.image),
        )


class CatalogListResponse(BaseModel):
    items: list[CatalogItemOut]
    total: int
    page: int
    page_size: int


# --- /api/wishlist ------------------------------------------------------------------


class WishlistItemOut(BaseModel):
    id: int
    card_id: int
    name: str
    set_code: str | None
    expansion_name: str | None
    card_number: str | None
    rarity: str | None
    finish: str | None
    treatment: str | None
    quantity_wanted: int
    priority: str
    max_price: float | None
    currency: str | None
    notes: str | None
    status: str
    current_price: float | None
    image: CardImageOut | None

    @classmethod
    def from_row(cls, row: WishlistRow) -> "WishlistItemOut":
        return cls(
            id=row.id, card_id=row.card_id, name=row.name, set_code=row.set_code,
            expansion_name=row.expansion_name, card_number=row.card_number,
            rarity=row.rarity, finish=row.finish, treatment=row.treatment,
            quantity_wanted=row.quantity_wanted, priority=row.priority,
            max_price=row.max_price, currency=row.currency, notes=row.notes,
            status=row.status, current_price=row.current_price,
            image=CardImageOut.from_data(row.image),
        )


class WishlistListResponse(BaseModel):
    items: list[WishlistItemOut]


class WishlistCreateIn(BaseModel):
    card_id: int
    quantity_wanted: int = Field(1, gt=0)
    priority: str = Field("medium", pattern="^(low|medium|high)$")
    max_price: float | None = Field(None, ge=0)
    currency: str | None = "USD"
    notes: str | None = None


class WishlistUpdateIn(BaseModel):
    quantity_wanted: int | None = Field(None, gt=0)
    priority: str | None = Field(None, pattern="^(low|medium|high)$")
    max_price: float | None = Field(None, ge=0)
    currency: str | None = None
    notes: str | None = None
