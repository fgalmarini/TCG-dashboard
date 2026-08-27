"""Acceso a datos de backend/api/ -- SQL crudo (sqlite3), tuplas -> @dataclass.

Todo overview/collection/detail comparte un unico builder de query base
(_build_query, mas abajo) -- nunca dos copias del SELECT ... FROM collection_items
(fase6-dashboard-basico-sprint-contract.md, requisito explicito). Filtros de
`/api/collection` siempre parametrizados con `?` -- nunca interpolar valores de
usuario en el SQL (`sort` se resuelve contra un diccionario fijo de columnas reales,
nunca el nombre de columna crudo del query param).
"""

import sqlite3
from dataclasses import dataclass, field

# --- Query base compartida ----------------------------------------------------------
# CTE de "ultimo snapshot de precio por producto": UNIQUE(cardmarket_product_id,
# observed_at) en market_price_history ya garantiza que MAX(observed_at) no tenga
# empate, no hace falta desempate adicional.
_LATEST_PRICE_CTE = """
WITH latest_price AS (
    SELECT
        h.cardmarket_product_id,
        COALESCE(NULLIF(h.trend, 0), NULLIF(h.trend_alt, 0)) AS trend,
        COALESCE(NULLIF(h.avg, 0), NULLIF(h.avg_alt, 0)) AS avg,
        COALESCE(NULLIF(h.low, 0), NULLIF(h.low_alt, 0)) AS low,
        COALESCE(NULLIF(h.avg30, 0), NULLIF(h.avg30_alt, 0)) AS avg30,
        h.observed_at
    FROM market_price_history h
    WHERE h.observed_at = (
        SELECT MAX(h2.observed_at) FROM market_price_history h2
        WHERE h2.cardmarket_product_id = h.cardmarket_product_id
    )
)
"""

# Columnas completas de una fila de collection_items + joins. Los dos LEFT JOIN
# (card_id, cardmarket_product_id) son independientes a proposito -- una fila puede
# tener producto sin tener card_id resoluble o viceversa, no asumir que uno implica
# el otro.
_COLLECTION_COLUMNS = """
    ci.id, ci.card_id, ci.cardmarket_product_id, ci.language_id, ci.condition,
    ci.grading_company, ci.grade, ci.quantity, ci.purchase_price, ci.purchase_currency,
    ci.purchase_date, ci.trade_value, ci.status, ci.manual_entry, ci.manual_entry_note,
    ci.notes,
    c.name AS card_name, c.card_number, c.printing_variant, c.variant_label,
    e.name AS expansion_name, e.set_code AS expansion_set_code,
    g.code AS game_code, g.name AS game_name,
    lp.trend AS market_trend, lp.avg AS market_avg, lp.low AS market_low,
    lp.avg30 AS market_avg30, lp.observed_at AS price_observed_at
"""

_FROM_JOINS = """
    FROM collection_items ci
    LEFT JOIN cards c        ON c.id = ci.card_id
    LEFT JOIN expansions e   ON e.id = c.expansion_id
    LEFT JOIN games g        ON g.id = c.game_id
    LEFT JOIN latest_price lp ON lp.cardmarket_product_id = ci.cardmarket_product_id
"""


def _build_query(
    select_clause: str,
    where_sql: str = "",
    order_by_sql: str = "",
    limit_offset_sql: str = "",
) -> str:
    """Unico builder de la query base (CTE + joins). Parametrizable por endpoint --
    /api/overview, /api/collection y /api/collection/{id} llaman siempre a esta misma
    funcion, nunca duplican el SELECT/FROM/JOIN."""
    return f"{_LATEST_PRICE_CTE}SELECT {select_clause}{_FROM_JOINS}{where_sql}{order_by_sql}{limit_offset_sql}"


# --- Regla unica de "sin precio" -----------------------------------------------------
# market_trend IS NULL es la UNICA regla de "esta fila no tiene valor de mercado" en
# todo el codigo -- nunca usar card_id IS NULL como proxy (cubre tanto las altas
# manuales de hoy como el caso futuro "tiene producto pero sin snapshot todavia").


@dataclass
class CardImageFaceData:
    face_index: int
    small_url: str | None
    large_url: str | None


@dataclass
class CardImageData:
    source: str
    match_quality: str
    faces: list[CardImageFaceData] = field(default_factory=list)


