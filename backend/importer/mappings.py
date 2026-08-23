"""Lookup/upsert de cardmarket_product_mappings."""

import sqlite3
from dataclasses import dataclass


@dataclass
class ExistingMapping:
    card_id: int | None
    status: str


def get_existing_mapping(conn: sqlite3.Connection, cardmarket_product_id: int) -> ExistingMapping | None:
    row = conn.execute(
        "SELECT card_id, status FROM cardmarket_product_mappings WHERE cardmarket_product_id = ?",
        (cardmarket_product_id,),
    ).fetchone()
    if row is None:
        return None
    return ExistingMapping(card_id=row[0], status=row[1])


def upsert_mapping(
    conn: sqlite3.Connection,
    cardmarket_product_id: int,
    card_id: int | None,
    status: str,
    notes: str | None,
) -> None:
    conn.execute(
        """INSERT INTO cardmarket_product_mappings (cardmarket_product_id, card_id, status, notes)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(cardmarket_product_id) DO UPDATE SET
             card_id = excluded.card_id,
             status = excluded.status,
             notes = excluded.notes""",
        (cardmarket_product_id, card_id, status, notes),
    )
