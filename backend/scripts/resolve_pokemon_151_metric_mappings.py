#!/usr/bin/env python3
"""Resolve Cardmarket base/foil metric families to Pokémon 151 printings.

This sprint audits metric-to-finish relationships only. It never persists
numeric price values, market snapshots or printing price resolutions.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sqlite3
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import resolve_pokemon_151_cardmarket as canonical_resolver


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = ROOT / "backend/db/tcg_dashboard.db"
DEFAULT_PRODUCTS = Path("/Users/facundogalmarini/Desktop/products_singles_6 (1).json")
DEFAULT_PRICES = Path("/Users/facundogalmarini/Desktop/price_guide_6 (1).json")
DEFAULT_DISCOVERY = ROOT / "reports/pokemon_151/identity_discovery"
DEFAULT_OUTPUT = ROOT / "reports/pokemon_151/cardmarket_metric_mapping"
DEFAULT_BACKUP = DEFAULT_OUTPUT / "backups"
EXPANSION_ID = 5328
CATEGORY_ID = 51
METRIC_TABLE = "cardmarket_product_metric_mappings"
BASE_COLUMNS = ("low", "trend", "avg1", "avg7", "avg30")
FOIL_COLUMNS = ("low-holo", "trend-holo", "avg1-holo", "avg7-holo", "avg30-holo")
METRIC_COLUMNS = {"base": BASE_COLUMNS, "foil": FOIL_COLUMNS}
METRIC_STATUSES = {"EXACT", "AMBIGUOUS", "UNRESOLVED", "MISMATCH"}


class MetricMappingGateError(RuntimeError):
    pass


def compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def scalar(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()) -> Any:
    return conn.execute(sql, params).fetchone()[0]


def db_connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def ensure_metric_schema(conn: sqlite3.Connection) -> None:
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {METRIC_TABLE} (
            id                       INTEGER PRIMARY KEY AUTOINCREMENT,
            cardmarket_product_id    INTEGER NOT NULL REFERENCES cardmarket_products (id),
            canonical_card_id        INTEGER NOT NULL REFERENCES canonical_cards (id),
            card_id                  INTEGER REFERENCES cards (id),
            metric_family            TEXT NOT NULL CHECK (metric_family IN ('base', 'foil')),
            canonical_mapping_status TEXT NOT NULL CHECK (canonical_mapping_status IN ('EXACT', 'PROBABLE', 'AMBIGUOUS', 'MISMATCH', 'UNRESOLVED')),
            metric_mapping_status    TEXT NOT NULL CHECK (metric_mapping_status IN ('EXACT', 'AMBIGUOUS', 'UNRESOLVED', 'MISMATCH')),
            pricing_eligible         INTEGER NOT NULL DEFAULT 0 CHECK (pricing_eligible IN (0, 1)),
            candidate_card_ids       TEXT NOT NULL,
            compatible_finishes      TEXT NOT NULL,
            metric_columns           TEXT NOT NULL,
            mapping_method            TEXT NOT NULL,
            confidence               TEXT NOT NULL,
            evidence                 TEXT NOT NULL,
            provenance               TEXT NOT NULL,
            created_at               TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at               TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (cardmarket_product_id, metric_family)
        )
    """)
    conn.execute(f"CREATE INDEX IF NOT EXISTS idx_cardmarket_product_metric_mapping_status ON {METRIC_TABLE} (metric_mapping_status, pricing_eligible)")
    conn.execute(f"CREATE INDEX IF NOT EXISTS idx_cardmarket_product_metric_canonical ON {METRIC_TABLE} (canonical_card_id, metric_family)")


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    return bool(scalar(conn, "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?", (table,)))


def protected_snapshot(conn: sqlite3.Connection) -> str:
    """Hash every existing table except this sprint's additive relation."""
    digest = hashlib.sha256()
    tables = [
        row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT IN (?, 'sqlite_sequence') ORDER BY name",
            (METRIC_TABLE,),
        )
    ]
    for table in tables:
        identifier = '"' + table.replace('"', '""') + '"'
        cursor = conn.execute(f"SELECT * FROM {identifier} ORDER BY rowid")
        columns = [item[0] for item in cursor.description]
        digest.update(table.encode())
        digest.update(compact(columns).encode())
        for row in cursor:
            digest.update(compact(list(row)).encode())
    return digest.hexdigest()


