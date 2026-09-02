"""Generic, additive schema support for Pokémon catalog finish and images.

The production importer applies this only to an isolated SQLite copy. Existing
rows and IDs are preserved while SQLite CHECK constraints are rebuilt.
"""

from __future__ import annotations

import sqlite3


CARDS_TABLE_SQL = """
CREATE TABLE cards__pokemon_schema (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL REFERENCES games (id),
    expansion_id INTEGER NOT NULL REFERENCES expansions (id),
    card_number TEXT,
    name TEXT NOT NULL,
    printing_variant TEXT NOT NULL CHECK (printing_variant IN ('normal', 'suggested_parallel', 'confirmed_parallel', 'other')),
    variant_label TEXT,
    cardmarket_id_metacard INTEGER,
    image_url TEXT,
    image_source TEXT CHECK (image_source IS NULL OR image_source IN ('scryfall', 'onepiece_official', 'manual')),
    data_source TEXT CHECK (data_source IS NULL OR data_source IN ('scryfall', 'cardmarket_heuristic', 'manual')),
    scryfall_raw TEXT,
    set_code TEXT,
    normalized_name TEXT,
    rarity TEXT,
    finish TEXT CHECK (finish IS NULL OR finish IN ('nonfoil', 'foil', 'etched', 'normal', 'holo', 'reverse_holo')),
    treatment TEXT,
    language_id INTEGER REFERENCES languages (id),
    scryfall_id TEXT,
    scryfall_oracle_id TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    canonical_card_id INTEGER REFERENCES canonical_cards (id),
    set_id INTEGER REFERENCES sets (id),
    release_kind TEXT NOT NULL DEFAULT 'unknown' CHECK (release_kind IN ('original', 'reprint', 'promo', 'special', 'unknown')),
    art_kind TEXT NOT NULL DEFAULT 'unknown' CHECK (art_kind IN ('base', 'alternate_art', 'parallel', 'manga', 'special', 'unknown')),
    source_variant TEXT,
    catalog_status TEXT NOT NULL DEFAULT 'legacy' CHECK (catalog_status IN ('active', 'legacy', 'ambiguous', 'excluded')),
    catalog_source TEXT
)
"""

CARD_COLUMNS = (
    "id", "game_id", "expansion_id", "card_number", "name", "printing_variant",
    "variant_label", "cardmarket_id_metacard", "image_url", "image_source",
    "data_source", "scryfall_raw", "set_code", "normalized_name", "rarity",
    "finish", "treatment", "language_id", "scryfall_id", "scryfall_oracle_id",
    "created_at", "updated_at", "canonical_card_id", "set_id", "release_kind",
    "art_kind", "source_variant", "catalog_status", "catalog_source",
)

CARD_INDEX_SQL = (
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_cards_legacy_identity ON cards (expansion_id, card_number, printing_variant) WHERE finish IS NULL AND catalog_status = 'legacy'",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_cards_catalog_identity ON cards (game_id, set_code, card_number, language_id, finish) WHERE set_code IS NOT NULL AND card_number IS NOT NULL AND language_id IS NOT NULL AND finish IS NOT NULL",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_cards_scryfall_finish_identity ON cards (scryfall_id, language_id, finish) WHERE scryfall_id IS NOT NULL AND language_id IS NOT NULL AND finish IS NOT NULL",
    "CREATE INDEX IF NOT EXISTS idx_cards_catalog_search ON cards (game_id, set_code, normalized_name)",
    "CREATE INDEX IF NOT EXISTS idx_cards_canonical ON cards (canonical_card_id, catalog_status, language_id)",
    "CREATE INDEX IF NOT EXISTS idx_cards_one_piece_commercial_identity ON cards (canonical_card_id, set_id, language_id, art_kind, source_variant) WHERE catalog_status = 'active' AND canonical_card_id IS NOT NULL AND set_id IS NOT NULL AND language_id IS NOT NULL AND source_variant IS NOT NULL",
)


