"""Helper de tests para backend/api/ -- DB temporal (archivo, no :memory:) cargada
con schema.sql + seed.sql reales, mas fixtures a mano cubriendo los 4 casos del
sprint contract de Fase 6: fila mapeada con precio, fila con producto pero sin
snapshot todavia, fila manual, fila con purchase_price IS NULL.

Archivo (no :memory:) a proposito: test_api.py necesita que la dependency override de
FastAPI (get_db) abra una conexion nueva por request contra la misma DB, igual que en
produccion -- una DB :memory: no se comparte entre conexiones sqlite3 distintas.
"""

import sqlite3
from pathlib import Path

DB_SQL_DIR = Path(__file__).resolve().parent.parent / "db"

FIXTURE_TIMESTAMP = "2026-01-01T00:00:00"


def make_test_db(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript((DB_SQL_DIR / "schema.sql").read_text())
    conn.executescript((DB_SQL_DIR / "seed.sql").read_text())
    conn.commit()
    conn.close()


def insert_fixtures(conn: sqlite3.Connection) -> dict[str, int]:
    """Inserta los 4 casos y devuelve los ids relevantes para que los tests los
    referencien por nombre en vez de por numero magico."""
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO expansions (game_id, cardmarket_id_expansion, name, set_code) "
        "VALUES (3, 5285, 'The Lord of the Rings', 'ltr')"
    )
    expansion_id = cur.lastrowid

    cur.execute(
        "INSERT INTO cards (game_id, expansion_id, card_number, name, printing_variant) "
        "VALUES (3, ?, '1', 'Test Card A', 'normal')",
        (expansion_id,),
    )
    card_a_id = cur.lastrowid

    cur.execute(
        "INSERT INTO cards (game_id, expansion_id, card_number, name, printing_variant) "
        "VALUES (3, ?, '2', 'Test Card B', 'normal')",
        (expansion_id,),
    )
    card_b_id = cur.lastrowid

    cur.execute(
        """INSERT INTO cardmarket_products
               (cardmarket_id_product, raw_name, cardmarket_id_category, cardmarket_id_expansion,
                date_added, last_seen_at)
           VALUES (1001, 'Test Card A', 1, 5285, ?, ?)""",
        (FIXTURE_TIMESTAMP, FIXTURE_TIMESTAMP),
    )
    product_a_id = cur.lastrowid

    cur.execute(
        """INSERT INTO cardmarket_products
               (cardmarket_id_product, raw_name, cardmarket_id_category, cardmarket_id_expansion,
                date_added, last_seen_at)
           VALUES (1002, 'Test Card B', 1, 5285, ?, ?)""",
        (FIXTURE_TIMESTAMP, FIXTURE_TIMESTAMP),
    )
    product_b_id = cur.lastrowid

    cur.execute(
        "INSERT INTO cardmarket_product_mappings (cardmarket_product_id, card_id, status) "
        "VALUES (?, ?, 'mapped')",
        (product_a_id, card_a_id),
    )
    cur.execute(
        "INSERT INTO cardmarket_product_mappings (cardmarket_product_id, card_id, status) "
        "VALUES (?, ?, 'mapped')",
        (product_b_id, card_b_id),
    )

    # Producto A: dos snapshots -- el mas reciente (2026-01-08) debe ganar sobre el
    # viejo (2026-01-01). Prueba que la CTE latest_price toma MAX(observed_at), no
    # una fila cualquiera.
    cur.execute(
        """INSERT INTO market_price_history
               (cardmarket_product_id, observed_at, low, avg, trend, avg30, imported_at)
           VALUES (?, '2026-01-01T00:00:00', 8.0, 9.0, 10.0, 9.5, ?)""",
        (product_a_id, FIXTURE_TIMESTAMP),
    )
    cur.execute(
        """INSERT INTO market_price_history
               (cardmarket_product_id, observed_at, low, avg, trend, avg30, imported_at)
           VALUES (?, '2026-01-08T00:00:00', 11.0, 12.0, 12.5, 11.5, ?)""",
        (product_a_id, FIXTURE_TIMESTAMP),
    )
    # Producto B: sin ninguna fila en market_price_history -- caso "tiene producto
    # pero no tiene snapshot todavia" (distinto de las altas manuales).

    # Row 1: mapeada, con precio (trend mas reciente = 12.5), purchase_price seteado.
    cur.execute(
        """INSERT INTO collection_items
               (card_id, cardmarket_product_id, language_id, quantity, purchase_price, status, manual_entry)
           VALUES (?, ?, 1, 2, 5.0, 'KEEP', 0)""",
        (card_a_id, product_a_id),
    )
    row1_id = cur.lastrowid

    # Row 2: producto sin snapshot todavia -- market_trend debe ser NULL, pero
    # manual_entry=0 (no es alta manual).
    cur.execute(
        """INSERT INTO collection_items
               (card_id, cardmarket_product_id, language_id, quantity, purchase_price, status, manual_entry)
           VALUES (?, ?, 1, 1, 3.0, 'KEEP', 0)""",
        (card_b_id, product_b_id),
    )
    row2_id = cur.lastrowid

    # Row 3: alta manual -- card_id/cardmarket_product_id NULL, sin precio posible.
    cur.execute(
        """INSERT INTO collection_items
               (card_id, cardmarket_product_id, language_id, quantity, purchase_price, status,
                manual_entry, manual_entry_note)
           VALUES (NULL, NULL, 1, 1, 20.0, 'KEEP', 1,
                   'Alta manual: Some Promo Card | link: https://cardmarket.example/x')"""
    )
    row3_id = cur.lastrowid

    # Row 4: purchase_price IS NULL, pero SI tiene precio de mercado (misma card A).
    cur.execute(
        """INSERT INTO collection_items
               (card_id, cardmarket_product_id, language_id, quantity, purchase_price, status, manual_entry)
           VALUES (?, ?, 1, 1, NULL, 'HOLD', 0)""",
        (card_a_id, product_a_id),
    )
    row4_id = cur.lastrowid

    cur.execute(
        """INSERT INTO card_images
               (card_id, source, source_card_id, language, face_index, image_url_small,
                image_url_large, match_quality, status, last_checked_at)
           VALUES (?, 'scryfall', 'sf-card-a', 'en', 0,
                   'https://cards.scryfall.io/small/front/a/a/card-a.jpg',
                   'https://cards.scryfall.io/large/front/a/a/card-a.jpg',
                   'exact', 'resolved', ?)""",
        (card_a_id, FIXTURE_TIMESTAMP),
    )

    cur.execute(
        """INSERT INTO card_images
               (card_id, source, source_card_id, language, face_index, image_url_small,
                image_url_large, match_quality, status, last_checked_at)
           VALUES (?, 'scryfall', 'sf-card-b', 'en', 0,
                   'https://cards.scryfall.io/small/front/b/b/card-b-front.jpg',
                   'https://cards.scryfall.io/large/front/b/b/card-b-front.jpg',
                   'representative', 'resolved', ?)""",
        (card_b_id, FIXTURE_TIMESTAMP),
    )

    conn.commit()

    return {
        "expansion_id": expansion_id,
        "card_a_id": card_a_id,
        "card_b_id": card_b_id,
        "product_a_id": product_a_id,
        "product_b_id": product_b_id,
        "row1_id": row1_id,
        "row2_id": row2_id,
        "row3_id": row3_id,
        "row4_id": row4_id,
    }