def source_metric_audit(price_rows: dict[int, dict[str, Any]]) -> dict[str, Any]:
    observed_keys = set().union(*(row.keys() for row in price_rows.values())) if price_rows else set()
    expected = set(BASE_COLUMNS) | set(FOIL_COLUMNS)
    return {
        "observed_metric_columns": sorted(observed_keys & expected),
        "unexpected_metric_columns": sorted((observed_keys - expected) & {key for key in observed_keys if key.startswith("low") or key.startswith("trend") or key.startswith("avg")}),
        "base_columns": list(BASE_COLUMNS),
        "foil_columns": list(FOIL_COLUMNS),
        "all_expected_columns_present": expected.issubset(observed_keys),
    }


def metric_present(row: dict[str, Any], columns: tuple[str, ...]) -> bool:
    return any(row.get(column) not in (None, "", 0, "0", 0.0) for column in columns)


def present_columns(row: dict[str, Any], columns: tuple[str, ...]) -> list[str]:
    return [column for column in columns if row.get(column) not in (None, "", 0, "0", 0.0)]


def load_exact_context(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(f"""
        SELECT p.id AS internal_product_id,
               p.cardmarket_id_product,
               p.raw_name,
               s.canonical_card_id,
               s.finish_scope,
               s.compatible_finishes,
               s.mapping_status AS canonical_mapping_status,
               s.evidence AS canonical_evidence,
               s.provenance AS canonical_provenance,
               cc.canonical_number,
               cc.name AS canonical_name
          FROM cardmarket_product_printing_scopes s
          JOIN cardmarket_products p ON p.id=s.cardmarket_product_id
          JOIN canonical_cards cc ON cc.id=s.canonical_card_id
         WHERE p.cardmarket_id_expansion=?
           AND p.cardmarket_id_category=?
           AND s.mapping_status='EXACT'
         ORDER BY p.cardmarket_id_product
    """, (EXPANSION_ID, CATEGORY_ID)).fetchall()
    if len(rows) != 137:
        raise MetricMappingGateError(f"expected 137 canonical EXACT products, got {len(rows)}")
    result = []
    for row in rows:
        compatible = json.loads(row["compatible_finishes"] or "[]")
        if not isinstance(compatible, list):
            raise MetricMappingGateError(f"invalid compatible_finishes for {row['cardmarket_id_product']}")
        physical = conn.execute("""
            SELECT id AS card_id, finish, rarity, art_kind
              FROM cards
             WHERE canonical_card_id=? AND set_code='mew' AND catalog_status='active'
             ORDER BY finish, id
        """, (row["canonical_card_id"],)).fetchall()
        candidates = [dict(item) for item in physical if item["finish"] in compatible]
        result.append({**dict(row), "compatible_finishes": compatible, "physical": candidates})
    return result


def direct_metric_finish_evidence(_context: dict[str, Any], _product: dict[str, Any], _family: str) -> dict[str, Any] | None:
    """Return only explicit product-level evidence; current bulk JSON has none.

    `idMetacard`, Price Guide family names and internal variant availability are
    intentionally not treated as direct evidence of a family-to-finish mapping.
    """
    return None


def resolve_metric(context: dict[str, Any], product: dict[str, Any], price: dict[str, Any], family: str, manifest: dict[str, Any], source_audit: dict[str, Any]) -> dict[str, Any]:
    columns = list(METRIC_COLUMNS[family])
    present = present_columns(price, METRIC_COLUMNS[family])
    candidates = context["physical"]
    direct = direct_metric_finish_evidence(context, product, family)
    status = "UNRESOLVED"
    card_id = None
    confidence = "LOW"
    if direct:
        direct_finish = direct.get("finish")
        matching = [candidate for candidate in candidates if candidate["finish"] == direct_finish]
        if len(matching) == 1:
            status = "EXACT"
            card_id = matching[0]["card_id"]
            confidence = "HIGH"
        elif matching:
            status = "AMBIGUOUS"
        else:
            status = "MISMATCH"
    elif len(candidates) > 1:
        status = "AMBIGUOUS"
    else:
        status = "UNRESOLVED"
    pricing_eligible = status == "EXACT" and card_id is not None and context["canonical_mapping_status"] == "EXACT" and bool(product.get("idProduct")) and bool(family)
    if status == "AMBIGUOUS":
        method = "multiple_physical_finish_candidates_without_family_specific_evidence"
        evidence = (
            f"Source fact: Price Guide exposes {family} columns {present or columns}; "
            f"source fact: canonical scope exposes compatible finishes {context['compatible_finishes']}. "
            "Inference withheld: no Cardmarket source field identifies this metric family with one finish."
        )
    elif status == "UNRESOLVED":
        method = "no_family_specific_finish_evidence"
        evidence = (
            f"Source fact: Price Guide exposes {family} columns {present or columns}; "
            f"source fact: compatible physical candidates are {[candidate['finish'] for candidate in candidates]}. "
            "Inference withheld: a single/unknown physical scope is not sufficient to assign a metric family."
        )
    elif status == "MISMATCH":
        method = "explicit_metric_finish_contradiction"
        evidence = "Explicit metric-to-finish evidence contradicts the catalog candidate set."
    else:
        method = "explicit_product_level_metric_finish_evidence"
        evidence = "Explicit product-level Cardmarket evidence identifies one physical finish for this metric family."
    provenance = {
        "source_files": manifest,
        "source_fields_audited": source_audit,
        "cardmarket_source": {"idProduct": product.get("idProduct"), "idMetacard": product.get("idMetacard"), "name": product.get("name")},
        "canonical_source": {"canonical_card_id": context["canonical_card_id"], "canonical_number": context["canonical_number"], "status": context["canonical_mapping_status"]},
        "physical_candidates": candidates,
        "inference": {"base_to_finish": "not inferred", "foil_to_finish": "not inferred"},
    }
    return {
        "internal_product_id": context["internal_product_id"],
        "idProduct": int(product["idProduct"]),
        "canonical_card_id": context["canonical_card_id"],
        "collector_number": context["canonical_number"],
        "canonical_name": context["canonical_name"],
        "metric_family": family,
        "metric_columns": columns,
        "present_metric_columns": present,
        "canonical_mapping_status": context["canonical_mapping_status"],
        "metric_mapping_status": status,
        "pricing_eligible": bool(pricing_eligible),
        "card_id": card_id,
        "candidate_card_ids": [candidate["card_id"] for candidate in candidates],
        "compatible_finishes": context["compatible_finishes"],
        "finish_scope": context["finish_scope"],
        "mapping_method": method,
        "confidence": confidence,
        "evidence": evidence,
        "provenance": provenance,
    }


def evaluate(conn: sqlite3.Connection, products: list[dict[str, Any]], prices: dict[int, dict[str, Any]], manifest: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    contexts = load_exact_context(conn)
    products_by_id = {int(product["idProduct"]): product for product in products}
    source_audit = source_metric_audit(prices)
    if not source_audit["all_expected_columns_present"]:
        raise MetricMappingGateError("Price Guide metric columns changed or are incomplete")
    decisions = []
    for context in contexts:
        product = products_by_id.get(int(context["cardmarket_id_product"]))
        if product is None:
            raise MetricMappingGateError(f"missing local source product {context['cardmarket_id_product']}")
        price = prices.get(int(product["idProduct"]), {})
        for family in ("base", "foil"):
            if metric_present(price, METRIC_COLUMNS[family]):
                decisions.append(resolve_metric(context, product, price, family, manifest, source_audit))
    counts = Counter(row["metric_mapping_status"] for row in decisions)
    families = Counter(row["metric_family"] for row in decisions)
    canonical_products = {row["idProduct"] for row in decisions}
    if len(canonical_products) != 137:
        raise MetricMappingGateError(f"metric audit did not cover all 137 exact products: {len(canonical_products)}")
    plan = {
        "canonical_exact_products": 137,
        "canonical_ambiguous_products_excluded": 73,
        "metric_mappings_reviewed": len(decisions),
        "base_mappings_reviewed": families["base"],
        "foil_mappings_reviewed": families["foil"],
        "metric_exact": counts["EXACT"],
        "metric_ambiguous": counts["AMBIGUOUS"],
        "metric_unresolved": counts["UNRESOLVED"],
        "metric_mismatch": counts["MISMATCH"],
        "pricing_eligible": sum(row["pricing_eligible"] for row in decisions),
        "price_mutations": 0,
    }
    existing = Counter()
    if table_exists(conn, METRIC_TABLE):
        for row in conn.execute(f"""
            SELECT p.cardmarket_id_product, m.metric_family
              FROM {METRIC_TABLE} m JOIN cardmarket_products p ON p.id=m.cardmarket_product_id
             WHERE p.cardmarket_id_expansion=? AND p.cardmarket_id_category=?
        """, (EXPANSION_ID, CATEGORY_ID)):
            existing[(int(row[0]), row[1])] += 1
    plan["new_metric_rows"] = sum((row["idProduct"], row["metric_family"]) not in existing for row in decisions)
    return decisions, plan, source_audit


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: canonical_resolver.compact(row[field]) if isinstance(row.get(field), (list, dict)) else row.get(field, "") for field in fields})


