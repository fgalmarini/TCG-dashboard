"""Acceso a datos de backend/api/ -- SQL crudo (sqlite3), tuplas -> @dataclass.

Todo overview/collection/detail comparte un unico builder de query base
(_build_query, mas abajo) -- nunca dos copias del SELECT ... FROM collection_items
(fase6-dashboard-basico-sprint-contract.md, requisito explicito). Filtros de
`/api/collection` siempre parametrizados con `?` -- nunca interpolar valores de
usuario en el SQL (`sort` se resuelve contra un diccionario fijo de columnas reales,
nunca el nombre de columna crudo del query param).
"""

import re
import sqlite3
import json
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

# --- Query base compartida ----------------------------------------------------------
# CTE de "ultimo snapshot de precio por producto": UNIQUE(cardmarket_product_id,
# observed_at) en market_price_history ya garantiza que MAX(observed_at) no tenga
# empate, no hace falta desempate adicional.
_LATEST_PRICE_CTE = """
WITH latest_price AS (
    SELECT
        h.cardmarket_product_id,
        COALESCE(NULLIF(h.trend, 0), NULLIF(h.trend_alt, 0)) AS trend,
        NULLIF(h.trend, 0) AS trend_base, NULLIF(h.trend_alt, 0) AS trend_alt_value,
        COALESCE(NULLIF(h.avg, 0), NULLIF(h.avg_alt, 0)) AS avg,
        NULLIF(h.avg, 0) AS avg_base, NULLIF(h.avg_alt, 0) AS avg_alt_value,
        COALESCE(NULLIF(h.avg1, 0), NULLIF(h.avg1_alt, 0)) AS avg1,
        NULLIF(h.avg1, 0) AS avg1_base, NULLIF(h.avg1_alt, 0) AS avg1_alt_value,
        COALESCE(NULLIF(h.avg7, 0), NULLIF(h.avg7_alt, 0)) AS avg7,
        NULLIF(h.avg7, 0) AS avg7_base, NULLIF(h.avg7_alt, 0) AS avg7_alt_value,
        COALESCE(NULLIF(h.low, 0), NULLIF(h.low_alt, 0)) AS low,
        NULLIF(h.low, 0) AS low_base,
        NULLIF(h.low_alt, 0) AS low_alt,
        COALESCE(NULLIF(h.avg30, 0), NULLIF(h.avg30_alt, 0)) AS avg30,
        NULLIF(h.avg30, 0) AS avg30_base, NULLIF(h.avg30_alt, 0) AS avg30_alt_value,
        h.observed_at,
        (
            SELECT COALESCE(NULLIF(h2.trend, 0), NULLIF(h2.trend_alt, 0))
              FROM market_price_history h2
             WHERE h2.cardmarket_product_id = h.cardmarket_product_id
               AND (
                    h2.observed_at < h.observed_at
                    OR (h2.observed_at = h.observed_at AND h2.id < h.id)
               )
               AND COALESCE(NULLIF(h2.trend, 0), NULLIF(h2.trend_alt, 0)) IS NOT NULL
             ORDER BY h2.observed_at DESC, h2.id DESC
             LIMIT 1
        ) AS previous_trend
    FROM market_price_history h
    WHERE h.observed_at = (
        SELECT MAX(h2.observed_at) FROM market_price_history h2
        WHERE h2.cardmarket_product_id = h.cardmarket_product_id
    )
), latest_printing_resolution AS (
    SELECT r.id, r.card_id, r.language_id, r.current_price, r.currency,
           r.source, r.resolution_method, r.resolved_at,
           r.match_status, r.selected_metric, r.cardmarket_low,
           r.cardmarket_trend, r.cardmarket_avg1, r.cardmarket_avg7,
           r.cardmarket_avg30, r.source_currency,
           (
               SELECT r2.current_price
                 FROM printing_price_resolutions r2
                WHERE r2.card_id = r.card_id
                  AND r2.language_id = r.language_id
                  AND r2.collection_item_id IS NULL
                  AND r2.wishlist_item_id IS NULL
                  AND r2.current_price IS NOT NULL
                  AND (
                       r2.resolved_at < r.resolved_at
                       OR (r2.resolved_at = r.resolved_at AND r2.id < r.id)
                  )
                ORDER BY r2.resolved_at DESC, r2.id DESC
                LIMIT 1
           ) AS previous_current_price
      FROM printing_price_resolutions r
     WHERE r.is_current = 1
       AND r.collection_item_id IS NULL
       AND r.wishlist_item_id IS NULL
       AND COALESCE(r.source, 'cardmarket') = 'cardmarket'
), latest_collection_resolution AS (
    SELECT r.id, r.collection_item_id, r.card_id, r.language_id,
           r.current_price, r.currency, r.source, r.resolution_method,
           r.resolved_at, r.match_status, r.selected_metric,
           r.cardmarket_low, r.cardmarket_trend, r.cardmarket_avg1,
           r.cardmarket_avg7, r.cardmarket_avg30, r.source_currency,
           (
               SELECT r2.current_price
                 FROM printing_price_resolutions r2
                WHERE r2.collection_item_id = r.collection_item_id
                  AND r2.wishlist_item_id IS NULL
                  AND r2.current_price IS NOT NULL
                  AND (
                       r2.resolved_at < r.resolved_at
                       OR (r2.resolved_at = r.resolved_at AND r2.id < r.id)
                  )
                ORDER BY r2.resolved_at DESC, r2.id DESC
                LIMIT 1
           ) AS previous_current_price
      FROM printing_price_resolutions r
     WHERE r.is_current = 1
       AND r.collection_item_id IS NOT NULL
       AND r.wishlist_item_id IS NULL
       AND COALESCE(r.source, 'cardmarket') = 'cardmarket'
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
    ci.notes, ci.match_status, ci.match_quality, ci.match_reason,
    ci.finish AS collection_finish, ci.treatment AS collection_treatment,
    c.name AS card_name, c.card_number, c.printing_variant, c.variant_label,
    c.treatment, c.source_variant, c.finish,
    c.canonical_card_id, c.release_kind, c.art_kind,
    COALESCE(s.name, e.name) AS expansion_name,
    COALESCE(s.code, c.set_code, e.set_code) AS expansion_set_code,
    g.code AS game_code, g.name AS game_name,
    cl.code AS language,
    CASE WHEN c.catalog_status = 'active' OR (g.code = 'magic'
              AND lower(COALESCE(c.set_code, e.set_code)) IN ('ltr', 'ltc')
              AND c.card_number IS NOT NULL AND c.finish IS NOT NULL)
         THEN 1 ELSE 0 END AS catalog_matched,
    CASE WHEN cr.id IS NOT NULL THEN cr.current_price WHEN pr.id IS NOT NULL THEN pr.current_price ELSE CASE WHEN lower(c.finish) = 'foil' THEN lp.low_alt ELSE lp.low_base END END AS market_trend,
    CASE WHEN cr.id IS NOT NULL THEN cr.previous_current_price WHEN pr.id IS NOT NULL THEN pr.previous_current_price ELSE lp.previous_trend END AS previous_market_trend,
    CASE WHEN cr.id IS NOT NULL THEN cr.cardmarket_avg1 WHEN pr.id IS NOT NULL THEN pr.cardmarket_avg1 ELSE CASE WHEN lower(c.finish) = 'foil' THEN lp.avg_alt_value ELSE lp.avg_base END END AS market_avg,
    CASE WHEN cr.id IS NOT NULL THEN cr.cardmarket_low WHEN pr.id IS NOT NULL THEN pr.cardmarket_low ELSE CASE WHEN lower(c.finish) = 'foil' THEN lp.low_alt ELSE lp.low_base END END AS market_low,
    CASE WHEN cr.id IS NOT NULL THEN cr.cardmarket_avg30 WHEN pr.id IS NOT NULL THEN pr.cardmarket_avg30 ELSE lp.avg30 END AS market_avg30,
    CASE WHEN cr.id IS NOT NULL THEN cr.resolved_at WHEN pr.id IS NOT NULL THEN pr.resolved_at ELSE lp.observed_at END AS price_observed_at,
    CASE WHEN cr.id IS NOT NULL THEN cr.source WHEN pr.id IS NOT NULL THEN pr.source ELSE 'cardmarket' END AS price_source,
    CASE WHEN cr.id IS NOT NULL THEN COALESCE(cr.source_currency, cr.currency) WHEN pr.id IS NOT NULL THEN COALESCE(pr.source_currency, pr.currency) ELSE 'EUR' END AS price_currency,
    CASE WHEN cr.id IS NOT NULL THEN cr.resolution_method WHEN pr.id IS NOT NULL THEN pr.resolution_method ELSE 'cardmarket_price_guide' END AS resolution_method,
    CASE WHEN cr.id IS NOT NULL THEN cr.cardmarket_low WHEN pr.id IS NOT NULL THEN pr.cardmarket_low ELSE lp.low END AS cardmarket_low,
    CASE WHEN cr.id IS NOT NULL THEN cr.cardmarket_trend WHEN pr.id IS NOT NULL THEN pr.cardmarket_trend ELSE CASE WHEN lower(c.finish) = 'foil' THEN lp.trend_alt_value ELSE lp.trend_base END END AS cardmarket_trend,
    CASE WHEN cr.id IS NOT NULL THEN cr.cardmarket_avg1 WHEN pr.id IS NOT NULL THEN pr.cardmarket_avg1 ELSE lp.avg END AS cardmarket_avg1,
    CASE WHEN cr.id IS NOT NULL THEN cr.cardmarket_avg7 WHEN pr.id IS NOT NULL THEN pr.cardmarket_avg7 ELSE lp.avg7 END AS cardmarket_avg7,
    CASE WHEN cr.id IS NOT NULL THEN cr.cardmarket_avg30 WHEN pr.id IS NOT NULL THEN pr.cardmarket_avg30 ELSE lp.avg30 END AS cardmarket_avg30,
    CASE WHEN cr.id IS NOT NULL THEN cr.source_currency WHEN pr.id IS NOT NULL THEN pr.source_currency ELSE 'EUR' END AS source_currency,
    (SELECT COUNT(*) FROM cards pc
      WHERE pc.canonical_card_id = c.canonical_card_id AND pc.catalog_status = 'active') AS printing_count,
    (SELECT COUNT(*) FROM cards rc
      WHERE rc.canonical_card_id = c.canonical_card_id AND rc.catalog_status = 'active'
        AND rc.release_kind = 'reprint') AS reprint_count
"""

