"""Create (or update) the TCG Dashboard SQLite database from schema.sql + seed.sql.

Usage:
    python3 backend/db/init_db.py [path/to/db]
"""

import sqlite3
import sys
from pathlib import Path

DB_DIR = Path(__file__).parent
DEFAULT_DB_PATH = DB_DIR / "tcg_dashboard.db"


def ensure_pricing_columns(conn: sqlite3.Connection) -> None:
    """Apply the additive pricing migration to databases created before Phase 7."""
    additions = {
        "market_price_history": {
            "source": "TEXT NOT NULL DEFAULT 'cardmarket'",
            "source_currency": "TEXT NOT NULL DEFAULT 'EUR'",
            "source_snapshot_created_at": "TEXT", "source_snapshot_sha256": "TEXT",
            "source_manifest_id": "TEXT", "provenance": "TEXT",
        },
        "printing_price_resolutions": {
            "cardmarket_product_id": "INTEGER REFERENCES cardmarket_products(id)",
            "collection_item_id": "INTEGER REFERENCES collection_items(id)",
            "resolution_scope": "TEXT NOT NULL DEFAULT 'global' CHECK (resolution_scope IN ('global','collection','wishlist'))",
            "match_status": "TEXT", "is_current": "INTEGER NOT NULL DEFAULT 0",
            "selected_metric": "TEXT", "cardmarket_low": "REAL", "cardmarket_trend": "REAL",
            "cardmarket_avg1": "REAL", "cardmarket_avg7": "REAL", "cardmarket_avg30": "REAL",
            "cardmarket_foil_low": "REAL", "cardmarket_foil_trend": "REAL", "cardmarket_foil_avg1": "REAL",
            "cardmarket_foil_avg7": "REAL", "cardmarket_foil_avg30": "REAL", "source_currency": "TEXT",
            "source_snapshot_created_at": "TEXT", "source_snapshot_sha256": "TEXT",
            "source_manifest_id": "TEXT", "provenance": "TEXT",
        },
    }
    for table, fields in additions.items():
        existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
        for field, definition in fields.items():
            if field not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {field} {definition}")
    conn.execute("CREATE TABLE IF NOT EXISTS collection_price_overrides (id INTEGER PRIMARY KEY AUTOINCREMENT, collection_item_id INTEGER NOT NULL REFERENCES collection_items(id), card_id INTEGER NOT NULL REFERENCES cards(id), language_id INTEGER NOT NULL REFERENCES languages(id), cardmarket_product_id INTEGER NOT NULL REFERENCES cardmarket_products(id), match_status TEXT NOT NULL CHECK (match_status = 'EXACT'), approved INTEGER NOT NULL CHECK (approved IN (0,1)), row_hash TEXT NOT NULL, source_manifest_id TEXT NOT NULL, evidence TEXT NOT NULL, provenance TEXT NOT NULL, is_current INTEGER NOT NULL DEFAULT 1 CHECK (is_current IN (0,1)), created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE(collection_item_id, row_hash))")
    conn.execute("DROP INDEX IF EXISTS idx_printing_price_current_identity")
    conn.execute("CREATE UNIQUE INDEX idx_printing_price_current_identity ON printing_price_resolutions (card_id, language_id, COALESCE(source, 'cardmarket')) WHERE is_current = 1 AND collection_item_id IS NULL")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_collection_price_current_identity ON printing_price_resolutions (collection_item_id, COALESCE(source, 'cardmarket')) WHERE is_current = 1 AND collection_item_id IS NOT NULL")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_collection_override_current ON collection_price_overrides (collection_item_id) WHERE is_current = 1 AND approved = 1")


def init_db(db_path: Path) -> None:
    schema_sql = (DB_DIR / "schema.sql").read_text()
    seed_sql = (DB_DIR / "seed.sql").read_text()

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(schema_sql)
        conn.executescript(seed_sql)
        ensure_pricing_columns(conn)
        conn.commit()

        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
        ).fetchall()
        games = conn.execute("SELECT code FROM games ORDER BY id").fetchall()
        languages = conn.execute("SELECT code FROM languages ORDER BY id").fetchall()
    finally:
        conn.close()

    print(f"DB creada/actualizada en: {db_path}")
    print(f"Tablas ({len(tables)}): {', '.join(t[0] for t in tables)}")
    print(f"games seed: {', '.join(g[0] for g in games)}")
    print(f"languages seed: {', '.join(l[0] for l in languages)}")


if __name__ == "__main__":
    db_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DB_PATH
    init_db(db_path)