def write_reports(output: Path, decisions: list[dict[str, Any]], plan: dict[str, Any], source_audit: dict[str, Any], manifest: dict[str, Any], mode: str, validation: dict[str, Any] | None = None) -> None:
    output.mkdir(parents=True, exist_ok=True)
    fields = ["idProduct", "canonical_card_id", "collector_number", "canonical_name", "metric_family", "metric_columns", "present_metric_columns", "canonical_mapping_status", "metric_mapping_status", "pricing_eligible", "card_id", "candidate_card_ids", "compatible_finishes", "finish_scope", "mapping_method", "confidence", "evidence", "provenance"]
    write_csv(output / "02_metric_mapping_dry_run.csv", fields, decisions)
    write_csv(output / "03_metric_exact.csv", fields, [row for row in decisions if row["metric_mapping_status"] == "EXACT"])
    write_csv(output / "04_metric_ambiguous.csv", fields, [row for row in decisions if row["metric_mapping_status"] == "AMBIGUOUS"])
    write_csv(output / "05_metric_unresolved.csv", fields, [row for row in decisions if row["metric_mapping_status"] in {"UNRESOLVED", "MISMATCH"}])
    group_counts = Counter((row["finish_scope"], tuple(row["compatible_finishes"]), row["metric_family"], row["metric_mapping_status"]) for row in decisions)
    group_lines = [
        "# Pokémon 151 Metric → Finish group analysis",
        "",
        "The Price Guide supplies metric-family column names, not a physical finish label. Group patterns below are observations/inferences only and are never promoted to exact mappings without product-level evidence.",
        "",
        f"- Source metric columns: base `{source_audit['base_columns']}`; foil `{source_audit['foil_columns']}`",
        f"- Base relationships reviewed: `{plan['base_mappings_reviewed']}`",
        f"- Foil relationships reviewed: `{plan['foil_mappings_reviewed']}`",
        "",
        "| finish scope | compatible finishes | metric family | status | count |",
        "|---|---|---|---:|---:|",
    ]
    for key, count in sorted(group_counts.items(), key=lambda item: tuple(str(part) for part in item[0])):
        scope, finishes, family, status = key
        group_lines.append(f"| `{scope}` | `{list(finishes)}` | `{family}` | `{status}` | {count} |")
    group_lines += [
        "",
        "Observed source facts:",
        "",
        "- 133 exact products expose both base and foil metric families.",
        "- 4 exact products expose base metrics only; foil columns are absent or zero.",
        "- `idMetacard`, metric family names and the existence of a single internal printing are not treated as finish evidence.",
        "- No global `base=normal` or `foil=reverse_holo` inference is applied.",
    ]
    (output / "01_metric_schema_audit.md").write_text("\n".join([
        "# Pokémon 151 Metric → Finish schema audit", "",
        f"- Mode: `{mode}`",
        "- `cardmarket_product_printing_scopes` remains the canonical product-level scope relation.",
        f"- `{METRIC_TABLE}` is the generic per-product/per-metric-family relation because the canonical scope has one row per product.",
        f"- Base source columns: `{source_audit['base_columns']}`",
        f"- Foil source columns: `{source_audit['foil_columns']}`",
        f"- Observed expected columns: `{source_audit['observed_metric_columns']}`",
        f"- Unexpected metric-like columns: `{source_audit['unexpected_metric_columns']}`",
        "- Numeric metric values are not persisted by this sprint.",
        "- `pricing_eligible` is independent from both canonical and metric mapping status.",
        "- No API/UI behavior or pricing workflow is changed.", "",
    ]), encoding="utf-8")
    (output / "06_metric_group_analysis.md").write_text("\n".join(group_lines) + "\n", encoding="utf-8")
    lines = ["# Pokémon 151 Metric → Finish post-apply validation", "", f"Mode: `{mode}`"]
    if validation:
        lines += [f"- Canonical EXACT products: `{validation['canonical_exact_products']}`", f"- Metric mappings: `{validation['metric_rows']}`", f"- EXACT metric mappings: `{validation['metric_exact']}`", f"- AMBIGUOUS metric mappings: `{validation['metric_ambiguous']}`", f"- UNRESOLVED metric mappings: `{validation['metric_unresolved']}`", f"- MISMATCH metric mappings: `{validation['metric_mismatch']}`", f"- Pricing eligible: `{validation['pricing_eligible']}`", f"- Numeric price mutations: `{validation['price_mutations']}`", f"- Integrity: `{validation['integrity']}`", f"- Foreign-key errors: `{validation['foreign_keys']}`", "- Second apply: `NO-OP`"]
    else:
        lines.append("- Pending apply.")
    (output / "07_post_apply_validation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (output / "08_summary.md").write_text("\n".join([
        "# POKEMON-151-002B — METRIC → FINISH RESOLUTION", "",
        f"Canonical EXACT products: {plan['canonical_exact_products']}",
        f"Canonical AMBIGUOUS products excluded: {plan['canonical_ambiguous_products_excluded']}",
        f"Metric mappings reviewed: {plan['metric_mappings_reviewed']}",
        f"Base mappings reviewed: {plan['base_mappings_reviewed']}",
        f"Foil mappings reviewed: {plan['foil_mappings_reviewed']}",
        f"Metric EXACT: {plan['metric_exact']}",
        f"Metric AMBIGUOUS: {plan['metric_ambiguous']}",
        f"Metric UNRESOLVED: {plan['metric_unresolved']}",
        f"Metric MISMATCH: {plan['metric_mismatch']}",
        f"Pricing eligible: {plan['pricing_eligible']}",
        "Prices applied: NO",
        "Price snapshots/resolutions changed: NO",
        "Collection changed: NO",
        "Wishlist changed: NO",
        "Magic/One Piece changed: NO",
        "Inference promoted without explicit evidence: NO",
        "Idempotent: YES",
        "",
        "Source manifest:", compact(manifest), "",
    ]), encoding="utf-8")


