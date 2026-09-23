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
            "wishlist_item_id": "INTEGER REFERENCES wishlist_items(id)",
            "resolution_scope": "TEXT NOT NULL DEFAULT 'global' CHECK (resolution_scope IN ('global','collection','wishlist'))",
            "match_status": "TEXT", "is_current": "INTEGER NOT NULL DEFAULT 0",
            "selected_metric": "TEXT", "cardmarket_low": "REAL", "cardmarket_trend": "REAL",
            "cardmarket_avg1": "REAL", "cardmarket_avg7": "REAL", "cardmarket_avg30": "REAL",
            "cardmarket_foil_low": "REAL", "cardmarket_foil_trend": "REAL", "cardmarket_foil_avg1": "REAL",
            "cardmarket_foil_avg7": "REAL", "cardmarket_foil_avg30": "REAL", "source_currency": "TEXT",
            "valuation_status": "TEXT CHECK (valuation_status IS NULL OR valuation_status IN ('EXACT','ESTIMATED'))",
            "valuation_method": "TEXT", "valuation_value": "REAL", "reason": "TEXT",
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
    conn.execute("DROP INDEX IF EXISTS idx_collection_price_current_identity")
    conn.execute("DROP INDEX IF EXISTS idx_wishlist_price_current_item")
    conn.execute("CREATE UNIQUE INDEX idx_printing_price_current_identity ON printing_price_resolutions (card_id, language_id, COALESCE(source, 'cardmarket')) WHERE is_current = 1 AND collection_item_id IS NULL AND wishlist_item_id IS NULL")
    conn.execute("CREATE UNIQUE INDEX idx_collection_price_current_identity ON printing_price_resolutions (collection_item_id, COALESCE(source, 'cardmarket')) WHERE is_current = 1 AND collection_item_id IS NOT NULL AND wishlist_item_id IS NULL")
    conn.execute("CREATE UNIQUE INDEX idx_wishlist_price_current_item ON printing_price_resolutions (wishlist_item_id, COALESCE(source, 'cardmarket')) WHERE is_current = 1 AND wishlist_item_id IS NOT NULL AND collection_item_id IS NULL")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_collection_override_current ON collection_price_overrides (collection_item_id) WHERE is_current = 1 AND approved = 1")
    rows = conn.execute("SELECT id, resolution_scope, collection_item_id, wishlist_item_id FROM printing_price_resolutions").fetchall()
    for row in rows:
        scope = row[1] or "global"
        valid = (
            (scope == "global" and row[2] is None and row[3] is None)
            or (scope == "collection" and row[2] is not None and row[3] is None)
            or (scope == "wishlist" and row[2] is None and row[3] is not None)
        )
        if not valid:
            raise ValueError(f"Invalid printing resolution scope at id={row[0]}")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS market_price_observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id INTEGER NOT NULL REFERENCES cards(id),
            provider TEXT NOT NULL,
            market TEXT NOT NULL,
            metric TEXT NOT NULL,
            value REAL NOT NULL CHECK (value > 0),
            currency TEXT NOT NULL,
            source_updated_at TEXT,
            observed_at TEXT NOT NULL,
            snapshot_key TEXT NOT NULL,
            provenance TEXT NOT NULL,
            confidence TEXT,
            source_variant TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(card_id, provider, market, metric, currency, snapshot_key)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_market_price_observations_card_source ON market_price_observations(card_id, provider, market, observed_at DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_market_price_observations_snapshot ON market_price_observations(snapshot_key, provider, market)")


def ensure_event_schema(conn: sqlite3.Connection) -> None:
    """Add reusable event links and allow sets without Cardmarket expansion IDs."""
    columns = {row[1]: row for row in conn.execute("PRAGMA table_info(expansions)")}
    if columns.get("cardmarket_id_expansion") and columns["cardmarket_id_expansion"][3]:
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.executescript("""
            CREATE TABLE expansions_nullable_cm (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER NOT NULL REFERENCES games(id),
                cardmarket_id_expansion INTEGER UNIQUE,
                name TEXT,
                set_code TEXT,
                release_date TEXT,
                set_id INTEGER REFERENCES sets(id)
            );
            INSERT INTO expansions_nullable_cm SELECT * FROM expansions;
            DROP TABLE expansions;
            ALTER TABLE expansions_nullable_cm RENAME TO expansions;
        """)
        conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            starts_at TEXT,
            ends_at TEXT,
            status TEXT NOT NULL DEFAULT 'planned',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS event_wishlist_items (
            event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
            wishlist_item_id INTEGER NOT NULL REFERENCES wishlist_items(id) ON DELETE CASCADE,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(event_id, wishlist_item_id)
        );
    """)


def ensure_canonical_only_cardmarket_scopes(conn: sqlite3.Connection) -> None:
    """Allow a canonical Cardmarket mapping without inferring a physical finish.

    Existing rows are copied byte-for-byte for all finish fields.  This is an
    additive compatibility migration for databases created before 004B.
    """
    columns = {row[1]: row for row in conn.execute("PRAGMA table_info(cardmarket_product_printing_scopes)")}
    if not columns or columns["finish_scope"][3] == 0:
        return
    conn.execute("PRAGMA foreign_keys=OFF")
    try:
        conn.execute("""
            CREATE TABLE cardmarket_product_printing_scopes_004b (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cardmarket_product_id INTEGER NOT NULL UNIQUE REFERENCES cardmarket_products (id),
                canonical_card_id INTEGER NOT NULL REFERENCES canonical_cards (id),
                card_id INTEGER REFERENCES cards (id),
                finish_scope TEXT CHECK (finish_scope IN ('single', 'multiple', 'unknown')),
                compatible_finishes TEXT,
                numbered_identity_status TEXT NOT NULL CHECK (numbered_identity_status IN ('EXACT', 'PROBABLE', 'AMBIGUOUS', 'MISMATCH', 'UNRESOLVED')),
                finish_mapping_status TEXT NOT NULL CHECK (finish_mapping_status IN ('EXACT_SINGLE', 'EXACT_MULTIPLE', 'SUPPORTED', 'AMBIGUOUS', 'UNKNOWN', 'NOT_APPLICABLE')),
                mapping_status TEXT NOT NULL CHECK (mapping_status IN ('EXACT', 'PROBABLE', 'AMBIGUOUS', 'MISMATCH', 'UNRESOLVED')),
                mapping_confidence TEXT NOT NULL,
                mapping_method TEXT NOT NULL,
                evidence TEXT NOT NULL,
                provenance TEXT NOT NULL,
                pricing_eligible INTEGER NOT NULL DEFAULT 0 CHECK (pricing_eligible IN (0, 1)),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""INSERT INTO cardmarket_product_printing_scopes_004b
            SELECT id, cardmarket_product_id, canonical_card_id, card_id, finish_scope,
                   compatible_finishes, numbered_identity_status, finish_mapping_status,
                   mapping_status, mapping_confidence, mapping_method, evidence,
                   provenance, pricing_eligible, created_at, updated_at
              FROM cardmarket_product_printing_scopes""")
        conn.execute("DROP TABLE cardmarket_product_printing_scopes")
        conn.execute("ALTER TABLE cardmarket_product_printing_scopes_004b RENAME TO cardmarket_product_printing_scopes")
        conn.execute("CREATE INDEX idx_cardmarket_product_scope_canonical ON cardmarket_product_printing_scopes (canonical_card_id, finish_scope)")
    finally:
        conn.execute("PRAGMA foreign_keys=ON")


def init_db(db_path: Path) -> None:
    schema_sql = (DB_DIR / "schema.sql").read_text()
    seed_sql = (DB_DIR / "seed.sql").read_text()

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(schema_sql)
        conn.executescript(seed_sql)
        ensure_pricing_columns(conn)
        ensure_event_schema(conn)
        conn.commit()
        ensure_canonical_only_cardmarket_scopes(conn)
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
