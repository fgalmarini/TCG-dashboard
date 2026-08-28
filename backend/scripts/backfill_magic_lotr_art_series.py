"""Promote verified Magic LOTR Art Series legacy cards in place.

The script is deliberately local-only: CardTrader data is read from a JSON
export and existing card_images metadata is used as a secondary signal.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sqlite3
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = REPO_ROOT / "backend" / "db" / "tcg_dashboard.db"
CARDTRADER_COLLECTOR_RE = re.compile(r"^A\d+[a-z]?$", re.IGNORECASE)


@dataclass(frozen=True)
class VariantEvidence:
    source: str
    variant: str
    source_variant: str
    source_collector_number: str | None = None


@dataclass
class BackfillReport:
    products_seen: int = 0
    cards_promoted: int = 0
    cards_changed: int = 0
    cards_created: int = 0
    rows_skipped: int = 0
    normal: int = 0
    gold_stamped: int = 0
    finish_null_after: int = 0
    collection_rows_relinked: int = 0
    ambiguous: list[dict[str, str]] = field(default_factory=list)
    missing_art_numbers: list[str] = field(default_factory=list)


@dataclass
class CollectionGoldReport:
    collection_rows: int = 0
    distinct_cards: int = 0
    cards_changed: int = 0
    cards_created: int = 0
    current_normal: int = 0
    current_gold_stamped: int = 0
    unmatched: int = 0
    legacy_card_links: int = 0
    audit_rows: list[dict[str, Any]] = field(default_factory=list)
    invalid_rows: list[dict[str, str]] = field(default_factory=list)


def _normalise_name(value: str) -> str:
    return " ".join(value.casefold().split())


def _load_cardtrader_export(path: Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        blueprints = payload
    elif isinstance(payload, dict):
        blueprints = next(
            (payload[key] for key in ("array", "blueprints", "data")
             if isinstance(payload.get(key), list)),
            None,
        )
    else:
        blueprints = None
    if not isinstance(blueprints, list) or not all(isinstance(item, dict) for item in blueprints):
        raise ValueError("CardTrader export debe ser una lista de blueprints JSON")
    return blueprints


def _blueprint_product_ids(blueprint: dict[str, Any]) -> Iterable[str]:
    values = blueprint.get("card_market_ids") or blueprint.get("cardmarket_ids") or []
    if isinstance(values, (str, int)):
        values = [values]
    for value in values:
        if value is not None:
            yield str(value)


def _blueprint_evidence(blueprint: dict[str, Any]) -> VariantEvidence | None:
    version = str(blueprint.get("version") or "").strip()
    fixed = blueprint.get("fixed_properties") or {}
    collector = str(fixed.get("collector_number") or blueprint.get("collector_number") or "").strip()
    is_gold = version.casefold() == "gold-stamped" or collector.casefold().endswith("g")
    if is_gold:
        return VariantEvidence("cardtrader_export", "gold_stamped", "art_series_gold_stamped", collector or None)
    if version or CARDTRADER_COLLECTOR_RE.fullmatch(collector):
        return VariantEvidence("cardtrader_export", "normal", "art_series", collector or None)
    return None


def _export_evidence(blueprints: list[dict[str, Any]], external_id: str) -> VariantEvidence | str | None:
    matches = [blueprint for blueprint in blueprints if external_id in set(_blueprint_product_ids(blueprint))]
    identifiers = {str(item.get("id")) for item in matches}
    identifiers.discard("None")
    if len(identifiers) > 1:
        return "cardtrader_export_multiple_blueprints"
    if not matches:
        return None
    evidence = _blueprint_evidence(matches[0])
    return evidence or "cardtrader_export_missing_variant_metadata"


def _image_evidence(conn: sqlite3.Connection, card_id: int) -> VariantEvidence | str | None:
    rows = conn.execute(
        """
        SELECT source_variant, source_collector_number
        FROM card_images
        WHERE card_id = ?
          AND lower(COALESCE(source, '')) = 'cardtrader'
          AND lower(COALESCE(status, '')) = 'resolved'
          AND lower(COALESCE(match_quality, '')) = 'exact'
        """,
        (card_id,),
    ).fetchall()
    variants: set[str] = set()
    selected: tuple[str, str | None] | None = None
    for row in rows:
        source_variant = str(row[0] or "").strip()
        collector = str(row[1] or "").strip()
        gold = source_variant.casefold() == "gold-stamped" or collector.casefold().endswith("g")
        if gold:
            variants.add("gold_stamped")
            selected = ("art_series_gold_stamped", collector or None)
        elif source_variant or CARDTRADER_COLLECTOR_RE.fullmatch(collector):
            variants.add("normal")
            if selected is None:
                selected = ("art_series", collector or None)
    if len(variants) > 1:
        return "card_images_conflicting_variant_metadata"
    if not selected:
        return None
    variant, collector = selected
    return VariantEvidence("card_images", "gold_stamped" if variant.endswith("gold_stamped") else "normal", variant, collector)


def _connect_readonly(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _connect_rw(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _art_series_rows(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT
            p.id AS product_pk,
            CAST(p.cardmarket_id_product AS TEXT) AS external_product_id,
            p.raw_name,
            m.card_id AS mapped_card_id,
            m.status AS mapping_status,
            c.id AS card_id,
            c.name,
            c.card_number,
            c.catalog_status,
            c.finish,
            c.release_kind,
            c.art_kind,
            c.printing_variant,
            c.variant_label,
            c.treatment,
            c.source_variant,
            c.catalog_source,
            c.normalized_name,
            c.set_code,
            c.game_id,
            e.cardmarket_id_expansion AS expansion_external_id
        FROM cardmarket_products p
        LEFT JOIN cardmarket_product_mappings m ON m.cardmarket_product_id = p.id
        LEFT JOIN cards c ON c.id = m.card_id
        LEFT JOIN expansions e ON e.id = c.expansion_id
        WHERE p.cardmarket_id_expansion = 5308
          AND p.raw_name LIKE 'Art Series%'
        ORDER BY p.id
        """
    ).fetchall()


