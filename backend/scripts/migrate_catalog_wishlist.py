"""Safe, idempotent migration for the catalog and wishlist schema.

The production database may live on a FUSE/bridge mount.  This script never copies
files itself: run it against a local temporary copy, validate SQLite, then sync the
healthy copy back as described in AGENTS.md.

Usage:
    python3 backend/scripts/migrate_catalog_wishlist.py --db /path/to/db --dry-run
    python3 backend/scripts/migrate_catalog_wishlist.py --db /path/to/db --apply
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


CARDS_SQL = """
CREATE TABLE cards (
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
    finish TEXT CHECK (finish IS NULL OR finish IN ('nonfoil', 'foil', 'etched')),
    treatment TEXT,
    language_id INTEGER REFERENCES languages (id),
    scryfall_id TEXT,
    scryfall_oracle_id TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""

WISHLIST_SQL = """
CREATE TABLE wishlist_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id INTEGER NOT NULL REFERENCES cards (id),
    quantity_wanted INTEGER NOT NULL DEFAULT 1 CHECK (quantity_wanted > 0),
    priority TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'none')),
    max_price REAL,
    currency TEXT,
    notes TEXT,
    status TEXT NOT NULL DEFAULT 'wanted' CHECK (status IN ('wanted', 'acquired', 'removed')),
    acquired_at TEXT,
    removed_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    language_id INTEGER REFERENCES languages (id),
    condition TEXT CHECK (condition IS NULL OR condition IN ('NM', 'EX', 'GD', 'LP', 'PL', 'PO')),
    grade_min REAL,
    target_price REAL,
    CHECK (target_price IS NULL OR max_price IS NULL OR target_price <= max_price),
    CHECK (
        (status = 'wanted' AND acquired_at IS NULL AND removed_at IS NULL)
        OR (status = 'acquired' AND acquired_at IS NOT NULL AND removed_at IS NULL)
        OR (status = 'removed' AND acquired_at IS NULL AND removed_at IS NOT NULL)
    )
)
"""


@dataclass
class MigrationReport:
    cards_rebuilt: bool = False
    wishlist_migrated: bool = False
    cards: int = 0
    wishlist_items: int = 0
    legacy_null_wishlist_cards: int = 0
    wishlist_rebuilt: bool = False
    invalid_wishlist_prices: int = 0


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f'PRAGMA table_info("{table}")')}


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is not None


def table_sql(conn: sqlite3.Connection, table: str) -> str:
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return (row[0] or "").lower() if row else ""


def raw_scryfall_values(raw: str | None) -> tuple[str | None, str | None]:
    if not raw:
        return None, None
    try:
        data = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return None, None
    return data.get("id"), data.get("oracle_id")


