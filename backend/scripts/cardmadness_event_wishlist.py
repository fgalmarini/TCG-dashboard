"""Plan and apply the curated Cardmadness identities to the existing Wishlist."""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = ROOT / "backend/db/tcg_dashboard.db"
DEFAULT_CATALOG = ROOT / "CARDMADNESS_HOB_HOC.csv"
EVENT_CODE = "cardmadness-2026"
EXPECTED_IDENTITIES = 116
EXPECTED_SURGE = 75
EXPECTED_TRADITIONAL = 41


@dataclass(frozen=True)
class WishlistTarget:
    card_id: int
    canonical_card_id: int
    set_code: str
    collector_number: str
    name: str
    treatment: str


@dataclass
class Resolution:
    targets: list[WishlistTarget]
    conflicts: list[str]
    missing: list[str]
    csv_rows: int
    surge_rows: int
    traditional_rows: int
    traditional_alternatives: int


def resolve_targets(conn: sqlite3.Connection, catalog_path: Path = DEFAULT_CATALOG) -> Resolution:
    """Resolve each CSV identity by exact set, collector, English and treatment."""
    with catalog_path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, delimiter=";")
        required = {"Set", "Base #", "Carta", "Surge #"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"Catalog is missing columns: {sorted(required - set(reader.fieldnames or []))}")
        rows = list(reader)

    language = conn.execute("SELECT id FROM languages WHERE lower(code)='en'").fetchone()
    if language is None:
        raise ValueError("English language is missing from the catalog database")
    language_id = int(language[0])

    targets: list[WishlistTarget] = []
    conflicts: list[str] = []
    missing: list[str] = []
    seen_csv_identities: set[tuple[str, str]] = set()
    seen_canonicals: set[int] = set()
    surge_rows = traditional_rows = alternatives = 0

    for row_number, row in enumerate(rows, start=2):
        set_code = (row.get("Set") or "").strip().lower()
        base_number = (row.get("Base #") or "").strip()
        surge_number = (row.get("Surge #") or "").strip()
        name = (row.get("Carta") or "").strip()
        identity = (set_code, base_number)
        label = f"{set_code.upper()} #{base_number} {name}".strip()

        if not set_code or not base_number or not name:
            conflicts.append(f"CSV row {row_number}: missing set, base collector number or name")
            continue
        if identity in seen_csv_identities:
            conflicts.append(f"{label}: duplicate logical identity in CSV")
            continue
        seen_csv_identities.add(identity)

        target_number = surge_number or base_number
        treatment = "surge_foil" if surge_number else "traditional_foil"
        matches = conn.execute(
            """SELECT c.id, c.canonical_card_id, c.set_id, c.card_number, c.name
                 FROM cards c JOIN games g ON g.id=c.game_id
                WHERE g.code='magic' AND lower(c.set_code)=? AND c.card_number=?
                  AND c.language_id=? AND c.treatment=? AND c.finish='foil'
                  AND c.catalog_status='active'""",
            (set_code, target_number, language_id, treatment),
        ).fetchall()
        if not matches:
            missing.append(f"{set_code.upper()} #{target_number} {treatment}")
            continue
        if len(matches) != 1:
            conflicts.append(f"{set_code.upper()} #{target_number} {treatment}: {len(matches)} exact printings")
            continue

        card = matches[0]
        if card[1] is None:
            conflicts.append(f"{label}: target printing has no canonical identity")
            continue
        canonical_id = int(card[1])
        if canonical_id in seen_canonicals:
            conflicts.append(f"{label}: canonical identity {canonical_id} is already selected")
            continue

        if treatment == "surge_foil":
            surge_rows += 1
            traditional_matches = conn.execute(
                """SELECT id FROM cards
                    WHERE canonical_card_id=? AND set_id=? AND language_id=?
                      AND lower(set_code)=? AND treatment='traditional_foil'
                      AND finish='foil' AND catalog_status='active'""",
                (canonical_id, card[2], language_id, set_code),
            ).fetchall()
            if len(traditional_matches) != 1:
                conflicts.append(
                    f"{label}: expected one exact Traditional Foil alternative, found {len(traditional_matches)}"
                )
                continue
            alternatives += 1
        else:
            traditional_rows += 1
            surge_matches = conn.execute(
                """SELECT id FROM cards
                    WHERE canonical_card_id=? AND set_id=? AND language_id=?
                      AND lower(set_code)=? AND treatment='surge_foil'
                      AND finish='foil' AND catalog_status='active'""",
                (canonical_id, card[2], language_id, set_code),
            ).fetchall()
            if surge_matches:
                conflicts.append(f"{label}: CSV says Traditional-only but a Surge Foil printing exists")
                continue

        seen_canonicals.add(canonical_id)
        targets.append(WishlistTarget(
            card_id=int(card[0]), canonical_card_id=canonical_id, set_code=set_code,
            collector_number=str(card[3]), name=str(card[4]), treatment=treatment,
        ))

    return Resolution(targets, conflicts, missing, len(rows), surge_rows, traditional_rows, alternatives)