@dataclass
class CollectionRow:
    id: int
    card_id: int | None
    cardmarket_product_id: int | None
    language_id: int
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
    card_name: str | None
    card_number: str | None
    printing_variant: str | None
    variant_label: str | None
    expansion_name: str | None
    expansion_set_code: str | None
    game_code: str | None
    game_name: str | None
    market_trend: float | None
    market_avg: float | None
    market_low: float | None
    market_avg30: float | None
    price_observed_at: str | None
    image: CardImageData | None = None

    @property
    def display_name(self) -> str:
        """Las 19 filas manuales no tienen ningun campo de "nombre" limpio -- solo
        manual_entry_note (texto libre, a veces con URL de Cardmarket embebida) o
        notes. Mostrar tal cual, calculado en Python, nunca parseado por heuristica
        (fase6-dashboard-basico-sprint-contract.md, hallazgo no cubierto por el
        contract original, resuelto en el plan de ejecucion)."""
        return self.card_name or self.manual_entry_note or self.notes or "(sin nombre)"

    @property
    def has_market_value(self) -> bool:
        return self.market_trend is not None


def _row_to_collection_row(row: sqlite3.Row) -> CollectionRow:
    return CollectionRow(
        id=row["id"],
        card_id=row["card_id"],
        cardmarket_product_id=row["cardmarket_product_id"],
        language_id=row["language_id"],
        condition=row["condition"],
        grading_company=row["grading_company"],
        grade=row["grade"],
        quantity=row["quantity"],
        purchase_price=row["purchase_price"],
        purchase_currency=row["purchase_currency"],
        purchase_date=row["purchase_date"],
        trade_value=row["trade_value"],
        status=row["status"],
        manual_entry=bool(row["manual_entry"]),
        manual_entry_note=row["manual_entry_note"],
        notes=row["notes"],
        card_name=row["card_name"],
        card_number=row["card_number"],
        printing_variant=row["printing_variant"],
        variant_label=row["variant_label"],
        expansion_name=row["expansion_name"],
        expansion_set_code=row["expansion_set_code"],
        game_code=row["game_code"],
        game_name=row["game_name"],
        market_trend=row["market_trend"],
        market_avg=row["market_avg"],
        market_low=row["market_low"],
        market_avg30=row["market_avg30"],
        price_observed_at=row["price_observed_at"],
    )


def fetch_collection_rows(
    conn: sqlite3.Connection,
    where_sql: str = "",
    where_params: tuple | list = (),
    order_by_sql: str = "",
    limit: int | None = None,
    offset: int | None = None,
    include_images: bool = False,
) -> list[CollectionRow]:
    limit_offset_sql = ""
    params = list(where_params)
    if limit is not None:
        limit_offset_sql = " LIMIT ? OFFSET ?"
        params += [limit, offset or 0]
    sql = _build_query(_COLLECTION_COLUMNS, where_sql, order_by_sql, limit_offset_sql)
    rows = conn.execute(sql, params).fetchall()
    collection_rows = [_row_to_collection_row(r) for r in rows]
    if include_images:
        attach_exact_images(conn, collection_rows)
    return collection_rows


def attach_exact_images(conn: sqlite3.Connection, rows: list[CollectionRow]) -> None:
    card_ids = sorted({row.card_id for row in rows if row.card_id is not None})
    if not card_ids:
        return

    by_card_id = fetch_exact_images(conn, card_ids)
    for row in rows:
        if row.card_id is not None:
            row.image = by_card_id.get(row.card_id)


def fetch_exact_images(conn: sqlite3.Connection, card_ids: list[int]) -> dict[int, CardImageData]:
    """Return exact images with the existing Scryfall > CardTrader precedence."""
    placeholders = ",".join("?" for _ in card_ids)
    image_rows = conn.execute(
        f"""SELECT card_id, source, match_quality, face_index, image_url_small, image_url_large
              FROM card_images
             WHERE card_id IN ({placeholders})
               AND source IN ('scryfall', 'cardtrader')
               AND status = 'resolved'
               AND match_quality = 'exact'
               AND (image_url_small IS NOT NULL OR image_url_large IS NOT NULL)
             ORDER BY card_id,
                      CASE source WHEN 'scryfall' THEN 0 ELSE 1 END,
                      face_index""",
        card_ids,
    ).fetchall()

    by_card_id: dict[int, CardImageData] = {}
    for image_row in image_rows:
        card_id = image_row["card_id"]
        selected = by_card_id.get(card_id)
        if selected is not None and selected.source != image_row["source"]:
            continue
        image = by_card_id.setdefault(
            card_id,
            CardImageData(source=image_row["source"], match_quality=image_row["match_quality"]),
        )
        image.faces.append(
            CardImageFaceData(
                face_index=image_row["face_index"],
                small_url=image_row["image_url_small"],
                large_url=image_row["image_url_large"],
            )
        )

    return by_card_id