_FROM_JOINS = """
    FROM collection_items ci
    LEFT JOIN cards c        ON c.id = ci.card_id
    LEFT JOIN expansions e   ON e.id = c.expansion_id
    LEFT JOIN sets s         ON s.id = c.set_id
    LEFT JOIN games g        ON g.id = c.game_id
    LEFT JOIN languages cl   ON cl.id = c.language_id
    LEFT JOIN latest_price lp ON lp.cardmarket_product_id = ci.cardmarket_product_id
    LEFT JOIN latest_printing_resolution pr
           ON pr.card_id = c.id AND COALESCE(pr.language_id, ci.language_id, -1) = COALESCE(c.language_id, ci.language_id, -1)
    LEFT JOIN latest_collection_resolution cr
           ON cr.collection_item_id = ci.id
"""


def _pricing_schema_sql(conn: sqlite3.Connection, sql: str) -> str:
    """Keep reads working on an unmigrated legacy DB; apply migrates atomically."""
    columns = {row[1] for row in conn.execute("PRAGMA table_info(printing_price_resolutions)")}
    if "collection_item_id" not in columns:
        # Very old databases do not have the collection-scoped table columns at
        # all.  Remove that CTE and join instead of issuing a query against a
        # nonexistent column; the legacy resolution path below still selects
        # one historical row per printing.
        marker = ", latest_collection_resolution AS ("
        start = sql.find(marker)
        if start >= 0:
            end = sql.find(")\nSELECT", start)
            if end >= 0:
                sql = sql[:start] + "\nSELECT" + sql[end + len(")\nSELECT"):]
        sql = sql.replace("       AND r.collection_item_id IS NULL\n", "")
        sql = sql.replace("    LEFT JOIN latest_collection_resolution cr\n           ON cr.collection_item_id = ci.id\n", "")
        sql = re.sub(r"\bcr\.[A-Za-z_]+\b", "NULL", sql)
    if "wishlist_item_id" not in columns:
        # During the additive migration the Wishlist relation is empty, while
        # the global query remains readable against the legacy schema.
        sql = sql.replace("r.id, r.wishlist_item_id, r.card_id", "r.id, NULL AS wishlist_item_id, r.card_id")
        sql = sql.replace("r.wishlist_item_id", "NULL")
        sql = sql.replace("r0.wishlist_item_id", "NULL")
        sql = sql.replace("r2.wishlist_item_id", "NULL")
    if "is_current" not in columns:
        # Legacy databases have no current marker.  Selecting every historical
        # resolution multiplies collection/catalog rows; emulate one current
        # Cardmarket resolution per printing, language and source instead.
        legacy_current = """
            r.id = (
                SELECT r3.id
                  FROM printing_price_resolutions r3
                 WHERE r3.card_id = r.card_id
                   AND COALESCE(r3.language_id, -1) = COALESCE(r.language_id, -1)
                   AND COALESCE(r3.source, 'cardmarket') = COALESCE(r.source, 'cardmarket')
                 ORDER BY r3.resolved_at DESC, r3.id DESC
                 LIMIT 1
            )
        """
        sql = sql.replace("cr.is_current = 1", "1=0")
        # The legacy compatibility fixture/database may also predate the
        # additive resolution columns.  Replace collection-scoped references
        # before the generic `r.` substitutions so `cr.cardmarket_*` is never
        # accidentally transformed into `cNULL`.
        for column in ("match_status", "selected_metric", "cardmarket_low", "cardmarket_trend", "cardmarket_avg1", "cardmarket_avg7", "cardmarket_avg30", "source_currency"):
            sql = sql.replace(f"cr.{column}", "NULL")
        sql = sql.replace("r.is_current = 1", legacy_current).replace("r0.is_current = 1", "1=0")
    # The API is also usable during the additive migration window.  Missing
    # resolution metadata is reported as NULL until update-prices applies it.
        for column in ("match_status", "selected_metric", "cardmarket_low", "cardmarket_trend", "cardmarket_avg1", "cardmarket_avg7", "cardmarket_avg30", "cardmarket_foil_low", "cardmarket_foil_trend", "cardmarket_foil_avg1", "cardmarket_foil_avg7", "cardmarket_foil_avg30"):
            if column not in columns:
                sql = sql.replace(f"pr.{column}", "NULL").replace(f"r.{column}", "NULL")
    if "source_currency" not in columns:
        sql = sql.replace("pr.source_currency", "pr.currency").replace("r.source_currency", "r.currency")
    return sql