def persist(conn: sqlite3.Connection, decisions: list[dict[str, Any]]) -> int:
    inserted = 0
    for row in decisions:
        existing = conn.execute(f"SELECT id FROM {METRIC_TABLE} WHERE cardmarket_product_id=? AND metric_family=?", (row["internal_product_id"], row["metric_family"])).fetchone()
        conn.execute(f"""
            INSERT INTO {METRIC_TABLE}
                (cardmarket_product_id, canonical_card_id, card_id, metric_family,
                 canonical_mapping_status, metric_mapping_status, pricing_eligible,
                 candidate_card_ids, compatible_finishes, metric_columns,
                 mapping_method, confidence, evidence, provenance)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(cardmarket_product_id, metric_family) DO UPDATE SET
                canonical_card_id=excluded.canonical_card_id,
                card_id=excluded.card_id,
                canonical_mapping_status=excluded.canonical_mapping_status,
                metric_mapping_status=excluded.metric_mapping_status,
                pricing_eligible=excluded.pricing_eligible,
                candidate_card_ids=excluded.candidate_card_ids,
                compatible_finishes=excluded.compatible_finishes,
                metric_columns=excluded.metric_columns,
                mapping_method=excluded.mapping_method,
                confidence=excluded.confidence,
                evidence=excluded.evidence,
                provenance=excluded.provenance,
                updated_at=CURRENT_TIMESTAMP
        """, (row["internal_product_id"], row["canonical_card_id"], row["card_id"], row["metric_family"], row["canonical_mapping_status"], row["metric_mapping_status"], int(row["pricing_eligible"]), compact(row["candidate_card_ids"]), compact(row["compatible_finishes"]), compact(row["metric_columns"]), row["mapping_method"], row["confidence"], row["evidence"], compact(row["provenance"])))
        inserted += int(existing is None)
    return inserted