def rebuild_cards(conn: sqlite3.Connection, report: MigrationReport, apply: bool) -> None:
    if not table_exists(conn, "cards"):
        return
    existing = columns(conn, "cards")
    required = {
        "set_code", "normalized_name", "rarity", "finish", "treatment",
        "language_id", "scryfall_id", "scryfall_oracle_id", "created_at", "updated_at",
    }
    needs_rebuild = not required.issubset(existing)
    if not needs_rebuild:
        report.cards = conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0]
        return
    report.cards_rebuilt = True
    report.cards = conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0]
    if not apply:
        return

    legacy = "cards__catalog_migration_legacy"
    if table_exists(conn, legacy):
        raise RuntimeError(f"temporary table already exists: {legacy}")

    conn.execute("PRAGMA legacy_alter_table = ON")
    conn.execute(f'ALTER TABLE "cards" RENAME TO "{legacy}"')
    conn.execute(CARDS_SQL)

    def value(column: str, fallback: str) -> str:
        return f'c."{column}"' if column in existing else fallback

    raw_expr = value("scryfall_raw", "NULL")
    rows = conn.execute(
        f"""SELECT c.id, c.game_id, c.expansion_id, c.card_number, c.name,
                   c.printing_variant, c.variant_label, c.cardmarket_id_metacard,
                   c.image_url, c.image_source, c.data_source, {raw_expr} AS scryfall_raw,
                   e.set_code, {value('normalized_name', 'NULL')} AS normalized_name,
                   {value('rarity', 'NULL')} AS rarity, {value('finish', 'NULL')} AS finish,
                   {value('treatment', 'NULL')} AS treatment,
                   {value('language_id', '1')} AS language_id,
                   {value('scryfall_id', 'NULL')} AS scryfall_id,
                   {value('scryfall_oracle_id', 'NULL')} AS scryfall_oracle_id,
                   {value('created_at', 'NULL')} AS created_at,
                   {value('updated_at', 'NULL')} AS updated_at
              FROM "{legacy}" c
              JOIN expansions e ON e.id = c.expansion_id
             ORDER BY c.id"""
    ).fetchall()
    for row in rows:
        sf_id, oracle_id = raw_scryfall_values(row[11])
        conn.execute(
            """INSERT INTO cards
               (id, game_id, expansion_id, card_number, name, printing_variant,
                variant_label, cardmarket_id_metacard, image_url, image_source,
                data_source, scryfall_raw, set_code, normalized_name, rarity, finish,
                treatment, language_id, scryfall_id, scryfall_oracle_id, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8],
                row[9], row[10], row[11], row[12], row[13], row[14], row[15], row[16],
                row[17] or 1, row[18] or sf_id, row[19] or oracle_id,
                row[20] or utc_now(), row[21] or utc_now(),
            ),
        )
    conn.execute(f'DROP TABLE "{legacy}"')


def rebuild_wishlist(conn: sqlite3.Connection, report: MigrationReport, apply: bool) -> None:
    existing = columns(conn, "wishlist_items")
    report.wishlist_items = conn.execute("SELECT COUNT(*) FROM wishlist_items").fetchone()[0]
    report.wishlist_rebuilt = True
    if "target_price" in existing and "max_price" in existing:
        report.invalid_wishlist_prices = conn.execute(
            "SELECT COUNT(*) FROM wishlist_items "
            "WHERE target_price IS NOT NULL AND max_price IS NOT NULL "
            "AND target_price > max_price"
        ).fetchone()[0]
    if report.invalid_wishlist_prices:
        raise RuntimeError(
            "wishlist contiene target_price mayor que max_price; resolver los datos "
            "antes de --apply"
        )
    if not apply:
        return

    legacy = "wishlist_items__planning_migration_legacy"
    if table_exists(conn, legacy):
        raise RuntimeError(f"temporary table already exists: {legacy}")
    conn.execute(f'ALTER TABLE "wishlist_items" RENAME TO "{legacy}"')
    conn.execute(WISHLIST_SQL)

    def value(column: str, fallback: str) -> str:
        return f'w."{column}"' if column in existing else fallback

    status_column = value("status", "'wanted'")
    status_value = f"LOWER({status_column})"
    updated_value = value("updated_at", "CURRENT_TIMESTAMP")

    conn.execute(
        f"""INSERT INTO wishlist_items
           (id, card_id, quantity_wanted, priority, max_price, currency, notes, status,
            acquired_at, removed_at, created_at, updated_at, language_id, condition,
            grade_min, target_price)
           SELECT w.id, w.card_id, {value('quantity_wanted', '1')},
                  CASE LOWER({value('priority', "'medium'")})
                       WHEN 'high' THEN 'high'
                       WHEN 'low' THEN 'low'
                       WHEN 'none' THEN 'none'
                       ELSE 'medium' END,
                  {value('max_price', 'NULL')}, {value('currency', 'NULL')},
                  {value('notes', 'NULL')},
                  CASE WHEN {status_value} IN ('acquired', 'removed') THEN {status_value} ELSE 'wanted' END,
                  CASE WHEN {status_value} = 'acquired'
                       THEN COALESCE({value('acquired_at', 'NULL')}, {updated_value}) ELSE NULL END,
                  CASE WHEN {status_value} = 'removed'
                       THEN COALESCE({value('removed_at', 'NULL')}, {updated_value}) ELSE NULL END,
                  {value('created_at', 'CURRENT_TIMESTAMP')},
                  {updated_value},
                  {value('language_id', 'NULL')}, {value('condition', 'NULL')},
                  {value('grade_min', 'NULL')}, {value('target_price', 'NULL')}
             FROM [{legacy}] w"""
    )
    conn.execute(f'DROP TABLE "{legacy}"')


def migrate_wishlist(conn: sqlite3.Connection, report: MigrationReport, apply: bool) -> None:
    if table_exists(conn, "wishlist_items"):
        required = {
            "acquired_at", "removed_at", "target_price", "max_price", "status",
        }
        sql = table_sql(conn, "wishlist_items")
        needs_rebuild = (
            not required.issubset(columns(conn, "wishlist_items"))
            or "'none'" not in sql
            or "target_price <= max_price" not in sql
            or "status = 'wanted'" not in sql
        )
        if needs_rebuild:
            rebuild_wishlist(conn, report, apply)
        else:
            report.wishlist_items = conn.execute("SELECT COUNT(*) FROM wishlist_items").fetchone()[0]
        return
    if not table_exists(conn, "want_list_items"):
        return

    legacy_columns = columns(conn, "want_list_items")
    report.wishlist_items = conn.execute("SELECT COUNT(*) FROM want_list_items").fetchone()[0]
    report.wishlist_migrated = True
    if "card_id" in legacy_columns:
        report.legacy_null_wishlist_cards = conn.execute(
            "SELECT COUNT(*) FROM want_list_items WHERE card_id IS NULL"
        ).fetchone()[0]
    if report.legacy_null_wishlist_cards:
        raise RuntimeError(
            "cannot migrate wishlist rows with NULL card_id; resolve them before --apply"
        )
    if not apply:
        return

    legacy = "want_list_items__wishlist_migration_legacy"
    conn.execute(f'ALTER TABLE want_list_items RENAME TO "{legacy}"')
    conn.execute(WISHLIST_SQL)
    conn.execute(
        f"""INSERT INTO wishlist_items
           (id, card_id, quantity_wanted, priority, max_price, currency, notes, status,
            acquired_at, removed_at, created_at, updated_at, language_id, condition,
            grade_min, target_price)
           SELECT id, card_id, 1,
                  CASE UPPER(priority) WHEN 'HIGH' THEN 'high'
                       WHEN 'LOW' THEN 'low' WHEN 'NONE' THEN 'none' ELSE 'medium' END,
                  max_price, NULL, notes, 'wanted', NULL, NULL, ?, ?, language_id,
                  condition, grade_min, target_price
             FROM [{legacy}]""",
        (utc_now(), utc_now()),
    )
    conn.execute(f'DROP TABLE "{legacy}"')


def ensure_indexes(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_cards_legacy_identity
            ON cards (expansion_id, card_number, printing_variant)
            WHERE finish IS NULL;
        CREATE UNIQUE INDEX IF NOT EXISTS idx_cards_catalog_identity
            ON cards (game_id, set_code, card_number, language_id, finish)
            WHERE set_code IS NOT NULL AND card_number IS NOT NULL
              AND language_id IS NOT NULL AND finish IS NOT NULL;
        CREATE UNIQUE INDEX IF NOT EXISTS idx_cards_scryfall_finish_identity
            ON cards (scryfall_id, language_id, finish)
            WHERE scryfall_id IS NOT NULL AND language_id IS NOT NULL AND finish IS NOT NULL;
        CREATE INDEX IF NOT EXISTS idx_cards_catalog_search
            ON cards (game_id, set_code, normalized_name);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_wishlist_active_card
            ON wishlist_items (card_id) WHERE status = 'wanted';
        CREATE INDEX IF NOT EXISTS idx_wishlist_status_updated
            ON wishlist_items (status, updated_at DESC, id DESC);
        """
    )