def _build_query(
    conn: sqlite3.Connection,
    select_clause: str,
    where_sql: str = "",
    order_by_sql: str = "",
    limit_offset_sql: str = "",
) -> str:
    """Unico builder de la query base (CTE + joins). Parametrizable por endpoint --
    /api/overview, /api/collection y /api/collection/{id} llaman siempre a esta misma
    funcion, nunca duplican el SELECT/FROM/JOIN."""
    return _pricing_schema_sql(conn, f"{_LATEST_PRICE_CTE}SELECT {select_clause}{_FROM_JOINS}{where_sql}{order_by_sql}{limit_offset_sql}")


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
    actual_image_language: str | None = None
    requested_language: str | None = None
    is_language_fallback: bool = False
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
    match_status: str
    match_quality: str | None
    match_reason: str | None
    card_name: str | None
    card_number: str | None
    printing_variant: str | None
    variant_label: str | None
    treatment: str | None
    source_variant: str | None
    finish: str | None
    canonical_card_id: int | None
    release_kind: str | None
    art_kind: str | None
    expansion_name: str | None
    expansion_set_code: str | None
    game_code: str | None
    game_name: str | None
    language: str | None
    catalog_matched: bool
    market_trend: float | None
    previous_market_trend: float | None
    market_avg: float | None
    market_low: float | None
    market_avg30: float | None
    cardmarket_low: float | None
    cardmarket_trend: float | None
    cardmarket_avg1: float | None
    cardmarket_avg7: float | None
    cardmarket_avg30: float | None
    source_currency: str | None
    price_observed_at: str | None
    price_source: str | None
    price_currency: str | None
    resolution_method: str | None
    printing_count: int
    reprint_count: int
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

    @property
    def price_variation(self) -> float | None:
        if self.market_trend is None or self.previous_market_trend in (None, 0):
            return None
        return (self.market_trend - self.previous_market_trend) / self.previous_market_trend


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
        match_status=row["match_status"],
        match_quality=row["match_quality"],
        match_reason=row["match_reason"],
        card_name=row["card_name"],
        card_number=row["card_number"],
        printing_variant=row["printing_variant"],
        variant_label=row["variant_label"],
        treatment=row["treatment"],
        source_variant=row["source_variant"],
        finish=row["finish"],
        canonical_card_id=row["canonical_card_id"],
        release_kind=row["release_kind"],
        art_kind=row["art_kind"],
        expansion_name=row["expansion_name"],
        expansion_set_code=row["expansion_set_code"],
        game_code=row["game_code"],
        game_name=row["game_name"],
        language=row["language"],
        catalog_matched=bool(row["catalog_matched"]),
        market_trend=row["market_trend"],
        previous_market_trend=row["previous_market_trend"],
        market_avg=row["market_avg"],
        market_low=row["market_low"],
        market_avg30=row["market_avg30"],
        cardmarket_low=row["cardmarket_low"],
        cardmarket_trend=row["cardmarket_trend"],
        cardmarket_avg1=row["cardmarket_avg1"],
        cardmarket_avg7=row["cardmarket_avg7"],
        cardmarket_avg30=row["cardmarket_avg30"],
        source_currency=row["source_currency"],
        price_observed_at=row["price_observed_at"],
        price_source=row["price_source"],
        price_currency=row["price_currency"],
        resolution_method=row["resolution_method"],
        printing_count=row["printing_count"],
        reprint_count=row["reprint_count"],
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
    sql = _build_query(conn, _COLLECTION_COLUMNS, where_sql, order_by_sql, limit_offset_sql)
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
    """Return display images without crossing a printing's requested language.

    One Piece fallback rows keep the card's requested language in ``ci.language``
    and store the actual asset language separately. Exact requested-language rows
    always win over visual fallbacks. Magic keeps its Scryfall > CardTrader order.
    """
    placeholders = ",".join("?" for _ in card_ids)
    image_rows = conn.execute(
        f"""SELECT ci.card_id, ci.source, ci.match_quality, ci.face_index,
                      ci.image_url_small, ci.image_url_large, ci.language,
                      ci.image_language_scope, ci.is_language_fallback,
                      l.code AS requested_language
              FROM card_images ci
              JOIN cards c ON c.id = ci.card_id
              LEFT JOIN languages l ON l.id = c.language_id
             WHERE ci.card_id IN ({placeholders})
               AND source IN ('scryfall', 'cardtrader', 'tcgdex')
               AND ci.status = 'resolved'
               AND ci.match_quality = 'exact'
               AND (ci.image_url_small IS NOT NULL OR ci.image_url_large IS NOT NULL)
               AND (l.code IS NULL OR ci.language = l.code OR ci.is_language_fallback = 1)
             ORDER BY ci.card_id,
                      CASE
                        WHEN ci.is_language_fallback = 0
                         AND (ci.image_language_scope = l.code OR
                              (ci.image_language_scope = 'unknown' AND ci.language = l.code))
                        THEN 0
                        WHEN ci.is_language_fallback = 1 THEN 1
                        ELSE 2
                      END,
                      CASE ci.source WHEN 'scryfall' THEN 0 ELSE 1 END,
                      ci.face_index""",
        card_ids,
    ).fetchall()

    by_card_id: dict[int, CardImageData] = {}
    for image_row in image_rows:
        card_id = image_row["card_id"]
        selected = by_card_id.get(card_id)
        if selected is not None and (
            selected.source != image_row["source"]
            or selected.is_language_fallback != bool(image_row["is_language_fallback"])
        ):
            continue
        image = by_card_id.setdefault(
            card_id,
            CardImageData(
                source=image_row["source"],
                match_quality=image_row["match_quality"],
                actual_image_language=(
                    image_row["image_language_scope"]
                    if image_row["image_language_scope"] not in (None, "unknown")
                    else image_row["language"]
                ),
                requested_language=image_row["requested_language"] or image_row["language"],
                is_language_fallback=bool(image_row["is_language_fallback"]),
            ),
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
    sql = _build_query(conn, "COUNT(*) AS total", where_sql)
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
    "valor": "(market_trend IS NULL), market_trend",
    "fecha": "ci.purchase_date",
}