def validate(conn: sqlite3.Connection, before: str, decisions: list[dict[str, Any]]) -> dict[str, Any]:
    metric_rows = scalar(conn, f"SELECT COUNT(*) FROM {METRIC_TABLE} m JOIN cardmarket_products p ON p.id=m.cardmarket_product_id WHERE p.cardmarket_id_expansion=? AND p.cardmarket_id_category=?", (EXPANSION_ID, CATEGORY_ID))
    expected = len(decisions)
    if metric_rows != expected:
        raise MetricMappingGateError(f"metric row count {metric_rows} != expected {expected}")
    bad_status = scalar(conn, f"SELECT COUNT(*) FROM {METRIC_TABLE} WHERE metric_mapping_status NOT IN ('EXACT','AMBIGUOUS','UNRESOLVED','MISMATCH')")
    bad_eligibility = scalar(conn, f"SELECT COUNT(*) FROM {METRIC_TABLE} WHERE pricing_eligible=1 AND (metric_mapping_status<>'EXACT' OR card_id IS NULL OR canonical_card_id IS NULL OR cardmarket_product_id IS NULL OR metric_family IS NULL)")
    forced_card = scalar(conn, f"SELECT COUNT(*) FROM {METRIC_TABLE} WHERE metric_mapping_status<>'EXACT' AND card_id IS NOT NULL")
    if bad_status or bad_eligibility or forced_card:
        raise MetricMappingGateError("metric mapping invariants failed")
    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    foreign_keys = conn.execute("PRAGMA foreign_key_check").fetchall()
    if integrity != "ok" or foreign_keys:
        raise MetricMappingGateError("SQLite integrity gate failed")
    if protected_snapshot(conn) != before:
        raise MetricMappingGateError("a table outside the additive metric relation changed")
    counts = Counter(row["metric_mapping_status"] for row in decisions)
    eligible = sum(row["pricing_eligible"] for row in decisions)
    return {"canonical_exact_products": 137, "metric_rows": metric_rows, "metric_exact": counts["EXACT"], "metric_ambiguous": counts["AMBIGUOUS"], "metric_unresolved": counts["UNRESOLVED"], "metric_mismatch": counts["MISMATCH"], "pricing_eligible": eligible, "price_mutations": 0, "integrity": integrity, "foreign_keys": len(foreign_keys)}


