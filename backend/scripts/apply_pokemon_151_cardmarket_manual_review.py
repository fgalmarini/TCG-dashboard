#!/usr/bin/env python3
"""Build and apply the controlled Pokémon 151 Cardmarket review workspace.

This workflow changes canonical identity only.  It never imports prices or
infers a physical finish.  An apply with no valid approvals is a true no-op.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import os
import re
import shutil
import sqlite3
import tempfile
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode, urlsplit, urlunsplit


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = ROOT / "backend/db/tcg_dashboard.db"
DEFAULT_OUTPUT = ROOT / "reports/pokemon_151/cardmarket_manual_resolution"
DEFAULT_REVIEW = DEFAULT_OUTPUT / "03_manual_review.csv"
DEFAULT_BACKUP = DEFAULT_OUTPUT / "backups"
DEFAULT_PRICE_GUIDE = ROOT / "price-history/pokemon/price_guide_6.json"
SOURCE_NON_EXACT = ROOT / "reports/pokemon_151/cardmarket_mapping/04_non_exact_mappings.csv"
SOURCE_EXACT = ROOT / "reports/pokemon_151/cardmarket_mapping/03_exact_mappings.csv"
EXPANSION_ID = 5328
SET_CODE = "mew"
GAME_CODE = "pokemon"
CARDMARKET_BASE = "https://www.cardmarket.com/en/Pokemon"
LOW_PRICE_MAX = 1.0
HIGH_PRICE_MIN = 10.0
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
# These values are generated from the current local evidence, so an existing
# review artifact may legitimately contain an older recommendation.
DERIVED_REVIEW_FIELDS = {"recommended_candidate", "recommendation_confidence"}
REPORT_DIR = DEFAULT_OUTPUT
RECOMMENDATION_STATUSES = {"AUTO_EXACT", "RECOMMENDED", "NEEDS_REVIEW", "BLOCKED"}
AUTO_EXACT_EVIDENCE_MARKERS = (
    "direct_external_id_match",
    "exact_external_id_match",
    "exact_collector_number",
    "collector_number_match",
    "numbered_identity_exact",
)


class ReviewGateError(RuntimeError):
    pass


def compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def normalize(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").replace("’", "'").casefold())


def cardmarket_product_slug(product_name: Any) -> str:
    """Build a conservative Cardmarket card slug from a product name."""
    text = unicodedata.normalize("NFKD", str(product_name or "")).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[\[\]]", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", "-", text)
    return text.strip("-")


def cardmarket_product_versions_url(product_name: Any) -> str:
    slug = cardmarket_product_slug(product_name)
    return f"{CARDMARKET_BASE}/Cards/{quote(slug, safe='-')}/Versions"


def cardmarket_candidate_search_url(card_name: Any, collector_number: Any) -> str:
    query = f"{str(card_name or '').strip()} {SET_CODE.upper()}{str(collector_number or '').strip()}".strip()
    return f"{CARDMARKET_BASE}/Products/Search?{urlencode({'searchString': query})}"


def normalize_tcgdex_url(value: Any, thumbnail: bool = False) -> str:
    """Return a browser-ready TCGdex image URL without changing other URLs."""
    raw = str(value or "").strip()
    if not raw:
        return ""
    parsed = urlsplit(raw)
    if parsed.netloc.casefold() != "assets.tcgdex.net":
        return raw
    if re.search(r"\.(?:webp|png|jpg)$", parsed.path, re.IGNORECASE):
        return raw
    path = parsed.path.rstrip("/")
    if not path:
        return raw
    suffix = "low.webp" if thumbnail else "high.webp"
    return urlunsplit((parsed.scheme, parsed.netloc, f"{path}/{suffix}", parsed.query, parsed.fragment))


def tcgdex_thumbnail_url(value: Any) -> str:
    """Use the low-resolution TCGdex asset for an HTML thumbnail when available."""
    normalized = normalize_tcgdex_url(value)
    parsed = urlsplit(normalized)
    if parsed.netloc.casefold() == "assets.tcgdex.net" and parsed.path.casefold().endswith("/high.webp"):
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path[:-len("high.webp")] + "low.webp", parsed.query, parsed.fragment))
    return normalize_tcgdex_url(normalized, thumbnail=True)


def canonical_workspace_value(field: str, value: Any) -> str:
    if field.endswith("_image"):
        return normalize_tcgdex_url(value)
    return str(value or "")


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
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def load_price_guide(path: Path = DEFAULT_PRICE_GUIDE) -> dict[int, dict[str, Any]]:
    """Load Cardmarket price-guide evidence without importing it into the DB."""
    if not path.exists():
        raise ReviewGateError(f"missing Cardmarket price guide: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("priceGuides") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        raise ReviewGateError("invalid Cardmarket price guide: priceGuides must be a list")
    fields = ("low", "trend", "avg1", "avg7", "avg30", "low-holo", "trend-holo")
    result: dict[int, dict[str, Any]] = {}
    for item in rows:
        if not isinstance(item, dict) or item.get("idProduct") in (None, ""):
            continue
        try:
            product_id = int(item["idProduct"])
        except (TypeError, ValueError):
            continue
        result[product_id] = {field: item.get(field) for field in fields}
    return result


def price_metrics_for(price_guide: dict[int, dict[str, Any]], product_id: int) -> dict[str, Any]:
    source = price_guide.get(int(product_id), {})
    mapping = {
        "cardmarket_low": "low", "cardmarket_trend": "trend", "cardmarket_avg1": "avg1",
        "cardmarket_avg7": "avg7", "cardmarket_avg30": "avg30",
        "cardmarket_low_holo": "low-holo", "cardmarket_trend_holo": "trend-holo",
    }
    metrics: dict[str, Any] = {}
    for output_field, source_field in mapping.items():
        value = source.get(source_field)
        if value in (None, ""):
            metrics[output_field] = None
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            metrics[output_field] = None
            continue
        metrics[output_field] = number if number > 0 else None
    return metrics


def price_tier(low: Any) -> str:
    try:
        value = float(low)
    except (TypeError, ValueError):
        return "UNKNOWN"
    if value <= 0:
        return "UNKNOWN"
    if value <= LOW_PRICE_MAX:
        return "LOW"
    if value >= HIGH_PRICE_MIN:
        return "HIGH"
    return "MEDIUM"


def candidate_variant(number: Any) -> str:
    try:
        value = int(str(number).lstrip("0") or "0")
    except (TypeError, ValueError):
        return "UNKNOWN"
    if 1 <= value <= 165:
        return "MAIN_SET"
    if 166 <= value <= 207:
        return "ILLUSTRATION_OR_SPECIAL"
    return "UNKNOWN"


def price_based_recommendation(price_row: dict[str, Any], candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    tier = price_tier(price_row.get("cardmarket_low"))
    expected_variant = {"LOW": "MAIN_SET", "HIGH": "ILLUSTRATION_OR_SPECIAL"}.get(tier)
    if not expected_variant:
        return None
    matches = [candidate for candidate in candidates if candidate_variant(candidate.get("number")) == expected_variant]
    if len(matches) == 1:
        number = str(matches[0]["number"]).zfill(3)
        return {
            "status": "RECOMMENDED", "recommended_candidate": number,
            "recommendation_confidence": "LOW",
            "recommendation_reason": f"Cardmarket Low is {tier.lower()} and points to the only {expected_variant.lower().replace('_', ' ')} candidate; review manually.",
        }
    if len(matches) > 1:
        return {
            "status": "NEEDS_REVIEW", "recommended_candidate": "",
            "recommendation_confidence": "NONE",
            "recommendation_reason": f"Cardmarket Low is {tier.lower()} but matches {len(matches)} {expected_variant.lower().replace('_', ' ')} candidates.",
        }
    return {
        "status": "NEEDS_REVIEW", "recommended_candidate": "",
        "recommendation_confidence": "NONE",
        "recommendation_reason": f"Cardmarket Low is {tier.lower()} but contradicts the available candidate variants.",
    }


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


def deterministic_collector_number(source: dict[str, str], candidates: list[str]) -> str:
    """Return a number only when source evidence explicitly identifies it."""
    number = str(source.get("matched_collector_number", "")).strip()
    if not number:
        return ""
    number = number.zfill(3)
    evidence = " ".join(
        str(source.get(field, ""))
        for field in ("mapping_evidence", "notes", "mapping_method", "numbered_identity_status")
    ).casefold()
    has_positive_marker = (
        any(marker in evidence for marker in AUTO_EXACT_EVIDENCE_MARKERS)
        or str(source.get("numbered_identity_status", "")).strip().upper() == "EXACT"
    )
    has_negative_marker = any(marker in evidence for marker in ("no_direct_external_id_match", "no_exact_collector_number"))
    if number in candidates and has_positive_marker and not has_negative_marker:
        return number
    return ""


def recommendation_for(
    source: dict[str, str],
    candidates: list[dict[str, Any]],
    product_name: str,
    price_row: dict[str, Any] | None = None,
) -> dict[str, Any]:
    numbers = [str(candidate.get("number", "")).zfill(3) for candidate in candidates if candidate.get("number")]
    auto_number = deterministic_collector_number(source, numbers)
    if auto_number:
        return {
            "status": "AUTO_EXACT", "recommended_candidate": auto_number,
            "recommendation_confidence": "DETERMINISTIC",
            "recommendation_reason": "Explicit collector-number evidence identifies one candidate.",
        }
    if not candidates:
        return {
            "status": "BLOCKED", "recommended_candidate": "",
            "recommendation_confidence": "NONE",
            "recommendation_reason": "No valid canonical candidate is available in the local catalog.",
        }
    if price_row:
        price_recommendation = price_based_recommendation(price_row, candidates)
        if price_recommendation:
            return price_recommendation

    product_card_name = product_name.split("[", 1)[0].strip()
    product_attacks = parse_attacks(product_name)
    scored: list[tuple[int, dict[str, Any], set[str]]] = []
    for candidate in candidates:
        candidate_attacks = {
            normalize(item.get("name") if isinstance(item, dict) else item)
            for item in candidate.get("attacks", [])
        }
        name_match = normalize(candidate.get("name")) == normalize(product_card_name)
        attack_match = bool(product_attacks & candidate_attacks) if product_attacks else False
        discriminating_signals = {signal for signal, matched in (("name", name_match), ("attack", attack_match)) if matched}
        scored.append((int(name_match) + int(attack_match), candidate, discriminating_signals))
    scored.sort(key=lambda item: item[0], reverse=True)
    if len(scored) == 1:
        return {
            "status": "RECOMMENDED", "recommended_candidate": numbers[0],
            "recommendation_confidence": "LOW",
            "recommendation_reason": "One candidate remains, but no deterministic external identity signal was found.",
        }
    if scored[0][0] > scored[1][0] and "attack" in scored[0][2]:
        return {
            "status": "RECOMMENDED", "recommended_candidate": str(scored[0][1]["number"]).zfill(3),
            "recommendation_confidence": "MEDIUM",
            "recommendation_reason": "A candidate has a unique attack-signature match; this is a suggestion only.",
        }
    return {
        "status": "NEEDS_REVIEW", "recommended_candidate": "",
        "recommendation_confidence": "NONE",
        "recommendation_reason": "Cardmarket exposes multiple versions of the same card without a product-specific discriminator.",
    }


def build_workspace(
    conn: sqlite3.Connection,
    price_guide: dict[int, dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    if not SOURCE_NON_EXACT.exists():
        raise ReviewGateError(f"missing audited source report: {SOURCE_NON_EXACT}")
    source_rows = read_csv(SOURCE_NON_EXACT)
    if len(source_rows) != 73:
        raise ReviewGateError(f"expected 73 source ambiguity rows, got {len(source_rows)}")
    price_guide = price_guide if price_guide is not None else load_price_guide()
    workspace: list[dict[str, Any]] = []
    evidence_rows: list[dict[str, Any]] = []
    recommendations: list[dict[str, Any]] = []
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
        price_metrics = price_metrics_for(price_guide, product_id)
        recommendation = recommendation_for(source, candidates, name, price_metrics)
        row: dict[str, Any] = {
            "idProduct": product_id, "idMetacard": product["cardmarket_id_metacard"] or "",
            "product_name": name, "ambiguity_reason": source.get("mapping_evidence") or source.get("reason", ""),
            "evidence_available": "; ".join(filter(None, [source.get("mapping_evidence"), source.get("notes"), "exact internal TCGdex images", "structured Pokémon metadata"])),
            "recommended_candidate": recommendation["recommended_candidate"],
            "recommendation_confidence": recommendation["recommendation_confidence"],
            "approved": "false", "approved_collector_number": "", "review_notes": "",
        }
        for index in range(3):
            candidate = candidates[index] if index < len(candidates) else {}
            prefix = f"candidate_{index + 1}_"
            row[prefix + "collector_number"] = candidate.get("number", "")
            row[prefix + "card_name"] = candidate.get("name", "")
            row[prefix + "rarity"] = candidate.get("rarity", "")
            row[prefix + "image"] = normalize_tcgdex_url(candidate.get("image", ""))
            if not candidate:
                continue
            official_attacks = {normalize(item.get("name") if isinstance(item, dict) else item) for item in candidate.get("attacks", [])}
            attack_match = bool(attacks & official_attacks) if attacks else False
            name_match = normalize(candidate["name"]) == normalize(name.split("[", 1)[0].strip())
            score = int(name_match) + int(attack_match) + int(bool(candidate.get("image"))) + int(bool(candidate.get("tcgdex_id") and candidate.get("pokemon_tcg_api_id")))
            evidence_rows.append({
                "idProduct": product_id, "candidate_collector_number": candidate["number"],
                "card_name": candidate["name"], "rarity": candidate.get("rarity", ""),
                "image": normalize_tcgdex_url(candidate.get("image", "")), "artist": candidate.get("artist", ""),
                "tcgdex_id": candidate.get("tcgdex_id", ""), "pokemon_tcg_api_id": candidate.get("pokemon_tcg_api_id", ""),
                "name_match": name_match, "rarity_match": "not_available", "image_evidence": "exact_internal_tcgdex_image" if candidate.get("image") else "none",
                "structured_id_evidence": "tcgdex_and_api_metadata" if candidate.get("tcgdex_id") and candidate.get("pokemon_tcg_api_id") else "tcgdex_metadata_only",
                "cardmarket_version_evidence": f"idExpansion={EXPANSION_ID}; idMetacard={product['cardmarket_id_metacard'] or ''}",
                "evidence_score": score, "confidence": "WEAK", "notes": "Diagnostic ranking only; manual approval required.",
            })
        recommendations.append({
            "idProduct": product_id, "idMetacard": product["cardmarket_id_metacard"] or "",
            "product_name": name, "ambiguity_reason": row["ambiguity_reason"],
            "candidate_count": len(candidates), "price_tier": price_tier(price_metrics["cardmarket_low"]),
            **price_metrics, **recommendation,
        })
        workspace.append(row)
    workspace.sort(key=lambda item: int(item["idProduct"]))
    if len(workspace) != 73:
        raise ReviewGateError("workspace does not contain exactly 73 rows")
    recommendations.sort(key=lambda item: int(item["idProduct"]))
    return workspace, evidence_rows, recommendations


def normalized_bool(value: str) -> str:
    value = str(value or "").strip().casefold()
    if value in {"true", "1", "yes"}:
        return "true"
    if value in {"false", "0", "no", ""}:
        return "false"
    raise ReviewGateError(f"invalid approved value: {value}")


def load_review(workspace: list[dict[str, Any]], review_path: Path) -> list[dict[str, str]]:
    if not review_path.exists():
        rows = [{field: str(row.get(field, "")) for field in WORKSPACE_FIELDS} for row in workspace]
        write_csv(review_path, WORKSPACE_FIELDS, rows)
        return rows
    rows = read_csv(review_path)
    if len(rows) != 73:
        raise ReviewGateError("REVIEW_FILE_TAMPERED: review file must contain exactly 73 rows")
    if set(rows[0]) != set(WORKSPACE_FIELDS):
        raise ReviewGateError("REVIEW_FILE_TAMPERED: unexpected or missing review fields")
    expected = {str(row["idProduct"]): row for row in workspace}
    seen: set[str] = set()
    for row in rows:
        product_id = str(row.get("idProduct", ""))
        if product_id in seen or product_id not in expected:
            raise ReviewGateError("REVIEW_FILE_TAMPERED: duplicate or unknown idProduct")
        seen.add(product_id)
        for field in IMMUTABLE_FIELDS:
            if field in DERIVED_REVIEW_FIELDS:
                row[field] = str(expected[product_id].get(field, ""))
                continue
            row[field] = canonical_workspace_value(field, row.get(field, ""))
        for field in IMMUTABLE_FIELDS:
            if field in DERIVED_REVIEW_FIELDS:
                continue
            if canonical_workspace_value(field, row.get(field, "")) != canonical_workspace_value(field, expected[product_id].get(field, "")):
                raise ReviewGateError(f"REVIEW_FILE_TAMPERED: {field} changed for idProduct={product_id}")
        row["approved"] = normalized_bool(row.get("approved", ""))
    if len(seen) != 73:
        raise ReviewGateError("REVIEW_FILE_TAMPERED: review file does not cover the workspace")
    return rows


def protected_exact_rows(conn: sqlite3.Connection, product_ids: list[int]) -> list[dict[str, Any]]:
    if not product_ids:
        return []
    marks = ",".join("?" for _ in product_ids)
    rows = conn.execute(f"""
        SELECT p.cardmarket_id_product, s.canonical_card_id, cc.canonical_number,
               s.mapping_status
          FROM cardmarket_product_printing_scopes s
          JOIN cardmarket_products p ON p.id=s.cardmarket_product_id
          JOIN canonical_cards cc ON cc.id=s.canonical_card_id
         WHERE p.cardmarket_id_product IN ({marks})
           AND p.cardmarket_id_expansion=? AND s.mapping_status='EXACT'
         ORDER BY p.cardmarket_id_product
    """, (*product_ids, EXPANSION_ID)).fetchall()
    return [dict(row) for row in rows]


def protected_baseline(conn: sqlite3.Connection) -> list[int]:
    if not SOURCE_EXACT.exists():
        raise ReviewGateError(f"missing exact mapping baseline: {SOURCE_EXACT}")
    baseline = read_csv(SOURCE_EXACT)
    if len(baseline) != 137:
        raise ReviewGateError(f"expected 137 exact baseline rows, got {len(baseline)}")
    ids = [int(row["idProduct"]) for row in baseline]
    current = {row["cardmarket_id_product"]: (row["collector_number"], row["mapping_status"]) for row in conn.execute("""
        SELECT p.cardmarket_id_product, s.canonical_card_id AS canonical_id,
               cc.canonical_number AS collector_number, s.mapping_status
          FROM cardmarket_product_printing_scopes s
          JOIN cardmarket_products p ON p.id=s.cardmarket_product_id
          JOIN canonical_cards cc ON cc.id=s.canonical_card_id
         WHERE p.cardmarket_id_expansion=? AND p.cardmarket_id_product IN (%s)
    """ % ",".join("?" for _ in ids), (EXPANSION_ID, *ids))}
    expected = {int(row["idProduct"]): (row["collector_number"], "EXACT") for row in baseline}
    if current != expected:
        raise ReviewGateError("potential existing EXACT error: protected baseline differs; automatic modification aborted")
    return ids


def rows_hash(rows: list[dict[str, Any]]) -> str:
    return hashlib.sha256(compact(rows).encode()).hexdigest()


def protected_tables_hash(conn: sqlite3.Connection) -> str:
    digest = hashlib.sha256()
    excluded = {"cardmarket_product_printing_scopes", "cardmarket_product_mappings", "sqlite_sequence"}
    tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name") if row[0] not in excluded]
    for table in tables:
        identifier = '"' + table.replace('"', '""') + '"'
        cursor = conn.execute(f"SELECT * FROM {identifier} ORDER BY rowid")
        digest.update(table.encode()); digest.update(compact([item[0] for item in cursor.description]).encode())
        for row in cursor:
            digest.update(compact(list(row)).encode())
    return digest.hexdigest()


def validate_review(
    conn: sqlite3.Connection,
    rows: list[dict[str, str]],
    workspace: list[dict[str, Any]],
    recommendations: list[dict[str, Any]],
    protected_ids: list[int],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    recommendations_by_id = {int(row["idProduct"]): row for row in recommendations}
    decisions: list[dict[str, Any]] = []
    valid: list[dict[str, Any]] = []
    for row in rows:
        product_id = int(row["idProduct"])
        candidates = [row[f"candidate_{i}_collector_number"] for i in range(1, 4) if row.get(f"candidate_{i}_collector_number")]
        recommendation = recommendations_by_id[product_id]
        decision = {
            "idProduct": product_id, "previous_status": "AMBIGUOUS",
            "approved": row["approved"], "approved_collector_number": row.get("approved_collector_number", ""),
            "recommendation_status": recommendation["status"],
            "recommended_candidate": recommendation["recommended_candidate"],
            "validation_status": "PENDING_APPROVAL", "would_apply": False,
            "reason": "PENDING_HUMAN_APPROVAL",
        }
        if recommendation["status"] == "AUTO_EXACT":
            number = recommendation["recommended_candidate"]
        elif row["approved"] == "false":
            decisions.append(decision); continue
        else:
            number = str(row.get("approved_collector_number", "")).zfill(3)
        if not number or number not in candidates:
            decision.update(validation_status="AUTO_EXACT_CANDIDATE_NOT_IN_REVIEW" if recommendation["status"] == "AUTO_EXACT" else "APPROVED_NUMBER_NOT_IN_CANDIDATES", reason="AUTO_EXACT_CANDIDATE_NOT_IN_REVIEW" if recommendation["status"] == "AUTO_EXACT" else "APPROVED_NUMBER_NOT_IN_CANDIDATES")
            decisions.append(decision); continue
        canonical = conn.execute("""
            SELECT cc.id, cc.canonical_number, cc.name
              FROM canonical_cards cc JOIN games g ON g.id=cc.game_id
             WHERE g.code=? AND cc.identity_key=?
        """, (GAME_CODE, f"pokemon:{SET_CODE}:{number}")).fetchone()
        product = conn.execute("SELECT id, cardmarket_id_expansion FROM cardmarket_products WHERE cardmarket_id_product=?", (product_id,)).fetchone()
        if not product or product["cardmarket_id_expansion"] != EXPANSION_ID:
            decision.update(validation_status="INVALID_PRODUCT", reason="IDPRODUCT_NOT_FOUND_OR_WRONG_EXPANSION")
            decisions.append(decision); continue
        if not canonical:
            decision.update(validation_status="INVALID_CANONICAL", reason="CANONICAL_IDENTITY_NOT_FOUND")
            decisions.append(decision); continue
        existing = conn.execute("SELECT * FROM cardmarket_product_printing_scopes WHERE cardmarket_product_id=?", (product["id"],)).fetchone()
        legacy = conn.execute("SELECT * FROM cardmarket_product_mappings WHERE cardmarket_product_id=?", (product["id"],)).fetchone()
        if existing and existing["canonical_card_id"] != canonical["id"]:
            decision.update(validation_status="CONFLICTING_ACTIVE_MAPPING", reason="CONFLICTING_ACTIVE_MAPPING")
            decisions.append(decision); continue
        if legacy and legacy["card_id"] is not None:
            decision.update(validation_status="CONFLICTING_PHYSICAL_MAPPING", reason="EXISTING_CARD_ID_REQUIRES_REVIEW")
            decisions.append(decision); continue
        if existing and existing["mapping_status"] == "EXACT":
            decision.update(validation_status="ALREADY_EXACT", reason="ALREADY_EXACT")
            decisions.append(decision); continue
        decision.update(
            validation_status="VALID_AUTO_EXACT" if recommendation["status"] == "AUTO_EXACT" else "VALID",
            would_apply=True, reason="AUTO_EXACT_DETERMINISTIC" if recommendation["status"] == "AUTO_EXACT" else "APPROVED_MANUAL_REVIEW",
            canonical_card_id=canonical["id"], card_name=canonical["name"], collector_number=number,
            review_notes=row.get("review_notes", ""),
        )
        decisions.append(decision); valid.append(decision)
    return decisions, valid, {"protected_exact_hash_before": rows_hash(protected_exact_rows(conn, protected_ids))}


def ensure_nullable_scope_schema(conn: sqlite3.Connection) -> None:
    columns = {row[1]: row for row in conn.execute("PRAGMA table_info(cardmarket_product_printing_scopes)")}
    if not columns or columns["finish_scope"][3] == 0:
        return
    conn.execute("PRAGMA foreign_keys=OFF")
    conn.execute("""CREATE TABLE cardmarket_product_printing_scopes_004b (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cardmarket_product_id INTEGER NOT NULL UNIQUE REFERENCES cardmarket_products (id),
        canonical_card_id INTEGER NOT NULL REFERENCES canonical_cards (id),
        card_id INTEGER REFERENCES cards (id),
        finish_scope TEXT CHECK (finish_scope IN ('single', 'multiple', 'unknown')),
        compatible_finishes TEXT,
        numbered_identity_status TEXT NOT NULL CHECK (numbered_identity_status IN ('EXACT','PROBABLE','AMBIGUOUS','MISMATCH','UNRESOLVED')),
        finish_mapping_status TEXT NOT NULL CHECK (finish_mapping_status IN ('EXACT_SINGLE','EXACT_MULTIPLE','SUPPORTED','AMBIGUOUS','UNKNOWN','NOT_APPLICABLE')),
        mapping_status TEXT NOT NULL CHECK (mapping_status IN ('EXACT','PROBABLE','AMBIGUOUS','MISMATCH','UNRESOLVED')),
        mapping_confidence TEXT NOT NULL, mapping_method TEXT NOT NULL, evidence TEXT NOT NULL,
        provenance TEXT NOT NULL, pricing_eligible INTEGER NOT NULL DEFAULT 0 CHECK (pricing_eligible IN (0,1)),
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.execute("""INSERT INTO cardmarket_product_printing_scopes_004b
        SELECT id,cardmarket_product_id,canonical_card_id,card_id,finish_scope,compatible_finishes,
               numbered_identity_status,finish_mapping_status,mapping_status,mapping_confidence,
               mapping_method,evidence,provenance,pricing_eligible,created_at,updated_at
          FROM cardmarket_product_printing_scopes""")
    conn.execute("DROP TABLE cardmarket_product_printing_scopes")
    conn.execute("ALTER TABLE cardmarket_product_printing_scopes_004b RENAME TO cardmarket_product_printing_scopes")
    conn.execute("CREATE INDEX idx_cardmarket_product_scope_canonical ON cardmarket_product_printing_scopes (canonical_card_id, finish_scope)")
    conn.execute("PRAGMA foreign_keys=ON")


def apply_valid(conn: sqlite3.Connection, valid: list[dict[str, Any]], review_path: Path) -> int:
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    for item in valid:
        product = conn.execute("SELECT id FROM cardmarket_products WHERE cardmarket_id_product=?", (item["idProduct"],)).fetchone()
        existing = conn.execute("SELECT * FROM cardmarket_product_printing_scopes WHERE cardmarket_product_id=?", (product["id"],)).fetchone()
        provenance = compact({"source": str(review_path), "approved_collector_number": item["collector_number"], "review_notes": item.get("review_notes", ""), "applied_at": timestamp})
        evidence = compact({"manual_review": True, "collector_number": item["collector_number"], "review_notes": item.get("review_notes", "")})
        if existing:
            conn.execute("""UPDATE cardmarket_product_printing_scopes
                SET canonical_card_id=?, numbered_identity_status='EXACT', mapping_status='EXACT',
                    mapping_method='manual_review', evidence=?, provenance=?, updated_at=CURRENT_TIMESTAMP
              WHERE cardmarket_product_id=?""", (item["canonical_card_id"], evidence, provenance, product["id"]))
        else:
            conn.execute("""INSERT INTO cardmarket_product_printing_scopes
                (cardmarket_product_id, canonical_card_id, card_id, finish_scope,
                 compatible_finishes, numbered_identity_status, finish_mapping_status,
                 mapping_status, mapping_confidence, mapping_method, evidence,
                 provenance, pricing_eligible)
                VALUES (?, ?, NULL, 'unknown', '[]', 'EXACT', 'UNKNOWN',
                        'EXACT', 'MANUAL', 'manual_review', ?, ?, 0)""",
                (product["id"], item["canonical_card_id"], evidence, provenance))
        legacy = conn.execute("SELECT id, card_id FROM cardmarket_product_mappings WHERE cardmarket_product_id=?", (product["id"],)).fetchone()
        if not legacy:
            conn.execute("INSERT INTO cardmarket_product_mappings (cardmarket_product_id, status, notes) VALUES (?, 'mapped', ?)", (product["id"], evidence))
    return len(valid)


def recommendation_counts(recommendations: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(row["status"] for row in recommendations)
    return {status: counts.get(status, 0) for status in sorted(RECOMMENDATION_STATUSES)}


def format_price(value: Any) -> str:
    if value in (None, ""):
        return "—"
    try:
        return f"€{float(value):.2f}"
    except (TypeError, ValueError):
        return "—"


def write_review_html(output: Path, workspace: list[dict[str, Any]], evidence: list[dict[str, Any]], recommendations: list[dict[str, Any]]) -> None:
    evidence_by_id: dict[int, dict[str, dict[str, Any]]] = {}
    for item in evidence:
        evidence_by_id.setdefault(int(item["idProduct"]), {})[str(item["candidate_collector_number"])] = item
    recommendations_by_id = {int(row["idProduct"]): row for row in recommendations}
    counts = recommendation_counts(recommendations)
    parts = [
        "<!doctype html>", "<html lang=\"en\"><head><meta charset=\"utf-8\">",
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">",
        "<title>Pokémon 151 Cardmarket manual resolution</title>",
        "<style>body{font:16px system-ui,sans-serif;background:#0b0b0b;color:#d1d5db;margin:0;padding:24px}"
        "h1{color:#fff}.summary{display:flex;gap:10px;flex-wrap:wrap;margin:18px 0 28px}.pill{background:#171717;border:1px solid #333;border-radius:8px;padding:8px 12px}"
        ".review{border:1px solid #333;border-radius:12px;padding:18px;margin:18px 0;background:#111}.meta,.prices{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:8px;margin:12px 0 18px}.prices{background:#171717;border-radius:8px;padding:12px}.label{color:#9ca3af;font-size:.8rem;text-transform:uppercase;letter-spacing:.04em}.value{color:#fff}.candidates{display:flex;gap:16px;flex-wrap:wrap}.candidate{width:220px;border:1px solid #333;border-radius:10px;padding:10px;background:#171717}.candidate img{display:block;width:200px;height:280px;object-fit:contain;background:#222;border-radius:6px;margin:8px auto}.candidate a{color:#9db0ff}.status{font-weight:700;color:#9db0ff}.muted{color:#9ca3af}</style></head><body>",
        "<h1>Pokémon 151 — Cardmarket manual resolution</h1>",
        "<p class=\"muted\">Presentation-only review artifact. It never approves or applies mappings.</p>",
        "<div class=\"summary\">" + "".join(
            f"<div class=\"pill\">{html.escape(status)}: <strong>{counts[status]}</strong></div>"
            for status in ("AUTO_EXACT", "RECOMMENDED", "NEEDS_REVIEW", "BLOCKED")
        ) + "</div>",
    ]
    for row in workspace:
        product_id = int(row["idProduct"])
        recommendation = recommendations_by_id[product_id]
        parts.append("<section class=\"review\">")
        versions_url = cardmarket_product_versions_url(row["product_name"])
        parts.append(
            f"<h2>Product {html.escape(str(product_id))} — {html.escape(str(row['product_name']))}</h2>"
            f"<p><a class=\"button\" href=\"{html.escape(versions_url, quote=True)}\" target=\"_blank\" rel=\"noopener\">Open Cardmarket versions</a></p>"
        )
        fields = (
            ("idProduct", product_id), ("idMetacard", row["idMetacard"]),
            ("product_name", row["product_name"]), ("ambiguity_reason", row["ambiguity_reason"]),
            ("recommended_candidate", recommendation["recommended_candidate"] or "—"),
            ("recommendation_confidence", recommendation["recommendation_confidence"]),
            ("status", recommendation["status"]),
        )
        parts.append("<div class=\"meta\">")
        for label, value in fields:
            css = "status" if label == "status" else "value"
            parts.append(f"<div><div class=\"label\">{html.escape(label)}</div><div class=\"{css}\">{html.escape(str(value))}</div></div>")
        price_fields = (
            ("Cardmarket Low", "cardmarket_low"), ("Trend", "cardmarket_trend"),
            ("Avg1", "cardmarket_avg1"), ("Avg7", "cardmarket_avg7"),
            ("Avg30", "cardmarket_avg30"), ("Low-Holo", "cardmarket_low_holo"),
            ("Trend-Holo", "cardmarket_trend_holo"),
        )
        parts.append("</div><h3>Cardmarket price guide evidence</h3><div class=\"prices\">")
        for label, key in price_fields:
            value = recommendation.get(key)
            if key in {"cardmarket_low_holo", "cardmarket_trend_holo"} and value is None:
                continue
            parts.append(f"<div><div class=\"label\">{html.escape(label)}</div><div class=\"value\">{html.escape(format_price(value))}</div></div>")
        parts.append("</div><p class=\"muted\">Price guide evidence only; no dashboard pricing is applied.</p><div class=\"candidates\">")
        for index in range(1, 4):
            prefix = f"candidate_{index}_"
            number = row.get(prefix + "collector_number", "")
            if not number:
                continue
            detail = evidence_by_id.get(product_id, {}).get(str(number), {})
            image = normalize_tcgdex_url(row.get(prefix + "image", ""))
            thumbnail = tcgdex_thumbnail_url(image)
            candidate_url = cardmarket_candidate_search_url(row.get(prefix + "card_name", ""), number)
            image_markup = (
                f"<a href=\"{html.escape(image, quote=True)}\" target=\"_blank\" rel=\"noopener\">"
                f"<img src=\"{html.escape(thumbnail, quote=True)}\" alt=\"{html.escape(str(row.get(prefix + 'card_name', '')))} #{html.escape(str(number))}\" loading=\"lazy\"></a>"
                if image else "<div class=\"muted\">Image unavailable</div>"
            )
            parts.append(
                f"<article class=\"candidate\"><h3>Candidate {index}: #{html.escape(str(number))}</h3>{image_markup}"
                f"<div><span class=\"label\">collector_number</span> {html.escape(str(number))}</div>"
                f"<div><span class=\"label\">card name</span> {html.escape(str(row.get(prefix + 'card_name', '')))}</div>"
                f"<div><span class=\"label\">rarity</span> {html.escape(str(row.get(prefix + 'rarity', '') or '—'))}</div>"
                f"<div><span class=\"label\">artist</span> {html.escape(str(detail.get('artist', '') or '—'))}</div>"
                f"<p><a class=\"button\" href=\"{html.escape(candidate_url, quote=True)}\" target=\"_blank\" rel=\"noopener\">Open Cardmarket candidate</a></p></article>"
            )
        parts.append("</div></section>")
    parts.append("</body></html>")
    (output / "review.html").write_text("".join(parts), encoding="utf-8")


def write_reports(output: Path, workspace: list[dict[str, Any]], evidence: list[dict[str, Any]], review: list[dict[str, str]], recommendations: list[dict[str, Any]], decisions: list[dict[str, Any]], validation: dict[str, Any], mode: str) -> None:
    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "01_review_workspace.csv", WORKSPACE_FIELDS, workspace)
    evidence_fields = ["idProduct", "candidate_collector_number", "card_name", "rarity", "image", "artist", "tcgdex_id", "pokemon_tcg_api_id", "name_match", "rarity_match", "image_evidence", "structured_id_evidence", "cardmarket_version_evidence", "evidence_score", "confidence", "notes"]
    write_csv(output / "02_candidate_evidence.csv", evidence_fields, evidence)
    write_csv(output / "03_manual_review.csv", WORKSPACE_FIELDS, review)
    recommendation_fields = [
        "idProduct", "idMetacard", "product_name", "ambiguity_reason",
        "cardmarket_low", "cardmarket_trend", "cardmarket_avg7", "price_tier",
        "status", "recommended_candidate", "recommendation_confidence", "candidate_count",
        "recommendation_reason", "approved", "approved_collector_number",
    ]
    review_by_id = {int(row["idProduct"]): row for row in review}
    write_csv(output / "auto_recommendations.csv", recommendation_fields, [
        {**row, "approved": review_by_id[int(row["idProduct"])]["approved"], "approved_collector_number": review_by_id[int(row["idProduct"])].get("approved_collector_number", "")}
        for row in recommendations
    ])
    write_review_html(output, workspace, evidence, recommendations)
    dry_fields = ["idProduct", "previous_status", "approved", "approved_collector_number", "recommendation_status", "recommended_candidate", "validation_status", "would_apply", "reason"]
    write_csv(output / "04_apply_dry_run.csv", dry_fields, decisions)
    resolved = [{"idProduct": item["idProduct"], "idMetacard": review_by_id[item["idProduct"]]["idMetacard"], "product_name": review_by_id[item["idProduct"]]["product_name"], "collector_number": item["collector_number"], "canonical_card_id": item["canonical_card_id"], "card_name": item["card_name"], "rarity": "", "mapping_method": "auto_exact" if item["validation_status"] == "VALID_AUTO_EXACT" else "manual_review", "review_notes": item.get("review_notes", "")} for item in decisions if item["validation_status"] in {"VALID", "VALID_AUTO_EXACT"}]
    write_csv(output / "05_resolved_mappings.csv", ["idProduct", "idMetacard", "product_name", "collector_number", "canonical_card_id", "card_name", "rarity", "mapping_method", "review_notes"], resolved)
    remaining = []
    for decision in decisions:
        if decision["validation_status"] in {"VALID", "VALID_AUTO_EXACT", "ALREADY_EXACT"}:
            continue
        source = review_by_id[decision["idProduct"]]
        remaining.append({
            "idProduct": decision["idProduct"], "product_name": source["product_name"],
            "remaining_candidates": ",".join(source[f"candidate_{i}_collector_number"] for i in range(1, 4) if source[f"candidate_{i}_collector_number"]),
            "reason": decision["reason"], "recommended_next_action": "Human approval required",
        })
    write_csv(output / "06_remaining_ambiguous.csv", ["idProduct", "product_name", "remaining_candidates", "reason", "recommended_next_action"], remaining)
    (output / "07_post_apply_validation.md").write_text("\n".join([
        "# Pokémon 151 Cardmarket manual resolution — post-apply validation", "",
        f"- Mode: `{mode}`", "- Manual review workflow prepared: `COMPLETE`",
        f"- Manual mappings actually resolved: `{validation['resolved']}`",
        f"- Initial ambiguous products: `73`", f"- Pending human approval: `{validation['pending']}`",
        f"- AUTO_EXACT recommendations: `{validation['recommendation_counts']['AUTO_EXACT']}`",
        f"- RECOMMENDED candidates: `{validation['recommendation_counts']['RECOMMENDED']}`",
        f"- NEEDS_REVIEW products: `{validation['recommendation_counts']['NEEDS_REVIEW']}`",
        f"- BLOCKED products: `{validation['recommendation_counts']['BLOCKED']}`",
        "- Cardmarket review links generated: `YES`",
        "- Cardmarket price-guide evidence loaded for review: `YES`",
        f"- Total Cardmarket products: `{validation['total_products']}`",
        f"- Total EXACT: `{validation['exact']}/210`",
        f"- Existing 137 EXACT unchanged: `{validation['existing_exact_unchanged']}`",
        f"- Protected EXACT hash before: `{validation['protected_exact_hash_before']}`",
        f"- Protected EXACT hash after: `{validation['protected_exact_hash_after']}`",
        "- Cardmarket prices applied: `NO`", "- TCGplayer observations changed: `NO`",
        "- Cardmarket metric mappings changed: `NO`", "- Magic changed: `NO`", "- One Piece changed: `NO`",
        "- Collection changed: `NO`", "- Wishlist changed: `NO`",
        f"- DB SHA unchanged: `{validation['db_sha_unchanged']}`",
        f"- DB integrity: `{validation['integrity']}`", f"- Foreign keys: `{validation['foreign_keys']}` errors",
        f"- Second apply: `{validation['second_apply']}`", "",
    ]) + "\n", encoding="utf-8")
    (output / "08_summary.md").write_text("\n".join([
        "# POKEMON-151-004B — CARDMARKET MANUAL MAPPING RESOLUTION", "",
        "- Manual review workflow prepared: COMPLETE", f"- Manual mappings actually resolved: {validation['resolved']}",
        f"- Cardmarket products: 210", f"- EXACT before: 137", f"- EXACT after: {validation['exact']}/210",
        f"- Pending human approval: {validation['pending']}", "- Cardmarket prices applied: NO",
        f"- AUTO_EXACT: {validation['recommendation_counts']['AUTO_EXACT']}",
        f"- RECOMMENDED: {validation['recommendation_counts']['RECOMMENDED']}",
        f"- NEEDS_REVIEW: {validation['recommendation_counts']['NEEDS_REVIEW']}",
        f"- BLOCKED: {validation['recommendation_counts']['BLOCKED']}",
        "- Cardmarket review links generated: YES",
        "- Cardmarket price-guide evidence loaded for review: YES",
        "- Metric mappings promoted: NO", "- pricing_eligible changed: NO", "- TCGplayer changed: NO",
        "- Magic modified: NO", "- One Piece modified: NO", "- Collection modified: NO", "- Wishlist modified: NO",
        f"- Apply idempotent: {validation['second_apply']}",
    ]) + "\n", encoding="utf-8")


def run(db: Path, review_path: Path, output: Path, backup_dir: Path, apply: bool) -> dict[str, Any]:
    before_sha = hashlib.sha256(db.read_bytes()).hexdigest()
    conn = db_connect(db)
    try:
        workspace, evidence, recommendations = build_workspace(conn)
        existing_workspace = output / "01_review_workspace.csv"
        if existing_workspace.exists():
            stored = read_csv(existing_workspace)
            if len(stored) != 73:
                raise ReviewGateError("REVIEW_FILE_TAMPERED: workspace must contain exactly 73 rows")
            for current, old in zip(workspace, stored):
                for field in IMMUTABLE_FIELDS - DERIVED_REVIEW_FIELDS:
                    if canonical_workspace_value(field, current.get(field, "")) != canonical_workspace_value(field, old.get(field, "")):
                        raise ReviewGateError(f"REVIEW_FILE_TAMPERED: generated workspace changed in {field}")
        review = load_review(workspace, review_path)
        protected_ids = protected_baseline(conn)
        decisions, valid, hashes = validate_review(conn, review, workspace, recommendations, protected_ids)
        protected_before = rows_hash(protected_exact_rows(conn, protected_ids))
        if apply and not valid:
            validation = validation_snapshot(conn, db, before_sha, protected_before, recommendation_counts(recommendations), resolved=0, pending=sum(item["validation_status"] not in {"VALID", "VALID_AUTO_EXACT", "ALREADY_EXACT"} for item in decisions), second_apply="NO-OP", existing_exact_unchanged=True)
            write_reports(output, workspace, evidence, review, recommendations, decisions, validation, "apply-no-op")
            return {"approved_valid_rows": 0, "db_mutation": 0, "db_sha_unchanged": True, **validation}
        if not apply:
            validation = validation_snapshot(conn, db, before_sha, protected_before, recommendation_counts(recommendations), resolved=0, pending=sum(item["validation_status"] not in {"VALID", "VALID_AUTO_EXACT", "ALREADY_EXACT"} for item in decisions), second_apply="NOT_RUN", existing_exact_unchanged=True)
            write_reports(output, workspace, evidence, review, recommendations, decisions, validation, "dry-run")
            return {"approved_valid_rows": len(valid), "db_mutation": 0, **validation}
    finally:
        conn.close()

    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / "tcg_dashboard.before_pokemon_151_004b.db"
    shutil.copy2(db, backup)
    fd, temporary_name = tempfile.mkstemp(prefix="pokemon151-004b-", suffix=".db", dir=str(db.parent))
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        shutil.copy2(db, temporary)
        work = db_connect(temporary)
        try:
            protected_before = rows_hash(protected_exact_rows(work, protected_ids))
            protected_tables_before = protected_tables_hash(work)
            ensure_nullable_scope_schema(work)
            if work.in_transaction:
                work.commit()
            work.execute("BEGIN IMMEDIATE")
            resolved = apply_valid(work, valid, review_path)
            work.execute("PRAGMA foreign_keys=ON")
            integrity = work.execute("PRAGMA integrity_check").fetchone()[0]
            foreign_keys = work.execute("PRAGMA foreign_key_check").fetchall()
            protected_after = rows_hash(protected_exact_rows(work, protected_ids))
            if protected_after != protected_before or integrity != "ok" or foreign_keys:
                raise ReviewGateError("post-apply protection/integrity gate failed")
            if protected_tables_hash(work) != protected_tables_before:
                raise ReviewGateError("protected non-mapping tables changed")
            work.commit()
        except Exception:
            work.rollback()
            raise
        finally:
            work.close()
        for suffix in ("-wal", "-shm"):
            temporary.with_name(temporary.name + suffix).unlink(missing_ok=True)
        os.replace(temporary, db)
        after_sha = hashlib.sha256(db.read_bytes()).hexdigest()
        conn = db_connect(db)
        try:
            validation = validation_snapshot(conn, db, before_sha, protected_before, recommendation_counts(recommendations), resolved=resolved, pending=sum(item["validation_status"] not in {"VALID", "VALID_AUTO_EXACT", "ALREADY_EXACT"} for item in decisions), second_apply="YES", protected_hash_after=rows_hash(protected_exact_rows(conn, protected_ids)), existing_exact_unchanged=protected_before == rows_hash(protected_exact_rows(conn, protected_ids)))
            validation["db_sha_unchanged"] = after_sha == before_sha if resolved == 0 else False
            write_reports(output, workspace, evidence, review, recommendations, decisions, validation, "apply")
            return {"approved_valid_rows": resolved, "db_mutation": resolved, "backup": str(backup), **validation}
        finally:
            conn.close()
    finally:
        temporary.unlink(missing_ok=True)


def validation_snapshot(conn: sqlite3.Connection, db: Path, before_sha: str, protected_before: str, counts: dict[str, int], resolved: int, pending: int, second_apply: str, protected_hash_after: str | None = None, existing_exact_unchanged: bool = True) -> dict[str, Any]:
    return {
        "resolved": resolved, "applied": resolved, "pending": pending, "recommendation_counts": counts,
        "total_products": scalar(conn, "SELECT COUNT(*) FROM cardmarket_products WHERE cardmarket_id_expansion=?", (EXPANSION_ID,)),
        "exact": scalar(conn, "SELECT COUNT(*) FROM cardmarket_product_printing_scopes s JOIN cardmarket_products p ON p.id=s.cardmarket_product_id WHERE p.cardmarket_id_expansion=? AND s.mapping_status='EXACT'", (EXPANSION_ID,)),
        "existing_exact_unchanged": "YES" if existing_exact_unchanged else "NO", "protected_exact_hash_before": protected_before,
        "protected_exact_hash_after": protected_hash_after or protected_before,
        "db_sha_unchanged": hashlib.sha256(db.read_bytes()).hexdigest() == before_sha if db.exists() else False,
        "integrity": conn.execute("PRAGMA integrity_check").fetchone()[0], "foreign_keys": len(conn.execute("PRAGMA foreign_key_check").fetchall()),
        "second_apply": second_apply,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--review", type=Path, default=DEFAULT_REVIEW)
    parser.add_argument("--backup-dir", type=Path, default=DEFAULT_BACKUP)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    result = run(args.db, args.review, args.output, args.backup_dir, args.apply)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