def build_order_by(sort: str | None) -> str:
    column_expr = SORT_COLUMNS.get(sort or "")
    if not column_expr:
        return " ORDER BY ci.id"
    return f" ORDER BY {column_expr}"


def build_collection_filters(
    game: str | None = None,
    language: str | None = None,
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
    if language:
        clauses.append("cl.code = ?")
        params.append(language.casefold())
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
    top_cards: list[CollectionRow] = field(default_factory=list)


def compute_overview(conn: sqlite3.Connection) -> OverviewData:
    """Una sola llamada a la query base sin WHERE, agregacion en Python -- dataset
    ~100 filas no justifica 6 queries SUM/GROUP BY separadas (AGENTS.md seccion 24)."""
    rows = fetch_collection_rows(conn, include_images=True)

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
        top_cards=sorted(
            (row for row in rows if row.market_trend is not None),
            key=lambda row: (-row.market_trend, row.id),
        )[:10],
    )


# --- Catalog / wishlist -------------------------------------------------------------

_CARD_PRICE_CTE = """
WITH latest_price AS (
    SELECT h.cardmarket_product_id,
           COALESCE(NULLIF(h.trend, 0), NULLIF(h.trend_alt, 0)) AS trend,
           NULLIF(h.low, 0) AS low_base, NULLIF(h.low_alt, 0) AS low_alt,
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
), legacy_card_price AS (
    SELECT sp.card_id, lp.low_base AS current_price, lp.observed_at,
           'cardmarket' AS source, 'cardmarket_exact_language' AS resolution_method
      FROM single_product sp
      JOIN latest_price lp ON lp.cardmarket_product_id = sp.cardmarket_product_id
     WHERE lp.low_base IS NOT NULL
       AND NOT EXISTS (
           SELECT 1 FROM printing_price_resolutions r0
            WHERE r0.card_id = sp.card_id AND r0.is_current = 1
              AND r0.collection_item_id IS NULL AND r0.wishlist_item_id IS NULL
       )
), latest_resolution AS (
    SELECT r.card_id, r.language_id, r.current_price, r.currency,
           r.resolved_at AS observed_at, r.source, r.resolution_method,
           r.external_id, r.sample_size, r.lowest_price, r.median_price,
           r.price_confidence, r.cardmarket_low, r.cardmarket_trend,
           r.cardmarket_avg1, r.cardmarket_avg7, r.cardmarket_avg30,
           r.source_currency
     FROM printing_price_resolutions r
     WHERE r.is_current = 1
       AND r.collection_item_id IS NULL
       AND r.wishlist_item_id IS NULL
       AND COALESCE(r.source, 'cardmarket') = 'cardmarket'
), latest_wishlist_resolution AS (
    SELECT r.id, r.wishlist_item_id, r.card_id, r.current_price, r.currency,
           r.resolved_at AS observed_at, r.source, r.resolution_method,
           r.external_id, r.sample_size, r.lowest_price, r.median_price,
           r.price_confidence, r.match_status, r.selected_metric,
           CASE WHEN r.match_status = 'EXACT' AND r.current_price IS NOT NULL
                THEN CASE WHEN r.selected_metric = 'Foil Low'
                          THEN r.cardmarket_foil_low ELSE r.cardmarket_low END
           END AS selected_low,
           CASE WHEN r.match_status = 'EXACT' AND r.current_price IS NOT NULL
                THEN CASE WHEN r.selected_metric = 'Foil Low'
                          THEN r.cardmarket_foil_trend ELSE r.cardmarket_trend END
           END AS selected_trend,
           CASE WHEN r.match_status = 'EXACT' AND r.current_price IS NOT NULL
                THEN CASE WHEN r.selected_metric = 'Foil Low'
                          THEN r.cardmarket_foil_avg1 ELSE r.cardmarket_avg1 END
           END AS selected_avg1,
           CASE WHEN r.match_status = 'EXACT' AND r.current_price IS NOT NULL
                THEN CASE WHEN r.selected_metric = 'Foil Low'
                          THEN r.cardmarket_foil_avg7 ELSE r.cardmarket_avg7 END
           END AS selected_avg7,
           CASE WHEN r.match_status = 'EXACT' AND r.current_price IS NOT NULL
                THEN CASE WHEN r.selected_metric = 'Foil Low'
                          THEN r.cardmarket_foil_avg30 ELSE r.cardmarket_avg30 END
           END AS selected_avg30,
           r.source_currency
      FROM printing_price_resolutions r
     WHERE r.is_current = 1
       AND r.collection_item_id IS NULL
       AND r.wishlist_item_id IS NOT NULL
       AND COALESCE(r.source, 'cardmarket') = 'cardmarket'
), card_price AS (
    SELECT c.id AS card_id,
           CASE WHEN r.card_id IS NOT NULL THEN r.current_price ELSE CASE WHEN lower(c.finish) = 'foil' THEN lp.low_alt ELSE l.current_price END END AS current_price,
           CASE WHEN r.card_id IS NOT NULL THEN r.observed_at ELSE l.observed_at END AS observed_at,
           CASE WHEN r.card_id IS NOT NULL THEN r.source ELSE l.source END AS source,
           CASE WHEN r.card_id IS NOT NULL THEN r.resolution_method ELSE l.resolution_method END AS resolution_method,
           CASE WHEN r.card_id IS NOT NULL THEN COALESCE(r.source_currency, r.currency) ELSE 'EUR' END AS currency,
           CASE WHEN r.card_id IS NOT NULL THEN r.external_id ELSE NULL END AS external_id,
           COALESCE(CASE WHEN r.card_id IS NOT NULL THEN r.sample_size ELSE 0 END, 0) AS sample_size,
           CASE WHEN r.card_id IS NOT NULL THEN r.lowest_price ELSE NULL END AS lowest_price,
           CASE WHEN r.card_id IS NOT NULL THEN r.median_price ELSE NULL END AS median_price,
           CASE WHEN r.card_id IS NOT NULL THEN r.price_confidence ELSE NULL END AS price_confidence,
           CASE WHEN r.card_id IS NOT NULL THEN r.cardmarket_low ELSE l.current_price END AS cardmarket_low,
           CASE WHEN r.card_id IS NOT NULL THEN r.cardmarket_trend ELSE NULL END AS cardmarket_trend,
           CASE WHEN r.card_id IS NOT NULL THEN r.cardmarket_avg1 ELSE NULL END AS cardmarket_avg1,
           CASE WHEN r.card_id IS NOT NULL THEN r.cardmarket_avg7 ELSE NULL END AS cardmarket_avg7,
           CASE WHEN r.card_id IS NOT NULL THEN r.cardmarket_avg30 ELSE NULL END AS cardmarket_avg30
      FROM cards c
      JOIN games g ON g.id = c.game_id
      LEFT JOIN legacy_card_price l ON l.card_id = c.id
      LEFT JOIN latest_price lp ON lp.cardmarket_product_id = (SELECT cardmarket_product_id FROM single_product sp2 WHERE sp2.card_id = c.id)
      LEFT JOIN latest_resolution r
             ON r.card_id = c.id AND COALESCE(r.language_id, -1) = COALESCE(c.language_id, -1)
)
"""


