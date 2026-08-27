"""Repair Magic collection rows that were imported as manual entries.

This is a one-off audited repair for the 2026-08 Magic collection issue: the CSV
loader could not resolve several Cardmarket Holiday Release / Commander Extras
URLs because those expansions were outside the original Magic LOTR scope.

Usage:
    python3 backend/scripts/repair_magic_manual_entries.py --dry-run
    python3 backend/scripts/repair_magic_manual_entries.py --apply
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import sqlite3
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from scryfall_backfill import BackfillReport, apply_scryfall_data, classify_variant, ensure_schema

DB_PATH = Path(__file__).resolve().parent.parent / "db" / "tcg_dashboard.db"
PRICE_HISTORY_DIR = Path(__file__).resolve().parent.parent.parent / "price-history" / "magic"
PRODUCTS_PATH = PRICE_HISTORY_DIR / "products_singles_1.json"
PRICE_GUIDE_PATH = PRICE_HISTORY_DIR / "price_guide_1.json"

MAGIC_GAME_ID = 3
MAGIC_CATEGORY_ID = 1
SCRYFALL_TIMEOUT_SECONDS = 10
SCRYFALL_COURTESY_DELAY_SECONDS = 0.12

# Audited from the Cardmarket URLs stored in collection_items.manual_entry_note.
# Product IDs are Cardmarket idProduct values from products_singles_1.json.
REPAIR_MAPPINGS: dict[int, int] = {
    33: 737031,   # Frodo Baggins (V.3) / Surge Foil
    36: 736847,   # Samwise the Stouthearted (V.3) / Surge Foil
    38: 737025,   # Meriadoc Brandybuck (V.3) / Surge Foil
    40: 737037,   # Pippin, Guard of the Citadel (V.3) / Surge Foil
    43: 737035,   # Legolas, Counter of Kills (V.3) / Surge Foil
    45: 737023,   # Gimli, Counter of Kills (V.3) / Surge Foil
    46: 737034,   # Gimli, Mournful Avenger (V.3) / Surge Foil
    48: 737033,   # Gandalf the Grey (V.3) / Surge Foil
    50: 736849,   # Gandalf, Friend of the Shire (V.3) / Surge Foil
    52: 737029,   # Elrond, Master of Healing (V.3) / Surge Foil
    53: 736844,   # Faramir, Field Commander (V.3) / Surge Foil
    56: 736850,   # Gollum, Patient Plotter (V.3) / Surge Foil
    62: 736524,   # Rohirrim Chargers (V.1)
    63: 717998,   # Sword of the Animist / Ring of Barahir (V.2) / Surge Foil
    64: 736555,   # Gandalf of the Secret Fire (V.1)
    69: 738108,   # Long List of the Ents (V.1)
    70: 737570,   # The Bath Song (V.1), Cardmarket product has no Scryfall lookup
    129: 738025,  # King of the Oathbreakers / Surge Foil
    130: 738021,  # Radagast the Brown (V.4) / Surge Foil
}

EXPANSION_FALLBACKS = {
    5387: ("Tales of Middle-earth Commander", "ltc"),
    5489: ("The Lord of the Rings: Tales of Middle-earth Holiday Release", "ltr"),
}

BASE_PRICE_FIELDS = ("low", "avg", "trend", "avg1", "avg7", "avg30")


@dataclass
class RepairReport:
    total: int = 0
    repaired: int = 0
    skipped: list[str] | None = None
    scryfall_missing: list[int] | None = None
    price_rows_inserted: int = 0

    def __post_init__(self) -> None:
        self.skipped = []
        self.scryfall_missing = []


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def load_json_inputs() -> tuple[dict[int, dict], dict[int, dict], str]:
    products_data = json.loads(PRODUCTS_PATH.read_text())
    price_data = json.loads(PRICE_GUIDE_PATH.read_text())
    products = {entry["idProduct"]: entry for entry in products_data["products"]}
    prices = {entry["idProduct"]: entry for entry in price_data["priceGuides"]}
    return products, prices, price_data["createdAt"]


def integrity_check(conn: sqlite3.Connection) -> None:
    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        raise RuntimeError(f"PRAGMA integrity_check failed: {integrity}")
    fk_rows = conn.execute("PRAGMA foreign_key_check").fetchall()
    if fk_rows:
        raise RuntimeError(f"PRAGMA foreign_key_check failed: {fk_rows}")


def fetch_scryfall_card(cardmarket_id_product: int) -> tuple[dict | None, str | None]:
    req = urllib.request.Request(
        f"https://api.scryfall.com/cards/cardmarket/{cardmarket_id_product}",
        headers={"User-Agent": "TCGDashboardLocalRepair/1.0", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=SCRYFALL_TIMEOUT_SECONDS) as response:
            return json.loads(response.read()), None
    except urllib.error.HTTPError as exc:
        return None, f"HTTP {exc.code}"
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
        return None, str(exc)


def upsert_product(conn: sqlite3.Connection, product: dict, last_seen_at: str) -> int:
    conn.execute(
        """INSERT INTO cardmarket_products
             (cardmarket_id_product, raw_name, cardmarket_id_category, cardmarket_id_expansion,
              cardmarket_id_metacard, date_added, last_seen_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(cardmarket_id_product) DO UPDATE SET
             raw_name = excluded.raw_name,
             cardmarket_id_category = excluded.cardmarket_id_category,
             cardmarket_id_expansion = excluded.cardmarket_id_expansion,
             cardmarket_id_metacard = excluded.cardmarket_id_metacard,
             last_seen_at = excluded.last_seen_at""",
        (
            product["idProduct"],
            product["name"],
            product.get("idCategory", MAGIC_CATEGORY_ID),
            product["idExpansion"],
            product.get("idMetacard"),
            product.get("dateAdded") or last_seen_at,
            last_seen_at,
        ),
    )
    return conn.execute(
        "SELECT id FROM cardmarket_products WHERE cardmarket_id_product = ?",
        (product["idProduct"],),
    ).fetchone()[0]


def get_or_create_expansion(conn: sqlite3.Connection, cardmarket_id_expansion: int) -> int:
    row = conn.execute(
        "SELECT id FROM expansions WHERE cardmarket_id_expansion = ?",
        (cardmarket_id_expansion,),
    ).fetchone()
    if row:
        return row[0]
    fallback_name, fallback_set_code = EXPANSION_FALLBACKS.get(cardmarket_id_expansion, (None, None))
    conn.execute(
        "INSERT INTO expansions (game_id, cardmarket_id_expansion, name, set_code) VALUES (?, ?, ?, ?)",
        (MAGIC_GAME_ID, cardmarket_id_expansion, fallback_name, fallback_set_code),
    )
    return conn.execute(
        "SELECT id FROM expansions WHERE cardmarket_id_expansion = ?",
        (cardmarket_id_expansion,),
    ).fetchone()[0]


def find_existing_card(
    conn: sqlite3.Connection, expansion_id: int, card_number: str | None, printing_variant: str, name: str
) -> int | None:
    if card_number is not None:
        row = conn.execute(
            """SELECT id FROM cards
                WHERE expansion_id = ? AND card_number = ? AND printing_variant = ?""",
            (expansion_id, card_number, printing_variant),
        ).fetchone()
        if row:
            return row[0]
    row = conn.execute(
        """SELECT id FROM cards
            WHERE expansion_id = ? AND name = ? AND card_number IS NULL AND printing_variant = ?""",
        (expansion_id, name, printing_variant),
    ).fetchone()
    return row[0] if row else None


def get_or_create_card(conn: sqlite3.Connection, expansion_id: int, product: dict, scryfall_data: dict | None) -> int:
    if scryfall_data is not None:
        name = scryfall_data.get("name") or product["name"]
        card_number = scryfall_data.get("collector_number")
        printing_variant, variant_label = classify_variant(scryfall_data)
        card_id = find_existing_card(conn, expansion_id, card_number, printing_variant, name)
        if card_id is None:
            conn.execute(
                """INSERT INTO cards
                     (game_id, expansion_id, card_number, name, printing_variant, variant_label)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (MAGIC_GAME_ID, expansion_id, card_number, name, printing_variant, variant_label),
            )
            card_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        apply_scryfall_data(conn, card_id, expansion_id, scryfall_data, BackfillReport())
        return card_id

    name = product["name"]
    variant_label = "Cardmarket audited product"
    card_id = find_existing_card(conn, expansion_id, None, "other", name)
    if card_id is None:
        conn.execute(
            """INSERT INTO cards
                 (game_id, expansion_id, card_number, name, printing_variant, variant_label,
                  data_source)
               VALUES (?, ?, NULL, ?, 'other', ?, 'manual')""",
            (MAGIC_GAME_ID, expansion_id, name, variant_label),
        )
        card_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    return card_id