def validate_resolution(resolution: Resolution) -> None:
    actual = (len(resolution.targets), resolution.surge_rows, resolution.traditional_rows)
    expected = (EXPECTED_IDENTITIES, EXPECTED_SURGE, EXPECTED_TRADITIONAL)
    if resolution.conflicts or resolution.missing or actual != expected or resolution.traditional_alternatives != EXPECTED_SURGE:
        raise ValueError(
            "Preflight gate failed: " + json.dumps({
                "expected": {"identities": expected[0], "surge": expected[1], "traditional_only": expected[2]},
                "actual": {"identities": actual[0], "surge": actual[1], "traditional_only": actual[2]},
                "traditional_alternatives": resolution.traditional_alternatives,
                "conflicts": resolution.conflicts, "missing": resolution.missing,
            }, ensure_ascii=False)
        )


def wishlist_snapshot(conn: sqlite3.Connection) -> list[tuple]:
    columns = [row[1] for row in conn.execute("PRAGMA table_info(wishlist_items)")]
    names = ", ".join(f'"{column}"' for column in columns)
    return [tuple(row) for row in conn.execute(f"SELECT {names} FROM wishlist_items ORDER BY id")]


def apply_targets(
    conn: sqlite3.Connection,
    targets: list[WishlistTarget],
    create_wishlist_item: Callable[[int], int],
    link_event_item: Callable[[str, int], None],
    event_code: str = EVENT_CODE,
) -> dict[str, int]:
    """Use supplied existing API operations, reusing exact items and links."""
    events = conn.execute("SELECT id FROM events WHERE code=?", (event_code,)).fetchall()
    if len(events) != 1:
        raise ValueError(f"Expected exactly one {event_code} event, found {len(events)}")
    event_id = int(events[0][0])
    created = reused = linked = already_linked = 0
    item_ids: set[int] = set()

    for target in targets:
        rows = conn.execute(
            "SELECT id, status FROM wishlist_items WHERE card_id=? ORDER BY id", (target.card_id,)
        ).fetchall()
        if len(rows) > 1:
            raise ValueError(f"Printing {target.card_id} has {len(rows)} existing Wishlist rows")
        if rows:
            item_id = int(rows[0][0])
            reused += 1
        else:
            item_id = int(create_wishlist_item(target.card_id))
            created += 1
        if item_id in item_ids:
            raise ValueError(f"Wishlist item {item_id} was selected for multiple identities")
        item_ids.add(item_id)

        existing_link = conn.execute(
            "SELECT 1 FROM event_wishlist_items WHERE event_id=? AND wishlist_item_id=?",
            (event_id, item_id),
        ).fetchone()
        if existing_link:
            already_linked += 1
        else:
            link_event_item(event_code, item_id)
            linked += 1

    return {"created": created, "reused": reused, "linked": linked, "already_linked": already_linked}


