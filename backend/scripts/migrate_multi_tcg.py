"""Additive Multi-TCG schema migration.

The migration never rebuilds, renames, deletes, or rewrites an existing table. It is
safe to run repeatedly and is intentionally separate from the historical catalog /
wishlist migration, which had different compatibility requirements.
"""

from __future__ import annotations

import argparse
import sqlite3
from dataclasses import dataclass
from pathlib import Path


DB_DIR = Path(__file__).resolve().parent.parent / "db"
SCHEMA_SQL = (DB_DIR / "schema.sql").read_text(encoding="utf-8")
SEED_SQL = (DB_DIR / "seed.sql").read_text(encoding="utf-8")


ADDITIVE_COLUMNS: dict[str, tuple[str, ...]] = {
    "games": (
        "catalog_is_active INTEGER NOT NULL DEFAULT 0 CHECK (catalog_is_active IN (0, 1))",
    ),
    "expansions": (
        "set_id INTEGER REFERENCES sets (id)",
    ),
    "cards": (
        "canonical_card_id INTEGER REFERENCES canonical_cards (id)",
        "set_id INTEGER REFERENCES sets (id)",
        "release_kind TEXT NOT NULL DEFAULT 'unknown' CHECK (release_kind IN ('original', 'reprint', 'promo', 'special', 'unknown'))",
        "art_kind TEXT NOT NULL DEFAULT 'unknown' CHECK (art_kind IN ('base', 'alternate_art', 'parallel', 'manga', 'special', 'unknown'))",
        "source_variant TEXT",
        "catalog_status TEXT NOT NULL DEFAULT 'legacy' CHECK (catalog_status IN ('active', 'legacy', 'ambiguous', 'excluded'))",
        "catalog_source TEXT",
    ),
    "collection_items": (
        "match_status TEXT NOT NULL DEFAULT 'unmatched' CHECK (match_status IN ('exact', 'high_confidence', 'ambiguous', 'unmatched'))",
        "match_quality TEXT",
        "match_reason TEXT",
        "finish TEXT",
        "treatment TEXT",
    ),
}


@dataclass
class MigrationReport:
    columns_added: int = 0
    magic_canonical_cards: int = 0
    magic_printings_linked: int = 0