@dataclass
class CatalogRow:
    id: int
    canonical_card_id: int | None
    game_code: str
    name: str
    artist: str | None
    metadata: dict | None
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
    price_observed_at: str | None
    price_source: str | None
    resolution_method: str | None
    price_currency: str | None
    price_external_id: str | None
    price_sample_size: int
    lowest_price: float | None
    median_price: float | None
    price_confidence: str | None
    cardmarket_low: float | None
    cardmarket_trend: float | None
    cardmarket_avg1: float | None
    cardmarket_avg7: float | None
    cardmarket_avg30: float | None
    source_currency: str | None
    owned: bool
    wishlist: bool
    wishlist_item_id: int | None
    price_sources: list["PriceSourceData"] = field(default_factory=list)
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
    canonical_card_id: int | None
    game_code: str
    quantity_wanted: int
    priority: str
    target_price: float | None
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
    language: str | None
    release_kind: str | None
    art_kind: str | None
    printing_count: int
    reprint_count: int
    current_price: float | None
    source: str | None
    resolution_method: str | None
    price_currency: str | None
    cardmarket_low: float | None
    cardmarket_trend: float | None
    cardmarket_avg1: float | None
    cardmarket_avg7: float | None
    cardmarket_avg30: float | None
    source_currency: str | None
    matched: bool
    acquired_at: str | None
    removed_at: str | None
    image: CardImageData | None = None


def _catalog_row(row: sqlite3.Row) -> CatalogRow:
    metadata = None
    if row["canonical_metadata"]:
        try:
            parsed = json.loads(row["canonical_metadata"])
            metadata = parsed if isinstance(parsed, dict) else None
        except (TypeError, json.JSONDecodeError):
            metadata = None
    pokemon_metadata = metadata.get("pokemon") if metadata else None
    artist = pokemon_metadata.get("artist") if isinstance(pokemon_metadata, dict) else None
    return CatalogRow(
        id=row["id"], canonical_card_id=row["canonical_card_id"], game_code=row["game_code"],
        name=row["name"], artist=artist, metadata=metadata, set_code=row["set_code"],
        expansion_name=row["expansion_name"], card_number=row["card_number"],
        rarity=row["rarity"], finish=row["finish"], treatment=row["treatment"],
        language=row["language"], release_kind=row["release_kind"], art_kind=row["art_kind"],
        printing_count=row["printing_count"], reprint_count=row["reprint_count"],
        current_price=row["current_price"], price_observed_at=row["price_observed_at"],
        price_source=row["price_source"], resolution_method=row["resolution_method"], owned=bool(row["owned"]),
        price_currency=row["price_currency"], price_external_id=row["price_external_id"],
        price_sample_size=row["price_sample_size"], lowest_price=row["lowest_price"],
        median_price=row["median_price"], price_confidence=row["price_confidence"],
        cardmarket_low=row["cardmarket_low"], cardmarket_trend=row["cardmarket_trend"],
        cardmarket_avg1=row["cardmarket_avg1"], cardmarket_avg7=row["cardmarket_avg7"],
        cardmarket_avg30=row["cardmarket_avg30"], source_currency=row["source_currency"],
        wishlist=bool(row["wishlist"]), wishlist_item_id=row["wishlist_item_id"],
    )


@dataclass
class PriceSourceData:
    """Generic source payload kept separate from the primary Cardmarket price."""

    role: str
    provider: str
    market: str
    currency: str
    source_variant: str | None
    metrics: dict[str, float]
    source_updated_at: str | None
    observed_at: str
    provenance: str
    confidence: str | None


def fetch_price_sources(conn: sqlite3.Connection, card_ids: list[int]) -> dict[int, list[PriceSourceData]]:
    if not card_ids:
        return {}
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='market_price_observations'").fetchone():
        return {}
    placeholders = ",".join("?" for _ in card_ids)
    rows = conn.execute(f"""
        SELECT o.*
          FROM market_price_observations o
         WHERE o.card_id IN ({placeholders})
         ORDER BY o.card_id, o.provider, o.market, o.currency,
                  COALESCE(o.source_updated_at, ''), o.observed_at, o.id
    """, card_ids).fetchall()
    grouped: dict[tuple, dict[str, Any]] = {}
    for row in rows:
        key = (row["card_id"], row["provider"], row["market"], row["currency"], row["source_variant"], row["snapshot_key"])
        grouped.setdefault(key, {"row": row, "metrics": {}})["metrics"][row["metric"]] = row["value"]
    latest: dict[tuple, dict[str, Any]] = {}
    for key, payload in grouped.items():
        identity = key[:-1]
        row = payload["row"]
        ordering = (row["source_updated_at"] or "", row["observed_at"] or "", row["id"])
        previous = latest.get(identity)
        if previous is None or ordering > previous["ordering"]:
            latest[identity] = {"ordering": ordering, **payload}
    result: dict[int, list[PriceSourceData]] = defaultdict(list)
    for payload in latest.values():
        row = payload["row"]
        result[row["card_id"]].append(PriceSourceData(
            role="secondary", provider=row["provider"], market=row["market"], currency=row["currency"],
            source_variant=row["source_variant"], metrics=payload["metrics"], source_updated_at=row["source_updated_at"],
            observed_at=row["observed_at"], provenance=row["provenance"], confidence=row["confidence"],
        ))
    return result