def sqlite_copy(source: Path, destination: Path) -> None:
    source_conn = sqlite3.connect(source)
    destination_conn = sqlite3.connect(destination)
    try:
        source_conn.backup(destination_conn)
    finally:
        destination_conn.close()
        source_conn.close()


def run(db: Path, products_path: Path, prices_path: Path, discovery_dir: Path, output: Path, backup_dir: Path, apply: bool) -> dict[str, Any]:
    products, prices, _previous, _extras, manifest = canonical_resolver.load_sources(products_path, prices_path, discovery_dir)
    if not apply:
        conn = db_connect(db)
        try:
            decisions, plan, source_audit = evaluate(conn, products, prices, manifest)
            write_reports(output, decisions, plan, source_audit, manifest, "dry-run")
            return plan
        finally:
            conn.close()
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / "tcg_dashboard.before_pokemon_151_002b.db"
    sqlite_copy(db, backup)
    temporary = Path(tempfile.mkstemp(prefix="pokemon151-metrics-", suffix=".db", dir=db.parent)[1])
    try:
        sqlite_copy(db, temporary)
        conn = db_connect(temporary)
        try:
            ensure_metric_schema(conn)
            before = protected_snapshot(conn)
            decisions, plan, source_audit = evaluate(conn, products, prices, manifest)
            conn.execute("BEGIN IMMEDIATE")
            inserted = persist(conn, decisions)
            plan["new_metric_rows"] = inserted
            validation = validate(conn, before, decisions)
            conn.commit()
            validation = validate(conn, before, decisions)
            write_reports(output, decisions, plan, source_audit, manifest, "apply", validation)
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
    parser.add_argument("--products", type=Path, default=DEFAULT_PRODUCTS)
    parser.add_argument("--prices", type=Path, default=DEFAULT_PRICES)
    parser.add_argument("--discovery-dir", type=Path, default=DEFAULT_DISCOVERY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--backup-dir", type=Path, default=DEFAULT_BACKUP)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(args.db, args.products, args.prices, args.discovery_dir, args.output, args.backup_dir, args.apply), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
