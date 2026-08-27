"""Backfill and audit collection references to the canonical ``cards`` catalog.

Existing rows already use ``collection_items.card_id``.  The script only fills a
missing card_id when the available legacy mapping is unique; ambiguous/unmatched
rows are reported and left untouched.
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
from dataclasses import dataclass
from pathlib import Path
import unicodedata


DB_PATH = Path(__file__).resolve().parent.parent / "db" / "tcg_dashboard.db"


@dataclass
class BackfillReport:
    matched_exact: int = 0
    matched_by_collector_number: int = 0
    unmatched: int = 0
    ambiguous: int = 0

    def print_summary(self) -> None:
        print("Collection catalog backfill completed")
        print(f"Matched exact: {self.matched_exact}")
        print(f"Matched by collector number: {self.matched_by_collector_number}")
        print(f"Unmatched: {self.unmatched}")
        print(f"Ambiguous: {self.ambiguous}")


def normalize(value: str | None) -> str:
    if not value:
        return ""
    text = unicodedata.normalize("NFKD", value)
    return "".join(char for char in text if not unicodedata.combining(char)).casefold().strip()


def find_candidates(
    conn: sqlite3.Connection,
    game_code: str,
    set_code: str,
    collector_number: str,
    name: str,
) -> tuple[list[sqlite3.Row], str]:
    rows = conn.execute(
        """SELECT c.id, c.name, c.card_number, e.set_code
             FROM cards c JOIN expansions e ON e.id = c.expansion_id
             JOIN games g ON g.id = c.game_id
            WHERE g.code = ? AND lower(COALESCE(c.set_code, e.set_code)) = ?
              AND c.card_number = ? AND lower(c.name) = lower(?)
            ORDER BY c.id""",
        (game_code, set_code.casefold(), collector_number, name),
    ).fetchall()
    if rows:
        return rows, "exact"
    rows = conn.execute(
        """SELECT c.id, c.name, c.card_number, e.set_code
             FROM cards c JOIN expansions e ON e.id = c.expansion_id
             JOIN games g ON g.id = c.game_id
            WHERE g.code = ? AND lower(COALESCE(c.set_code, e.set_code)) = ?
              AND c.card_number = ?
            ORDER BY c.id""",
        (game_code, set_code.casefold(), collector_number),
    ).fetchall()
    return rows, "collector_number"


def run(db_path: Path, apply: bool, source: Path | None = None) -> BackfillReport:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    report = BackfillReport()
    try:
        source_collection_ids: set[int] = set()
        if source is not None:
            with source.open(newline="") as handle:
                source_rows = list(csv.DictReader(handle))
            for source_row in source_rows:
                candidates, method = find_candidates(
                    conn,
                    source_row.get("game", "magic"),
                    source_row.get("set_code", ""),
                    source_row.get("collector_number", ""),
                    source_row.get("name", ""),
                )
                collection_id = source_row.get("collection_item_id")
                if len(candidates) == 1 and collection_id:
                    source_collection_ids.add(int(collection_id))
                    if apply:
                        conn.execute(
                            "UPDATE collection_items SET card_id=? WHERE id=? AND card_id IS NULL",
                            (candidates[0]["id"], int(collection_id)),
                        )
                    if method == "exact":
                        report.matched_exact += 1
                    else:
                        report.matched_by_collector_number += 1
                elif len(candidates) > 1:
                    report.ambiguous += 1
                else:
                    report.unmatched += 1

        rows = conn.execute(
            """SELECT ci.id, ci.card_id, ci.cardmarket_product_id,
                      c.name, c.card_number, c.set_code
                 FROM collection_items ci
                 LEFT JOIN cards c ON c.id = ci.card_id
                ORDER BY ci.id"""
        ).fetchall()
        for row in rows:
            if row["id"] in source_collection_ids:
                continue
            if row["card_id"] is not None:
                if row["name"] and row["card_number"] and row["set_code"]:
                    report.matched_exact += 1
                else:
                    report.unmatched += 1
                continue
            if row["cardmarket_product_id"] is None:
                report.unmatched += 1
                continue
            candidates = conn.execute(
                """SELECT DISTINCT card_id FROM cardmarket_product_mappings
                    WHERE cardmarket_product_id=? AND status='mapped' AND card_id IS NOT NULL""",
                (row["cardmarket_product_id"],),
            ).fetchall()
            if len(candidates) == 1:
                if apply:
                    conn.execute(
                        "UPDATE collection_items SET card_id=? WHERE id=? AND card_id IS NULL",
                        (candidates[0][0], row["id"]),
                    )
                report.matched_exact += 1
            elif len(candidates) > 1:
                report.ambiguous += 1
            else:
                report.unmatched += 1
        if apply:
            conn.commit()
        return report
    except Exception:
        if apply:
            conn.rollback()
        raise
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--source", type=Path, help="optional CSV with legacy name/set/collector data")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.apply and args.dry_run:
        parser.error("use either --apply or --dry-run")
    report = run(args.db, args.apply, args.source)
    report.print_summary()


if __name__ == "__main__":
    main()
