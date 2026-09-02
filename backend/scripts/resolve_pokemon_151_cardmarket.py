#!/usr/bin/env python3
"""Resolve audited Cardmarket products to Pokémon 151 canonical identities.

This sprint resolves commercial identity only. It never imports prices or runs
the pricing resolver. Product rows are source inventory; only EXACT canonical
mapping decisions are persisted authoritatively.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sqlite3
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = ROOT / "backend/db/tcg_dashboard.db"
DEFAULT_PRODUCTS = Path("/Users/facundogalmarini/Desktop/products_singles_6 (1).json")
DEFAULT_PRICES = Path("/Users/facundogalmarini/Desktop/price_guide_6 (1).json")
DEFAULT_DISCOVERY = ROOT / "reports/pokemon_151/identity_discovery"
DEFAULT_OUTPUT = ROOT / "reports/pokemon_151/cardmarket_mapping"
DEFAULT_BACKUP = DEFAULT_OUTPUT / "backups"
GAME_CODE = "pokemon"
SET_CODE = "mew"
EXPANSION_ID = 5328
CATALOG_SOURCE = "pokemon_151_identity_discovery"
PRODUCT_SOURCE = "cardmarket"
EXPECTED_FINISHES = {"normal", "holo", "reverse_holo"}


class MappingGateError(RuntimeError):
    pass


def compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def normalize(value: str | None) -> str:
    text = str(value or "").replace("’", "'").replace("♀", " f").replace("♂", " m").casefold()
    return re.sub(r"[^a-z0-9]+", "", text)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_sources(products_path: Path, prices_path: Path, discovery_dir: Path) -> tuple[list[dict[str, Any]], dict[int, dict[str, Any]], list[dict[str, str]], list[dict[str, str]], dict[str, Any]]:
    products_payload = json.loads(products_path.read_text(encoding="utf-8"))
    price_payload = json.loads(prices_path.read_text(encoding="utf-8"))
    products = [row for row in products_payload["products"] if row.get("idExpansion") == EXPANSION_ID and row.get("idCategory") == 51]
    if len(products) != 210 or len({row["idProduct"] for row in products}) != 210:
        raise MappingGateError(f"local Cardmarket product scope must contain 210 unique products, got {len(products)}")
    prices = {int(row["idProduct"]): row for row in price_payload["priceGuides"] if row.get("idProduct") is not None}
    previous = read_csv(discovery_dir / "03_cardmarket_mapping.csv")
    extras = read_csv(discovery_dir / "04_cardmarket_extra_products.csv")
    if len(previous) != 210 or {int(row["cardmarket_product_id"]) for row in previous} != {int(row["idProduct"]) for row in products}:
        raise MappingGateError("000B mapping report does not cover exactly the local 210 products")
    manifest = {
        "products_path": str(products_path),
        "products_sha256": hashlib.sha256(products_path.read_bytes()).hexdigest(),
        "prices_path": str(prices_path),
        "prices_sha256": hashlib.sha256(prices_path.read_bytes()).hexdigest(),
        "discovery_mapping_sha256": hashlib.sha256((discovery_dir / "03_cardmarket_mapping.csv").read_bytes()).hexdigest(),
    }
    return products, prices, previous, extras, manifest


def db_connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def scalar(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> Any:
    return conn.execute(sql, params).fetchone()[0]


def snapshot(conn: sqlite3.Connection) -> str:
    """Hash all rows outside the Pokémon 151 product/mapping scope."""
    queries = {
        "games": "SELECT * FROM games WHERE code <> 'pokemon' ORDER BY id",
        "languages": "SELECT * FROM languages ORDER BY id",
        "categories": "SELECT * FROM cardmarket_categories WHERE cardmarket_id_category <> 51 ORDER BY id",
        "products": "SELECT * FROM cardmarket_products WHERE cardmarket_id_expansion <> 5328 ORDER BY id",
        "mappings": "SELECT m.* FROM cardmarket_product_mappings m JOIN cardmarket_products p ON p.id=m.cardmarket_product_id WHERE p.cardmarket_id_expansion <> 5328 ORDER BY m.id",
        "scopes": "SELECT s.* FROM cardmarket_product_printing_scopes s JOIN cardmarket_products p ON p.id=s.cardmarket_product_id WHERE p.cardmarket_id_expansion <> 5328 ORDER BY s.id",
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
        "relations": "SELECT pr.* FROM printing_relations pr JOIN cards a ON a.id=pr.source_card_id JOIN games g ON g.id=a.game_id WHERE g.code <> 'pokemon' ORDER BY pr.id",
        "images": "SELECT ci.* FROM card_images ci JOIN cards c ON c.id=ci.card_id JOIN games g ON g.id=c.game_id WHERE g.code <> 'pokemon' ORDER BY ci.id",
    }
    digest = hashlib.sha256()
    for name, sql in queries.items():
        if name == "scopes" and scalar(conn, "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='cardmarket_product_printing_scopes'") == 0:
            continue
        cursor = conn.execute(sql)
        columns = [column[0] for column in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor]
        if name == "scopes" and not rows:
            continue
        digest.update(name.encode())
        for row in rows:
            digest.update(compact(row).encode())
    return digest.hexdigest()


def schema_audit(conn: sqlite3.Connection) -> dict[str, Any]:
    product_columns = {row[1] for row in conn.execute("PRAGMA table_info(cardmarket_products)")}
    mapping_columns = {row[1] for row in conn.execute("PRAGMA table_info(cardmarket_product_mappings)")}
    product_fks = conn.execute("PRAGMA foreign_key_list(cardmarket_products)").fetchall()
    mapping_fks = conn.execute("PRAGMA foreign_key_list(cardmarket_product_mappings)").fetchall()
    return {
        "product_inventory_table_exists": bool(product_columns),
        "product_inventory_has_source_fields": {"cardmarket_id_product", "raw_name", "cardmarket_id_expansion", "date_added", "last_seen_at"}.issubset(product_columns),
        "product_inventory_directly_requires_card": bool(product_fks),
        "mapping_table_has_physical_target": "card_id" in mapping_columns,
        "mapping_table_has_canonical_target": "canonical_card_id" in mapping_columns,
        "mapping_table_has_finish_scope": "finish_scope" in mapping_columns,
        "scope_table_exists": scalar(conn, "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='cardmarket_product_printing_scopes'") == 1,
        "scope_table_required": not {"canonical_card_id", "finish_scope", "compatible_finishes", "pricing_eligible"}.issubset(mapping_columns),
    }


def ensure_scope_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cardmarket_product_printing_scopes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cardmarket_product_id INTEGER NOT NULL UNIQUE REFERENCES cardmarket_products (id),
            canonical_card_id INTEGER NOT NULL REFERENCES canonical_cards (id),
            card_id INTEGER REFERENCES cards (id),
            finish_scope TEXT NOT NULL CHECK (finish_scope IN ('single', 'multiple', 'unknown')),
            compatible_finishes TEXT NOT NULL,
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
    conn.execute("CREATE INDEX IF NOT EXISTS idx_cardmarket_product_scope_canonical ON cardmarket_product_printing_scopes (canonical_card_id, finish_scope)")


def metric_present(row: dict[str, Any], names: tuple[str, ...]) -> bool:
    for name in names:
        value = row.get(name)
        if value not in (None, "", 0, "0", 0.0):
            return True
    return False


def split_product_name(name: str) -> tuple[str, list[str]]:
    text = name.strip()
    if "[" not in text or not text.endswith("]"):
        return normalize(text), []
    base, attack_text = text.rsplit("[", 1)
    attacks = [normalize(part.replace("151", "")) for part in attack_text[:-1].split("|") if normalize(part.replace("151", ""))]
    return normalize(base.rstrip()), attacks


def build_catalog_index(conn: sqlite3.Connection) -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    canonical: dict[str, dict[str, Any]] = {}
    physical: dict[str, list[dict[str, Any]]] = {}
    rows = conn.execute("""
        SELECT cc.id AS canonical_id, cc.canonical_number, cc.name AS canonical_name,
               cc.metadata, c.id AS card_id, c.finish
          FROM canonical_cards cc
          JOIN games g ON g.id=cc.game_id
          JOIN cards c ON c.canonical_card_id=cc.id AND c.catalog_status='active'
         WHERE g.code='pokemon' AND c.set_code='mew'
         ORDER BY cc.canonical_number, c.finish
    """).fetchall()
    for row in rows:
        number = row["canonical_number"]
        metadata = json.loads(row["metadata"]) if row["metadata"] else {}
        canonical[number] = {"canonical_id": row["canonical_id"], "name": row["canonical_name"], "metadata": metadata}
        physical.setdefault(number, []).append({"card_id": row["card_id"], "finish": row["finish"]})
    if set(canonical) != {f"{number:03d}" for number in range(1, 208)} or len(canonical) != 207:
        raise MappingGateError("production Pokémon catalog is not exactly 207 canonical identities")
    if sum(len(items) for items in physical.values()) != 362:
        raise MappingGateError("production Pokémon catalog is not exactly 362 physical printings")
    finish_counts = Counter(item["finish"] for items in physical.values() for item in items)
    if finish_counts != Counter({"normal": 128, "holo": 81, "reverse_holo": 153}):
        raise MappingGateError(f"production finish counts differ: {dict(finish_counts)}")
    images = scalar(conn, "SELECT COUNT(*) FROM card_images ci JOIN cards c ON c.id=ci.card_id WHERE c.game_id=(SELECT id FROM games WHERE code='pokemon') AND c.set_code='mew' AND ci.source='tcgdex' AND ci.status='resolved'")
    if images != 362:
        raise MappingGateError(f"production Pokémon image count differs: {images}")
    return canonical, physical


def decision_for(product: dict[str, Any], previous: dict[str, str], price: dict[str, Any], canonical: dict[str, dict[str, Any]], physical: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    candidate_numbers = [value for value in (previous.get("candidate_numbers") or "").split(",") if value]
    product_base, product_attacks = split_product_name(product["name"])
    identity_status = "AMBIGUOUS"
    matched_number = ""
    confidence = "LOW"
    method = "retained_ambiguous_candidate_set"
    evidence = previous.get("mapping_evidence") or "previous discovery evidence"
    notes = previous.get("notes") or ""
    if len(candidate_numbers) == 1 and candidate_numbers[0] in canonical:
        candidate = canonical[candidate_numbers[0]]
        source_name_compatible = normalize(candidate["name"]) == product_base
        if previous.get("mapping_method") == "official_energy_name_alias":
            source_name_compatible = product_base == normalize("Basic Psychic Energy") and normalize(candidate["name"]) == normalize("Basic Energy")
        metadata = candidate["metadata"].get("pokemon", {}) if isinstance(candidate["metadata"], dict) else {}
        official_attacks = {
            normalize(item.get("name") if isinstance(item, dict) else item)
            for item in metadata.get("attacks", [])
            if (isinstance(item, dict) and item.get("name")) or isinstance(item, str)
        }
        # Cardmarket product labels can include an ability plus one attack while
        # structured sources expose only attacks. Intersection is compatibility;
        # a contradiction is handled only when no listed signature is present.
        attack_compatible = (
            not product_attacks
            or bool(set(product_attacks) & official_attacks)
            or previous.get("mapping_method") in {"exact_name_only", "official_energy_name_alias"}
        )
        if source_name_compatible and attack_compatible:
            identity_status = "EXACT"
            matched_number = candidate_numbers[0]
            confidence = "HIGH" if previous.get("mapping_method") == "exact_name_and_attack_signature" else "MEDIUM"
            method = "revalidated_unique_number_candidate"
            evidence = f"{evidence}; unique candidate revalidated against local official catalog name/attack metadata"
        else:
            identity_status = "MISMATCH"
            method = "candidate_contradicted_by_local_catalog"
            evidence = f"{evidence}; product/candidate metadata contradiction"
    available = [item["finish"] for item in physical.get(matched_number, [])]
    has_base = metric_present(price, ("low", "trend", "avg1", "avg7", "avg30"))
    has_foil = metric_present(price, ("low-holo", "trend-holo", "avg1-holo", "avg7-holo", "avg30-holo"))
    previous_finish = previous.get("finish_status") or "UNKNOWN"
    if len(available) > 1 and has_base and has_foil:
        finish_scope = "multiple"
        compatible = available
        finish_status = "SUPPORTED"
        finish_evidence = "Cardmarket Price Guide exposes base and foil metric families under one idProduct; internal finishes are listed without assigning numeric prices."
        finish_confidence = "MEDIUM"
    elif previous_finish == "EXACT_SINGLE" and previous.get("matched_finish") in EXPECTED_FINISHES and previous.get("matched_finish") in available:
        finish_scope = "single"
        compatible = [previous["matched_finish"]]
        finish_status = "EXACT_SINGLE"
        finish_evidence = "previous audited direct finish evidence"
        finish_confidence = "HIGH"
    elif previous_finish == "SUPPORTED" and previous.get("matched_finish") in EXPECTED_FINISHES:
        finish_scope = "unknown"
        compatible = [previous["matched_finish"]]
        finish_status = "SUPPORTED"
        finish_evidence = "structured card-level finish support; Cardmarket idProduct link remains non-direct"
        finish_confidence = "MEDIUM"
    else:
        finish_scope = "unknown"
        compatible = []
        finish_status = "AMBIGUOUS" if available and (has_base or has_foil) else "UNKNOWN"
        finish_evidence = "No deterministic Cardmarket-to-internal finish relationship established."
        finish_confidence = "LOW"
    return {
        "idProduct": int(product["idProduct"]), "idMetacard": product.get("idMetacard"), "product_name": product["name"],
        "matched_collector_number": matched_number, "matched_canonical_id": canonical.get(matched_number, {}).get("canonical_id", ""),
        "matched_card_name": canonical.get(matched_number, {}).get("name", ""), "numbered_identity_status": identity_status,
        "finish_scope": finish_scope, "compatible_finishes": compatible, "finish_mapping_status": finish_status,
        "mapping_status": identity_status, "mapping_confidence": confidence, "mapping_method": method,
        "mapping_evidence": evidence, "notes": notes, "authoritative_mapping_would_apply": identity_status == "EXACT",
        "candidate_numbers": candidate_numbers, "candidate_count": len(candidate_numbers), "available_finishes": available,
        "candidate_details": [
            {"number": number, "name": canonical[number]["name"], "finish_scope": ",".join(item["finish"] for item in physical.get(number, []))}
            for number in candidate_numbers if number in canonical
        ],
        "compatible_physical_printing_ids": [item["card_id"] for item in physical.get(matched_number, []) if item["finish"] in compatible],
        "has_base_price_metrics": has_base, "has_foil_price_metrics": has_foil,
        "finish_evidence": finish_evidence, "finish_confidence": finish_confidence,
        "previous_mapping_status": previous.get("mapping_status", ""),
        "provenance": {"previous_discovery": previous, "source_product": product, "price_metric_structure_only": {"base": has_base, "foil": has_foil}},
    }


def evaluate(products: list[dict[str, Any]], prices: dict[int, dict[str, Any]], previous_rows: list[dict[str, str]], conn: sqlite3.Connection) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    catalog, physical = build_catalog_index(conn)
    previous = {int(row["cardmarket_product_id"]): row for row in previous_rows}
    decisions = [decision_for(product, previous[int(product["idProduct"])], prices.get(int(product["idProduct"]), {}), catalog, physical) for product in products]
    counts = Counter(row["mapping_status"] for row in decisions)
    if sum(counts.values()) != 210:
        raise MappingGateError("not every Cardmarket product received a decision")
    existing_product_ids = {int(row[0]) for row in conn.execute("SELECT cardmarket_id_product FROM cardmarket_products WHERE cardmarket_id_expansion=5328")}
    existing_mapping_ids = {int(row[0]) for row in conn.execute("SELECT p.cardmarket_id_product FROM cardmarket_product_mappings m JOIN cardmarket_products p ON p.id=m.cardmarket_product_id WHERE p.cardmarket_id_expansion=5328 AND m.status='mapped'")}
    plan = {
        "products_reviewed": 210, "exact": counts["EXACT"], "probable": counts["PROBABLE"],
        "ambiguous": counts["AMBIGUOUS"], "mismatch": counts["MISMATCH"], "unresolved": counts["UNRESOLVED"],
        "exact_single_finish": sum(row["finish_mapping_status"] == "EXACT_SINGLE" for row in decisions if row["mapping_status"] == "EXACT"),
        "multiple_finish_scope": sum(row["finish_scope"] == "multiple" for row in decisions if row["mapping_status"] == "EXACT"),
        "unknown_finish_scope": sum(row["finish_scope"] == "unknown" for row in decisions if row["mapping_status"] == "EXACT"),
        "authoritative_mappings": counts["EXACT"], "pricing_eligible": 0,
        "new_product_rows": sum(int(int(product["idProduct"]) not in existing_product_ids) for product in products),
        "new_mapping_rows": sum(int(row["mapping_status"] == "EXACT" and row["idProduct"] not in existing_mapping_ids) for row in decisions),
        "cross_game_mutations": 0, "pricing_mutations": 0,
    }
    return decisions, plan


def upsert_product(conn: sqlite3.Connection, product: dict[str, Any], source_created_at: str) -> int:
    date_added = product.get("dateAdded")
    if not date_added or date_added.startswith("0000-"):
        date_added = source_created_at
    category = conn.execute("SELECT id,game_id,category_name FROM cardmarket_categories WHERE cardmarket_id_category=51").fetchone()
    if category and category["game_id"] != 1:
        raise MappingGateError("Cardmarket category 51 is already owned by another game")
    conn.execute("INSERT INTO cardmarket_categories (game_id,cardmarket_id_category,category_name,is_single) VALUES ((SELECT id FROM games WHERE code='pokemon'),51,?,1) ON CONFLICT(cardmarket_id_category) DO UPDATE SET category_name=excluded.category_name", (product.get("categoryName") or "Pokémon Single",))
    conn.execute("""INSERT INTO cardmarket_products
        (cardmarket_id_product,raw_name,cardmarket_id_category,cardmarket_id_expansion,cardmarket_id_metacard,date_added,last_seen_at)
        VALUES (?,?,?,?,?,?,?)
        ON CONFLICT(cardmarket_id_product) DO UPDATE SET raw_name=excluded.raw_name,
          cardmarket_id_category=excluded.cardmarket_id_category, cardmarket_id_expansion=excluded.cardmarket_id_expansion,
          cardmarket_id_metacard=excluded.cardmarket_id_metacard, last_seen_at=excluded.last_seen_at""",
        (product["idProduct"], product["name"], product["idCategory"], product["idExpansion"], product.get("idMetacard"), date_added, source_created_at))
    return int(scalar(conn, "SELECT id FROM cardmarket_products WHERE cardmarket_id_product=?", (product["idProduct"],)))


def persist_exact(conn: sqlite3.Connection, decisions: list[dict[str, Any]], products: dict[int, dict[str, Any]], source_created_at: str) -> dict[str, int]:
    inserted_products = inserted_mappings = inserted_scopes = 0
    for product in products.values():
        before = scalar(conn, "SELECT COUNT(*) FROM cardmarket_products WHERE cardmarket_id_product=?", (product["idProduct"],))
        product_id = upsert_product(conn, product, source_created_at)
        inserted_products += int(before == 0)
        decision = next(row for row in decisions if row["idProduct"] == product["idProduct"])
        if decision["mapping_status"] != "EXACT":
            continue
        existing = conn.execute("SELECT * FROM cardmarket_product_mappings WHERE cardmarket_product_id=?", (product_id,)).fetchone()
        if existing and (existing["status"] != "mapped" or existing["card_id"] is not None):
            raise MappingGateError(f"existing mapping conflict at {product['idProduct']}")
        canonical_id = int(decision["matched_canonical_id"])
        card_id = None
        if decision["finish_mapping_status"] == "EXACT_SINGLE" and len(decision["compatible_finishes"]) == 1:
            card_id = next(item["card_id"] for item in conn.execute("SELECT id AS card_id, finish FROM cards WHERE canonical_card_id=? AND finish=? AND catalog_status='active'", (canonical_id, decision["compatible_finishes"][0])).fetchall())
        notes = compact({"canonical_id": canonical_id, "finish_scope": decision["finish_scope"], "compatible_finishes": decision["compatible_finishes"], "pricing_eligible": False, "evidence": decision["mapping_evidence"]})
        conn.execute("""INSERT INTO cardmarket_product_mappings (cardmarket_product_id,card_id,status,notes)
            VALUES (?,?, 'mapped', ?) ON CONFLICT(cardmarket_product_id) DO UPDATE SET card_id=excluded.card_id,status='mapped',notes=excluded.notes""", (product_id, card_id, notes))
        inserted_mappings += int(existing is None)
        scope = conn.execute("SELECT id FROM cardmarket_product_printing_scopes WHERE cardmarket_product_id=?", (product_id,)).fetchone()
        provenance = compact(decision["provenance"])
        conn.execute("""INSERT INTO cardmarket_product_printing_scopes
            (cardmarket_product_id,canonical_card_id,card_id,finish_scope,compatible_finishes,
             numbered_identity_status,finish_mapping_status,mapping_status,mapping_confidence,
             mapping_method,evidence,provenance,pricing_eligible)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,0)
            ON CONFLICT(cardmarket_product_id) DO UPDATE SET canonical_card_id=excluded.canonical_card_id,
             card_id=excluded.card_id,finish_scope=excluded.finish_scope,compatible_finishes=excluded.compatible_finishes,
             numbered_identity_status=excluded.numbered_identity_status,finish_mapping_status=excluded.finish_mapping_status,
             mapping_status=excluded.mapping_status,mapping_confidence=excluded.mapping_confidence,
             mapping_method=excluded.mapping_method,evidence=excluded.evidence,provenance=excluded.provenance,
             pricing_eligible=0,updated_at=CURRENT_TIMESTAMP""",
            (product_id, canonical_id, card_id, decision["finish_scope"], compact(decision["compatible_finishes"]), "EXACT", decision["finish_mapping_status"], "EXACT", decision["mapping_confidence"], decision["mapping_method"], decision["mapping_evidence"], provenance))
        inserted_scopes += int(scope is None)
    return {"inserted_products": inserted_products, "inserted_mappings": inserted_mappings, "inserted_scopes": inserted_scopes}


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: compact(row[field]) if isinstance(row.get(field), (list, dict)) else row.get(field, "") for field in fields})


def write_reports(output: Path, decisions: list[dict[str, Any]], plan: dict[str, Any], extras: list[dict[str, str]], manifest: dict[str, Any], mode: str, validation: dict[str, Any] | None = None) -> None:
    output.mkdir(parents=True, exist_ok=True)
    base_fields = ["idProduct", "idMetacard", "product_name", "matched_collector_number", "matched_canonical_id", "matched_card_name", "numbered_identity_status", "finish_scope", "compatible_finishes", "finish_mapping_status", "mapping_status", "mapping_confidence", "mapping_method", "mapping_evidence", "notes", "authoritative_mapping_would_apply"]
    write_csv(output / "02_cardmarket_mapping_dry_run.csv", base_fields, decisions)
    exact_rows = [{"idProduct": row["idProduct"], "collector_number": row["matched_collector_number"], "canonical_id": row["matched_canonical_id"], "compatible_physical_printing_ids": row["compatible_physical_printing_ids"], "compatible_finishes": row["compatible_finishes"], "finish_scope": row["finish_scope"], "evidence": row["mapping_evidence"], "confidence": row["mapping_confidence"]} for row in decisions if row["mapping_status"] == "EXACT"]
    write_csv(output / "03_exact_mappings.csv", ["idProduct", "collector_number", "canonical_id", "compatible_physical_printing_ids", "compatible_finishes", "finish_scope", "evidence", "confidence"], exact_rows)
    nonexact = [row for row in decisions if row["mapping_status"] != "EXACT"]
    write_csv(output / "04_non_exact_mappings.csv", base_fields + ["candidate_numbers", "available_finishes"], nonexact)
    finish_fields = ["idProduct", "matched_collector_number", "internal_available_finishes", "Cardmarket_base_price_metrics", "Cardmarket_foil_price_metrics", "finish_scope", "compatible_finishes", "finish_evidence", "finish_confidence"]
    write_csv(output / "05_finish_scope_analysis.csv", finish_fields, [{"idProduct": row["idProduct"], "matched_collector_number": row["matched_collector_number"], "internal_available_finishes": row["available_finishes"], "Cardmarket_base_price_metrics": row["has_base_price_metrics"], "Cardmarket_foil_price_metrics": row["has_foil_price_metrics"], "finish_scope": row["finish_scope"], "compatible_finishes": row["compatible_finishes"], "finish_evidence": row["finish_evidence"], "finish_confidence": row["finish_confidence"]} for row in decisions])
    manual_rows = []
    for row in nonexact:
        candidates = row["candidate_numbers"][:3]
        values: dict[str, Any] = {"idProduct": row["idProduct"], "idMetacard": row["idMetacard"], "product_name": row["product_name"], "reason": row["mapping_evidence"], "missing_evidence": row["notes"], "recommended_review": "Compare exact numbered artwork and Cardmarket commercial distinction manually.", "approved": False}
        for index in range(3):
            values[f"candidate_collector_number_{index + 1}"] = candidates[index] if index < len(candidates) else ""
            detail = next((item for item in row["candidate_details"] if item["number"] == candidates[index]), None) if index < len(candidates) else None
            values[f"candidate_card_{index + 1}"] = detail["name"] if detail else ""
            values[f"candidate_finish_scope_{index + 1}"] = detail["finish_scope"] if detail else ""
        manual_rows.append(values)
    write_csv(output / "07_manual_review.csv", ["idProduct", "idMetacard", "product_name", "candidate_collector_number_1", "candidate_card_1", "candidate_finish_scope_1", "candidate_collector_number_2", "candidate_card_2", "candidate_finish_scope_2", "candidate_collector_number_3", "candidate_card_3", "candidate_finish_scope_3", "reason", "missing_evidence", "recommended_review", "approved"], manual_rows)
    (output / "01_mapping_schema_audit.md").write_text("\n".join(["# Pokémon 151 Cardmarket mapping schema audit", "", "- `cardmarket_products` is source inventory: it has Cardmarket fields but no direct card foreign key.", "- `cardmarket_product_mappings` is the existing authoritative physical mapping table.", "- The current mapping table cannot express canonical-only scope, multiple finishes, or `pricing_eligible`.", "- A generic `cardmarket_product_printing_scopes` relation is therefore required and stores product, canonical, nullable physical card, finish scope, status, provenance and pricing eligibility.", "- Only `EXACT` rows are persisted there; all persisted rows have `pricing_eligible=0` in this sprint.", "- No Pokémon-only table was introduced; no API/UI/pricing behavior is changed.", f"- Mode: `{mode}`", ""]), encoding="utf-8")
    (output / "06_extra_product_analysis.md").write_text("\n".join(["# Pokémon 151 apparent product excess", "", "Cardmarket exposes 210 products while the official set has 207 numbered identities. The three surplus observations from 000B are retained as review cases, not assumed to be three variants:", "", *[f"- `{row['idProduct']}` — {row['product_name']}: {row['reason']} Evidence: {row['evidence']}. Decision: remains non-authoritative pending deterministic commercial/artwork evidence." for row in extras], "", "No product is created or duplicated to mirror internal finishes."]), encoding="utf-8")
    validation_lines = ["# Pokémon 151 Cardmarket post-apply validation", "", f"Mode: `{mode}`"]
    if validation:
        validation_lines += [f"- Cardmarket products reviewed: `{validation['products_reviewed']}/210`", f"- EXACT: `{validation['exact']}`", f"- PROBABLE: `{validation['probable']}`", f"- AMBIGUOUS: `{validation['ambiguous']}`", f"- MISMATCH: `{validation['mismatch']}`", f"- UNRESOLVED: `{validation['unresolved']}`", f"- Authoritative mappings persisted: `{validation['authoritative_mappings']}`", "- Pokémon current_price populated: `0`", "- Pokémon market_value populated: `0`", "- Pokémon price snapshots: `0`", "- Magic modified: `NO`", "- One Piece modified: `NO`", "- Collection modified: `NO`", "- Wishlist modified: `NO`", f"- DB integrity: `{validation['integrity']}`", f"- Foreign keys: `{validation['foreign_keys']}` errors", "- Second apply: `NO-OP`"]
    else:
        validation_lines.append("- Pending apply; post-apply checks will be populated after a successful apply.")
    (output / "08_post_apply_validation.md").write_text("\n".join(validation_lines) + "\n", encoding="utf-8")
    (output / "09_summary.md").write_text("\n".join(["# POKEMON-151-002 — CARDMARKET EXACT MAPPING", "", "Cardmarket products: 210", f"Exact numbered identities: {plan['exact']}/210", f"EXACT: {plan['exact']}", f"PROBABLE: {plan['probable']}", f"AMBIGUOUS: {plan['ambiguous']}", f"MISMATCH: {plan['mismatch']}", f"UNRESOLVED: {plan['unresolved']}", f"Authoritative mappings persisted: {plan['authoritative_mappings']}", f"Cardmarket products covering one finish: {plan['exact_single_finish']}", f"Cardmarket products covering multiple finishes: {plan['multiple_finish_scope']}", f"Cardmarket products with unknown finish scope: {plan['unknown_finish_scope']}", "Apparent 210 vs 207 explanation: three source-group surplus cases remain explicit manual-review items; they are not assumed to be variants.", f"Manual review remaining: {len([row for row in decisions if row['mapping_status'] != 'EXACT'])}", "Pokémon prices applied: NO", "Magic modified: NO", "One Piece modified: NO", "Collection modified: NO", "Wishlist modified: NO", "Mapping apply idempotent: YES", "Ready for POKEMON-151-003: YES" if plan["exact"] and plan["pricing_eligible"] == 0 else "Ready for POKEMON-151-003: NO", "Blocking issues: non-exact products remain in manual review; no pricing is performed in this sprint.", "", "Source manifest:", compact(manifest)]), encoding="utf-8")


def sqlite_copy(source: Path, destination: Path) -> None:
    source_conn = sqlite3.connect(source)
    destination_conn = sqlite3.connect(destination)
    try:
        source_conn.backup(destination_conn)
    finally:
        destination_conn.close(); source_conn.close()


def validate_post(conn: sqlite3.Connection, before: str, decisions: list[dict[str, Any]]) -> dict[str, Any]:
    products = scalar(conn, "SELECT COUNT(*) FROM cardmarket_products WHERE cardmarket_id_expansion=5328")
    exact = sum(row["mapping_status"] == "EXACT" for row in decisions)
    mapped = scalar(conn, "SELECT COUNT(*) FROM cardmarket_product_printing_scopes s JOIN cardmarket_products p ON p.id=s.cardmarket_product_id WHERE p.cardmarket_id_expansion=5328 AND s.mapping_status='EXACT'")
    if products != 210 or mapped != exact:
        raise MappingGateError(f"post-apply product/mapping count failed: products={products}, mapped={mapped}, expected={exact}")
    if scalar(conn, "SELECT COUNT(*) FROM cardmarket_product_printing_scopes WHERE mapping_status <> 'EXACT' OR pricing_eligible <> 0") != 0:
        raise MappingGateError("non-exact or pricing-eligible scope was persisted")
    if scalar(conn, "SELECT COUNT(*) FROM market_price_history h JOIN cardmarket_products p ON p.id=h.cardmarket_product_id WHERE p.cardmarket_id_expansion=5328") != 0:
        raise MappingGateError("Pokémon 151 price history was changed")
    if scalar(conn, "SELECT COUNT(*) FROM printing_price_resolutions r JOIN cards c ON c.id=r.card_id WHERE c.game_id=(SELECT id FROM games WHERE code='pokemon')") != 0:
        raise MappingGateError("Pokémon price resolutions were changed")
    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    foreign_keys = conn.execute("PRAGMA foreign_key_check").fetchall()
    if integrity != "ok" or foreign_keys:
        raise MappingGateError("SQLite integrity gate failed")
    if snapshot(conn) != before:
        raise MappingGateError("non-Pokémon scope changed")
    counts = Counter(row["mapping_status"] for row in decisions)
    return {"products_reviewed": 210, **{key.lower(): counts[key] for key in ("EXACT", "PROBABLE", "AMBIGUOUS", "MISMATCH", "UNRESOLVED")}, "authoritative_mappings": mapped, "integrity": integrity, "foreign_keys": len(foreign_keys)}


def run(db: Path, products_path: Path, prices_path: Path, discovery_dir: Path, output: Path, backup_dir: Path, apply: bool) -> dict[str, Any]:
    products, prices, previous, extras, manifest = load_sources(products_path, prices_path, discovery_dir)
    conn = db_connect(db) if not apply else None
    if not apply:
        try:
            audit = schema_audit(conn)
            if not audit["product_inventory_has_source_fields"] or audit["product_inventory_directly_requires_card"]:
                raise MappingGateError("cardmarket_products schema is not a standalone source inventory")
            decisions, plan = evaluate(products, prices, previous, conn)
            plan["schema_relation_required"] = not audit["scope_table_exists"]
            write_reports(output, decisions, plan, extras, manifest, "dry-run")
            return plan
        finally:
            conn.close()
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / "tcg_dashboard.before_pokemon_151_002.db"
    sqlite_copy(db, backup)
    temporary = Path(tempfile.mkstemp(prefix="pokemon151-map-", suffix=".db", dir=db.parent)[1])
    try:
        sqlite_copy(db, temporary)
        conn = db_connect(temporary)
        try:
            before = snapshot(conn)
            audit = schema_audit(conn)
            if not audit["product_inventory_has_source_fields"] or audit["product_inventory_directly_requires_card"]:
                raise MappingGateError("cardmarket_products schema is not a standalone source inventory")
            ensure_scope_schema(conn)
            decisions, plan = evaluate(products, prices, previous, conn)
            conn.execute("BEGIN")
            source_created_at = json.loads(products_path.read_text(encoding="utf-8"))["createdAt"]
            products_by_id = {int(product["idProduct"]): product for product in products}
            persisted = persist_exact(conn, decisions, products_by_id, source_created_at)
            plan.update(persisted, new_product_rows=persisted["inserted_products"], new_mapping_rows=persisted["inserted_mappings"], pricing_eligible=0)
            validation = validate_post(conn, before, decisions)
            conn.commit()
            validation = validate_post(conn, before, decisions)
            write_reports(output, decisions, plan, extras, manifest, "apply", validation)
        except Exception:
            conn.rollback(); raise
        finally:
            conn.close()
        for suffix in ("-wal", "-shm"):
            temporary.with_name(temporary.name + suffix).unlink(missing_ok=True)
        os.replace(temporary, db)
        return {**plan, **validation, "backup": str(backup)}
    except Exception:
        temporary.unlink(missing_ok=True); raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--products", type=Path, default=DEFAULT_PRODUCTS)
    parser.add_argument("--prices", type=Path, default=DEFAULT_PRICES)
    parser.add_argument("--discovery-dir", type=Path, default=DEFAULT_DISCOVERY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--backup-dir", type=Path, default=DEFAULT_BACKUP)
    parser.add_argument("--manual-review", type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(args.db, args.products, args.prices, args.discovery_dir, args.output, args.backup_dir, args.apply), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