def count_collection_rows(
    conn: sqlite3.Connection,
    where_sql: str = "",
    where_params: tuple | list = (),
) -> int:
    sql = _build_query("COUNT(*) AS total", where_sql)
    row = conn.execute(sql, list(where_params)).fetchone()
    return row["total"]


def fetch_collection_row_by_id(
    conn: sqlite3.Connection,
    item_id: int,
    include_images: bool = True,
) -> CollectionRow | None:
    rows = fetch_collection_rows(
        conn,
        where_sql=" WHERE ci.id = ?",
        where_params=(item_id,),
        include_images=include_images,
    )
    return rows[0] if rows else None


# --- /api/collection: filtros y orden ------------------------------------------------

# sort -> columna real, mapeado via diccionario fijo (nunca interpolar el nombre de
# columna del query param). "valor": "(lp.trend IS NULL), lp.trend" antepone un
# booleano (0=tiene precio, 1=no tiene) para que las filas sin precio no queden
# intercaladas al ordenar ascendente -- siempre quedan al final del resultado.
SORT_COLUMNS: dict[str, str] = {
    "nombre": "COALESCE(c.name, ci.manual_entry_note, ci.notes)",
    "valor": "(lp.trend IS NULL), lp.trend",
    "fecha": "ci.purchase_date",
}


def build_order_by(sort: str | None) -> str:
    column_expr = SORT_COLUMNS.get(sort or "")
    if not column_expr:
        return " ORDER BY ci.id"
    return f" ORDER BY {column_expr}"


def build_collection_filters(
    game: str | None = None,
    status: str | None = None,
    search: str | None = None,
) -> tuple[str, list]:
    """game -> g.code = ?; status -> ci.status = ?; search (case-insensitive) sobre
    c.name Y TAMBIEN manual_entry_note/notes -- si search solo mirara c.name las 19
    filas manuales quedarian inalcanzables por busqueda."""
    clauses: list[str] = []
    params: list = []

    if game:
        clauses.append("g.code = ?")
        params.append(game)
    if status:
        clauses.append("ci.status = ?")
        params.append(status)
    if search:
        clauses.append(
            "(c.name LIKE ? COLLATE NOCASE OR ci.manual_entry_note LIKE ? COLLATE NOCASE"
            " OR ci.notes LIKE ? COLLATE NOCASE)"
        )
        like = f"%{search}%"
        params += [like, like, like]

    where_sql = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    return where_sql, params


# --- /api/overview: agregacion en Python ---------------------------------------------


@dataclass
class TcgBucketData:
    market_value: float = 0.0
    unique_cards: int = 0
    total_cards: int = 0


@dataclass
class OverviewData:
    total_cost: float
    cost_basis_row_count: int
    rows_without_cost: int
    total_market_value: float
    market_value_row_count: int
    unrealized_pl: float
    roi: float | None
    total_cards: int
    unique_cards: int
    cards_without_market_value_count: int
    cards_without_market_value_ids: list[int]
    value_by_tcg: dict[str, TcgBucketData] = field(default_factory=dict)


def compute_overview(conn: sqlite3.Connection) -> OverviewData:
    """Una sola llamada a la query base sin WHERE, agregacion en Python -- dataset
    ~100 filas no justifica 6 queries SUM/GROUP BY separadas (AGENTS.md seccion 24)."""
    rows = fetch_collection_rows(conn)

    total_cost = 0.0
    cost_basis_row_count = 0
    total_market_value = 0.0
    market_value_row_count = 0
    total_cards = 0
    without_market_ids: list[int] = []
    tcg_buckets: dict[str, TcgBucketData] = {}

    for row in rows:
        total_cards += row.quantity

        if row.purchase_price is not None:
            total_cost += row.purchase_price * row.quantity
            cost_basis_row_count += 1

        bucket_key = row.game_code or "sin_catalogar"
        bucket = tcg_buckets.setdefault(bucket_key, TcgBucketData())
        bucket.unique_cards += 1
        bucket.total_cards += row.quantity

        if row.has_market_value:
            value = row.market_trend * row.quantity
            total_market_value += value
            market_value_row_count += 1
            bucket.market_value += value
        else:
            without_market_ids.append(row.id)

    unique_cards = len(rows)
    rows_without_cost = unique_cards - cost_basis_row_count
    unrealized_pl = total_market_value - total_cost
    roi = (unrealized_pl / total_cost) if total_cost > 0 else None

    return OverviewData(
        total_cost=round(total_cost, 2),
        cost_basis_row_count=cost_basis_row_count,
        rows_without_cost=rows_without_cost,
        total_market_value=round(total_market_value, 2),
        market_value_row_count=market_value_row_count,
        unrealized_pl=round(unrealized_pl, 2),
        roi=roi,
        total_cards=total_cards,
        unique_cards=unique_cards,
        cards_without_market_value_count=len(without_market_ids),
        cards_without_market_value_ids=without_market_ids,
        value_by_tcg=tcg_buckets,
    )


