"""Upsert de cardmarket_categories.

No tiene FK declarado desde cardmarket_products ni seed en Fase 3, pero se puebla
igual (solo categorias "Single", por eso is_single=1 siempre en estos inserts) --
decision discrecional: barata, deja la tabla util a futuro en vez de vacia.
"""

import sqlite3


def upsert_category(conn: sqlite3.Connection, game_id: int, cardmarket_id_category: int, category_name: str) -> None:
    conn.execute(
        """INSERT INTO cardmarket_categories (game_id, cardmarket_id_category, category_name, is_single)
           VALUES (?, ?, ?, 1)
           ON CONFLICT(cardmarket_id_category) DO UPDATE SET category_name = excluded.category_name""",
        (game_id, cardmarket_id_category, category_name),
    )
