#!/usr/bin/env python3
"""Build and apply the controlled Pokémon 151 Cardmarket review workspace.

This workflow changes canonical identity only.  It never imports prices or
infers a physical finish.  An apply with no valid approvals is a true no-op.

Known review UX limitation: CSV image columns may contain base TCGdex asset
URLs. Browser-accessible review exports should normalize those URLs to
`/high.webp` or render them inside an HTML review artifact.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import sqlite3
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = ROOT / "backend/db/tcg_dashboard.db"
DEFAULT_OUTPUT = ROOT / "reports/pokemon_151/cardmarket_manual_resolution"
DEFAULT_REVIEW = DEFAULT_OUTPUT / "03_manual_review.csv"
DEFAULT_BACKUP = DEFAULT_OUTPUT / "backups"
SOURCE_NON_EXACT = ROOT / "reports/pokemon_151/cardmarket_mapping/04_non_exact_mappings.csv"
SOURCE_EXACT = ROOT / "reports/pokemon_151/cardmarket_mapping/03_exact_mappings.csv"
EXPANSION_ID = 5328
SET_CODE = "mew"
GAME_CODE = "pokemon"
WORKSPACE_FIELDS = [
    "idProduct", "idMetacard", "product_name",
    "candidate_1_collector_number", "candidate_1_card_name", "candidate_1_rarity", "candidate_1_image",
    "candidate_2_collector_number", "candidate_2_card_name", "candidate_2_rarity", "candidate_2_image",
    "candidate_3_collector_number", "candidate_3_card_name", "candidate_3_rarity", "candidate_3_image",
    "ambiguity_reason", "evidence_available", "recommended_candidate", "recommendation_confidence",
    "approved", "approved_collector_number", "review_notes",
]
EDITABLE_FIELDS = {"approved", "approved_collector_number", "review_notes"}
IMMUTABLE_FIELDS = set(WORKSPACE_FIELDS) - EDITABLE_FIELDS
REPORT_DIR = DEFAULT_OUTPUT


class ReviewGateError(RuntimeError):
    pass


def compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def normalize(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").replace("’", "'").casefold())


def db_connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def scalar(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()) -> Any:
    return conn.execute(sql, params).fetchone()[0]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def source_metadata(conn: sqlite3.Connection, number: str) -> dict[str, Any]:
    row = conn.execute("""
        SELECT cc.id, cc.canonical_number, cc.name, cc.metadata
          FROM canonical_cards cc JOIN games g ON g.id=cc.game_id
         WHERE g.code=? AND cc.identity_key=?
    """, (GAME_CODE, f"pokemon:{SET_CODE}:{number}")).fetchone()
    if not row:
        raise ReviewGateError(f"canonical candidate missing: {number}")
    metadata = json.loads(row["metadata"] or "{}")
    pokemon = metadata.get("pokemon", {}) if isinstance(metadata, dict) else {}
    provenance = pokemon.get("source_provenance", {}) if isinstance(pokemon, dict) else {}
    image = conn.execute("""
        SELECT ci.image_url_large, ci.image_url_small
          FROM card_images ci JOIN cards c ON c.id=ci.card_id
         WHERE c.canonical_card_id=? AND c.set_code=? AND ci.source='tcgdex'
           AND ci.status='resolved'
         ORDER BY CASE WHEN ci.image_url_large IS NOT NULL THEN 0 ELSE 1 END,
                  CASE WHEN ci.source_variant='holo' THEN 0 ELSE 1 END, ci.id
         LIMIT 1
    """, (row["id"], SET_CODE)).fetchone()
    image_url = (image[0] or image[1]) if image else ""
    return {
        "id": row["id"], "number": number, "name": row["name"],
        "rarity": pokemon.get("rarity", ""), "image": image_url or "",
        "artist": pokemon.get("artist", ""), "category": pokemon.get("category", ""),
        "tcgdex_id": provenance.get("tcgdex_id", f"sv03.5-{number}"),
        "pokemon_tcg_api_id": provenance.get("pokemon_tcg_api_id", ""),
        "attacks": pokemon.get("attacks", []), "abilities": pokemon.get("abilities", []),
    }


def parse_attacks(name: str) -> set[str]:
    if "[" not in name or not name.endswith("]"):
        return set()
    inside = name.rsplit("[", 1)[1][:-1]
    return {normalize(item.replace("151", "")) for item in inside.split("|") if normalize(item.replace("151", ""))}


def candidate_numbers(row: dict[str, str]) -> list[str]:
    raw = row.get("candidate_numbers", "")
    try:
        values = json.loads(raw)
    except json.JSONDecodeError:
        values = [item.strip() for item in raw.split(",") if item.strip()]
    return [str(value).zfill(3) for value in values][:3]


def build_workspace(conn: sqlite3.Connection) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not SOURCE_NON_EXACT.exists():
        raise ReviewGateError(f"missing audited source report: {SOURCE_NON_EXACT}")
    source_rows = read_csv(SOURCE_NON_EXACT)
    if len(source_rows) != 73:
        raise ReviewGateError(f"expected 73 source ambiguity rows, got {len(source_rows)}")
    workspace: list[dict[str, Any]] = []
    evidence_rows: list[dict[str, Any]] = []
    seen: set[int] = set()
    for source in source_rows:
        product_id = int(source["idProduct"])
        if product_id in seen:
            raise ReviewGateError(f"duplicate source idProduct: {product_id}")
        seen.add(product_id)
        product = conn.execute("""
            SELECT cardmarket_id_product, cardmarket_id_metacard, raw_name,
                   cardmarket_id_expansion
              FROM cardmarket_products
             WHERE cardmarket_id_product=?
        """, (product_id,)).fetchone()
        if not product or product["cardmarket_id_expansion"] != EXPANSION_ID:
            raise ReviewGateError(f"invalid local Cardmarket product: {product_id}")
        name = product["raw_name"]
        candidates = [source_metadata(conn, number) for number in candidate_numbers(source)]
        attacks = parse_attacks(name)
        row: dict[str, Any] = {
            "idProduct": product_id, "idMetacard": product["cardmarket_id_metacard"] or "",
            "product_name": name, "ambiguity_reason": source.get("mapping_evidence") or source.get("reason", ""),
            "evidence_available": "; ".join(filter(None, [source.get("mapping_evidence"), source.get("notes"), "exact internal TCGdex images", "structured Pokémon metadata"])),
            "recommended_candidate": "", "recommendation_confidence": "NONE",
            "approved": "false", "approved_collector_number": "", "review_notes": "",
        }
        for index in range(3):
            candidate = candidates[index] if index < len(candidates) else {}
            prefix = f"candidate_{index + 1}_"
            row[prefix + "collector_number"] = candidate.get("number", "")
            row[prefix + "card_name"] = candidate.get("name", "")
            row[prefix + "rarity"] = candidate.get("rarity", "")
            row[prefix + "image"] = candidate.get("image", "")
            if not candidate:
                continue
            official_attacks = {normalize(item.get("name") if isinstance(item, dict) else item) for item in candidate.get("attacks", [])}
            attack_match = bool(attacks & official_attacks) if attacks else False
            name_match = normalize(candidate["name"]) == normalize(name.split("[", 1)[0].strip())
            score = int(name_match) + int(attack_match) + int(bool(candidate.get("image"))) + int(bool(candidate.get("tcgdex_id") and candidate.get("pokemon_tcg_api_id")))
            evidence_rows.append({
                "idProduct": product_id, "candidate_collector_number": candidate["number"],
                "card_name": candidate["name"], "rarity": candidate.get("rarity", ""),
                "image": candidate.get("image", ""), "artist": candidate.get("artist", ""),
                "tcgdex_id": candidate.get("tcgdex_id", ""), "pokemon_tcg_api_id": candidate.get("pokemon_tcg_api_id", ""),
                "name_match": name_match, "rarity_match": "not_available", "image_evidence": "exact_internal_tcgdex_image" if candidate.get("image") else "none",
                "structured_id_evidence": "tcgdex_and_api_metadata" if candidate.get("tcgdex_id") and candidate.get("pokemon_tcg_api_id") else "tcgdex_metadata_only",
                "cardmarket_version_evidence": f"idExpansion={EXPANSION_ID}; idMetacard={product['cardmarket_id_metacard'] or ''}",
                "evidence_score": score, "confidence": "WEAK", "notes": "Diagnostic ranking only; manual approval required.",
            })
        workspace.append(row)
    workspace.sort(key=lambda item: int(item["idProduct"]))
    if len(workspace) != 73:
        raise ReviewGateError("workspace does not contain exactly 73 rows")
    return workspace, evidence_rows
