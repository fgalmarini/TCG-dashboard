"""Upsert de cardmarket_products por cardmarket_id_product."""

import sqlite3


def upsert_product(
    conn: sqlite3.Connection,
    cardmarket_id_product: int,
    raw_name: str,
    cardmarket_id_category: int,
    cardmarket_id_expansion: int,
    cardmarket_id_metacard: int | None,
    date_added: str | None,
    last_seen_at: str,
) -> int:
    """date_added no se pisa en corridas posteriores (se conserva el valor original de
    la primera vez que se vio el producto); last_seen_at siempre se actualiza."""
    conn.execute(
        """INSERT INTO cardmarket_products
             (cardmarket_id_product, raw_name, cardmarket_id_category, cardmarket_id_expansion,
              cardmarket_id_metacard, date_added, last_seen_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(cardmarket_id_product) DO UPDATE SET
             raw_name = excluded.raw_name,
             cardmarket_id_category = excluded.cardmarket_id_category,
             cardmarket_id_expansion = excluded.cardmarket_id_expansion,
             cardmarket_id_metacard = excluded.cardmarket_id_metacard,
             last_seen_at = excluded.last_seen_at""",
        (
            cardmarket_id_product,
            raw_name,
            cardmarket_id_category,
            cardmarket_id_expansion,
            cardmarket_id_metacard,
            date_added,
            last_seen_at,
        ),
    )
    row = conn.execute(
        "SELECT id FROM cardmarket_products WHERE cardmarket_id_product = ?",
        (cardmarket_id_product,),
    ).fetchone()
    return row[0]