def column_names(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def add_missing_columns(conn: sqlite3.Connection) -> int:
    added = 0
    for table, definitions in ADDITIVE_COLUMNS.items():
        existing = column_names(conn, table)
        for definition in definitions:
            name = definition.split()[0]
            if name in existing:
                continue
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {definition}")
            existing.add(name)
            added += 1
    return added


def backfill_magic(conn: sqlite3.Connection) -> tuple[int, int]:
    game_id = conn.execute("SELECT id FROM games WHERE code='magic'").fetchone()[0]
    for row in conn.execute(
        """SELECT lower(COALESCE(c.set_code, e.set_code)) AS code,
                  MAX(COALESCE(e.name, upper(COALESCE(c.set_code, e.set_code)))) AS name
             FROM cards c
             JOIN expansions e ON e.id=c.expansion_id
            WHERE c.game_id=? AND COALESCE(c.set_code, e.set_code) IS NOT NULL
            GROUP BY lower(COALESCE(c.set_code, e.set_code))""",
        (game_id,),
    ):
        conn.execute(
            """INSERT INTO sets (game_id, code, name, release_status)
               VALUES (?, ?, ?, 'released')
               ON CONFLICT(game_id, code) DO UPDATE SET
                   name=excluded.name, release_status='released', updated_at=CURRENT_TIMESTAMP""",
            (game_id, row[0], row[1] or row[0].upper()),
        )

    conn.execute(
        """UPDATE expansions
              SET set_id=(SELECT s.id FROM sets s
                           WHERE s.game_id=expansions.game_id
                             AND lower(s.code)=lower(expansions.set_code))
            WHERE game_id=? AND set_code IS NOT NULL""",
        (game_id,),
    )

    oracle_rows = conn.execute(
        """SELECT scryfall_oracle_id, MIN(name), MIN(normalized_name)
             FROM cards
            WHERE game_id=? AND scryfall_oracle_id IS NOT NULL
            GROUP BY scryfall_oracle_id""",
        (game_id,),
    ).fetchall()
    for oracle_id, name, normalized_name in oracle_rows:
        conn.execute(
            """INSERT INTO canonical_cards
                   (game_id, identity_key, name, normalized_name)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(game_id, identity_key) DO UPDATE SET
                   name=excluded.name,
                   normalized_name=COALESCE(excluded.normalized_name, canonical_cards.normalized_name),
                   updated_at=CURRENT_TIMESTAMP""",
            (game_id, f"scryfall_oracle:{oracle_id}", name, normalized_name),
        )
        canonical_id = conn.execute(
            "SELECT id FROM canonical_cards WHERE game_id=? AND identity_key=?",
            (game_id, f"scryfall_oracle:{oracle_id}"),
        ).fetchone()[0]
        conn.execute(
            """INSERT INTO card_external_ids (canonical_card_id, source, external_id)
               VALUES (?, 'scryfall_oracle', ?)
               ON CONFLICT(source, external_id) DO NOTHING""",
            (canonical_id, oracle_id),
        )

    conn.execute(
        """UPDATE cards
              SET canonical_card_id=(
                      SELECT cc.id FROM canonical_cards cc
                       WHERE cc.game_id=cards.game_id
                         AND cc.identity_key='scryfall_oracle:' || cards.scryfall_oracle_id
                  ),
                  set_id=(SELECT s.id FROM sets s
                           WHERE s.game_id=cards.game_id
                             AND lower(s.code)=lower(cards.set_code)),
                  release_kind='original',
                  art_kind=CASE
                      WHEN lower(COALESCE(treatment,'')) LIKE '%borderless%'
                        OR lower(COALESCE(treatment,'')) LIKE '%showcase%'
                        OR lower(COALESCE(treatment,'')) LIKE '%extended%' THEN 'alternate_art'
                      ELSE 'base'
                  END,
                  source_variant=COALESCE(scryfall_id,'legacy') || ':' || COALESCE(finish,'unknown'),
                  catalog_status='active',
                  catalog_source='scryfall'
            WHERE game_id=? AND scryfall_oracle_id IS NOT NULL
              AND lower(set_code) IN ('ltr','ltc') AND finish IS NOT NULL""",
        (game_id,),
    )
    linked = conn.execute(
        "SELECT COUNT(*) FROM cards WHERE game_id=? AND canonical_card_id IS NOT NULL",
        (game_id,),
    ).fetchone()[0]
    return len(oracle_rows), linked


def run(db_path: Path, apply: bool = False) -> MigrationReport:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    report = MigrationReport()
    try:
        if not apply:
            for table, definitions in ADDITIVE_COLUMNS.items():
                existing = column_names(conn, table)
                report.columns_added += sum(definition.split()[0] not in existing for definition in definitions)
            return report

        report.columns_added = add_missing_columns(conn)
        conn.commit()
        conn.executescript(SCHEMA_SQL)
        conn.executescript(SEED_SQL)
        legacy_index_sql = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='index' AND name='idx_cards_legacy_identity'"
        ).fetchone()
        if legacy_index_sql and "catalog_status" not in (legacy_index_sql[0] or ""):
            conn.execute("DROP INDEX idx_cards_legacy_identity")
            conn.execute(
                """CREATE UNIQUE INDEX idx_cards_legacy_identity
                     ON cards (expansion_id, card_number, printing_variant)
                  WHERE finish IS NULL AND catalog_status='legacy'"""
            )
        commercial_index = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='index' AND name='idx_cards_one_piece_commercial_identity'"
        ).fetchone()
        if commercial_index and "CREATE UNIQUE INDEX" in (commercial_index[0] or "").upper():
            conn.execute("DROP INDEX idx_cards_one_piece_commercial_identity")
            conn.execute(
                """CREATE INDEX idx_cards_one_piece_commercial_identity
                     ON cards (canonical_card_id, set_id, language_id, art_kind, source_variant)
                  WHERE catalog_status='active' AND canonical_card_id IS NOT NULL
                    AND set_id IS NOT NULL AND language_id IS NOT NULL
                    AND source_variant IS NOT NULL"""
            )
        conn.execute("UPDATE games SET catalog_is_active=CASE WHEN code IN ('magic','one_piece') THEN 1 ELSE 0 END")
        report.magic_canonical_cards, report.magic_printings_linked = backfill_magic(conn)
        conn.commit()
        if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("PRAGMA integrity_check failed")
        if conn.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise RuntimeError("PRAGMA foreign_key_check failed")
        return report
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    report = run(args.db, apply=args.apply)
    print(f"Mode: {'apply' if args.apply else 'dry-run'}")
    print(f"Columns added: {report.columns_added}")
    print(f"Magic canonical cards: {report.magic_canonical_cards}")
    print(f"Magic printings linked: {report.magic_printings_linked}")


if __name__ == "__main__":
    main()