def build_catalog_filters(
    game: str = "magic",
    language: str | None = None,
    sets: list[str] | None = None,
    search: str | None = None,
    ownership: str | None = None,
    rarity: str | None = None,
    finish: str | None = None,
    treatment: str | None = None,
) -> tuple[str, list]:
    clauses = [
        "g.code = ?",
        "(c.catalog_status = 'active' OR (g.code = 'magic' AND lower(COALESCE(c.set_code, e.set_code)) IN ('ltr', 'ltc') AND c.finish IS NOT NULL))",
    ]
    params: list = [game]
    if sets:
        placeholders = ",".join("?" for _ in sets)
        clauses.append(f"lower(COALESCE(s.code, c.set_code, e.set_code)) IN ({placeholders})")
        params.extend(value.casefold() for value in sets)
    if search:
        like = f"%{search}%"
        clauses.append("(c.name LIKE ? COLLATE NOCASE OR c.normalized_name LIKE ? COLLATE NOCASE OR c.card_number LIKE ? COLLATE NOCASE)")
        params.extend([like, like, like])
    if language:
        clauses.append("l.code = ?")
        params.append(language.casefold())
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
    sql = _pricing_schema_sql(conn, _CARD_PRICE_CTE) + f"""
        SELECT c.id, c.canonical_card_id, g.code AS game_code, c.name,
               cc.metadata AS canonical_metadata,
               COALESCE(s.code, c.set_code, e.set_code) AS set_code,
               COALESCE(s.name, e.name) AS expansion_name, c.card_number,
               c.rarity, c.finish, c.treatment, l.code AS language,
               c.release_kind, c.art_kind,
               (SELECT COUNT(*) FROM cards pc WHERE pc.canonical_card_id=c.canonical_card_id AND pc.catalog_status='active') AS printing_count,
               (SELECT COUNT(*) FROM cards rc WHERE rc.canonical_card_id=c.canonical_card_id AND rc.catalog_status='active' AND rc.release_kind='reprint') AS reprint_count,
               cp.current_price, cp.observed_at AS price_observed_at,
               cp.source AS price_source, cp.resolution_method,
               cp.currency AS price_currency, cp.external_id AS price_external_id,
               cp.sample_size AS price_sample_size, cp.lowest_price,
               cp.median_price, cp.price_confidence,
               cp.cardmarket_low, cp.cardmarket_trend, cp.cardmarket_avg1,
               cp.cardmarket_avg7, cp.cardmarket_avg30, cp.currency AS source_currency,
               EXISTS (SELECT 1 FROM collection_items ci WHERE ci.card_id = c.id) AS owned,
               EXISTS (SELECT 1 FROM wishlist_items wi WHERE wi.card_id = c.id AND wi.status = 'wanted') AS wishlist,
               (SELECT wi.id FROM wishlist_items wi WHERE wi.card_id = c.id AND wi.status = 'wanted' ORDER BY wi.id LIMIT 1) AS wishlist_item_id
          FROM cards c
          JOIN expansions e ON e.id = c.expansion_id
          JOIN games g ON g.id = c.game_id
          LEFT JOIN canonical_cards cc ON cc.id = c.canonical_card_id
          LEFT JOIN sets s ON s.id = c.set_id
          LEFT JOIN languages l ON l.id = c.language_id
          LEFT JOIN card_price cp ON cp.card_id = c.id
          {where_sql}
         ORDER BY c.name COLLATE NOCASE, COALESCE(s.code, c.set_code), c.card_number, c.finish, c.id
         LIMIT ? OFFSET ?"""
    rows = conn.execute(sql, [*where_params, limit, offset]).fetchall()
    result = [_catalog_row(row) for row in rows]
    secondary = fetch_price_sources(conn, [row.id for row in result])
    for row in result:
        row.price_sources = secondary.get(row.id, [])
    images = fetch_exact_images(conn, sorted({row.id for row in result}))
    for row in result:
        row.image = images.get(row.id)
    return result


def count_catalog_rows(conn: sqlite3.Connection, where_sql: str, where_params: list) -> int:
    row = conn.execute(
        _pricing_schema_sql(conn, _CARD_PRICE_CTE) + f"SELECT COUNT(*) FROM cards c JOIN expansions e ON e.id=c.expansion_id JOIN games g ON g.id=c.game_id LEFT JOIN sets s ON s.id=c.set_id LEFT JOIN languages l ON l.id=c.language_id {where_sql}",
        where_params,
    ).fetchone()
    return row[0]


def count_catalog_identities(conn: sqlite3.Connection, where_sql: str, where_params: list) -> int:
    row = conn.execute(
        _pricing_schema_sql(conn, _CARD_PRICE_CTE)
        + "SELECT COUNT(DISTINCT COALESCE(c.canonical_card_id, c.id)) FROM cards c JOIN expansions e ON e.id=c.expansion_id JOIN games g ON g.id=c.game_id LEFT JOIN sets s ON s.id=c.set_id LEFT JOIN languages l ON l.id=c.language_id LEFT JOIN canonical_cards cc ON cc.id=c.canonical_card_id "
        + where_sql,
        where_params,
    ).fetchone()
    return row[0]


def fetch_catalog_detail(conn: sqlite3.Connection, card_id: int) -> tuple[CatalogRow, list[CatalogRow]] | None:
    selected = fetch_catalog_rows(conn, " WHERE c.id = ?", [card_id], 1, 0)
    if not selected:
        return None
    printing = selected[0]
    if printing.canonical_card_id is None:
        return printing, [printing]
    related = fetch_catalog_rows(
        conn,
        " WHERE c.canonical_card_id = ? AND c.catalog_status = 'active'",
        [printing.canonical_card_id],
        500,
        0,
    )
    return printing, related


def fetch_catalog_options(conn: sqlite3.Connection, game: str | None = None) -> dict[str, list[dict[str, str]]]:
    games = [
        {"value": row["code"], "label": row["name"]}
        for row in conn.execute(
            "SELECT code, name FROM games WHERE catalog_is_active=1 ORDER BY name"
        ).fetchall()
    ]
    language_rows = conn.execute(
        """SELECT DISTINCT l.code, l.name
             FROM cards c JOIN languages l ON l.id=c.language_id JOIN games g ON g.id=c.game_id
            WHERE c.catalog_status='active' AND (? IS NULL OR g.code=?)
            ORDER BY l.name""",
        (game, game),
    ).fetchall()
    set_rows = conn.execute(
        """SELECT DISTINCT s.code, s.name
             FROM sets s JOIN games g ON g.id=s.game_id JOIN cards c ON c.set_id=s.id
            WHERE c.catalog_status='active' AND (? IS NULL OR g.code=?)
            ORDER BY s.release_date, s.code""",
        (game, game),
    ).fetchall()
    return {
        "games": games,
        "languages": [{"value": row["code"], "label": row["name"]} for row in language_rows],
        "sets": [{"value": row["code"], "label": row["name"]} for row in set_rows],
    }


def _wishlist_row(row: sqlite3.Row) -> WishlistRow:
    return WishlistRow(
        id=row["id"], card_id=row["card_id"], canonical_card_id=row["canonical_card_id"],
        game_code=row["game_code"], quantity_wanted=row["quantity_wanted"],
        priority=row["priority"], target_price=row["target_price"], max_price=row["max_price"], currency=row["currency"],
        notes=row["notes"], status=row["status"], created_at=row["created_at"],
        updated_at=row["updated_at"], name=row["name"], set_code=row["set_code"],
        expansion_name=row["expansion_name"], card_number=row["card_number"],
        rarity=row["rarity"], finish=row["finish"], treatment=row["treatment"],
        language=row["language"], release_kind=row["release_kind"], art_kind=row["art_kind"],
        printing_count=row["printing_count"], reprint_count=row["reprint_count"],
        current_price=row["current_price"], source=row["source"],
        resolution_method=row["resolution_method"],
        price_currency=row["price_currency"],
        cardmarket_low=row["cardmarket_low"], cardmarket_trend=row["cardmarket_trend"],
        cardmarket_avg1=row["cardmarket_avg1"], cardmarket_avg7=row["cardmarket_avg7"],
        cardmarket_avg30=row["cardmarket_avg30"], source_currency=row["source_currency"],
        matched=bool(row["matched"]), acquired_at=row["acquired_at"],
        removed_at=row["removed_at"],
    )


