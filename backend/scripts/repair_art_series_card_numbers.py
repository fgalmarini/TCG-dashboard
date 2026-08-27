"""One-off repair for Magic LOTR Art Series card numbers.

The collection import originally matched Art Series cards by name but left
cards.card_number empty. Facundo provided the Cardmarket art-card numbers for the
cards he has; this script applies that audited mapping to local catalog rows.

Usage:
    python3 backend/scripts/repair_art_series_card_numbers.py --dry-run
    python3 backend/scripts/repair_art_series_card_numbers.py --apply
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import tempfile
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "db" / "tcg_dashboard.db"

ART_SERIES_NUMBERS = {
    "Fog on the Barrow-Downs": "2",
    "Gandalf the White": "3",
    "Goldberry, River-Daughter": "6",
    "The Watcher in the Water": "7",
    "Éomer of the Riddermark": "9",
    "Gimli, Counter of Kills": "10",
    "Generous Ent": "11",
    "Mirrormere Guardian": "12",
    "Bilbo, Retired Burglar": "14",
    "Legolas, Counter of Kills": "17",
    "Saruman of Many Colors": "20",
    "Sharkey, Tyrant of the Shire": "22",
    "Shelob, Child of Ungoliant": "23",
    "Théoden, King of Rohan": "25",
    "Tom Bombadil": "26",
    "Uglúk of the White Hand": "27",
    "Plains": "30",
    "Mountain": "31",
    "Elanor Gardner": "32",
    "Aragorn and Arwen, Wed": "33",
    "Bilbo's Ring": "37",
    "Faramir, Field Commander": "38",
    "Faramir, Steward of Gondor": "62",
    "Elrond, Lord of Rivendell": "40",
    "Witch-king of Angmar": "43",
    "Frodo Baggins": "47",
    "Galadriel of Lothlórien": "48",
    "Merry, Esquire of Rohan": "50",
    "Nazgûl": "53",
    "Pippin, Guard of the Citadel": "51",
    "Mines of Moria": "56",
    "Aragorn, King of Gondor": "57",
    "Gwaihir, Greatest of the Eagles": "59",
    "Call for Aid": "60",
    "Cavern-Hoard Dragon": "61",
    "Gríma, Saruman's Footman": "63",
    "Merry, Warden of Isengard": "65",
    "Samwise Gamgee": "19",
    "Sauron, the Dark Lord": "21",
    "Treebeard, Gracious Host": "67",
    "Asceticism": "72",
    "Realm Seekers": "74",
    "Ghost Quarter": "78",
    "Valley of Gorgoroth": "80",
    "Éowyn, Fearless Knight": "15",
}


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def integrity_check(conn: sqlite3.Connection) -> None:
    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        raise RuntimeError(f"PRAGMA integrity_check failed: {integrity}")
    fk_rows = conn.execute("PRAGMA foreign_key_check").fetchall()
    if fk_rows:
        raise RuntimeError(f"PRAGMA foreign_key_check failed: {fk_rows}")


def collection_art_series_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        """SELECT DISTINCT c.name
             FROM collection_items ci
             JOIN cards c ON c.id = ci.card_id
            WHERE c.name LIKE 'Art Series:%'"""
    ).fetchall()
    return {row["name"].removeprefix("Art Series: ") for row in rows}


def apply_numbers(db_path: Path, dry_run: bool) -> tuple[int, list[str], list[str]]:
    conn = connect(db_path)
    try:
        integrity_check(conn)
        collection_names = collection_art_series_names(conn)
        missing_for_collection = sorted(collection_names - set(ART_SERIES_NUMBERS))
        provided_not_in_collection = sorted(set(ART_SERIES_NUMBERS) - collection_names)

        updated = 0
        for card_name, card_number in ART_SERIES_NUMBERS.items():
            full_name = f"Art Series: {card_name}"
            rows = conn.execute(
                """SELECT c.id, c.card_number,
                          EXISTS(SELECT 1 FROM collection_items ci WHERE ci.card_id = c.id) AS in_collection
                     FROM cards c
                    WHERE c.name = ?""",
                (full_name,),
            ).fetchall()
            if not rows:
                print(f"sin filas en catalogo: {full_name}")
                continue
            target_ids = [row["id"] for row in rows if row["in_collection"]]
            if not target_ids:
                print(f"sin filas en coleccion cargada: {full_name}")
                continue
            stored_card_number = f"ART-{card_number}"
            print(
                f"{'DRY ' if dry_run else ''}set {full_name} -> card_number={card_number} "
                f"(stored={stored_card_number}; {len(target_ids)} fila(s) de coleccion, {len(rows)} de catalogo)"
            )
            if not dry_run:
                placeholders = ",".join("?" for _ in target_ids)
                cursor = conn.execute(
                    f"UPDATE cards SET card_number = ? WHERE id IN ({placeholders})",
                    (stored_card_number, *target_ids),
                )
                updated += cursor.rowcount

        if not dry_run:
            integrity_check(conn)
            conn.commit()
        return updated, missing_for_collection, provided_not_in_collection
    finally:
        conn.close()


def apply_via_local_copy() -> tuple[int, list[str], list[str]]:
    with tempfile.TemporaryDirectory(prefix="tcg-art-series-") as tmp:
        tmp_dir = Path(tmp)
        work_db = tmp_dir / "tcg_dashboard.db"
        shutil.copy2(DB_PATH, work_db)
        result = apply_numbers(work_db, dry_run=False)
        replacement = DB_PATH.with_suffix(".db.art-series-repaired")
        shutil.copy2(work_db, replacement)
        replacement.replace(DB_PATH)
        return result


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    updated, missing, extra = apply_numbers(DB_PATH, dry_run=True) if args.dry_run else apply_via_local_copy()
    print(f"Resumen: updated_rows={updated}")
    print(f"Faltantes en tu coleccion: {missing}")
    print(f"Provistos pero no cargados en coleccion: {extra}")


if __name__ == "__main__":
    main()