def upsert_mapping(conn: sqlite3.Connection, local_product_id: int, card_id: int) -> None:
    conn.execute(
        """INSERT INTO cardmarket_product_mappings (cardmarket_product_id, card_id, status, notes)
           VALUES (?, ?, 'mapped', 'manual Magic repair from audited Cardmarket URL')
           ON CONFLICT(cardmarket_product_id) DO UPDATE SET
             card_id = excluded.card_id,
             status = excluded.status,
             notes = excluded.notes""",
        (local_product_id, card_id),
    )


def insert_price_snapshot(
    conn: sqlite3.Connection,
    local_product_id: int,
    price_entry: dict,
    observed_at: str,
    imported_at: str,
) -> int:
    values = {field: price_entry.get(field) for field in BASE_PRICE_FIELDS}
    for field in BASE_PRICE_FIELDS:
        values[f"{field}_alt"] = price_entry.get(f"{field}-foil")
    cursor = conn.execute(
        """INSERT INTO market_price_history
             (cardmarket_product_id, observed_at, low, avg, trend, avg1, avg7, avg30,
              low_alt, avg_alt, trend_alt, avg1_alt, avg7_alt, avg30_alt, imported_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(cardmarket_product_id, observed_at) DO NOTHING""",
        (
            local_product_id,
            observed_at,
            values["low"],
            values["avg"],
            values["trend"],
            values["avg1"],
            values["avg7"],
            values["avg30"],
            values["low_alt"],
            values["avg_alt"],
            values["trend_alt"],
            values["avg1_alt"],
            values["avg7_alt"],
            values["avg30_alt"],
            imported_at,
        ),
    )
    return cursor.rowcount