def _table_sql(conn: sqlite3.Connection, table: str) -> str:
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return (row[0] or "") if row else ""


def schema_status(conn: sqlite3.Connection) -> dict[str, bool]:
    return {
        "cards_finish_variants": "'reverse_holo'" in _table_sql(conn, "cards"),
        "card_images_tcgdex": "'tcgdex'" in _table_sql(conn, "card_images"),
    }


def _rebuild_cards(conn: sqlite3.Connection) -> None:
    existing = {row[1] for row in conn.execute("PRAGMA table_info(cards)")}
    missing = set(CARD_COLUMNS) - existing
    if missing:
        raise RuntimeError(f"cards schema missing required columns: {sorted(missing)}")
    for index_name in (
        "idx_cards_legacy_identity", "idx_cards_catalog_identity",
        "idx_cards_scryfall_finish_identity", "idx_cards_catalog_search",
        "idx_cards_canonical", "idx_cards_one_piece_commercial_identity",
    ):
        conn.execute(f"DROP INDEX IF EXISTS {index_name}")
    conn.execute(CARDS_TABLE_SQL)
    columns = ", ".join(CARD_COLUMNS)
    conn.execute(
        f"INSERT INTO cards__pokemon_schema ({columns}) SELECT {columns} FROM cards"
    )
    conn.execute("DROP TABLE cards")
    conn.execute("ALTER TABLE cards__pokemon_schema RENAME TO cards")
    for sql in CARD_INDEX_SQL:
        conn.execute(sql)


def _rebuild_card_images(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE card_images__pokemon_schema (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id INTEGER NOT NULL REFERENCES cards (id),
            source TEXT NOT NULL CHECK (source IN ('scryfall', 'cardtrader', 'tcgdex', 'manual')),
            source_card_id TEXT,
            source_variant TEXT,
            source_collector_number TEXT,
            language TEXT NOT NULL,
            face_index INTEGER NOT NULL CHECK (face_index >= 0),
            image_url_small TEXT,
            image_url_large TEXT,
            match_quality TEXT NOT NULL CHECK (match_quality IN ('exact', 'representative', 'manual')),
            status TEXT NOT NULL CHECK (status IN ('resolved', 'ambiguous', 'missing', 'error')),
            last_checked_at TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            image_language_scope TEXT NOT NULL DEFAULT 'unknown',
            is_language_fallback INTEGER NOT NULL DEFAULT 0 CHECK (is_language_fallback IN (0, 1)),
            UNIQUE (card_id, source, language, face_index)
        )
    """)
    columns = "id, card_id, source, source_card_id, source_variant, source_collector_number, language, face_index, image_url_small, image_url_large, image_language_scope, is_language_fallback, match_quality, status, last_checked_at, created_at, updated_at"
    conn.execute(
        f"INSERT INTO card_images__pokemon_schema ({columns}) SELECT {columns} FROM card_images"
    )
    conn.execute("DROP TABLE card_images")
    conn.execute("ALTER TABLE card_images__pokemon_schema RENAME TO card_images")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_card_images_card_id ON card_images (card_id)")


def ensure_schema(conn: sqlite3.Connection, *, apply_changes: bool) -> dict[str, object]:
    """Return schema status, rebuilding only when explicitly requested."""
    status = schema_status(conn)
    required = all(status.values())
    if required or not apply_changes:
        return {**status, "required": required, "changed": False}

    conn.commit()
    conn.execute("PRAGMA foreign_keys=OFF")
    try:
        conn.execute("BEGIN")
        if not status["cards_finish_variants"]:
            _rebuild_cards(conn)
        if not status["card_images_tcgdex"]:
            _rebuild_card_images(conn)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.execute("PRAGMA foreign_keys=ON")
    final = schema_status(conn)
    if not all(final.values()):
        raise RuntimeError(f"schema extension failed: {final}")
    return {**final, "required": True, "changed": True}