def _validate_product_card_pairs(rows: list[sqlite3.Row]) -> tuple[list[sqlite3.Row], list[tuple[sqlite3.Row, str]]]:
    valid: list[sqlite3.Row] = []
    invalid: list[tuple[sqlite3.Row, str]] = []
    by_product: dict[int, list[sqlite3.Row]] = {}
    by_card: dict[int, list[sqlite3.Row]] = {}
    for row in rows:
        by_product.setdefault(row["product_pk"], []).append(row)
        if row["card_id"] is not None:
            by_card.setdefault(row["card_id"], []).append(row)
    invalid_product_ids: set[int] = set()
    for product_pk, product_rows in by_product.items():
        cards = {row["card_id"] for row in product_rows if row["card_id"] is not None}
        statuses = {row["mapping_status"] for row in product_rows}
        if len(product_rows) != 1 or len(cards) != 1 or statuses != {"mapped"}:
            invalid_product_ids.add(product_pk)
            invalid.append((product_rows[0], "product_card_mapping_not_one_to_one"))
    for card_id, card_rows in by_card.items():
        if len({row["product_pk"] for row in card_rows}) != 1:
            for row in card_rows:
                invalid_product_ids.add(row["product_pk"])
                invalid.append((row, "card_has_multiple_art_series_products"))
    for row in rows:
        if row["product_pk"] in invalid_product_ids:
            continue
        if row["game_id"] != 3 or row["expansion_external_id"] != 5308 or row["set_code"] != "ltr":
            invalid.append((row, "not_magic_lotr_art_series_card"))
            continue
        valid.append(row)
    return valid, invalid


def _desired_values(evidence: VariantEvidence) -> dict[str, str]:
    gold = evidence.variant == "gold_stamped"
    return {
        "catalog_status": "active",
        "finish": "nonfoil",
        "release_kind": "special",
        "art_kind": "special",
        "treatment": "Art Series Gold-Stamped" if gold else "Art Series",
        "source_variant": "art_series_gold_stamped" if gold else "art_series",
        "catalog_source": "cardmarket",
        "printing_variant": "other" if gold else "normal",
        "variant_label": "Gold-Stamped" if gold else "Art Series",
    }


