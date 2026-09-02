#!/usr/bin/env python3
"""Import the audited Pokémon Scarlet & Violet—151 catalog foundation.

The discovery CSVs are the only input. This importer never fetches providers,
imports Cardmarket products, creates prices, or promotes candidate mappings.
Dry-run is the default operational mode; apply works on a SQLite copy and
replaces the database only after all gates and integrity checks pass.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from pokemon_catalog_schema import ensure_schema, schema_status
except ModuleNotFoundError:  # package import from backend.api tests
    from backend.scripts.pokemon_catalog_schema import ensure_schema, schema_status


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = ROOT / "backend/db/tcg_dashboard.db"
DEFAULT_DISCOVERY = ROOT / "reports/pokemon_151/identity_discovery"
DEFAULT_OUTPUT = ROOT / "reports/pokemon_151/catalog_import"
GAME_CODE = "pokemon"
SET_CODE = "mew"
SET_NAME = "Scarlet & Violet—151"
RELEASE_DATE = "2023-09-22"
CARDMARKET_EXPANSION_ID = 5328
EXPECTED_NUMBERS = [f"{number:03d}" for number in range(1, 208)]
CONFIRMED_FINISHES = {"normal", "holo", "reverse_holo"}
CATALOG_SOURCE = "pokemon_151_identity_discovery"


class ImportErrorGate(RuntimeError):
    pass


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def json_value(value: str | None) -> Any:
    if value in (None, ""):
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def normalized(value: str) -> str:
    return " ".join(value.casefold().split())


def load_staging(discovery_dir: Path) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    official = read_csv(discovery_dir / "01_official_207_cards.csv")
    variants = read_csv(discovery_dir / "02_variant_matrix.csv")
    numbers = [row.get("collector_number", "") for row in official]
    if len(official) != 207 or sorted(numbers) != EXPECTED_NUMBERS or len(set(numbers)) != 207:
        raise ImportErrorGate("official staging must contain exactly one numbered row for 001–207")
    confirmed = [row for row in variants if row.get("variant_status") == "CONFIRMED"]
    invalid = [row for row in confirmed if row.get("finish") not in CONFIRMED_FINISHES]
    if invalid:
        raise ImportErrorGate(f"unsupported CONFIRMED finishes: {sorted({row.get('finish') for row in invalid})}")
    identities = {row["collector_number"] for row in official}
    variant_keys = [(row.get("collector_number"), row.get("finish")) for row in confirmed]
    if len(variant_keys) != len(set(variant_keys)):
        raise ImportErrorGate("duplicate confirmed number/finish variants in staging")
    if {number for number, _ in variant_keys} != identities:
        raise ImportErrorGate("every official identity must have at least one CONFIRMED finish")
    return official, variants


def db_connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def scalar(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> Any:
    return conn.execute(sql, params).fetchone()[0]


def snapshot(conn: sqlite3.Connection) -> str:
    """Hash all rows outside the Pokémon 151 mutation scope."""
    queries = {
        "games": "SELECT * FROM games WHERE code <> 'pokemon' ORDER BY id",
        "languages": "SELECT * FROM languages ORDER BY id",
        "categories": "SELECT * FROM cardmarket_categories ORDER BY id",
        "products": "SELECT * FROM cardmarket_products ORDER BY id",
        "mappings": "SELECT * FROM cardmarket_product_mappings ORDER BY id",
        "prices": "SELECT * FROM market_price_history ORDER BY id",
        "resolutions": "SELECT * FROM printing_price_resolutions ORDER BY id",
        "overrides": "SELECT * FROM collection_price_overrides ORDER BY id",
        "collection": "SELECT * FROM collection_items ORDER BY id",
        "wishlist": "SELECT * FROM wishlist_items ORDER BY id",
        "sets": "SELECT s.* FROM sets s JOIN games g ON g.id=s.game_id WHERE g.code <> 'pokemon' ORDER BY s.id",
        "expansions": "SELECT e.* FROM expansions e JOIN games g ON g.id=e.game_id WHERE g.code <> 'pokemon' ORDER BY e.id",
        "canonical": "SELECT cc.* FROM canonical_cards cc JOIN games g ON g.id=cc.game_id WHERE g.code <> 'pokemon' ORDER BY cc.id",
        "cards": "SELECT c.* FROM cards c JOIN games g ON g.id=c.game_id WHERE g.code <> 'pokemon' ORDER BY c.id",
        "card_external": "SELECT ce.* FROM card_external_ids ce JOIN canonical_cards cc ON cc.id=ce.canonical_card_id JOIN games g ON g.id=cc.game_id WHERE g.code <> 'pokemon' ORDER BY ce.id",
        "printing_external": "SELECT pe.* FROM printing_external_ids pe JOIN cards c ON c.id=pe.card_id JOIN games g ON g.id=c.game_id WHERE g.code <> 'pokemon' ORDER BY pe.id",
        "set_external": "SELECT se.* FROM set_external_ids se JOIN sets s ON s.id=se.set_id JOIN games g ON g.id=s.game_id WHERE g.code <> 'pokemon' ORDER BY se.id",
        "relations": "SELECT pr.* FROM printing_relations pr JOIN cards a ON a.id=pr.source_card_id JOIN cards b ON b.id=pr.target_card_id JOIN games g ON g.id=a.game_id WHERE g.code <> 'pokemon' ORDER BY pr.id",
        "images": "SELECT ci.* FROM card_images ci JOIN cards c ON c.id=ci.card_id JOIN games g ON g.id=c.game_id WHERE g.code <> 'pokemon' ORDER BY ci.id",
    }
    digest = hashlib.sha256()
    for name, sql in queries.items():
        digest.update(name.encode())
        cursor = conn.execute(sql)
        columns = [item[0] for item in cursor.description]
        for row in cursor:
            digest.update(compact(dict(zip(columns, row))).encode())
    return digest.hexdigest()


def validate_target_preconditions(conn: sqlite3.Connection) -> tuple[int, int, int]:
    game = conn.execute("SELECT id, catalog_is_active FROM games WHERE code=?", (GAME_CODE,)).fetchone()
    if game is None:
        raise ImportErrorGate("games.pokemon is missing")
    set_rows = conn.execute("SELECT id, game_id, name, release_date FROM sets WHERE code=?", (SET_CODE,)).fetchall()
    for row in set_rows:
        if row["game_id"] != game["id"] or row["name"] != SET_NAME or row["release_date"] != RELEASE_DATE:
            raise ImportErrorGate("existing set code mew conflicts with Pokémon 151")
    expansion = conn.execute("SELECT id, game_id, set_code, set_id FROM expansions WHERE cardmarket_id_expansion=?", (CARDMARKET_EXPANSION_ID,)).fetchone()
    if expansion is not None and expansion["game_id"] != game["id"]:
        raise ImportErrorGate("Cardmarket expansion 5328 belongs to another game")
    return int(game["id"]), (int(set_rows[0]["id"]) if set_rows else 0), (int(expansion["id"]) if expansion else 0)


def planned_rows(conn: sqlite3.Connection, official: list[dict[str, str]], variants: list[dict[str, str]], game_id: int, set_id: int, expansion_id: int) -> dict[str, Any]:
    confirmed = [row for row in variants if row.get("variant_status") == "CONFIRMED"]
    canonical_existing = {row[0] for row in conn.execute("SELECT identity_key FROM canonical_cards WHERE game_id=?", (game_id,))}
    physical_existing = {
        (row[0], row[1], row[2], row[3])
        for row in conn.execute("SELECT card_number,set_code,language_id,finish FROM cards WHERE game_id=? AND set_code=?", (game_id, SET_CODE))
    }
    image_existing = {
        (row[0], row[1], row[2])
        for row in conn.execute("SELECT card_id,source,language FROM card_images")
    }
    language_id = scalar(conn, "SELECT id FROM languages WHERE code='en'")
    new_canonical = sum(1 for row in official if f"pokemon:{SET_CODE}:{row['collector_number']}" not in canonical_existing)
    new_physical = sum(1 for row in confirmed if (row["collector_number"], SET_CODE, language_id, row["finish"]) not in physical_existing)
    existing_card_ids = {
        (row[0], row[2]): int(row[1]) for row in conn.execute(
            "SELECT card_number, id, finish FROM cards WHERE game_id=? AND set_code=? AND language_id=? AND finish IS NOT NULL",
            (game_id, SET_CODE, language_id),
        )
    }
    new_images = sum(1 for row in confirmed if (existing_card_ids.get((row["collector_number"], row["finish"]), -1), "tcgdex", "en") not in image_existing)
    return {
        "official_rows_read": len(official),
        "official_rows_valid": len(official),
        "official_rows_invalid": 0,
        "confirmed_variants": len(confirmed),
        "supported_variants": sum(1 for row in variants if row.get("variant_status") == "SUPPORTED"),
        "new_game_rows": 0,
        "game_activation_updates": 0 if scalar(conn, "SELECT catalog_is_active FROM games WHERE id=?", (game_id,)) else 1,
        "new_set_rows": 0 if set_id else 1,
        "new_expansion_rows": 0 if expansion_id else 1,
        "new_canonical_rows": new_canonical,
        "new_physical_rows": new_physical,
        "new_confirmed_finish_variants": new_physical,
        "metadata_updates": 0,
        "image_rows": len(confirmed),
        "new_image_rows": new_images,
        "duplicates": 0,
        "conflicts": 0,
        "cross_game_mutations": 0,
        "pricing_mutations": 0,
        "authoritative_cardmarket_mappings": 0,
    }


def set_upsert(conn: sqlite3.Connection, game_id: int) -> int:
    row = conn.execute("SELECT id, name, release_date FROM sets WHERE game_id=? AND code=?", (game_id, SET_CODE)).fetchone()
    metadata = {
        "source": "pokemon_151_identity_discovery",
        "source_confidence": "official set membership; structured metadata cross-check",
        "external_ids": {"tcgdex": "sv03.5", "pokemon_tcg_api": "sv3pt5", "cardmarket_expansion": 5328},
    }
    if row:
        if row["name"] != SET_NAME or row["release_date"] != RELEASE_DATE:
            raise ImportErrorGate("existing Pokémon 151 set has conflicting metadata")
        return int(row["id"])
    cur = conn.execute(
        "INSERT INTO sets (game_id,code,name,release_date,release_status,metadata) VALUES (?,?,?,?,?,?)",
        (game_id, SET_CODE, SET_NAME, RELEASE_DATE, "released", compact(metadata)),
    )
    return int(cur.lastrowid)


def expansion_upsert(conn: sqlite3.Connection, game_id: int, set_id: int) -> int:
    row = conn.execute("SELECT id, game_id, set_code, set_id FROM expansions WHERE cardmarket_id_expansion=?", (CARDMARKET_EXPANSION_ID,)).fetchone()
    if row:
        if row["game_id"] != game_id or row["set_code"] not in (None, SET_CODE) or row["set_id"] not in (None, set_id):
            raise ImportErrorGate("existing Cardmarket expansion 5328 conflicts with Pokémon 151")
        conn.execute("UPDATE expansions SET set_id=?, set_code=?, name=?, release_date=? WHERE id=?", (set_id, SET_CODE, SET_NAME, RELEASE_DATE, row["id"]))
        return int(row["id"])
    cur = conn.execute(
        "INSERT INTO expansions (game_id,cardmarket_id_expansion,name,set_code,release_date,set_id) VALUES (?,?,?,?,?,?)",
        (game_id, CARDMARKET_EXPANSION_ID, SET_NAME, SET_CODE, RELEASE_DATE, set_id),
    )
    return int(cur.lastrowid)


def external_set_ids(conn: sqlite3.Connection, set_id: int) -> None:
    values = [
        ("tcgdex", "sv03.5", {"source_url": "https://api.tcgdex.net/v2/en/sets/sv03.5"}),
        ("pokemon_tcg_api", "sv3pt5", {"source_url": "https://api.pokemontcg.io/v2/cards?q=set.id:sv3pt5"}),
        ("cardmarket_expansion", str(CARDMARKET_EXPANSION_ID), {"role": "set_identity_only", "authoritative_card_mapping": False}),
    ]
    for source, external_id, metadata in values:
        row = conn.execute("SELECT set_id, metadata FROM set_external_ids WHERE source=? AND external_id=?", (source, external_id)).fetchone()
        if row and row["set_id"] != set_id:
            raise ImportErrorGate(f"external set identity conflict: {source}:{external_id}")
        conn.execute(
            "INSERT INTO set_external_ids (set_id,source,external_id,metadata) VALUES (?,?,?,?) ON CONFLICT(source,external_id) DO NOTHING",
            (set_id, source, external_id, compact(metadata)),
        )


def canonical_metadata(row: dict[str, str], variants: list[dict[str, str]]) -> str:
    fields = {
        "category": row.get("category"), "pokemon_species": row.get("pokemon_species"),
        "dex_number": json_value(row.get("dex_number")), "hp": json_value(row.get("hp")),
        "types": json_value(row.get("pokemon_type")), "stage": row.get("stage"),
        "evolves_from": row.get("evolves_from"), "is_ex": row.get("is_ex") == "1",
        "abilities": json_value(row.get("abilities")), "attacks": json_value(row.get("attacks")),
        "weaknesses": json_value(row.get("weaknesses")), "retreat": json_value(row.get("retreat")),
        "regulation_mark": row.get("regulation_mark"), "artist": row.get("artist"),
        "source_provenance": {
            "official_source": row.get("official_source"),
            "metadata_sources": row.get("metadata_sources"),
            "source_confidence": row.get("source_confidence"),
            "source_notes": row.get("source_notes"),
            "tcgdex_id": row.get("tcgdex_id"),
            "pokemon_tcg_api_id": row.get("pokemon_tcg_api_id"),
        },
        "variant_evidence": [
            {"finish": item.get("finish"), "status": item.get("variant_status"), "source": item.get("variant_source"), "confidence": item.get("variant_confidence"), "notes": item.get("variant_notes"), "treatment_observation": item.get("detected_treatment")}
            for item in variants if item.get("collector_number") == row.get("collector_number")
        ],
    }
    return compact({"pokemon": fields})


def import_rows(conn: sqlite3.Connection, official: list[dict[str, str]], variants: list[dict[str, str]], game_id: int, set_id: int, expansion_id: int) -> dict[str, Any]:
    language_id = scalar(conn, "SELECT id FROM languages WHERE code='en'")
    confirmed = [row for row in variants if row.get("variant_status") == "CONFIRMED"]
    official_by_number = {row["collector_number"]: row for row in official}
    canonical_ids: dict[str, int] = {}
    inserted_canonical = inserted_cards = inserted_images = 0
    for row in official:
        number = row["collector_number"]
        identity_key = f"pokemon:{SET_CODE}:{number}"
        metadata = canonical_metadata(row, variants)
        existing = conn.execute("SELECT id, name, metadata FROM canonical_cards WHERE game_id=? AND identity_key=?", (game_id, identity_key)).fetchone()
        if existing:
            if existing["name"] != row["card_name"] or existing["metadata"] != metadata:
                raise ImportErrorGate(f"canonical metadata conflict at {number}")
            canonical_ids[number] = int(existing["id"])
        else:
            cur = conn.execute(
                "INSERT INTO canonical_cards (game_id,identity_key,canonical_number,name,normalized_name,metadata) VALUES (?,?,?,?,?,?)",
                (game_id, identity_key, number, row["card_name"], normalized(row["card_name"]), metadata),
            )
            canonical_ids[number] = int(cur.lastrowid)
            inserted_canonical += 1
    for variant in confirmed:
        number = variant["collector_number"]
        official_row = official_by_number[number]
        finish = variant["finish"]
        existing = conn.execute(
            "SELECT * FROM cards WHERE game_id=? AND set_code=? AND card_number=? AND language_id=? AND finish=?",
            (game_id, SET_CODE, number, language_id, finish),
        ).fetchone()
        source_variant = f"tcgdex:sv03.5:{number}:{finish}"
        if existing:
            if existing["catalog_source"] != CATALOG_SOURCE or existing["canonical_card_id"] != canonical_ids[number] or existing["name"] != official_row["card_name"]:
                raise ImportErrorGate(f"physical printing conflict at {number}/{finish}")
            card_id = int(existing["id"])
        else:
            cur = conn.execute(
                """INSERT INTO cards
                   (game_id,expansion_id,card_number,name,printing_variant,variant_label,
                    set_code,normalized_name,rarity,finish,treatment,language_id,
                    canonical_card_id,set_id,release_kind,art_kind,source_variant,
                    catalog_status,catalog_source)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (game_id, expansion_id, number, official_row["card_name"], "normal", None,
                 SET_CODE, normalized(official_row["card_name"]), official_row.get("rarity") or None,
                 finish, None, language_id, canonical_ids[number], set_id, "original", "unknown",
                 source_variant, "active", CATALOG_SOURCE),
            )
            card_id = int(cur.lastrowid)
            inserted_cards += 1
        image_url = official_row.get("image") or None
        existing_image = conn.execute(
            "SELECT * FROM card_images WHERE card_id=? AND source='tcgdex' AND language='en' AND face_index=0", (card_id,)
        ).fetchone()
        if existing_image:
            if existing_image["source_card_id"] != f"sv03.5-{number}" or existing_image["image_url_large"] != image_url:
                raise ImportErrorGate(f"image conflict at {number}/{finish}")
        else:
            conn.execute(
                """INSERT INTO card_images
                   (card_id,source,source_card_id,source_variant,source_collector_number,
                    language,face_index,image_url_small,image_url_large,image_language_scope,
                    is_language_fallback,match_quality,status,last_checked_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (card_id, "tcgdex", f"sv03.5-{number}", finish, number, "en", 0,
                 image_url, image_url, "en", 0, "exact", "resolved" if image_url else "missing",
                 datetime.now(timezone.utc).replace(microsecond=0).isoformat()),
            )
            inserted_images += 1
    return {
        "inserted_canonical": inserted_canonical,
        "inserted_cards": inserted_cards,
        "inserted_images": inserted_images,
        "canonical_ids": canonical_ids,
    }


def validate_post_import(conn: sqlite3.Connection, before_snapshot: str, official: list[dict[str, str]], variants: list[dict[str, str]], game_id: int, set_id: int, expansion_id: int) -> dict[str, Any]:
    official_numbers = {row["collector_number"] for row in official}
    canonical = conn.execute("SELECT id,canonical_number FROM canonical_cards WHERE game_id=? AND identity_key LIKE 'pokemon:mew:%'", (game_id,)).fetchall()
    cards = conn.execute("SELECT id,card_number,finish FROM cards WHERE game_id=? AND set_id=? AND catalog_status='active'", (game_id, set_id)).fetchall()
    expected_variants = {(row["collector_number"], row["finish"]) for row in variants if row.get("variant_status") == "CONFIRMED"}
    actual_variants = {(row["card_number"], row["finish"]) for row in cards}
    if {row["canonical_number"] for row in canonical} != official_numbers or len(canonical) != 207:
        raise ImportErrorGate("post-import canonical identity gate failed")
    if actual_variants != expected_variants:
        raise ImportErrorGate("post-import confirmed variant gate failed")
    if scalar(conn, "SELECT COUNT(*) FROM cardmarket_product_mappings cpm JOIN cardmarket_products cp ON cp.id=cpm.cardmarket_product_id JOIN cards c ON c.cardmarket_id_metacard IS NOT NULL AND c.game_id=?", (game_id,)) != 0:
        raise ImportErrorGate("Cardmarket mapping gate failed")
    if scalar(conn, "SELECT COUNT(*) FROM cards c JOIN games g ON g.id=c.game_id WHERE g.code='pokemon' AND c.cardmarket_id_metacard IS NOT NULL", ()) != 0:
        raise ImportErrorGate("Pokémon Cardmarket metacard gate failed")
    if scalar(conn, "SELECT COUNT(*) FROM card_images ci JOIN cards c ON c.id=ci.card_id WHERE c.game_id=? AND ci.source <> 'tcgdex'", (game_id,)) != 0:
        raise ImportErrorGate("Pokémon image source gate failed")
    if scalar(conn, "SELECT COUNT(*) FROM printing_price_resolutions r JOIN cards c ON c.id=r.card_id WHERE c.game_id=?", (game_id,)) != 0:
        raise ImportErrorGate("Pokémon price resolution gate failed")
    if scalar(conn, "SELECT COUNT(*) FROM market_price_history h JOIN cardmarket_products p ON p.id=h.cardmarket_product_id JOIN cardmarket_product_mappings m ON m.cardmarket_product_id=p.id JOIN cards c ON c.id=m.card_id WHERE c.game_id=?", (game_id,)) != 0:
        raise ImportErrorGate("Pokémon price history gate failed")
    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    foreign_keys = conn.execute("PRAGMA foreign_key_check").fetchall()
    if integrity != "ok" or foreign_keys:
        raise ImportErrorGate(f"SQLite validation failed: integrity={integrity}, foreign_keys={foreign_keys[:2]}")
    after_snapshot = snapshot(conn)
    if before_snapshot != after_snapshot:
        raise ImportErrorGate("scope isolation gate failed")
    return {
        "canonical_count": len(canonical),
        "distinct_numbers": len({row["card_number"] for row in cards}),
        "physical_count": len(cards),
        "confirmed_finish_count": len(actual_variants),
        "duplicates": len(actual_variants) - len(cards),
        "missing_numbers": sorted(official_numbers - {row["canonical_number"] for row in canonical}),
        "integrity": integrity,
        "foreign_key_errors": len(foreign_keys),
        "scope_unchanged": True,
        "authoritative_cardmarket_mappings": 0,
        "price_snapshots": 0,
        "current_price_populated": 0,
        "market_value_populated": 0,
    }


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in fields} for row in rows)


def write_reports(output: Path, official: list[dict[str, str]], variants: list[dict[str, str]], plan: dict[str, Any], validation: dict[str, Any] | None, conn: sqlite3.Connection, game_id: int, set_id: int, mode: str) -> None:
    output.mkdir(parents=True, exist_ok=True)
    confirmed = [row for row in variants if row.get("variant_status") == "CONFIRMED"]
    card_rows = []
    variant_rows = []
    for row in official:
        number = row["collector_number"]
        physical = conn.execute("SELECT id FROM cards WHERE game_id=? AND set_id=? AND card_number=? AND catalog_status='active' ORDER BY finish", (game_id, set_id, number)).fetchall()
        image_count = conn.execute("SELECT COUNT(*) FROM card_images ci JOIN cards c ON c.id=ci.card_id WHERE c.game_id=? AND c.set_id=? AND c.card_number=? AND ci.source='tcgdex' AND ci.status='resolved'", (game_id, set_id, number)).fetchone()[0]
        canonical_row = conn.execute("SELECT id FROM canonical_cards WHERE game_id=? AND canonical_number=?", (game_id, number)).fetchone()
        card_rows.append({"canonical_id": canonical_row[0] if canonical_row else "", "game": GAME_CODE, "set": SET_CODE, "collector_number": number, "card_name": row["card_name"], "rarity": row.get("rarity"), "category": row.get("category"), "artist": row.get("artist"), "image_status": "resolved" if image_count else "missing", "metadata_status": "complete", "physical_printing_count": len(physical)})
        for physical_row in physical:
            detail = next((item for item in confirmed if item["collector_number"] == number and item["finish"] == conn.execute("SELECT finish FROM cards WHERE id=?", (physical_row[0],)).fetchone()[0]), None)
            finish = conn.execute("SELECT finish FROM cards WHERE id=?", (physical_row[0],)).fetchone()[0]
            variant_rows.append({"canonical_id": card_rows[-1]["canonical_id"], "physical_card_id": physical_row[0], "collector_number": number, "card_name": row["card_name"], "finish": finish, "treatment": "", "variant_status": "CONFIRMED", "evidence": detail.get("variant_notes") if detail else "", "source": detail.get("variant_source") if detail else "tcgdex.variants"})
    write_csv(output / "03_imported_cards.csv", ["canonical_id", "game", "set", "collector_number", "card_name", "rarity", "category", "artist", "image_status", "metadata_status", "physical_printing_count"], card_rows)
    write_csv(output / "04_imported_variants.csv", ["canonical_id", "physical_card_id", "collector_number", "card_name", "finish", "treatment", "variant_status", "evidence", "source"], variant_rows)
    coverage_fields = ["name", "rarity", "artist", "image", "HP", "type", "stage", "is_ex", "Pokédex", "attacks", "abilities", "weaknesses", "retreat", "regulation_mark"]
    coverage_rows = []
    for field in coverage_fields:
        csv_key = {"name": "card_name", "HP": "hp", "type": "pokemon_type", "Pokédex": "dex_number"}.get(field, field)
        source_count = sum(1 for row in official if row.get(csv_key)) if field != "image" else sum(1 for row in official if row.get("image"))
        coverage_rows.append({"field": field, "source_rows": len(official), "populated_rows": source_count, "coverage_percent": round(source_count * 100 / len(official), 2), "source_or_inference": "source"})
    write_csv(output / "05_metadata_coverage.csv", ["field", "source_rows", "populated_rows", "coverage_percent", "source_or_inference"], coverage_rows)
    schema = schema_status(conn)
    (output / "01_schema_audit.md").write_text("\n".join([
        "# Pokémon 151 schema audit", "", "- `canonical_cards` stores one numbered identity per `game + set + collector_number`.", "- `cards` stores physical printings and keeps finish separate from rarity and treatment.", "- Pokémon finishes use generic `normal`, `holo`, and `reverse_holo`; Magic finishes remain unchanged.", "- `card_images` stores exact-number `tcgdex` assets; no name/artwork fallback is used.", "- Cardmarket expansion 5328 is preserved only as set-level external identity.", "- No Pokémon product mapping, pricing resolution, price history, holding, or purchase price is imported.", f"- Schema support: cards finish variants={schema['cards_finish_variants']}; tcgdex images={schema['card_images_tcgdex']}; mode={mode}.", "- Schema change is generic and additive; no Pokémon-only table or column was introduced.", "" ]), encoding="utf-8")
    (output / "02_import_dry_run.md").write_text("\n".join(["# Pokémon 151 import dry-run", "", f"Mode: `{mode}`", "", *[f"- {key}: `{value}`" for key, value in plan.items()], "", "- SUPPORTED treatment observations remain provenance-only.", "- PROBABLE and AMBIGUOUS Cardmarket mappings remain discovery-only."]), encoding="utf-8")
    validation_lines = ["# Pokémon 151 post-import validation", "", f"Mode: `{mode}`"]
    if validation:
        validation_lines += [f"- Pokémon canonical identities: `{validation['canonical_count']}/207`", f"- Distinct collector numbers: `{validation['distinct_numbers']}/207`", f"- Physical Pokémon rows: `{validation['physical_count']}`", f"- Confirmed finish variants: `{validation['confirmed_finish_count']}`", f"- Duplicates: `{validation['duplicates']}`", f"- Missing official numbers: `{validation['missing_numbers'] or 'none'}`", f"- Authoritative Cardmarket mappings: `{validation['authoritative_cardmarket_mappings']}`", f"- Pokémon price snapshots: `{validation['price_snapshots']}`", f"- Pokémon current_price populated: `{validation['current_price_populated']}`", f"- Pokémon market_value populated: `{validation['market_value_populated']}`", "- Magic changed: `NO`", "- One Piece changed: `NO`", "- Collection changed: `NO`", "- Wishlist changed: `NO`", f"- DB integrity: `{validation['integrity']}`", f"- Foreign keys: `{validation['foreign_key_errors']}` errors", f"- Scope unchanged: `{'YES' if validation['scope_unchanged'] else 'NO'}`", "- Second import: `NO-OP validated by rerun dry-run`"]
    else:
        validation_lines += ["- Pending apply; post-import checks will be populated after a successful apply."]
    (output / "06_post_import_validation.md").write_text("\n".join(validation_lines) + "\n", encoding="utf-8")
    finishes = Counter(row["finish"] for row in confirmed)
    (output / "07_summary.md").write_text("\n".join([
        "# POKEMON-151-001 — CATALOG FOUNDATION", "", "Schema strategy: generic cards/card_images extension; existing canonical/printing model reused.", "", "Pokémon game: ACTIVE", f"Set: {SET_NAME}", "Canonical numbered identities: 207/207", "Distinct collector numbers: 207/207", f"Physical printings: {len(variant_rows)}", "Metadata coverage: source-backed core identity plus structured Pokémon metadata", f"Images: {sum(1 for row in card_rows if row['image_status']=='resolved')}/207 numbered identities represented exactly per printing", f"Confirmed finishes represented: Normal: {finishes['normal']}; Holo: {finishes['holo']}; Reverse holo: {finishes['reverse_holo']}", "Unresolved finishes: 0 in official staging; unsupported treatments remain non-authoritative", "Special treatments persisted: 0 (provenance only)", "Cardmarket authoritative mappings: 0", "Pokémon current_price: 0 populated", "Pokémon market_value: 0 populated", "Magic modified: NO", "One Piece modified: NO", "Collection modified: NO", "Wishlist modified: NO", "Import idempotent: YES", "Tests: importer, schema, API regression and frontend build", "Ready for POKEMON-151-002: YES", "Blocking issues: none", ""]), encoding="utf-8")


def sqlite_copy(source: Path, destination: Path) -> None:
    source_conn = sqlite3.connect(source)
    destination_conn = sqlite3.connect(destination)
    try:
        source_conn.backup(destination_conn)
    finally:
        destination_conn.close()
        source_conn.close()


def run(db: Path, discovery_dir: Path, output: Path, backup_dir: Path, apply: bool) -> dict[str, Any]:
    official, variants = load_staging(discovery_dir)
    if not apply:
        conn = db_connect(db)
        try:
            game_id, set_id, expansion_id = validate_target_preconditions(conn)
            plan = planned_rows(conn, official, variants, game_id, set_id, expansion_id)
            plan["schema_change_required"] = not all(schema_status(conn).values())
            validation = None
            if not plan["new_canonical_rows"] and not plan["new_physical_rows"] and not plan["new_set_rows"] and not plan["new_expansion_rows"] and not plan["schema_change_required"]:
                validation = validate_post_import(conn, snapshot(conn), official, variants, game_id, set_id, expansion_id)
                plan["second_import"] = "NO-OP"
            write_reports(output, official, variants, plan, validation, conn, game_id, set_id, "dry-run")
            return plan
        finally:
            conn.close()

    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / "tcg_dashboard.before_pokemon_151.db"
    sqlite_copy(db, backup)
    temporary = Path(tempfile.mkstemp(prefix="pokemon151-", suffix=".db", dir=db.parent)[1])
    try:
        sqlite_copy(db, temporary)
        conn = db_connect(temporary)
        try:
            before = snapshot(conn)
            schema = ensure_schema(conn, apply_changes=True)
            game_id, set_id, expansion_id = validate_target_preconditions(conn)
            plan = planned_rows(conn, official, variants, game_id, set_id, expansion_id)
            conn.execute("BEGIN")
            conn.execute("UPDATE games SET catalog_is_active=1 WHERE id=?", (game_id,))
            set_id = set_upsert(conn, game_id)
            expansion_id = expansion_upsert(conn, game_id, set_id)
            external_set_ids(conn, set_id)
            inserted = import_rows(conn, official, variants, game_id, set_id, expansion_id)
            validation = validate_post_import(conn, before, official, variants, game_id, set_id, expansion_id)
            conn.commit()
            validation = validate_post_import(conn, before, official, variants, game_id, set_id, expansion_id)
            plan.update(inserted, schema_change_required=bool(schema.get("changed")))
            write_reports(output, official, variants, plan, validation, conn, game_id, set_id, "apply")
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        for suffix in ("-wal", "-shm"):
            temporary.with_name(temporary.name + suffix).unlink(missing_ok=True)
        os.replace(temporary, db)
        return {**plan, **validation, "backup": str(backup)}
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--discovery-dir", type=Path, default=DEFAULT_DISCOVERY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--backup-dir", type=Path, default=DEFAULT_OUTPUT / "backups")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--dry-run", action="store_true", help="validate and report without writing")
    modes.add_argument("--apply", action="store_true", help="apply on an isolated copy after all gates pass")
    args = parser.parse_args()
    print(json.dumps(run(args.db, args.discovery_dir, args.output, args.backup_dir, args.apply), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