def read_only_connection(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def summary(conn: sqlite3.Connection, resolution: Resolution) -> dict:
    event = conn.execute("SELECT id FROM events WHERE code=?", (EVENT_CODE,)).fetchall()
    event_id = int(event[0][0]) if len(event) == 1 else None
    statuses = dict(conn.execute("SELECT status, count(*) FROM wishlist_items GROUP BY status").fetchall())
    hob_hoc = conn.execute(
        """SELECT count(*) FROM wishlist_items wi JOIN cards c ON c.id=wi.card_id
             WHERE lower(c.set_code) IN ('hob','hoc')"""
    ).fetchone()[0]
    associations = conn.execute(
        "SELECT count(*) FROM event_wishlist_items WHERE event_id=?", (event_id,)
    ).fetchone()[0] if event_id is not None else None
    duplicates = conn.execute(
        """SELECT count(*) FROM (
             SELECT event_id, wishlist_item_id FROM event_wishlist_items
              WHERE event_id=? GROUP BY event_id, wishlist_item_id HAVING count(*)>1
           )""", (event_id,),
    ).fetchone()[0] if event_id is not None else None
    return {
        "wishlist_total": conn.execute("SELECT count(*) FROM wishlist_items").fetchone()[0],
        "wanted": statuses.get("wanted", 0), "acquired": statuses.get("acquired", 0),
        "removed": statuses.get("removed", 0), "hob_hoc_wishlist": hob_hoc,
        "event_count": len(event), "event_associations": associations,
        "duplicate_associations": duplicates,
        "resolved_surge": resolution.surge_rows, "resolved_traditional_only": resolution.traditional_rows,
        "resolved_total": len(resolution.targets), "traditional_alternatives": resolution.traditional_alternatives,
        "conflicts": len(resolution.conflicts), "missing": len(resolution.missing),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--apply", action="store_true", help="Apply to a validated local temporary DB copy")
    args = parser.parse_args()
    if args.apply and args.db.resolve() == DEFAULT_DB.resolve():
        parser.error("Refusing to write the project DB directly; use a local temporary DB copy and sync only after validation")
    if not args.db.is_file():
        parser.error(f"Database does not exist: {args.db}")

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        resolution = resolve_targets(conn, args.catalog)
        report = summary(conn, resolution)
        print("Preflight:", json.dumps(report, ensure_ascii=False, sort_keys=True))
        if resolution.conflicts or resolution.missing:
            print("Conflicts:", json.dumps(resolution.conflicts, ensure_ascii=False))
            print("Missing:", json.dumps(resolution.missing, ensure_ascii=False))
        validate_resolution(resolution)
        if not args.apply:
            print("Result: PREFLIGHT PASS (read-only)")
            return 0

        sys.path.insert(0, str(ROOT))
        from backend.api.routers.events import EventWishlistLinkIn, add_event_wishlist_item
        from backend.api.routers.wishlist import create_wishlist_item as create_via_api
        from backend.api.schemas import WishlistCreateIn

        before = wishlist_snapshot(conn)
        def create(card_id: int) -> int:
            return int(create_via_api(WishlistCreateIn(card_id=card_id), conn).id)
        def link(code: str, item_id: int) -> None:
            add_event_wishlist_item(code, EventWishlistLinkIn(wishlist_item_id=item_id), conn)

        applied = apply_targets(conn, resolution.targets, create, link)
        after = wishlist_snapshot(conn)
        after_by_id = {row[0]: row for row in after}
        if any(after_by_id.get(row[0]) != row for row in before):
            raise RuntimeError("A pre-existing Wishlist row changed during apply")

        target_ids = [target.card_id for target in resolution.targets]
        target_items = conn.execute(
            f"SELECT id,card_id,status FROM wishlist_items WHERE card_id IN ({','.join('?' for _ in target_ids)})",
            target_ids,
        ).fetchall()
        if len(target_items) != EXPECTED_IDENTITIES or len({row[1] for row in target_items}) != EXPECTED_IDENTITIES:
            raise RuntimeError("Post-apply target printing count is not exactly 116")
        if any(row[2] != "wanted" for row in target_items):
            raise RuntimeError("A Cardmadness target Wishlist item is not wanted")
        final = summary(conn, resolution)
        if final["event_associations"] != EXPECTED_IDENTITIES or final["duplicate_associations"] != 0:
            raise RuntimeError("Post-apply event associations do not equal 116 unique links")
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_keys = conn.execute("PRAGMA foreign_key_check").fetchall()
        if integrity != "ok" or foreign_keys:
            raise RuntimeError(f"SQLite check failed: integrity={integrity}, foreign_keys={len(foreign_keys)}")
        print("Apply:", json.dumps(applied, sort_keys=True))
        print("Post-apply:", json.dumps(final, ensure_ascii=False, sort_keys=True))
        print("DB checks:", json.dumps({"integrity_check": integrity, "foreign_key_rows": len(foreign_keys)}))
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