def process_database(
    conn: sqlite3.Connection,
    *,
    apply: bool,
    cardtrader_export: list[dict[str, Any]] | None = None,
) -> BackfillReport:
    report = BackfillReport()
    rows = _art_series_rows(conn)
    report.products_seen = len(rows)
    valid, invalid = _validate_product_card_pairs(rows)
    for row, reason in invalid:
        report.rows_skipped += 1
        report.ambiguous.append({"product_id": str(row["external_product_id"]), "reason": reason})

    export = cardtrader_export or []
    promoted_card_ids: list[int] = []
    seen_cards: set[int] = set()
    for row in valid:
        card_id = int(row["card_id"])
        if card_id in seen_cards:
            continue
        seen_cards.add(card_id)
        evidence = _export_evidence(export, str(row["external_product_id"])) if export else None
        if evidence is None:
            evidence = _image_evidence(conn, card_id)
        if not isinstance(evidence, VariantEvidence):
            report.rows_skipped += 1
            report.ambiguous.append({
                "product_id": str(row["external_product_id"]),
                "reason": evidence or "variant_not_verified",
            })
            continue
        desired = _desired_values(evidence)
        changed = any(row[field] != value for field, value in desired.items())
        if apply:
            conn.execute(
                """
                UPDATE cards
                SET catalog_status = ?, finish = ?, release_kind = ?, art_kind = ?,
                    treatment = ?, source_variant = ?, catalog_source = ?,
                    printing_variant = ?, variant_label = ?, normalized_name = ?
                WHERE id = ?
                """,
                (
                    desired["catalog_status"], desired["finish"], desired["release_kind"],
                    desired["art_kind"], desired["treatment"], desired["source_variant"],
                    desired["catalog_source"], desired["printing_variant"],
                    desired["variant_label"], _normalise_name(row["name"]), card_id,
                ),
            )
        report.cards_promoted += 1
        report.cards_changed += int(changed)
        promoted_card_ids.append(card_id)
        if evidence.variant == "gold_stamped":
            report.gold_stamped += 1
        else:
            report.normal += 1
        if not row["card_number"]:
            report.missing_art_numbers.append(str(row["external_product_id"]))

    if promoted_card_ids:
        placeholders = ",".join("?" for _ in promoted_card_ids)
        query = f"""
            SELECT COUNT(*)
            FROM collection_items
            WHERE card_id IN ({placeholders}) AND match_status = 'unmatched'
        """
        report.collection_rows_relinked = int(conn.execute(query, promoted_card_ids).fetchone()[0])
        if apply:
            conn.execute(
                f"""
                UPDATE collection_items
                SET match_status = 'exact', match_quality = 'manual', match_reason = 'art_series_backfill'
                WHERE card_id IN ({placeholders}) AND match_status = 'unmatched'
                """,
                promoted_card_ids,
            )
    report.finish_null_after = int(conn.execute(
        """
        SELECT COUNT(*)
        FROM cards c
        JOIN expansions e ON e.id = c.expansion_id
        WHERE e.cardmarket_id_expansion = 5308 AND c.name LIKE 'Art Series%' AND c.finish IS NULL
        """
    ).fetchone()[0])
    return report


