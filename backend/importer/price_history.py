"""Insert de market_price_history solo para productos referenciados desde collection_items
o want_list_items (regla de scope de fase2-cardmarket-hallazgos-y-schema.md).

want_list_items no tiene columna cardmarket_product_id (solo card_id) -- hay que llegar
a cardmarket_product_id via cardmarket_product_mappings.
"""

import sqlite3

from price_mapping import map_price_guide_entry

_REFERENCED_PRODUCTS_SQL = """
    SELECT cp.id, cp.cardmarket_id_product
    FROM cardmarket_products cp
    WHERE cp.id IN (
        SELECT cardmarket_product_id FROM collection_items WHERE cardmarket_product_id IS NOT NULL
        UNION
        SELECT cpm.cardmarket_product_id
        FROM want_list_items wli
        JOIN cardmarket_product_mappings cpm ON cpm.card_id = wli.card_id
        WHERE wli.card_id IS NOT NULL
    )
"""


def insert_for_referenced_products(
    conn: sqlite3.Connection,
    price_guide_by_id_product: dict[int, dict],
    alt_suffix: str,
    observed_at: str,
    imported_at: str,
    game_key: str,
    report,
) -> int:
    rows = conn.execute(_REFERENCED_PRODUCTS_SQL).fetchall()
    inserted = 0
    for local_id, cardmarket_id_product in rows:
        entry = price_guide_by_id_product.get(cardmarket_id_product)
        if entry is None:
            continue  # no pertenece al price_guide de este juego
        mapped = map_price_guide_entry(entry, alt_suffix)
        conn.execute(
            """INSERT INTO market_price_history
                 (cardmarket_product_id, observed_at, low, avg, trend, avg1, avg7, avg30,
                  low_alt, avg_alt, trend_alt, avg1_alt, avg7_alt, avg30_alt, imported_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(cardmarket_product_id, observed_at) DO NOTHING""",
            (
                local_id,
                observed_at,
                mapped["low"], mapped["avg"], mapped["trend"], mapped["avg1"], mapped["avg7"], mapped["avg30"],
                mapped["low_alt"], mapped["avg_alt"], mapped["trend_alt"],
                mapped["avg1_alt"], mapped["avg7_alt"], mapped["avg30_alt"],
                imported_at,
            ),
        )
        inserted += 1
    report.price_history_inserted[game_key] = report.price_history_inserted.get(game_key, 0) + inserted
    return inserted