_WISHLIST_MATCHED_SQL = """(
    c.catalog_status = 'active' OR (
        g.code = 'magic'
        AND lower(COALESCE(c.set_code, e.set_code)) IN ('ltr', 'ltc')
        AND c.card_number IS NOT NULL
        AND c.finish IS NOT NULL
    )
)"""

_WISHLIST_FROM = """
          FROM wishlist_items wi
          JOIN cards c ON c.id = wi.card_id
          JOIN expansions e ON e.id = c.expansion_id
          JOIN games g ON g.id = c.game_id
          LEFT JOIN sets s ON s.id = c.set_id
          LEFT JOIN languages l ON l.id = c.language_id
          LEFT JOIN card_price cp ON cp.card_id = c.id
          LEFT JOIN latest_wishlist_resolution wr ON wr.wishlist_item_id = wi.id
"""


def build_wishlist_filters(
    status: str | None = "wanted",
    priorities: list[str] | None = None,
    sets: list[str] | None = None,
    finish: str | None = None,
    has_price: bool | None = None,
    matched: bool | None = None,
    game: str | None = None,
    language: str | None = None,
) -> tuple[str, list]:
    clauses: list[str] = []
    params: list = []
    if status and status != "all":
        clauses.append("wi.status = ?")
        params.append(status)
    if game:
        clauses.append("g.code = ?")
        params.append(game)
    if language:
        clauses.append("l.code = ?")
        params.append(language.casefold())
    if priorities:
        placeholders = ",".join("?" for _ in priorities)
        clauses.append(f"wi.priority IN ({placeholders})")
        params.extend(value.casefold() for value in priorities)
    if sets:
        placeholders = ",".join("?" for _ in sets)
        clauses.append(f"lower(COALESCE(s.code, c.set_code, e.set_code)) IN ({placeholders})")
        params.extend(value.casefold() for value in sets)
    if finish:
        clauses.append("c.finish = ?")
        params.append(finish.casefold())
    effective_price = "CASE WHEN wr.id IS NOT NULL THEN wr.selected_low ELSE cp.current_price END"
    if has_price is True:
        clauses.append(f"({effective_price}) IS NOT NULL")
    elif has_price is False:
        clauses.append(f"({effective_price}) IS NULL")
    if matched is True:
        clauses.append(_WISHLIST_MATCHED_SQL)
    elif matched is False:
        clauses.append(f"NOT {_WISHLIST_MATCHED_SQL}")
    return (" WHERE " + " AND ".join(clauses)) if clauses else "", params


def _wishlist_order(sort: str) -> str:
    effective_price = "CASE WHEN wr.id IS NOT NULL THEN wr.selected_low ELSE cp.current_price END"
    order_by = {
        "priority": "CASE wi.priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 WHEN 'low' THEN 2 ELSE 3 END, wi.updated_at DESC, wi.id DESC",
        "name": "c.name COLLATE NOCASE, wi.id DESC",
        "current_price": f"{effective_price} IS NULL, {effective_price}, c.name COLLATE NOCASE, wi.id DESC",
        "target_price": "wi.target_price IS NULL, wi.target_price, c.name COLLATE NOCASE, wi.id DESC",
        "max_price": "wi.max_price IS NULL, wi.max_price, c.name COLLATE NOCASE, wi.id DESC",
    }
    return order_by.get(sort, order_by["priority"])


def _wishlist_select_body(where_sql: str = "", order_by_sql: str = "") -> str:
    return f"""
        SELECT wi.id, wi.card_id, wi.quantity_wanted, wi.priority, wi.target_price,
               wi.max_price, wi.currency, wi.notes, wi.status, wi.acquired_at,
               wi.removed_at, wi.created_at, wi.updated_at, wi.language_id,
               c.canonical_card_id, g.code AS game_code, c.name,
               COALESCE(s.code, c.set_code, e.set_code) AS set_code,
               COALESCE(s.name, e.name) AS expansion_name, c.card_number,
               c.rarity, c.finish, c.treatment, l.code AS language,
               c.release_kind, c.art_kind,
               (SELECT COUNT(*) FROM cards pc WHERE pc.canonical_card_id=c.canonical_card_id AND pc.catalog_status='active') AS printing_count,
               (SELECT COUNT(*) FROM cards rc WHERE rc.canonical_card_id=c.canonical_card_id AND rc.catalog_status='active' AND rc.release_kind='reprint') AS reprint_count,
               CASE WHEN wr.id IS NOT NULL THEN wr.selected_low ELSE cp.current_price END AS current_price,
               CASE WHEN wr.id IS NOT NULL AND wr.selected_low IS NOT NULL THEN wr.source ELSE cp.source END AS source,
               CASE WHEN wr.id IS NOT NULL AND wr.selected_low IS NOT NULL THEN wr.resolution_method ELSE cp.resolution_method END AS resolution_method,
               CASE WHEN wr.id IS NOT NULL AND wr.selected_low IS NOT NULL THEN COALESCE(wr.source_currency, wr.currency) ELSE cp.currency END AS price_currency,
               CASE WHEN wr.id IS NOT NULL THEN wr.selected_low ELSE cp.cardmarket_low END AS cardmarket_low,
               CASE WHEN wr.id IS NOT NULL THEN wr.selected_trend ELSE cp.cardmarket_trend END AS cardmarket_trend,
               CASE WHEN wr.id IS NOT NULL THEN wr.selected_avg1 ELSE cp.cardmarket_avg1 END AS cardmarket_avg1,
               CASE WHEN wr.id IS NOT NULL THEN wr.selected_avg7 ELSE cp.cardmarket_avg7 END AS cardmarket_avg7,
               CASE WHEN wr.id IS NOT NULL THEN wr.selected_avg30 ELSE cp.cardmarket_avg30 END AS cardmarket_avg30,
               CASE WHEN wr.id IS NOT NULL AND wr.selected_low IS NOT NULL THEN wr.source_currency ELSE cp.currency END AS source_currency,
               {_WISHLIST_MATCHED_SQL} AS matched
          {_WISHLIST_FROM}
          {where_sql}
          {order_by_sql}"""


def _wishlist_select_sql(conn: sqlite3.Connection, where_sql: str = "", order_by_sql: str = "") -> str:
    return _pricing_schema_sql(conn, _CARD_PRICE_CTE) + _wishlist_select_body(where_sql, order_by_sql)


def fetch_wishlist_rows(
    conn: sqlite3.Connection,
    status: str | None = "wanted",
    priorities: list[str] | None = None,
    sets: list[str] | None = None,
    finish: str | None = None,
    has_price: bool | None = None,
    matched: bool | None = None,
    game: str | None = None,
    language: str | None = None,
    sort: str = "priority",
) -> list[WishlistRow]:
    where_sql, params = build_wishlist_filters(
        status=status, priorities=priorities, sets=sets, finish=finish,
        has_price=has_price, matched=matched, game=game, language=language,
    )
    sql = _wishlist_select_sql(conn, where_sql, f" ORDER BY {_wishlist_order(sort)}")
    result = [_wishlist_row(row) for row in conn.execute(sql, params).fetchall()]
    images = fetch_exact_images(conn, sorted({row.card_id for row in result}))
    for row in result:
        row.image = images.get(row.card_id)
    return result