# --- Catalog / wishlist -------------------------------------------------------------

_CARD_PRICE_CTE = """
WITH latest_price AS (
    SELECT h.cardmarket_product_id,
           COALESCE(NULLIF(h.trend, 0), NULLIF(h.trend_alt, 0)) AS trend,
           h.observed_at
      FROM market_price_history h
     WHERE h.observed_at = (
         SELECT MAX(h2.observed_at) FROM market_price_history h2
          WHERE h2.cardmarket_product_id = h.cardmarket_product_id
     )
), single_product AS (
    SELECT cpm.card_id, cpm.cardmarket_product_id
      FROM cardmarket_product_mappings cpm
     WHERE cpm.status = 'mapped'
     GROUP BY cpm.card_id
    HAVING COUNT(DISTINCT cpm.cardmarket_product_id) = 1
), card_price AS (
    SELECT sp.card_id, lp.trend AS current_price, lp.observed_at
      FROM single_product sp
      JOIN latest_price lp ON lp.cardmarket_product_id = sp.cardmarket_product_id
     WHERE lp.trend IS NOT NULL
)
"""


@dataclass
class CatalogRow:
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
    price_observed_at: str | None
    owned: bool
    wishlist: bool
    wishlist_item_id: int | None
    image: CardImageData | None = None

    @property
    def ownership_status(self) -> str:
        if self.owned and self.wishlist:
            return "owned_wishlist"
        if self.owned:
            return "owned"
        if self.wishlist:
            return "wishlist"
        return "none"


@dataclass
class WishlistRow:
    id: int
    card_id: int
    quantity_wanted: int
    priority: str
    max_price: float | None
    currency: str | None
    notes: str | None
    status: str
    created_at: str
    updated_at: str
    name: str
    set_code: str | None
    expansion_name: str | None
    card_number: str | None
    rarity: str | None
    finish: str | None
    treatment: str | None
    current_price: float | None
    image: CardImageData | None = None


def _catalog_row(row: sqlite3.Row) -> CatalogRow:
    return CatalogRow(
        id=row["id"], name=row["name"], set_code=row["set_code"],
        expansion_name=row["expansion_name"], card_number=row["card_number"],
        rarity=row["rarity"], finish=row["finish"], treatment=row["treatment"],
        language=row["language"], current_price=row["current_price"],
        price_observed_at=row["price_observed_at"], owned=bool(row["owned"]),
        wishlist=bool(row["wishlist"]), wishlist_item_id=row["wishlist_item_id"],
    )


def build_catalog_filters(
    game: str = "magic",
    sets: list[str] | None = None,
    search: str | None = None,
    ownership: str | None = None,
    rarity: str | None = None,
    finish: str | None = None,
    treatment: str | None = None,
) -> tuple[str, list]:
    clauses = ["g.code = ?", "lower(c.set_code) IN ('ltr', 'ltc')", "c.finish IS NOT NULL"]
    params: list = [game]
    if sets:
        placeholders = ",".join("?" for _ in sets)
        clauses.append(f"lower(c.set_code) IN ({placeholders})")
        params.extend(value.casefold() for value in sets)
    if search:
        like = f"%{search}%"
        clauses.append("(c.name LIKE ? COLLATE NOCASE OR c.normalized_name LIKE ? COLLATE NOCASE)")
        params.extend([like, like])
    if ownership == "owned":
        clauses.append("EXISTS (SELECT 1 FROM collection_items ci WHERE ci.card_id = c.id)")
    elif ownership == "not_owned":
        clauses.append("NOT EXISTS (SELECT 1 FROM collection_items ci WHERE ci.card_id = c.id)")
    elif ownership == "wishlist":
        clauses.append("EXISTS (SELECT 1 FROM wishlist_items wi WHERE wi.card_id = c.id AND wi.status = 'wanted')")
    if rarity:
        clauses.append("c.rarity = ?")
        params.append(rarity.casefold())
    if finish:
        clauses.append("c.finish = ?")
        params.append(finish.casefold())
    if treatment:
        clauses.append("c.treatment = ?")
        params.append(treatment)
    return " WHERE " + " AND ".join(clauses), params