def _collection_art_series_rows(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT
            ci.id AS collection_item_id,
            ci.card_id,
            ci.cardmarket_product_id,
            p.cardmarket_id_product,
            c.name,
            c.card_number,
            c.catalog_status,
            c.finish,
            c.treatment,
            c.source_variant,
            c.catalog_source,
            ci.match_status,
            i.image_sources,
            CASE WHEN m.status = 'mapped' AND m.card_id = c.id THEN 1 ELSE 0 END AS exact_mapping,
            g.code AS game_code,
            e.cardmarket_id_expansion
        FROM collection_items ci
        JOIN cards c ON c.id = ci.card_id
        JOIN expansions e ON e.id = c.expansion_id
        JOIN games g ON g.id = c.game_id
        LEFT JOIN cardmarket_products p ON p.id = ci.cardmarket_product_id
        LEFT JOIN cardmarket_product_mappings m ON m.cardmarket_product_id = ci.cardmarket_product_id
        LEFT JOIN (
            SELECT card_id, GROUP_CONCAT(DISTINCT source || ':' || match_quality) AS image_sources
            FROM card_images
            WHERE status = 'resolved'
            GROUP BY card_id
        ) i ON i.card_id = c.id
        WHERE g.code = 'magic'
          AND e.cardmarket_id_expansion = 5308
          AND c.name LIKE 'Art Series:%'
        ORDER BY ci.id
        """
    ).fetchall()


def process_collection_art_series_gold(
    conn: sqlite3.Connection,
    *,
    apply: bool,
) -> CollectionGoldReport:
    """Apply the user's physical Gold-Stamped confirmation only to owned rows."""
    rows = _collection_art_series_rows(conn)
    report = CollectionGoldReport(collection_rows=len(rows))
    report.distinct_cards = len({row["card_id"] for row in rows})
    report.current_normal = sum(
        row["treatment"] == "Art Series" or row["source_variant"] == "art_series"
        for row in rows
    )
    report.current_gold_stamped = sum(
        row["treatment"] == "Art Series Gold-Stamped"
        or row["source_variant"] == "art_series_gold_stamped"
        for row in rows
    )
    report.unmatched = sum(row["match_status"] != "exact" for row in rows)
    report.legacy_card_links = sum(row["catalog_status"] == "legacy" for row in rows)

    for row in rows:
        audit = {key: row[key] for key in row.keys()}
        report.audit_rows.append(audit)
        reasons: list[str] = []
        if row["card_id"] is None or not str(row["name"] or "").casefold().startswith("art series:"):
            reasons.append("card_not_art_series")
        if row["game_code"] != "magic" or row["cardmarket_id_expansion"] != 5308:
            reasons.append("not_magic_lotr")
        if row["cardmarket_product_id"] is not None and row["exact_mapping"] != 1:
            reasons.append("cardmarket_mapping_not_exact")
        if row["match_status"] != "exact":
            reasons.append("collection_not_matched")
        if reasons:
            report.invalid_rows.append({"collection_item_id": str(row["collection_item_id"]), "reason": ",".join(reasons)})

    if report.invalid_rows:
        raise RuntimeError(
            "Auditoría bloqueada: existen filas Collection Art Series no vinculadas correctamente: "
            + "; ".join(f"{item['collection_item_id']}={item['reason']}" for item in report.invalid_rows)
        )

    card_ids = sorted({int(row["card_id"]) for row in rows})
    if not card_ids:
        raise RuntimeError("Auditoría bloqueada: no se encontraron Art Series en Collection")
    placeholders = ",".join("?" for _ in card_ids)
    report.cards_changed = sum(
        any(row[field] != value for field, value in {
            "treatment": "Art Series Gold-Stamped",
            "source_variant": "art_series_gold_stamped",
            "finish": "nonfoil",
            "catalog_status": "active",
            "catalog_source": "cardmarket",
        }.items())
        for row in rows
    )
    if apply:
        conn.execute(
            f"""
            UPDATE cards
            SET treatment = 'Art Series Gold-Stamped',
                source_variant = 'art_series_gold_stamped',
                finish = 'nonfoil',
                catalog_status = 'active',
                catalog_source = 'cardmarket'
            WHERE id IN ({placeholders})
            """,
            card_ids,
        )
    return report


def validate_database(db_path: Path) -> tuple[bool, str, list[tuple[Any, ...]]]:
    conn = _connect_readonly(db_path)
    try:
        integrity = str(conn.execute("PRAGMA integrity_check").fetchone()[0])
        foreign_keys = [tuple(row) for row in conn.execute("PRAGMA foreign_key_check").fetchall()]
        return integrity == "ok" and not foreign_keys, integrity, foreign_keys
    finally:
        conn.close()


def _run_dry_run(db_path: Path, export_path: Path | None) -> BackfillReport:
    conn = _connect_readonly(db_path)
    try:
        return process_database(conn, apply=False, cardtrader_export=_load_cardtrader_export(export_path))
    finally:
        conn.close()


def _run_safe_apply(db_path: Path, export_path: Path | None) -> BackfillReport:
    export = _load_cardtrader_export(export_path)
    with tempfile.TemporaryDirectory(prefix="magic-art-series-") as temp_dir:
        work_db = Path(temp_dir) / db_path.name
        shutil.copy2(db_path, work_db)
        conn = _connect_rw(work_db)
        try:
            conn.execute("BEGIN IMMEDIATE")
            report = process_database(conn, apply=True, cardtrader_export=export)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        valid, integrity, foreign_keys = validate_database(work_db)
        if not valid:
            raise RuntimeError(f"La copia no superó las validaciones: integrity={integrity}, foreign_keys={foreign_keys}")

        backup_dir = REPO_ROOT / "backups" / "catalog"
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backup_path = backup_dir / f"{db_path.stem}-before-art-series-{stamp}{db_path.suffix}"
        shutil.copy2(db_path, backup_path)
        shutil.copy2(work_db, db_path)
        valid, integrity, foreign_keys = validate_database(db_path)
        if not valid:
            shutil.copy2(backup_path, db_path)
            raise RuntimeError(f"La DB real no superó las validaciones y fue restaurada: integrity={integrity}, foreign_keys={foreign_keys}")
        return report


def _run_collection_gold_dry_run(db_path: Path) -> CollectionGoldReport:
    conn = _connect_readonly(db_path)
    try:
        return process_collection_art_series_gold(conn, apply=False)
    finally:
        conn.close()


def _run_safe_collection_gold_apply(db_path: Path) -> CollectionGoldReport:
    with tempfile.TemporaryDirectory(prefix="magic-art-series-gold-") as temp_dir:
        work_db = Path(temp_dir) / db_path.name
        shutil.copy2(db_path, work_db)
        conn = _connect_rw(work_db)
        try:
            conn.execute("BEGIN IMMEDIATE")
            report = process_collection_art_series_gold(conn, apply=True)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        valid, integrity, foreign_keys = validate_database(work_db)
        if not valid:
            raise RuntimeError(f"La copia no superó las validaciones: integrity={integrity}, foreign_keys={foreign_keys}")

        backup_dir = REPO_ROOT / "backups" / "catalog"
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backup_path = backup_dir / f"{db_path.stem}-before-art-series-gold-{stamp}{db_path.suffix}"
        shutil.copy2(db_path, backup_path)
        shutil.copy2(work_db, db_path)
        valid, integrity, foreign_keys = validate_database(db_path)
        if not valid:
            shutil.copy2(backup_path, db_path)
            raise RuntimeError(f"La DB real no superó las validaciones y fue restaurada: integrity={integrity}, foreign_keys={foreign_keys}")
        return report


def _print_report(report: BackfillReport, mode: str) -> None:
    print(f"mode={mode}")
    print(f"Art Series products={report.products_seen}")
    print(f"cards promoted={report.cards_promoted}")
    print(f"cards changed={report.cards_changed}")
    print(f"cards created={report.cards_created}")
    print(f"normal={report.normal}")
    print(f"gold-stamped={report.gold_stamped}")
    print(f"collection rows relinked={report.collection_rows_relinked}")
    print(f"finish NULL after={report.finish_null_after}")
    print(f"ambiguous={len(report.ambiguous)}")
    if report.missing_art_numbers:
        print(f"missing ART-n evidence={len(report.missing_art_numbers)}")
    for item in report.ambiguous:
        print(f"AMBIGUOUS product={item['product_id']} reason={item['reason']}")


def _print_collection_gold_report(report: CollectionGoldReport, mode: str) -> None:
    print(f"mode={mode}")
    print(f"Collection Art Series total={report.collection_rows}")
    print(f"Collection distinct cards={report.distinct_cards}")
    print(f"Collection Art Series current normal={report.current_normal}")
    print(f"Collection Art Series current Gold-Stamped={report.current_gold_stamped}")
    print(f"Collection Art Series unmatched={report.unmatched}")
    print(f"Collection Art Series legacy links={report.legacy_card_links}")
    print(f"cards changed={report.cards_changed}")
    print(f"cards created={report.cards_created}")
    print("target treatment=Art Series Gold-Stamped")
    print("target source_variant=art_series_gold_stamped")
    for row in report.audit_rows:
        print(
            "AUDIT "
            f"collection_item_id={row['collection_item_id']} card_id={row['card_id']} "
            f"cardmarket_product_id={row['cardmarket_product_id']} "
            f"name={row['name']!r} card_number={row['card_number']!r} "
            f"catalog_status={row['catalog_status']} finish={row['finish']} "
            f"treatment={row['treatment']!r} source_variant={row['source_variant']!r} "
            f"catalog_source={row['catalog_source']!r} match_status={row['match_status']} "
            f"images={row['image_sources']!r}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--collection-art-series-gold-stamped",
        action="store_true",
        help="Reclasifica únicamente las Art Series vinculadas a Collection como Gold-Stamped",
    )
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--cardtrader-export", type=Path)
    args = parser.parse_args(argv)
    if not args.db.exists():
        parser.error(f"DB no encontrada: {args.db}")
    try:
        if args.collection_art_series_gold_stamped and args.dry_run:
            report = _run_collection_gold_dry_run(args.db)
            _print_collection_gold_report(report, "collection-gold-dry-run")
        elif args.collection_art_series_gold_stamped:
            report = _run_safe_collection_gold_apply(args.db)
            _print_collection_gold_report(report, "collection-gold-apply")
        elif args.dry_run:
            report = _run_dry_run(args.db, args.cardtrader_export)
            _print_report(report, "dry-run")
        else:
            report = _run_safe_apply(args.db, args.cardtrader_export)
            _print_report(report, "apply")
    except (OSError, ValueError, sqlite3.Error, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