def fetch_wishlist_row(conn: sqlite3.Connection, item_id: int) -> WishlistRow | None:
    rows = fetch_wishlist_rows(conn, status=None)
    return next((row for row in rows if row.id == item_id), None)


@dataclass
class WishlistSummary:
    wanted: int
    acquired: int
    missing_price: int
    unmatched: int
    estimated_total: float


@dataclass
class MatchCandidateRow:
    id: int
    name: str
    set_code: str | None
    expansion_name: str | None
    card_number: str | None
    finish: str | None
    treatment: str | None
    language: str | None
    image: CardImageData | None = None


@dataclass
class CollectionMatchContext:
    item_id: int
    name: str
    set_code: str | None
    card_number: str | None
    finish: str | None
    treatment: str | None
    language: str | None
    source: str
    source_note: str | None
    candidates: list[MatchCandidateRow] = field(default_factory=list)


def fetch_collection_match_context(
    conn: sqlite3.Connection,
    item_id: int,
    search: str | None = None,
) -> CollectionMatchContext | None:
    source = conn.execute(
        """SELECT ci.id, c.name, c.set_code, c.card_number, c.finish, c.treatment,
                  l.code AS language, ci.manual_entry_note, ci.notes,
                  ci.cardmarket_product_id
             FROM collection_items ci
             LEFT JOIN cards c ON c.id = ci.card_id
             LEFT JOIN languages l ON l.id = COALESCE(c.language_id, ci.language_id)
            WHERE ci.id=?""",
        (item_id,),
    ).fetchone()
    if source is None:
        return None
    name = source["name"] or source["manual_entry_note"] or source["notes"] or ""
    query = (search or name).strip()
    is_art_series = name.casefold().startswith("art series:")
    candidate_select = """SELECT c.id, c.name, COALESCE(c.set_code, e.set_code) AS set_code,
                      e.name AS expansion_name, c.card_number, c.finish, c.treatment,
                      l.code AS language
                 FROM cards c
                 JOIN expansions e ON e.id = c.expansion_id
                 JOIN games g ON g.id = c.game_id
                 LEFT JOIN languages l ON l.id = c.language_id
                WHERE {where}
                ORDER BY c.name COLLATE NOCASE, c.card_number, c.finish, c.id"""

    # Product mapping is the strongest identity.  It also prevents an Art
    # Series product from falling through to a playable card with the same name.
    candidates = []
    if source["cardmarket_product_id"] is not None:
        exact_clauses = [
            "m.cardmarket_product_id = ?",
            "m.status = 'mapped'",
            "c.catalog_status = 'active'",
            "g.code = 'magic'",
            "lower(COALESCE(c.set_code, e.set_code)) IN ('ltr', 'ltc')",
            "c.finish IS NOT NULL",
        ]
        exact_params: list = [source["cardmarket_product_id"]]
        if is_art_series:
            exact_clauses.append("c.name LIKE 'Art Series:%'")
        candidates = conn.execute(
            candidate_select.format(where=" AND ".join(exact_clauses)).replace(
                "JOIN expansions e ON e.id = c.expansion_id",
                "JOIN expansions e ON e.id = c.expansion_id\n                 JOIN cardmarket_product_mappings m ON m.card_id = c.id",
            ),
            exact_params,
        ).fetchall()

    if not candidates:
        clauses = [
            "c.catalog_status = 'active'",
            "g.code='magic'",
            "lower(COALESCE(c.set_code, e.set_code)) IN ('ltr', 'ltc')",
            "c.finish IS NOT NULL",
        ]
        params: list = []
        if is_art_series:
            # Art Series fallback is intentionally exact and never searches
            # playable cards with a similar name.
            clauses.append("c.name LIKE 'Art Series:%'")
            clauses.append("(lower(c.name) = lower(?) OR c.normalized_name = ?)")
            params.extend([name, " ".join(name.casefold().split())])
            if source["card_number"]:
                clauses.append("upper(c.card_number) = upper(?)")
                params.append(source["card_number"])
        else:
            clauses.append("c.card_number IS NOT NULL")
            if query:
                like = f"%{query}%"
                clauses.append("(c.name LIKE ? COLLATE NOCASE OR c.normalized_name LIKE ? COLLATE NOCASE)")
                params.extend([like, like])
        if source["set_code"]:
            clauses.append("lower(COALESCE(c.set_code, e.set_code)) = ?")
            params.append(source["set_code"].casefold())
        candidates = conn.execute(
            candidate_select.format(where=" AND ".join(clauses)),
            params,
        ).fetchall()
    result = [
        MatchCandidateRow(
            id=row["id"], name=row["name"], set_code=row["set_code"],
            expansion_name=row["expansion_name"], card_number=row["card_number"],
            finish=row["finish"], treatment=row["treatment"], language=row["language"],
        )
        for row in candidates
    ]
    images = fetch_exact_images(conn, [candidate.id for candidate in result])
    for candidate in result:
        candidate.image = images.get(candidate.id)
    return CollectionMatchContext(
        item_id=item_id, name=name, set_code=source["set_code"],
        card_number=source["card_number"], finish=source["finish"],
        treatment=source["treatment"], language=source["language"],
        source="cardmarket" if source["cardmarket_product_id"] is not None else "manual",
        source_note=source["manual_entry_note"] or source["notes"], candidates=result,
    )


def fetch_wishlist_summary(conn: sqlite3.Connection) -> WishlistSummary:
    row = conn.execute(
        _pricing_schema_sql(conn, _CARD_PRICE_CTE) + """
        SELECT
            COALESCE(SUM(CASE WHEN status = 'wanted' THEN 1 ELSE 0 END), 0) AS wanted,
            COALESCE(SUM(CASE WHEN status = 'acquired' THEN 1 ELSE 0 END), 0) AS acquired,
            COALESCE(SUM(CASE WHEN status = 'wanted' AND current_price IS NULL THEN 1 ELSE 0 END), 0) AS missing_price,
            COALESCE(SUM(CASE WHEN status = 'wanted' AND matched = 0 THEN 1 ELSE 0 END), 0) AS unmatched,
            COALESCE(SUM(CASE WHEN status = 'wanted' AND current_price IS NOT NULL
                              THEN current_price * quantity_wanted ELSE 0 END), 0) AS estimated_total
        FROM (""" + _wishlist_select_body() + ") AS wishlist_summary"
    ).fetchone()
    return WishlistSummary(
        wanted=row["wanted"], acquired=row["acquired"],
        missing_price=row["missing_price"], unmatched=row["unmatched"],
        estimated_total=round(float(row["estimated_total"]), 2),
    )