def fetch_catalog_rows(
    conn: sqlite3.Connection,
    where_sql: str,
    where_params: list,
    limit: int,
    offset: int,
) -> list[CatalogRow]:
    sql = _CARD_PRICE_CTE + f"""
        SELECT c.id, c.name, c.set_code, e.name AS expansion_name, c.card_number,
               c.rarity, c.finish, c.treatment, l.code AS language,
               cp.current_price, cp.observed_at AS price_observed_at,
               EXISTS (SELECT 1 FROM collection_items ci WHERE ci.card_id = c.id) AS owned,
               EXISTS (SELECT 1 FROM wishlist_items wi WHERE wi.card_id = c.id AND wi.status = 'wanted') AS wishlist,
               (SELECT wi.id FROM wishlist_items wi WHERE wi.card_id = c.id AND wi.status = 'wanted' ORDER BY wi.id LIMIT 1) AS wishlist_item_id
          FROM cards c
          JOIN expansions e ON e.id = c.expansion_id
          JOIN games g ON g.id = c.game_id
          LEFT JOIN languages l ON l.id = c.language_id
          LEFT JOIN card_price cp ON cp.card_id = c.id
          {where_sql}
         ORDER BY c.name COLLATE NOCASE, c.set_code, c.card_number, c.finish, c.id
         LIMIT ? OFFSET ?"""
    rows = conn.execute(sql, [*where_params, limit, offset]).fetchall()
    result = [_catalog_row(row) for row in rows]
    images = fetch_exact_images(conn, sorted({row.id for row in result}))
    for row in result:
        row.image = images.get(row.id)
    return result


def count_catalog_rows(conn: sqlite3.Connection, where_sql: str, where_params: list) -> int:
    row = conn.execute(
        _CARD_PRICE_CTE + f"SELECT COUNT(*) FROM cards c JOIN expansions e ON e.id=c.expansion_id JOIN games g ON g.id=c.game_id {where_sql}",
        where_params,
    ).fetchone()
    return row[0]


def _wishlist_row(row: sqlite3.Row) -> WishlistRow:
    return WishlistRow(
        id=row["id"], card_id=row["card_id"], quantity_wanted=row["quantity_wanted"],
        priority=row["priority"], max_price=row["max_price"], currency=row["currency"],
        notes=row["notes"], status=row["status"], created_at=row["created_at"],
        updated_at=row["updated_at"], name=row["name"], set_code=row["set_code"],
        expansion_name=row["expansion_name"], card_number=row["card_number"],
        rarity=row["rarity"], finish=row["finish"], treatment=row["treatment"],
        current_price=row["current_price"],
    )


def fetch_wishlist_rows(
    conn: sqlite3.Connection,
    status: str | None = "wanted",
) -> list[WishlistRow]:
    sql = _CARD_PRICE_CTE + """
        SELECT wi.*, c.name, c.set_code, e.name AS expansion_name, c.card_number,
               c.rarity, c.finish, c.treatment, cp.current_price
          FROM wishlist_items wi
          JOIN cards c ON c.id = wi.card_id
          JOIN expansions e ON e.id = c.expansion_id
          LEFT JOIN card_price cp ON cp.card_id = c.id
         WHERE (? IS NULL OR wi.status = ?)
         ORDER BY CASE wi.priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END,
                  wi.updated_at DESC, wi.id DESC"""
    result = [_wishlist_row(row) for row in conn.execute(sql, (status, status)).fetchall()]
    images = fetch_exact_images(conn, sorted({row.card_id for row in result}))
    for row in result:
        row.image = images.get(row.card_id)
    return result


def fetch_wishlist_row(conn: sqlite3.Connection, item_id: int) -> WishlistRow | None:
    rows = fetch_wishlist_rows(conn, status=None)
    return next((row for row in rows if row.id == item_id), None)
