#!/usr/bin/env python3
"""Load the selected Pokémon 151 wishlist targets safely and idempotently.

Dry-run by default. Use --apply to write.

Rules:
- Pokémon / set `mew` only.
- Exact card name + collector number.
- Prefer English when language metadata exists.
- One exact active printing must resolve for every requested card.
- Existing wanted rows are updated; missing rows are inserted.
- Historical removed rows are restored to wanted.
- Historical acquired rows block the load so an owned card is not silently re-added.
- target_price = user supplied "Bueno".
- max_price = user supplied "Caro".
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

DEFAULT_DB = Path(__file__).resolve().parent.parent / "db" / "tcg_dashboard.db"

WISHLIST = [
    ("Alakazam ex", "201", 63.00, 82.00),
    ("Blastoise ex", "200", 131.00, 170.00),
    ("Bulbasaur", "166", 58.00, 75.00),
    ("Caterpie", "172", 20.00, 26.00),
    ("Charizard ex", "199", 281.00, 364.00),
    ("Charmander", "168", 81.00, 104.00),
    ("Charmeleon", "169", 56.00, 73.00),
    ("Dragonair", "181", 46.00, 60.00),
    ("Erika’s Invitation", "203", 18.00, 23.00),
    ("Giovanni’s Charisma", "204", 17.00, 22.00),
    ("Mr. Mime", "179", 13.50, 17.50),
    ("Nidoking", "174", 19.00, 25.00),
    ("Omanyte", "180", 15.00, 19.50),
    ("Pikachu", "173", 68.00, 88.00),
    ("Poliwhirl", "176", 41.00, 53.50),
    ("Psyduck", "175", 46.00, 60.00),
    ("Squirtle", "170", 71.00, 92.00),
    ("Venusaur ex", "198", 98.00, 127.00),
    ("Wartortle", "171", 56.00, 73.00),
    ("Zapdos ex", "202", 103.00, 134.00),
]


def connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def resolve_card(conn: sqlite3.Connection, name: str, number: str) -> sqlite3.Row:
    rows = conn.execute(
        """
        SELECT
            c.id,
            c.name,
            c.card_number,
            c.finish,
            c.treatment,
            c.language_id,
            l.code AS language,
            COALESCE(s.code, c.set_code, e.set_code) AS set_code,
            c.catalog_status
        FROM cards c
        JOIN games g ON g.id = c.game_id
        LEFT JOIN sets s ON s.id = c.set_id
        LEFT JOIN expansions e ON e.id = c.expansion_id
        LEFT JOIN languages l ON l.id = c.language_id
        WHERE g.code = 'pokemon'
          AND lower(COALESCE(s.code, c.set_code, e.set_code, '')) = 'mew'
          AND lower(c.name) = lower(?)
          AND lower(replace(COALESCE(c.card_number, ''), ' ', '')) IN (lower(?), lower(?))
          AND c.catalog_status = 'active'
        ORDER BY
            CASE WHEN lower(COALESCE(l.code, '')) IN ('en', 'eng') THEN 0 ELSE 1 END,
            c.id
        """,
        (name, number, f"{number}/165"),
    ).fetchall()

    if not rows:
        raise RuntimeError(f"No active Pokémon 151 printing found for {name} {number}/165")

    english = [r for r in rows if (r["language"] or "").lower() in {"en", "eng"}]
    candidates = english if english else rows

    if len(candidates) != 1:
        details = ", ".join(
            f"id={r['id']} number={r['card_number']} finish={r['finish']} treatment={r['treatment']} language={r['language']}"
            for r in candidates
        )
        raise RuntimeError(f"Ambiguous Pokémon 151 printing for {name} {number}/165: {details}")

    return candidates[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if not args.db.exists():
        raise SystemExit(f"Database not found: {args.db}")

    conn = connect(args.db)
    try:
        resolved: list[tuple[sqlite3.Row, float, float]] = []
        for name, number, target_price, max_price in WISHLIST:
            card = resolve_card(conn, name, number)
            resolved.append((card, target_price, max_price))

        print(f"Resolved: {len(resolved)}/{len(WISHLIST)}")
        for card, target_price, max_price in resolved:
            historical = conn.execute(
                "SELECT id, status FROM wishlist_items WHERE card_id=? AND status IN ('wanted','acquired','removed') ORDER BY id DESC LIMIT 1",
                (card["id"],),
            ).fetchone()
            status = historical["status"] if historical else "new"
            print(
                f"  {card['name']} {card['card_number']} | card_id={card['id']} | "
                f"target=EUR {target_price:.2f} | max=EUR {max_price:.2f} | wishlist={status}"
            )
            if historical and historical["status"] == "acquired":
                raise RuntimeError(
                    f"Historical wishlist row exists for {card['name']} (status=acquired, id={historical['id']}); "
                    "not re-adding an acquired card automatically."
                )

        if not args.apply:
            print("\nDRY-RUN: no database changes. Re-run with --apply to write.")
            return 0

        conn.execute("BEGIN IMMEDIATE")
        inserted = 0
        updated = 0
        restored = 0

        for card, target_price, max_price in resolved:
            wanted = conn.execute(
                "SELECT id FROM wishlist_items WHERE card_id=? AND status='wanted'",
                (card["id"],),
            ).fetchone()

            if wanted:
                conn.execute(
                    """
                    UPDATE wishlist_items
                    SET quantity_wanted=1,
                        priority='medium',
                        target_price=?,
                        max_price=?,
                        currency='EUR',
                        updated_at=CURRENT_TIMESTAMP
                    WHERE id=?
                    """,
                    (target_price, max_price, wanted["id"]),
                )
                updated += 1
                continue

            historical = conn.execute(
                "SELECT id, status FROM wishlist_items WHERE card_id=? AND status IN ('acquired','removed') ORDER BY id DESC LIMIT 1",
                (card["id"],),
            ).fetchone()

            if historical and historical["status"] == "removed":
                conn.execute(
                    """
                    UPDATE wishlist_items
                    SET quantity_wanted=1,
                        priority='medium',
                        target_price=?,
                        max_price=?,
                        currency='EUR',
                        status='wanted',
                        acquired_at=NULL,
                        removed_at=NULL,
                        updated_at=CURRENT_TIMESTAMP
                    WHERE id=?
                    """,
                    (target_price, max_price, historical["id"]),
                )
                restored += 1
                continue

            if historical and historical["status"] == "acquired":
                raise RuntimeError(
                    f"Historical wishlist row exists for {card['name']} (status=acquired, id={historical['id']}); "
                    "not re-adding an acquired card automatically."
                )

            conn.execute(
                """
                INSERT INTO wishlist_items
                    (card_id, language_id, quantity_wanted, priority, target_price, max_price,
                     currency, notes, status, acquired_at, removed_at, created_at, updated_at)
                VALUES (?, ?, 1, 'medium', ?, ?, 'EUR', NULL, 'wanted', NULL, NULL,
                        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                (card["id"], card["language_id"], target_price, max_price),
            )
            inserted += 1

        conn.commit()
        print(
            f"\nAPPLIED: inserted={inserted}, updated={updated}, restored={restored}, total={len(resolved)}"
        )
        return 0
    except Exception:
        if conn.in_transaction:
            conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