def run(db_path: Path, apply: bool) -> MigrationReport:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    report = MigrationReport()
    try:
        if apply:
            conn.execute("PRAGMA foreign_keys = OFF")
            conn.execute("BEGIN")
        rebuild_cards(conn, report, apply)
        migrate_wishlist(conn, report, apply)
        if apply:
            ensure_indexes(conn)
            conn.commit()
            conn.execute("PRAGMA foreign_keys = ON")
            if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise RuntimeError("PRAGMA integrity_check failed")
            if conn.execute("PRAGMA foreign_key_check").fetchone() is not None:
                raise RuntimeError("PRAGMA foreign_key_check failed")
        report.cards = conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0]
        if table_exists(conn, "wishlist_items"):
            report.wishlist_items = conn.execute("SELECT COUNT(*) FROM wishlist_items").fetchone()[0]
        return report
    except Exception:
        if apply:
            conn.rollback()
            conn.execute("PRAGMA foreign_keys = ON")
        raise
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.apply and args.dry_run:
        parser.error("use either --apply or --dry-run")
    report = run(args.db, apply=args.apply)
    print(f"Mode: {'apply' if args.apply else 'dry-run'}")
    print(f"Cards: {report.cards}")
    print(f"Cards rebuilt: {'yes' if report.cards_rebuilt else 'no'}")
    print(f"Wishlist migrated: {'yes' if report.wishlist_migrated else 'no'}")
    print(f"Wishlist rebuilt: {'yes' if report.wishlist_rebuilt else 'no'}")
    print(f"Invalid wishlist prices: {report.invalid_wishlist_prices}")
    print(f"Wishlist items: {report.wishlist_items}")


if __name__ == "__main__":
    main()