def update_collection_item(conn: sqlite3.Connection, item_id: int, card_id: int, local_product_id: int) -> None:
    row = conn.execute(
        "SELECT manual_entry_note, notes FROM collection_items WHERE id = ?",
        (item_id,),
    ).fetchone()
    original_note = row["manual_entry_note"] or ""
    notes = row["notes"] or ""
    repaired_note = f"Original manual-entry note: {original_note}"
    if repaired_note not in notes:
        notes = f"{notes}\n{repaired_note}".strip() if notes else repaired_note
    conn.execute(
        """UPDATE collection_items
              SET card_id = ?,
                  cardmarket_product_id = ?,
                  manual_entry = 0,
                  notes = ?
            WHERE id = ?""",
        (card_id, local_product_id, notes, item_id),
    )


def repair_database(db_path: Path, dry_run: bool) -> RepairReport:
    products, prices, observed_at = load_json_inputs()
    imported_at = dt.datetime.now(dt.timezone.utc).isoformat()
    report = RepairReport(total=len(REPAIR_MAPPINGS))
    conn = connect(db_path)
    try:
        ensure_schema(conn)
        integrity_check(conn)
        for item_id, id_product in REPAIR_MAPPINGS.items():
            row = conn.execute(
                "SELECT id, manual_entry FROM collection_items WHERE id = ?",
                (item_id,),
            ).fetchone()
            if row is None:
                report.skipped.append(f"collection_items.id={item_id} no existe")
                continue
            product = products.get(id_product)
            price = prices.get(id_product)
            if product is None:
                report.skipped.append(f"idProduct={id_product} no existe en products_singles_1.json")
                continue
            if price is None:
                report.skipped.append(f"idProduct={id_product} no existe en price_guide_1.json")
                continue

            data, error = fetch_scryfall_card(id_product)
            time.sleep(SCRYFALL_COURTESY_DELAY_SECONDS)
            if data is None:
                report.scryfall_missing.append(id_product)

            print(
                f"{'DRY ' if dry_run else ''}repair item {item_id}: "
                f"{product['name']} idProduct={id_product} "
                f"trend={price.get('trend')} scryfall={'ok' if data else error}"
            )

            if dry_run:
                report.repaired += 1
                continue

            local_product_id = upsert_product(conn, product, observed_at)
            expansion_id = get_or_create_expansion(conn, product["idExpansion"])
            card_id = get_or_create_card(conn, expansion_id, product, data)
            upsert_mapping(conn, local_product_id, card_id)
            report.price_rows_inserted += insert_price_snapshot(conn, local_product_id, price, observed_at, imported_at)
            update_collection_item(conn, item_id, card_id, local_product_id)
            report.repaired += 1

        if not dry_run:
            integrity_check(conn)
            conn.commit()
    finally:
        conn.close()
    return report


def apply_via_local_copy() -> RepairReport:
    with tempfile.TemporaryDirectory(prefix="tcg-repair-") as tmp:
        tmp_dir = Path(tmp)
        work_db = tmp_dir / "tcg_dashboard.db"
        backup_db = tmp_dir / "tcg_dashboard.before-repair.db"
        shutil.copy2(DB_PATH, work_db)
        shutil.copy2(DB_PATH, backup_db)
        report = repair_database(work_db, dry_run=False)
        replacement = DB_PATH.with_suffix(".db.repaired")
        shutil.copy2(work_db, replacement)
        replacement.replace(DB_PATH)
        print(f"Backup temporal durante la reparacion: {backup_db}")
        return report


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    report = repair_database(DB_PATH, dry_run=True) if args.dry_run else apply_via_local_copy()
    print(
        f"Resumen: total={report.total}, procesadas={report.repaired}, "
        f"price_rows_inserted={report.price_rows_inserted}, "
        f"scryfall_missing={report.scryfall_missing}, skipped={report.skipped}"
    )


if __name__ == "__main__":
    main()
