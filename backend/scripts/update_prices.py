"""Apply validated Cardmarket pricing resolutions safely."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import tempfile
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.scripts import audit_pricing as audit
import downloader

DEFAULT_DB_PATH = REPO_ROOT / "backend" / "db" / "tcg_dashboard.db"
LOG_DIR = REPO_ROOT / "logs" / "pricing"
BACKUP_DIR = REPO_ROOT / "backups" / "pricing"
SUPPORTED_GAMES = ("magic", "one_piece")
EXPECTED_TABLES = {"games", "languages", "cards", "cardmarket_products", "cardmarket_product_mappings", "market_price_history", "printing_external_ids", "printing_price_resolutions", "collection_items", "wishlist_items"}


class WorkflowError(RuntimeError):
    exit_code = 1


class LockError(WorkflowError):
    pass


@dataclass
class ScopeWork:
    """A resolved work universe plus the write targets permitted for it."""

    scope: str
    wishlist_status: str = "wanted"
    rows_by_game: dict[str, list[dict]] = field(default_factory=dict)
    cards: dict[int, dict] = field(default_factory=dict)
    allowed_collection_ids: set[int] = field(default_factory=set)
    allowed_wishlist_ids: set[int] = field(default_factory=set)


@dataclass
class GameReport:
    game: str
    scope: str = "all"
    printings_checked: int = 0
    exact: int = 0
    ambiguous: int = 0
    mismatch: int = 0
    missing: int = 0
    unpriced: int = 0
    low_available: int = 0
    trend_available: int = 0
    avg7_available: int = 0
    identity_mismatches_prevented: int = 0
    prices_changed: int = 0
    prices_unchanged: int = 0
    history_rows_inserted: int = 0
    history_rows_skipped: int = 0
    collection_items: int = 0
    collection_units: int = 0
    collection_exact_item_coverage: float | None = None
    collection_exact_unit_coverage: float | None = None
    collection_legacy_value: float | None = None
    collection_low_value: float | None = None
    collection_value_coverage: float | None = None
    collection_value_without_exact: float | None = None
    collection_dealer_cash: float | None = None
    collection_dealer_cash_min: float | None = None
    collection_dealer_cash_max: float | None = None
    collection_trade_value: float | None = None
    collection_trade_value_min: float | None = None
    collection_trade_value_max: float | None = None
    wishlist_items: int = 0
    wishlist_units: int = 0
    wishlist_status: str | None = None
    wishlist_exact_item_coverage: float | None = None
    wishlist_exact_unit_coverage: float | None = None
    wishlist_legacy_value: float | None = None
    wishlist_resolved_low_value: float | None = None
    wishlist_estimated_value_coverage: float | None = None
    wishlist_value_without_exact: float | None = None
    write_candidates: int = 0
    current_pricing_changes: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def cardmarket_exact(self) -> int:
        return self.exact

    @property
    def updated(self) -> int:
        return self.prices_changed

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class WorkflowReport:
    mode: str
    scope: str
    games: tuple[str, ...]
    database: str
    started_at: str
    result: str = "FAILED"
    transaction: str = "NOT_STARTED"
    backup: str | None = None
    integrity: str = "NOT_RUN"
    foreign_keys: str = "NOT_RUN"
    providers: dict[str, str] = field(default_factory=dict)
    snapshots: dict[str, str] = field(default_factory=dict)
    source_manifest_id: str | None = None
    current_state_audit: dict[str, str] = field(default_factory=dict)
    proposed_state_validation: dict[str, str] = field(default_factory=dict)
    post_apply_validation: dict[str, str] = field(default_factory=dict)
    game_reports: dict[str, GameReport] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    collection_wishlist_unchanged: bool | None = None
    wishlist_status: str = "wanted"
    duration_seconds: float | None = None

    def to_dict(self) -> dict:
        return {"timestamp": self.started_at, "mode": self.mode, "scope": self.scope, "wishlist_status": self.wishlist_status, "games": list(self.games), "database": self.database, "providers": self.providers, "snapshots": self.snapshots, "source_manifest_id": self.source_manifest_id, "current_state_audit": self.current_state_audit, "proposed_state_validation": self.proposed_state_validation, "post_apply_validation": self.post_apply_validation, "printings": {k: v.to_dict() for k, v in self.game_reports.items()}, "transaction": self.transaction, "backup": self.backup, "integrity": self.integrity, "foreign_keys": self.foreign_keys, "collection_wishlist_unchanged": self.collection_wishlist_unchanged, "errors": self.errors, "result": self.result, "duration_seconds": self.duration_seconds}


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="microseconds")


def _connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=0")
    return conn


def _validate_database(conn: sqlite3.Connection) -> tuple[str, str]:
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    missing = sorted(EXPECTED_TABLES - tables)
    if missing:
        raise WorkflowError(f"Database is missing expected tables: {', '.join(missing)}")
    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        raise WorkflowError(f"PRAGMA integrity_check failed: {integrity}")
    foreign_keys = conn.execute("PRAGMA foreign_key_check").fetchall()
    if foreign_keys:
        raise WorkflowError(f"PRAGMA foreign_key_check failed with {len(foreign_keys)} rows")
    configured = {row[0] for row in conn.execute("SELECT code FROM games")}
    missing_games = sorted(set(SUPPORTED_GAMES) - configured)
    if missing_games:
        raise WorkflowError(f"Database is missing configured games: {', '.join(missing_games)}")
    _validate_resolution_scope_invariants(conn)
    return integrity, "ok"


def _validate_resolution_scope_invariants(conn: sqlite3.Connection) -> None:
    """Reject rows that mix global, Collection and Wishlist targets."""
    columns = {row[1] for row in conn.execute("PRAGMA table_info(printing_price_resolutions)")}
    if "wishlist_item_id" not in columns:
        return
    rows = conn.execute(
        """SELECT id, resolution_scope, collection_item_id, wishlist_item_id
             FROM printing_price_resolutions ORDER BY id"""
    ).fetchall()
    failures: list[str] = []
    for row in rows:
        scope = row["resolution_scope"] or "global"
        collection_id = row["collection_item_id"]
        wishlist_id = row["wishlist_item_id"]
        valid = (
            (scope == "global" and collection_id is None and wishlist_id is None)
            or (scope == "collection" and collection_id is not None and wishlist_id is None)
            or (scope == "wishlist" and collection_id is None and wishlist_id is not None)
        )
        if not valid:
            failures.append(
                f"resolution {row['id']}: scope={scope}, collection_item_id={collection_id}, wishlist_item_id={wishlist_id}"
            )
    if failures:
        raise WorkflowError("Resolution scope invariants failed: " + "; ".join(failures[:20]))


def ensure_pricing_schema(conn: sqlite3.Connection) -> None:
    additions = {
        "market_price_history": {"source": "TEXT NOT NULL DEFAULT 'cardmarket'", "source_currency": "TEXT NOT NULL DEFAULT 'EUR'", "source_snapshot_created_at": "TEXT", "source_snapshot_sha256": "TEXT", "source_manifest_id": "TEXT", "provenance": "TEXT"},
        "printing_price_resolutions": {"cardmarket_product_id": "INTEGER REFERENCES cardmarket_products(id)", "collection_item_id": "INTEGER REFERENCES collection_items(id)", "wishlist_item_id": "INTEGER REFERENCES wishlist_items(id)", "resolution_scope": "TEXT NOT NULL DEFAULT 'global' CHECK (resolution_scope IN ('global','collection','wishlist'))", "match_status": "TEXT", "is_current": "INTEGER NOT NULL DEFAULT 0", "selected_metric": "TEXT", "cardmarket_low": "REAL", "cardmarket_trend": "REAL", "cardmarket_avg1": "REAL", "cardmarket_avg7": "REAL", "cardmarket_avg30": "REAL", "cardmarket_foil_low": "REAL", "cardmarket_foil_trend": "REAL", "cardmarket_foil_avg1": "REAL", "cardmarket_foil_avg7": "REAL", "cardmarket_foil_avg30": "REAL", "source_currency": "TEXT", "source_snapshot_created_at": "TEXT", "source_snapshot_sha256": "TEXT", "source_manifest_id": "TEXT", "provenance": "TEXT"},
    }
    for table, fields in additions.items():
        existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
        for name, definition in fields.items():
            if name not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")
    conn.execute("CREATE TABLE IF NOT EXISTS collection_price_overrides (id INTEGER PRIMARY KEY AUTOINCREMENT, collection_item_id INTEGER NOT NULL REFERENCES collection_items(id), card_id INTEGER NOT NULL REFERENCES cards(id), language_id INTEGER NOT NULL REFERENCES languages(id), cardmarket_product_id INTEGER NOT NULL REFERENCES cardmarket_products(id), match_status TEXT NOT NULL CHECK (match_status = 'EXACT'), approved INTEGER NOT NULL CHECK (approved IN (0,1)), row_hash TEXT NOT NULL, source_manifest_id TEXT NOT NULL, evidence TEXT NOT NULL, provenance TEXT NOT NULL, is_current INTEGER NOT NULL DEFAULT 1 CHECK (is_current IN (0,1)), created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE(collection_item_id, row_hash))")
    # Recreate this index so databases migrated by the previous global-only
    # version cannot accidentally constrain Collection-scoped rows.
    conn.execute("DROP INDEX IF EXISTS idx_printing_price_current_identity")
    conn.execute("DROP INDEX IF EXISTS idx_collection_price_current_identity")
    conn.execute("DROP INDEX IF EXISTS idx_wishlist_price_current_item")
    conn.execute("CREATE UNIQUE INDEX idx_printing_price_current_identity ON printing_price_resolutions (card_id, language_id, COALESCE(source, 'cardmarket')) WHERE is_current = 1 AND collection_item_id IS NULL AND wishlist_item_id IS NULL")
    conn.execute("CREATE UNIQUE INDEX idx_collection_price_current_identity ON printing_price_resolutions (collection_item_id, COALESCE(source, 'cardmarket')) WHERE is_current = 1 AND collection_item_id IS NOT NULL AND wishlist_item_id IS NULL")
    conn.execute("CREATE UNIQUE INDEX idx_wishlist_price_current_item ON printing_price_resolutions (wishlist_item_id, COALESCE(source, 'cardmarket')) WHERE is_current = 1 AND wishlist_item_id IS NOT NULL AND collection_item_id IS NULL")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_collection_override_current ON collection_price_overrides (collection_item_id) WHERE is_current = 1 AND approved = 1")


def _personal_snapshot(conn: sqlite3.Connection) -> str:
    digest = hashlib.sha256()
    for table in ("collection_items", "wishlist_items"):
        columns = [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]
        digest.update(table.encode() + b"\0".join(column.encode() for column in columns))
        for row in conn.execute(f"SELECT * FROM {table} ORDER BY id"):
            digest.update(json.dumps(tuple(row), default=str, separators=(",", ":")).encode() + b"\n")
    return digest.hexdigest()


def _mapping_snapshot(conn: sqlite3.Connection) -> list[tuple]:
    return [tuple(row) for row in conn.execute("SELECT * FROM cardmarket_product_mappings ORDER BY id")]


def _load_sources(source_dir: Path | None, games: tuple[str, ...], conn: sqlite3.Connection, audited_at: str, download_fn: Callable | None, report: WorkflowReport):
    if source_dir is None:
        try:
            results = (download_fn or downloader.download_all)(games=games)
        except Exception as exc:
            raise WorkflowError(f"Cardmarket source download failed: {exc}") from exc
        paths = [Path(item.path) for item in results.values() if getattr(item, "path", None)]
        source_dir = Path(os.path.commonpath([str(path) for path in paths])) if paths else REPO_ROOT / "price-history"
        failures = [f"{key}: {item.error}" for key, item in results.items() if not item.ok]
        if failures:
            raise WorkflowError("Cardmarket source unavailable: " + "; ".join(failures))
    snapshots, manifest = audit.load_snapshots(source_dir, games, conn, audited_at)
    stable = {"sources": [{k: value for k, value in item.items() if k != "audit_timestamp"} for item in manifest["sources"]]}
    manifest["manifest_id"] = hashlib.sha256(json.dumps(stable, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    report.source_manifest_id = manifest["manifest_id"]
    for game in games:
        report.providers[f"cardmarket:{game}"] = "ok"
        for kind in audit.SOURCE_KINDS:
            report.snapshots[f"cardmarket:{game}:{kind}"] = snapshots[game][kind].created_at
    return snapshots, manifest


def _load_collection_review(path: Path | None) -> list[dict]:
    if path is None:
        return []
    if not path.is_file():
        raise WorkflowError(f"Collection review file does not exist: {path.resolve()}")
    import csv
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _review_printing_ids(path: Path | None) -> set[int]:
    """Return explicitly approved target printings needed by Collection reviews."""
    return {
        int(row["printing_id"])
        for row in _load_collection_review(path)
        if str(row.get("printing_id") or "").strip().isdigit()
    }


def _cardmarket_ids_for_card(conn: sqlite3.Connection, card_id: int) -> set[int]:
    rows = conn.execute(
        """SELECT external_id FROM printing_external_ids
            WHERE card_id=? AND source='cardmarket_product'""",
        (card_id,),
    ).fetchall()
    return {int(row[0]) for row in rows if str(row[0]).strip().isdigit()}


def _validate_review_target(row: dict, card: dict, item_id: int) -> None:
    """Ensure a manual target is the same physical identity, not a name-only match."""
    checks = (
        ("game", row.get("game"), card.get("game")),
        ("card name", audit.normalize(row.get("card_name")), audit.normalize(card.get("name"))),
        ("card number", audit.normalize_number(row.get("card_number")), audit.normalize_number(card.get("card_number"))),
        ("set", audit.normalize(row.get("local_set_code")), audit.normalize(card.get("resolved_set_code") or card.get("set_code"))),
        ("language", audit.normalize(row.get("language")), audit.normalize(card.get("language"))),
    )
    for label, expected, actual in checks:
        if expected and actual and expected != actual:
            raise WorkflowError(f"Collection review target printing does not match item {item_id}: {label}")


def _existing_collection_reviews(conn: sqlite3.Connection, rows_by_game: dict[str, list[dict]], snapshots: dict, manifest: dict) -> list[dict]:
    if not rows_by_game:
        return []
    table = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='collection_price_overrides'").fetchone()
    if table is None:
        return []
    rows_by_item = {int(row["collection_item_id"]): row for rows in rows_by_game.values() for row in rows if row.get("collection_item_id") is not None}
    result = []
    for override in conn.execute("""SELECT o.*, p.cardmarket_id_product AS external_product_id
                                      FROM collection_price_overrides o
                                      JOIN cardmarket_products p ON p.id=o.cardmarket_product_id
                                     WHERE o.approved=1 AND o.is_current=1
                                     ORDER BY o.collection_item_id, o.id"""):
        item_id = int(override["collection_item_id"])
        row = rows_by_item.get(item_id)
        if row is None or str(override["source_manifest_id"] or "") != manifest["manifest_id"]:
            continue
        game = str(row["game"])
        product = next((dict(value) for value in snapshots[game]["products"].records if int(value["idProduct"]) == int(override["external_product_id"])), None)
        if product is None:
            continue
        candidate_ids = [int(value) for value in str(row.get("cardmarket_candidates") or "").split(",") if value.strip().isdigit()]
        candidate_by_id = {int(value["idProduct"]): dict(value) for value in snapshots[game]["products"].records}
        candidate_products = [candidate_by_id[value] for value in candidate_ids if value in candidate_by_id]
        result.append({
            "collection_item_id": item_id, "printing_id": row.get("local_printing_id"), "game": game,
            "card_name": row.get("card_name"), "set": row.get("local_set_code"), "card_number": row.get("card_number"),
            "collector_number": row.get("card_number"), "language": row.get("language"), "variant": row.get("local_version"),
            "finish": row.get("finish"), "treatment": row.get("treatment"),
            "candidate_cardmarket_product_id": "|".join(value for value in str(row.get("cardmarket_candidates") or "").split(",") if value),
            "candidate_product_name": "|".join(str(value.get("name") or "") for value in candidate_products),
            "candidate_expansion": "|".join(str(value.get("idExpansion") or "") for value in candidate_products),
            "evidence": override["evidence"], "proposed_status": row.get("match_status"), "row_hash": override["row_hash"],
            "approved": "true", "selected_cardmarket_product_id": str(override["external_product_id"]), "manifest_id": manifest["manifest_id"],
            "_existing_override": True,
        })
    return result


def _apply_collection_reviews(conn: sqlite3.Connection, rows_by_game: dict[str, list[dict]], cards: dict[int, dict], snapshots: dict, manifest: dict, review_path: Path | None, expansion_names: dict[int, str | None]) -> None:
    reviews = _existing_collection_reviews(conn, rows_by_game, snapshots, manifest) + _load_collection_review(review_path)
    if not reviews:
        return
    by_item = {int(row["collection_item_id"]): row for rows in rows_by_game.values() for row in rows if row.get("collection_item_id") is not None}
    approved_by_item: dict[int, dict] = {}
    for review in reviews:
        try:
            item_id = int(review.get("collection_item_id"))
        except (TypeError, ValueError) as exc:
            raise WorkflowError("Collection review has invalid collection_item_id") from exc
        if str(review.get("manifest_id") or "") != manifest["manifest_id"]:
            raise WorkflowError(f"Collection review manifest mismatch for item {item_id}")
        row = by_item.get(item_id)
        if row is None:
            raise WorkflowError(f"Collection review references item outside selected Collection scope: {item_id}")
        if row.get("match_status") == "EXACT":
            # Automatic proof is authoritative.  A stale/manual row must not
            # block it; the writer will archive the manual approval below.
            continue
        candidate_ids = {int(value) for value in str(row.get("cardmarket_candidates") or "").split(",") if value.strip().isdigit()}
        csv_candidates = {int(value) for value in str(review.get("candidate_cardmarket_product_id") or "").split("|") if value.strip().isdigit()}
        current_card = cards.get(int(row.get("local_printing_id") or 0))
        if current_card is None:
            raise WorkflowError(f"Collection review item {item_id} has no local printing")
        target_raw = str(review.get("printing_id") or "").strip()
        target_id = int(target_raw) if target_raw.isdigit() else int(current_card["id"])
        target_card = cards.get(target_id)
        if target_card is None:
            raise WorkflowError(f"Collection review target printing is absent for item {item_id}: {target_id}")
        _validate_review_target(row, target_card, item_id)
        if target_id == int(current_card["id"]):
            if not candidate_ids.issubset(csv_candidates):
                raise WorkflowError(f"Collection review candidates changed for item {item_id}")
        else:
            target_external_ids = _cardmarket_ids_for_card(conn, target_id)
            if not target_external_ids or not csv_candidates.issubset(target_external_ids):
                raise WorkflowError(f"Collection review target candidates are not provenance-backed for item {item_id}")
        expected_hash = audit.collection_review_hash({**row, **review}, manifest["manifest_id"])
        if review.get("row_hash") != expected_hash:
            raise WorkflowError(f"Collection review row_hash invalid for item {item_id}")
        approved = str(review.get("approved") or "").strip().casefold() in {"true", "1", "yes"}
        if not approved:
            continue
        if item_id in approved_by_item:
            raise WorkflowError(f"Multiple approved Collection reviews for item {item_id}")
        selected_raw = str(review.get("selected_cardmarket_product_id") or "").strip()
        if not selected_raw.isdigit() or int(selected_raw) not in csv_candidates:
            raise WorkflowError(f"Collection review selected product is not a listed candidate for item {item_id}")
        selected = int(selected_raw)
        game = str(row.get("game"))
        products, raw_products = audit.build_product_indexes(snapshots[game]["products"], game)
        product = products.get(selected)
        if product is None or selected not in {int(value["idProduct"]) for value in snapshots[game]["price_guide"].records}:
            raise WorkflowError(f"Collection review selected product is absent from current snapshots for item {item_id}")
        matches, reasons = audit._product_matches_card(target_card, product, game, expansion_names)
        hard_reasons = [reason for reason in reasons if reason not in {"unproven_finish", "unproven_treatment"}]
        # Cardmarket omits the local alternate-art suffix from EB02-061A's
        # product number.  Accept only the explicitly approved EB02 JP V2
        # product; the expansion/family evidence still excludes PRB02.
        if (
            game == "one_piece"
            and audit.normalize_number(target_card.get("card_number")) == "EB02061A"
            and audit.normalize_number(product.get("card_number")) == "EB02061"
            and int(product.get("idExpansion") or 0) == 6018
            and "EB02-061A" in str(review.get("evidence") or "")
        ):
            hard_reasons = [reason for reason in hard_reasons if reason != "wrong_cardmarket_id"]
        if not matches and hard_reasons:
            raise WorkflowError(f"Collection review product does not match item {item_id}: {', '.join(hard_reasons)}")
        price = next(dict(value) for value in snapshots[game]["price_guide"].records if int(value["idProduct"]) == selected)
        price = audit.normalize_price_entry(price)
        for field in audit.METRICS + audit.FOIL_METRICS:
            row[field] = price.get(field)
        if target_id != int(current_card["id"]):
            for field, value in ((
                ("local_printing_id", target_card["id"]),
                ("local_set_code", target_card.get("resolved_set_code") or target_card.get("set_code")),
                ("set_name", target_card.get("resolved_set_name")),
                ("language", target_card.get("language")),
                ("local_version", target_card.get("variant_label") or target_card.get("source_variant")),
                ("rarity", target_card.get("rarity")),
                ("finish", target_card.get("finish")),
                ("treatment", target_card.get("treatment")),
                ("canonical_id", target_card.get("canonical_card_id")),
                ("canonical_identity", target_card.get("canonical_identity")),
            )):
                row[field] = value
        foil = game == "magic" and str(target_card.get("finish") or "").casefold() == "foil"
        row.update({
            "match_status": "EXACT", "resolved_cardmarket_id": selected,
            "cardmarket_candidates": str(selected), "cardmarket_product_name": product.get("name"),
            "cardmarket_expansion_id": product.get("idExpansion"), "cardmarket_expansion": expansion_names.get(int(product["idExpansion"])) if product.get("idExpansion") is not None else None,
            "cardmarket_version": product.get("version"), "cardmarket_number": product.get("card_number"),
            "cardmarket_language_scope": "unknown", "cardmarket_metric_used": "Foil Low" if foil else "Low",
            "match_reason": "approved Collection manual mapping", "primary_cause": None,
            "identity_mismatch": False, "manual_approval": review,
        })
        approved_by_item[item_id] = review


def _game_report_key(report: WorkflowReport, scope: str, game: str) -> str:
    # Keep the historical catalog keys stable; composite scoped work gets an
    # explicit prefix for Collection/Wishlist to avoid collisions.
    return game if report.scope != "all" or scope == "catalog" else f"{scope}:{game}"


def _register_game_report(
    report: WorkflowReport,
    scope: str,
    game: str,
    rows: list[dict],
    collection: list[dict] | None = None,
) -> None:
    item = GameReport(game, scope)
    item.printings_checked = len(rows)
    counts = Counter(row.get("match_status") for row in rows)
    item.exact, item.ambiguous, item.mismatch = counts["EXACT"], counts["AMBIGUOUS"], counts["MISMATCH"]
    item.missing, item.unpriced = counts["MISSING"], counts["UNPRICED"]
    item.low_available = sum(1 for row in rows if audit.usable(row.get("low" if row.get("cardmarket_metric_used") == "Low" else "low_alt")))
    item.trend_available = sum(1 for row in rows if audit.usable(row.get("trend" if row.get("cardmarket_metric_used") == "Low" else "trend_alt")))
    item.avg7_available = sum(1 for row in rows if audit.usable(row.get("avg7" if row.get("cardmarket_metric_used") == "Low" else "avg7_alt")))
    item.identity_mismatches_prevented = item.mismatch
    item.write_candidates = sum(1 for row in rows if row.get("local_printing_id") is not None)
    if scope == "collection":
        item.collection_items = len(rows)
        item.collection_units = sum(int(row.get("collection_quantity") or 0) for row in rows)
        item.low_available = sum(1 for row in rows if audit.collection_metric_available(row))
        item.unpriced = sum(1 for row in rows if audit.collection_unpriced(row))
        if collection is not None:
            metrics = audit.collection_summary(rows, [entry for entry in collection if entry.get("game") == game])
            item.collection_exact_item_coverage = metrics.get("item_coverage_percent")
            item.collection_exact_unit_coverage = metrics.get("unit_coverage_percent")
            item.collection_legacy_value = metrics.get("current_total")
            item.collection_low_value = metrics.get("resolved_low_total")
            item.collection_value_coverage = metrics.get("estimated_value_coverage_percent")
            item.collection_value_without_exact = metrics.get("value_without_exact_resolution")
            item.collection_dealer_cash = metrics.get("dealer_cash")
            item.collection_dealer_cash_min = metrics.get("dealer_cash_min")
            item.collection_dealer_cash_max = metrics.get("dealer_cash_max")
            item.collection_trade_value = metrics.get("trade_value")
            item.collection_trade_value_min = metrics.get("trade_value_min")
            item.collection_trade_value_max = metrics.get("trade_value_max")
    elif scope == "wishlist":
        item.wishlist_items = len(rows)
        item.wishlist_units = sum(int(row.get("wishlist_quantity") or 0) for row in rows)
        item.wishlist_status = rows[0].get("wishlist_status") if rows else None
        total_items = item.wishlist_items
        total_units = item.wishlist_units
        exact_rows = [row for row in rows if row.get("match_status") == "EXACT"]
        exact_units = sum(int(row.get("wishlist_quantity") or 0) for row in exact_rows)
        legacy_value = sum(
            float(row["current_price"]) * int(row.get("wishlist_quantity") or 0)
            for row in rows if row.get("current_price") is not None
        )
        resolved_low_value = 0.0
        for row in exact_rows:
            metric = row.get("cardmarket_metric_used")
            low = row.get("low_alt" if metric == "Foil Low" else "low")
            if audit.usable(low):
                resolved_low_value += float(low) * int(row.get("wishlist_quantity") or 0)
        value_without_exact = sum(
            float(row["current_price"]) * int(row.get("wishlist_quantity") or 0)
            for row in rows
            if row.get("match_status") != "EXACT" and row.get("current_price") is not None
        )
        denominator = resolved_low_value + value_without_exact
        estimated_coverage = (resolved_low_value / denominator * 100) if denominator else 0.0
        item.wishlist_exact_item_coverage = round(len(exact_rows) / total_items * 100, 2) if total_items else 0.0
        item.wishlist_exact_unit_coverage = round(exact_units / total_units * 100, 2) if total_units else 0.0
        item.wishlist_legacy_value = round(legacy_value, 2)
        item.wishlist_resolved_low_value = round(resolved_low_value, 2)
        item.wishlist_estimated_value_coverage = round(estimated_coverage, 2)
        item.wishlist_value_without_exact = round(value_without_exact, 2)
        # Keep the legacy report fields populated for consumers that already
        # render the Collection-named metrics for every pricing scope.
        item.collection_exact_item_coverage = item.wishlist_exact_item_coverage
        item.collection_exact_unit_coverage = item.wishlist_exact_unit_coverage
        item.collection_legacy_value = item.wishlist_legacy_value
        item.collection_low_value = item.wishlist_resolved_low_value
        item.collection_value_coverage = item.wishlist_estimated_value_coverage
        item.collection_value_without_exact = item.wishlist_value_without_exact
        item.current_pricing_changes = item.prices_changed
    report.game_reports[_game_report_key(report, scope, game)] = item


def _build_scope_work(
    conn: sqlite3.Connection,
    games: tuple[str, ...],
    snapshots: dict,
    report: WorkflowReport,
    scope: str,
    wishlist_status: str,
    manifest: dict | None = None,
    collection_review: Path | None = None,
) -> ScopeWork:
    if scope == "collection":
        collection_resolutions = audit.load_collection_current_prices(conn)
        rows_by_game, collection = audit.collection_audit_rows(conn, games, snapshots, collection_resolutions)
        expansion_names = audit.load_expansion_names(conn)
        if manifest is not None:
            collection_card_ids = {int(entry["card_id"]) for entry in collection if entry.get("card_id") is not None}
            collection_card_ids.update(_review_printing_ids(collection_review))
            collection_cards = audit.load_cards(conn, games, card_ids=collection_card_ids, include_inactive=True)
            _apply_collection_reviews(conn, rows_by_game, {int(row["id"]): dict(row) for row in collection_cards}, snapshots, manifest, collection_review, expansion_names)
        for game, rows in rows_by_game.items():
            audit.refresh_collection_contributions(rows)
            _register_game_report(report, scope, game, rows, collection)
        card_ids = {int(entry["card_id"]) for entry in collection if entry.get("card_id") is not None}
        card_ids.update(_review_printing_ids(collection_review))
        cards = audit.load_cards(conn, games, card_ids=card_ids, include_inactive=True)
        return ScopeWork(scope, wishlist_status, rows_by_game, {int(row["id"]): dict(row) for row in cards},
                         allowed_collection_ids={int(row["collection_item_id"]) for rows in rows_by_game.values() for row in rows if row.get("collection_item_id") is not None})

    if scope == "wishlist":
        rows_by_game, cards, wishlist = audit.wishlist_audit_rows(conn, games, snapshots, wishlist_status)
        for game, rows in rows_by_game.items():
            _register_game_report(report, scope, game, rows)
        return ScopeWork(scope, wishlist_status, rows_by_game, cards,
                         allowed_wishlist_ids={int(row["wishlist_item_id"]) for row in wishlist})

    if scope != "catalog":
        raise WorkflowError(f"Unknown concrete scope: {scope}")
    cards_list = audit.load_cards(conn, games)
    external = audit.load_external_ids(conn)
    mappings = audit.load_mappings(conn)
    resolutions, histories = audit.load_current_prices(conn)
    expansion_names = audit.load_expansion_names(conn)
    blueprints = audit.blueprint_diagnostics(conn)
    collection = audit.load_collection(conn)
    rows_by_game = {game: [] for game in games}
    for game in audit.GAME_ORDER:
        if game not in games:
            continue
        product_snapshot = snapshots[game]["products"]
        guide_snapshot = snapshots[game]["price_guide"]
        products, _ = audit.build_product_indexes(product_snapshot, game)
        prices = {int(row["idProduct"]): audit.normalize_price_entry(dict(row)) for row in guide_snapshot.records}
        rows = rows_by_game[game]
        for card in (value for value in cards_list if value["game"] == game):
            rows.append(audit.audit_card(card, game, products, prices, external, mappings, resolutions, histories, expansion_names, blueprints, guide_snapshot.created_at, "EUR"))
        audit.apply_collection_metrics(rows, collection, histories, {int(row["local_printing_id"]): {"current_price": row.get("current_price")} for row in rows}, prices, {int(row["local_printing_id"]): row for row in rows})
        _register_game_report(report, scope, game, rows)
    return ScopeWork(scope, wishlist_status, rows_by_game, {int(row["id"]): dict(row) for row in cards_list})


def _build_rows(
    conn: sqlite3.Connection,
    games: tuple[str, ...],
    snapshots: dict,
    report: WorkflowReport,
    manifest: dict | None = None,
    collection_review: Path | None = None,
    wishlist_status: str = "wanted",
) -> list[ScopeWork]:
    scopes = ("collection", "wishlist", "catalog") if report.scope == "all" else (report.scope,)
    return [
        _build_scope_work(conn, games, snapshots, report, scope, wishlist_status, manifest, collection_review)
        for scope in scopes
    ]


def _current_state_audit(works: list[ScopeWork], report: WorkflowReport) -> None:
    """Record the legacy state without making it a repair precondition."""
    for work in works:
        for game, rows in work.rows_by_game.items():
            identity, parity = audit.verdicts(rows)
            report.current_state_audit[_game_report_key(report, work.scope, game)] = f"identity={identity}; pricing_parity={parity}"


def _proposed_price(row: dict) -> tuple[float | None, str | None]:
    """Return the price the repair would write, independent of legacy current data."""
    if row.get("match_status") != "EXACT":
        return None, None
    metric = row.get("cardmarket_metric_used")
    value = row.get("low_alt" if metric == "Foil Low" else "low")
    return (float(value), metric) if audit.usable(value) else (None, None)


def _eb02_regression(rows: list[dict]) -> tuple[bool, str]:
    """Ensure the mandatory EB02-061 identities never share a resolved product."""
    relevant = [row for row in rows if audit.normalize_number(row.get("card_number")) == "eb02-061"]
    if not relevant:
        return True, "no active EB02-061 rows"

    by_product: dict[int, set[tuple[str, str, str]]] = {}
    groups: dict[tuple[str, str, str], set[int]] = {}
    for row in relevant:
        if row.get("match_status") != "EXACT" or row.get("resolved_cardmarket_id") is None:
            continue
        identity = (
            audit.normalize(row.get("local_set_code")),
            audit.normalize(row.get("language")),
            audit.normalize(row.get("local_version") or "unspecified"),
        )
        product_id = int(row["resolved_cardmarket_id"])
        by_product.setdefault(product_id, set()).add(identity)
        groups.setdefault(identity, set()).add(product_id)
    collisions = {product: sorted(keys) for product, keys in by_product.items() if len(keys) > 1}
    if collisions:
        return False, f"resolved Cardmarket id shared by distinct EB02-061 identities: {collisions}"

    def group_ids(set_code: str, language: str, version_token: str | None = None) -> set[int]:
        result: set[int] = set()
        for key, ids in groups.items():
            if key[0] != audit.normalize(set_code) or key[1] != audit.normalize(language):
                continue
            if version_token is None or version_token in key[2]:
                result.update(ids)
        return result

    eb_jp_v2 = group_ids("eb02", "jp", "v2")
    required_pairs = (("prb02", "jp", "v2"), ("eb02", "en", "v2"))
    for set_code, language, version in required_pairs:
        other = group_ids(set_code, language, version)
        if eb_jp_v2 and other and not eb_jp_v2.isdisjoint(other):
            return False, f"EB02 JP V2 overlaps {set_code.upper()} {language.upper()} {version.upper()}"
    alternatives = group_ids("eb02", "jp", "v1") | group_ids("eb02", "jp", "v3")
    if eb_jp_v2 and alternatives and not eb_jp_v2.isdisjoint(alternatives):
        return False, "EB02 JP V2 overlaps EB02 V1/V3"
    return True, "EB02-061 identity separation PASS"


def _validate_proposed_state(works: list[ScopeWork], report: WorkflowReport, *, persisted: bool = False) -> None:
    """Validate the state produced by the resolver, not the unsafe legacy state."""
    failures: list[str] = []
    for work in works:
        for game, rows in work.rows_by_game.items():
            game_failures: list[str] = []
            for row in rows:
                proposed, metric = _proposed_price(row)
                status = row.get("match_status")
                if status in {"AMBIGUOUS", "MISMATCH", "MISSING", "UNPRICED"} and proposed is not None:
                    game_failures.append(f"{row['local_printing_id']}: {status} has proposed price")
                if proposed is not None:
                    if status != "EXACT" or metric not in {"Low", "Foil Low"}:
                        game_failures.append(f"{row['local_printing_id']}: proposed price is not EXACT + Cardmarket Low")
                if persisted:
                    current = row.get("current_price")
                    if current is not None:
                        expected, expected_metric = _proposed_price(row)
                        if expected is None or row.get("current_source") != "cardmarket" or row.get("current_metric") != expected_metric or row.get("current_currency", "").casefold() != "eur" or float(current) != expected:
                            game_failures.append(f"{row['local_printing_id']}: persisted current state is not EXACT + Cardmarket Low")
            if game == "one_piece":
                passed, detail = _eb02_regression(rows)
                if not passed:
                    game_failures.append(detail)
            key = _game_report_key(report, work.scope, game)
            report.proposed_state_validation[key] = "UNSAFE" if game_failures else "SAFE"
            if game_failures:
                failures.extend(f"{key}: {detail}" for detail in game_failures)
    if failures:
        raise WorkflowError("Proposed state validation failed: " + "; ".join(failures[:20]))


def _resolution_snapshot(conn: sqlite3.Connection) -> list[tuple]:
    """Stable snapshot of global resolution rows."""
    columns = [row[1] for row in conn.execute("PRAGMA table_info(printing_price_resolutions)")]
    if "collection_item_id" not in columns:
        return [tuple(row) for row in conn.execute("SELECT * FROM printing_price_resolutions ORDER BY id")]
    wishlist_clause = " AND wishlist_item_id IS NULL" if "wishlist_item_id" in columns else ""
    return [tuple(row) for row in conn.execute(f"SELECT * FROM printing_price_resolutions WHERE collection_item_id IS NULL{wishlist_clause} ORDER BY id")]


def _resolution_snapshot_outside_work(conn: sqlite3.Connection, works: list[ScopeWork]) -> list[tuple]:
    """Snapshot every resolution row that the active work is not allowed to touch."""
    columns = {row[1] for row in conn.execute("PRAGMA table_info(printing_price_resolutions)")}
    rows = [tuple(row) for row in conn.execute("SELECT * FROM printing_price_resolutions ORDER BY id")]
    names = [row[1] for row in conn.execute("PRAGMA table_info(printing_price_resolutions)")]
    positions = {name: index for index, name in enumerate(names)}
    collection_ids = set().union(*(work.allowed_collection_ids for work in works))
    wishlist_ids = set().union(*(work.allowed_wishlist_ids for work in works))
    allow_global = any(work.scope == "catalog" for work in works)
    outside: list[tuple] = []
    for row in rows:
        scope = row[positions["resolution_scope"]] if "resolution_scope" in positions else None
        collection_id = row[positions["collection_item_id"]] if "collection_item_id" in positions else None
        wishlist_id = row[positions["wishlist_item_id"]] if "wishlist_item_id" in positions else None
        if scope == "global" or (scope is None and collection_id is None and wishlist_id is None):
            allowed = allow_global
        elif scope == "collection" or (scope is None and collection_id is not None):
            allowed = collection_id in collection_ids
        elif scope == "wishlist" or (scope is None and wishlist_id is not None):
            allowed = wishlist_id in wishlist_ids
        else:
            allowed = False
        if not allowed:
            outside.append(row)
    return outside


def _validate_collection_persisted(conn: sqlite3.Connection, rows_by_game: dict[str, list[dict]]) -> None:
    failures = []
    for rows in rows_by_game.values():
        for row in rows:
            item_id = row.get("collection_item_id")
            if item_id is None or row.get("local_printing_id") is None:
                continue
            current = conn.execute("""SELECT source, current_price, match_status, selected_metric,
                                             source_currency, cardmarket_low
                                        FROM printing_price_resolutions
                                       WHERE collection_item_id=? AND is_current=1""", (item_id,)).fetchall()
            if len(current) != 1:
                failures.append(f"collection item {item_id}: expected exactly one current resolution")
                continue
            value = current[0]
            if value[0] != "cardmarket":
                failures.append(f"collection item {item_id}: current source is not Cardmarket")
            if value[1] is not None and (row.get("match_status") != "EXACT" or value[2] != "EXACT" or value[3] not in {"Low", "Foil Low"} or str(value[4] or "").casefold() != "eur"):
                failures.append(f"collection item {item_id}: non-null current is not EXACT + Cardmarket Low")
            if row.get("match_status") != "EXACT" and value[1] is not None:
                failures.append(f"collection item {item_id}: unsafe status has non-null current")
    if failures:
        raise WorkflowError("Persisted Collection validation failed: " + "; ".join(failures[:20]))


def _validate_wishlist_persisted(conn: sqlite3.Connection, rows_by_game: dict[str, list[dict]]) -> None:
    failures = []
    for rows in rows_by_game.values():
        for row in rows:
            item_id = row.get("wishlist_item_id")
            if item_id is None or row.get("local_printing_id") is None:
                continue
            current = conn.execute(
                """SELECT resolution_scope, wishlist_item_id, collection_item_id,
                          source, current_price, match_status, selected_metric,
                          source_currency
                     FROM printing_price_resolutions
                    WHERE wishlist_item_id=? AND is_current=1""",
                (item_id,),
            ).fetchall()
            if len(current) != 1:
                failures.append(f"wishlist item {item_id}: expected exactly one current resolution")
                continue
            value = current[0]
            if value[0] != "wishlist" or value[1] != item_id or value[2] is not None or value[3] != "cardmarket":
                failures.append(f"wishlist item {item_id}: current target scope is invalid")
            if value[4] is not None and (row.get("match_status") != "EXACT" or value[5] != "EXACT" or value[6] not in {"Low", "Foil Low"} or str(value[7] or "").casefold() != "eur"):
                failures.append(f"wishlist item {item_id}: non-null current is not EXACT + Cardmarket Low")
            if row.get("match_status") != "EXACT" and value[4] is not None:
                failures.append(f"wishlist item {item_id}: unsafe status has non-null current")
    if failures:
        raise WorkflowError("Persisted Wishlist validation failed: " + "; ".join(failures[:20]))


def _local_product_id(conn: sqlite3.Connection, external_id: int | None) -> int | None:
    if external_id is None:
        return None
    row = conn.execute("SELECT id FROM cardmarket_products WHERE cardmarket_id_product=?", (external_id,)).fetchone()
    return int(row[0]) if row else None


def _ensure_local_product(conn: sqlite3.Connection, product: dict) -> int:
    """Materialize a selected Product Catalogue row without creating a mapping."""
    external_id = int(product["idProduct"])
    existing = _local_product_id(conn, external_id)
    if existing is not None:
        return existing
    cursor = conn.execute(
        """INSERT INTO cardmarket_products
           (cardmarket_id_product, raw_name, cardmarket_id_category,
            cardmarket_id_expansion, cardmarket_id_metacard, date_added, last_seen_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            external_id,
            str(product.get("name") or ""),
            int(product.get("idCategory") or 0),
            int(product.get("idExpansion") or 0),
            int(product["idMetacard"]) if product.get("idMetacard") is not None else None,
            product.get("dateAdded") or _utc_now(),
            product.get("lastSeenAt") or _utc_now(),
        ),
    )
    return int(cursor.lastrowid)


def _resolution_payload(row: dict, manifest: dict, snapshot: audit.SourceSnapshot, conn: sqlite3.Connection) -> dict:
    status = row["match_status"]
    resolved = row.get("resolved_cardmarket_id") if status in {"EXACT", "UNPRICED"} else None
    foil = row.get("cardmarket_metric_used") == "Foil Low"
    current = row.get("low_alt" if foil else "low") if status == "EXACT" else None
    provenance = {"audit_status": status, "reason": row.get("match_reason"), "evidence": json.loads(row.get("evidence") or "{}"), "stored_cardmarket_id": row.get("stored_cardmarket_id"), "resolved_cardmarket_id": resolved, "source_manifest_id": manifest["manifest_id"]}
    if row.get("manual_approval"):
        provenance["manual_approval"] = row["manual_approval"]
    scope = row.get("cardmarket_language_scope") or "unknown"
    if scope not in {"exact", "mixed", "unknown"}:
        scope = "unknown"
    return {"cardmarket_product_id": _local_product_id(conn, resolved), "external_id": str(resolved) if resolved is not None else None, "match_status": status, "current_price": float(current) if audit.usable(current) else None, "selected_metric": "Foil Low" if foil else "Low", "cardmarket_low": row.get("low"), "cardmarket_trend": row.get("trend"), "cardmarket_avg1": row.get("avg1"), "cardmarket_avg7": row.get("avg7"), "cardmarket_avg30": row.get("avg30"), "cardmarket_foil_low": row.get("low_alt"), "cardmarket_foil_trend": row.get("trend_alt"), "cardmarket_foil_avg1": row.get("avg1_alt"), "cardmarket_foil_avg7": row.get("avg7_alt"), "cardmarket_foil_avg30": row.get("avg30_alt"), "source_currency": "EUR", "source_snapshot_created_at": snapshot.created_at, "source_snapshot_sha256": snapshot.sha256, "source_manifest_id": manifest["manifest_id"], "provenance": json.dumps(provenance, sort_keys=True), "confidence": "high" if status == "EXACT" else None, "currency": "EUR", "source": "cardmarket", "resolution_method": "cardmarket_exact_language" if status in {"EXACT", "UNPRICED"} else "no_exact_language_price", "price_type": "low", "language_scope": scope}


def _sync_collection_override(conn: sqlite3.Connection, row: dict, card: dict, payload: dict, resolved_at: str) -> None:
    item_id = row.get("collection_item_id")
    if item_id is None:
        return
    if row.get("match_status") == "EXACT" and not row.get("manual_approval"):
        # Automatic proof always wins over a previous manual approval.
        conn.execute("UPDATE collection_price_overrides SET is_current=0 WHERE collection_item_id=?", (item_id,))
        return
    review = row.get("manual_approval")
    if not review:
        return
    local_product_id = payload.get("cardmarket_product_id")
    if local_product_id is None:
        raise WorkflowError(f"Manual Collection approval for item {item_id} has no local Cardmarket product")
    conn.execute("UPDATE collection_price_overrides SET is_current=0 WHERE collection_item_id=?", (item_id,))
    evidence = str(review.get("evidence") or "").strip()
    provenance = json.dumps({"source": "collection_manual_review.csv", "resolved_at": resolved_at, "manifest_id": review.get("manifest_id"), "row_hash": review.get("row_hash")}, sort_keys=True)
    conn.execute(
        """INSERT INTO collection_price_overrides
           (collection_item_id, card_id, language_id, cardmarket_product_id,
            match_status, approved, row_hash, source_manifest_id, evidence,
            provenance, is_current, created_at)
           VALUES (?, ?, ?, ?, 'EXACT', 1, ?, ?, ?, ?, 1, ?)
           ON CONFLICT(collection_item_id, row_hash) DO UPDATE SET
             approved=1, is_current=1, source_manifest_id=excluded.source_manifest_id,
             evidence=excluded.evidence, provenance=excluded.provenance""",
        (item_id, card["id"], card["language_id"], local_product_id,
         review["row_hash"], review["manifest_id"], evidence, provenance, resolved_at),
    )


def _resolution_equal(old: sqlite3.Row, new: dict) -> bool:
    fields = ("cardmarket_product_id", "match_status", "current_price", "selected_metric", "cardmarket_low", "cardmarket_trend", "cardmarket_avg1", "cardmarket_avg7", "cardmarket_avg30", "cardmarket_foil_low", "cardmarket_foil_trend", "cardmarket_foil_avg1", "cardmarket_foil_avg7", "cardmarket_foil_avg30", "source_currency", "source_snapshot_created_at", "source_snapshot_sha256", "source_manifest_id", "provenance", "source", "resolution_method")
    return all(old[field] == new.get(field) for field in fields if field in old.keys())


def _validate_write_target(work: ScopeWork, row: dict, card: dict) -> None:
    """Reject target IDs outside the selected work universe before any write."""
    if row.get("local_printing_id") is not None and int(row["local_printing_id"]) != int(card["id"]):
        raise WorkflowError(f"{work.scope} writer received a row for printing {row['local_printing_id']} with card {card['id']}")
    collection_id = row.get("collection_item_id")
    wishlist_id = row.get("wishlist_item_id")
    if work.scope == "collection":
        if collection_id is None or int(collection_id) not in work.allowed_collection_ids or wishlist_id is not None:
            raise WorkflowError(f"Collection writer received incompatible target: collection_item_id={collection_id}, wishlist_item_id={wishlist_id}")
    elif work.scope == "wishlist":
        if wishlist_id is None or int(wishlist_id) not in work.allowed_wishlist_ids or collection_id is not None:
            raise WorkflowError(f"Wishlist writer received incompatible target: collection_item_id={collection_id}, wishlist_item_id={wishlist_id}")
    elif work.scope == "catalog":
        if collection_id is not None or wishlist_id is not None:
            raise WorkflowError(f"Catalog writer received scoped target: collection_item_id={collection_id}, wishlist_item_id={wishlist_id}")
    else:
        raise WorkflowError(f"Unknown writer scope: {work.scope}")


def _write_resolution(conn: sqlite3.Connection, card: dict, row: dict, payload: dict, resolved_at: str, report: GameReport, work: ScopeWork) -> None:
    _validate_write_target(work, row, card)
    collection_item_id = row.get("collection_item_id") if work.scope == "collection" else None
    wishlist_item_id = row.get("wishlist_item_id") if work.scope == "wishlist" else None
    resolution_scope = work.scope if work.scope in {"collection", "wishlist"} else "global"
    if work.scope == "collection":
        old = conn.execute("SELECT * FROM printing_price_resolutions WHERE collection_item_id=? AND wishlist_item_id IS NULL AND COALESCE(source,'cardmarket')='cardmarket' AND is_current=1 ORDER BY id DESC LIMIT 1", (collection_item_id,)).fetchone()
    elif work.scope == "wishlist":
        old = conn.execute("SELECT * FROM printing_price_resolutions WHERE wishlist_item_id=? AND collection_item_id IS NULL AND COALESCE(source,'cardmarket')='cardmarket' AND is_current=1 ORDER BY id DESC LIMIT 1", (wishlist_item_id,)).fetchone()
    else:
        old = conn.execute("SELECT * FROM printing_price_resolutions WHERE card_id=? AND language_id=? AND collection_item_id IS NULL AND wishlist_item_id IS NULL AND COALESCE(source,'cardmarket')='cardmarket' AND is_current=1 ORDER BY id DESC LIMIT 1", (card["id"], card.get("language_id"))).fetchone()
    if old is not None and _resolution_equal(old, payload):
        # Idempotent Cardmarket state still supersedes any legacy source that
        # might have remained active for the same printing.
        if work.scope == "collection":
            conn.execute("UPDATE printing_price_resolutions SET is_current=0 WHERE collection_item_id=? AND wishlist_item_id IS NULL AND is_current=1", (collection_item_id,))
        elif work.scope == "wishlist":
            conn.execute("UPDATE printing_price_resolutions SET is_current=0 WHERE wishlist_item_id=? AND collection_item_id IS NULL AND is_current=1", (wishlist_item_id,))
        else:
            conn.execute("UPDATE printing_price_resolutions SET is_current=0 WHERE card_id=? AND language_id=? AND collection_item_id IS NULL AND wishlist_item_id IS NULL AND is_current=1 AND COALESCE(source,'cardmarket')<>'cardmarket'", (card["id"], card.get("language_id")))
        report.prices_unchanged += 1
        return
    # CardTrader rows remain historical evidence, but cannot remain active once
    # the Cardmarket resolution for the same printing is materialized.
    if work.scope == "collection":
        conn.execute("UPDATE printing_price_resolutions SET is_current=0 WHERE collection_item_id=? AND wishlist_item_id IS NULL AND is_current=1", (collection_item_id,))
    elif work.scope == "wishlist":
        conn.execute("UPDATE printing_price_resolutions SET is_current=0 WHERE wishlist_item_id=? AND collection_item_id IS NULL AND is_current=1", (wishlist_item_id,))
    else:
        conn.execute("UPDATE printing_price_resolutions SET is_current=0 WHERE card_id=? AND language_id=? AND collection_item_id IS NULL AND wishlist_item_id IS NULL AND is_current=1", (card["id"], card.get("language_id")))
    columns = ("card_id", "collection_item_id", "wishlist_item_id", "resolution_scope", "language_id", "resolved_at", "current_price", "currency", "source", "price_type", "resolution_method", "external_id", "price_confidence", "language_scope", "metadata", "cardmarket_product_id", "match_status", "is_current", "selected_metric", "cardmarket_low", "cardmarket_trend", "cardmarket_avg1", "cardmarket_avg7", "cardmarket_avg30", "cardmarket_foil_low", "cardmarket_foil_trend", "cardmarket_foil_avg1", "cardmarket_foil_avg7", "cardmarket_foil_avg30", "source_currency", "source_snapshot_created_at", "source_snapshot_sha256", "source_manifest_id", "provenance")
    values = (card["id"], collection_item_id, wishlist_item_id, resolution_scope, card.get("language_id"), resolved_at, payload["current_price"], payload["currency"], payload["source"], payload["price_type"], payload["resolution_method"], payload["external_id"], payload["confidence"], payload["language_scope"], payload["provenance"], payload["cardmarket_product_id"], payload["match_status"], 1, payload["selected_metric"], payload["cardmarket_low"], payload["cardmarket_trend"], payload["cardmarket_avg1"], payload["cardmarket_avg7"], payload["cardmarket_avg30"], payload["cardmarket_foil_low"], payload["cardmarket_foil_trend"], payload["cardmarket_foil_avg1"], payload["cardmarket_foil_avg7"], payload["cardmarket_foil_avg30"], payload["source_currency"], payload["source_snapshot_created_at"], payload["source_snapshot_sha256"], payload["source_manifest_id"], payload["provenance"])
    placeholders = ",".join("?" for _ in columns)
    conn.execute(f"INSERT INTO printing_price_resolutions ({','.join(columns)}) VALUES ({placeholders})", values)
    report.prices_changed += 1
    report.current_pricing_changes += 1


def _write_history(conn: sqlite3.Connection, game: str, snapshot: audit.SourceSnapshot, manifest: dict, report: GameReport, product_ids: set[int] | None = None) -> None:
    for raw in snapshot.records:
        if product_ids is not None and int(raw["idProduct"]) not in product_ids:
            continue
        product = _local_product_id(conn, int(raw["idProduct"]))
        if product is None:
            continue
        mapped = audit.normalize_price_entry(dict(raw))
        cursor = conn.execute("""INSERT INTO market_price_history (cardmarket_product_id, observed_at, low, avg, trend, avg1, avg7, avg30, low_alt, avg_alt, trend_alt, avg1_alt, avg7_alt, avg30_alt, imported_at, source, source_currency, source_snapshot_created_at, source_snapshot_sha256, source_manifest_id, provenance) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'cardmarket', 'EUR', ?, ?, ?, ?) ON CONFLICT(cardmarket_product_id, observed_at) DO NOTHING""", (product, snapshot.created_at, mapped.get("low"), mapped.get("avg"), mapped.get("trend"), mapped.get("avg1"), mapped.get("avg7"), mapped.get("avg30"), mapped.get("low_alt"), mapped.get("avg_alt"), mapped.get("trend_alt"), mapped.get("avg1_alt"), mapped.get("avg7_alt"), mapped.get("avg30_alt"), _utc_now(), snapshot.created_at, snapshot.sha256, manifest["manifest_id"], json.dumps({"source": "cardmarket_price_guide", "game": game, "manifest_id": manifest["manifest_id"]}, sort_keys=True)))
        if cursor.rowcount:
            report.history_rows_inserted += 1
        else:
            report.history_rows_skipped += 1


def _apply_game(conn: sqlite3.Connection, game: str, work: ScopeWork, snapshots: dict, manifest: dict, resolved_at: str, report: WorkflowReport) -> None:
    rows = work.rows_by_game.get(game, [])
    if not rows:
        return
    game_report = report.game_reports[_game_report_key(report, work.scope, game)]
    _validate_resolution_scope_invariants(conn)
    # Source-table writes are limited to products selected by the active target,
    # including Catalog. No mapping is inferred or created here.
    product_ids = {int(row["resolved_cardmarket_id"]) for row in rows if row.get("resolved_cardmarket_id") is not None and row.get("match_status") in {"EXACT", "UNPRICED"}}
    products, _ = audit.build_product_indexes(snapshots[game]["products"], game)
    for product_id in product_ids:
        product = products.get(product_id)
        if product is not None:
            _ensure_local_product(conn, product)
    _write_history(conn, game, snapshots[game]["price_guide"], manifest, game_report, product_ids)
    _validate_resolution_scope_invariants(conn)
    if game == "one_piece":
        _write_one_piece(conn, rows, work.cards, snapshots[game]["products"], manifest, resolved_at, game_report, work)
    else:
        for row in rows:
            if row.get("local_printing_id") is not None:
                card = work.cards[int(row["local_printing_id"])]
                payload = _resolution_payload(row, manifest, snapshots[game]["products"], conn)
                if work.scope == "collection":
                    _sync_collection_override(conn, row, card, payload, resolved_at)
                _write_resolution(conn, card, row, payload, resolved_at, game_report, work)
                _validate_resolution_scope_invariants(conn)


def _write_one_piece(conn: sqlite3.Connection, rows: list[dict], cards: dict[int, dict], snapshot: audit.SourceSnapshot, manifest: dict, resolved_at: str, report: GameReport, work: ScopeWork) -> None:
    """Compatibility-named writer; it uses the same Cardmarket resolver as Magic."""
    for row in rows:
        if row.get("local_printing_id") is not None:
            card = cards[int(row["local_printing_id"])]
            payload = _resolution_payload(row, manifest, snapshot, conn)
            if work.scope == "collection":
                _sync_collection_override(conn, row, card, payload, resolved_at)
            _write_resolution(conn, card, row, payload, resolved_at, report, work)
            _validate_resolution_scope_invariants(conn)


def _probe_write_lock(path: Path) -> None:
    conn = _connect(path)
    try:
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.rollback()
        except sqlite3.OperationalError as exc:
            if "locked" in str(exc).lower() or "busy" in str(exc).lower():
                raise LockError("Could not acquire SQLite write lock; another operation is in progress") from exc
            raise
    finally:
        conn.close()


def _fsync_path(path: Path) -> None:
    with path.open("rb") as handle:
        os.fsync(handle.fileno())
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def _make_backup(db_path: Path, started_at: str) -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = started_at.replace(":", "-").replace("+", "_")
    backup = BACKUP_DIR / f"tcg_dashboard_{stamp}.db"
    index = 1
    while backup.exists():
        backup = BACKUP_DIR / f"tcg_dashboard_{stamp}_{index}.db"
        index += 1
    shutil.copy2(db_path, backup)
    _fsync_path(backup)
    return backup


def _restore_backup(backup: Path, db_path: Path) -> None:
    """Restore through a second same-filesystem temporary file."""
    with tempfile.NamedTemporaryFile(prefix="tcg-rollback-", suffix=".db", dir=db_path.parent, delete=False) as handle:
        restore_path = Path(handle.name)
    try:
        shutil.copy2(backup, restore_path)
        _fsync_path(restore_path)
        os.replace(restore_path, db_path)
        _fsync_path(db_path)
    finally:
        if restore_path.exists():
            restore_path.unlink()


def _write_log(report: WorkflowReport) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = report.started_at.replace(":", "-").replace("+", "_")
    (LOG_DIR / f"{stamp}.json").write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_workflow(*, mode: str, games: tuple[str, ...], scope: str = "all", wishlist_status: str = "wanted", db_path: Path = DEFAULT_DB_PATH, now: str | None = None, download_fn: Callable | None = None, cardtrader_client=None, source_dir: Path | None = None, collection_review: Path | None = None) -> tuple[WorkflowReport, int]:
    if scope not in {"collection", "wishlist", "catalog", "all"}:
        raise WorkflowError(f"Unknown pricing scope: {scope}")
    if wishlist_status not in {"wanted", "acquired", "removed", "all"}:
        raise WorkflowError(f"Unknown Wishlist status: {wishlist_status}")
    if collection_review is not None and scope != "collection":
        raise WorkflowError("--collection-review requires --scope collection")
    del cardtrader_client
    started_at = now or _utc_now()
    report = WorkflowReport(mode, scope, games, str(db_path.resolve()), started_at, wishlist_status=wishlist_status)
    clock = dt.datetime.now(dt.timezone.utc)
    temp_path: Path | None = None
    backup: Path | None = None
    working: sqlite3.Connection | None = None
    original_personal: str | None = None
    try:
        if not db_path.is_file():
            raise WorkflowError(f"Database does not exist: {db_path.resolve()}")
        if mode == "apply" and db_path.resolve() == DEFAULT_DB_PATH.resolve():
            raise WorkflowError("Production pricing apply is disabled for the Wishlist scope safety sprint; use a temporary DB copy")
        original = _connect(db_path)
        try:
            report.integrity, report.foreign_keys = _validate_database(original)
            original_personal = _personal_snapshot(original)
            snapshots, manifest = _load_sources(source_dir, games, original, started_at, download_fn, report)
        finally:
            original.close()
        with tempfile.NamedTemporaryFile(prefix="tcg-pricing-", suffix=".db", dir=db_path.parent, delete=False) as handle:
            temp_path = Path(handle.name)
        shutil.copy2(db_path, temp_path)
        working = _connect(temp_path)
        ensure_pricing_schema(working)
        _validate_database(working)
        works = _build_rows(working, games, snapshots, report, manifest, collection_review, wishlist_status)
        protected_resolutions_before = _resolution_snapshot_outside_work(working, works)
        mappings_before = _mapping_snapshot(working)
        personal_before_work = _personal_snapshot(working)
        _current_state_audit(works, report)
        # This is the actual repair preflight. It intentionally does not call
        # the current-state verdict as a gate: legacy unsafe prices are what the
        # transaction is designed to replace.
        _validate_proposed_state(works, report)
        if mode == "dry-run":
            if _personal_snapshot(working) != personal_before_work or _mapping_snapshot(working) != mappings_before:
                raise WorkflowError("Collection/Wishlist changed during dry-run")
            report.transaction = "NOT_APPLIED"
            report.collection_wishlist_unchanged = True
            report.result = "SUCCESS"
            working.close()
        else:
            _probe_write_lock(db_path)
            backup = _make_backup(db_path, started_at)
            report.backup = str(backup.resolve())
            working.execute("BEGIN IMMEDIATE")
            for work in works:
                _validate_resolution_scope_invariants(working)
                for game in audit.GAME_ORDER:
                    if game in games:
                        _apply_game(working, game, work, snapshots, manifest, started_at, report)
            if _resolution_snapshot_outside_work(working, works) != protected_resolutions_before:
                raise WorkflowError("Pricing scope modified a resolution outside its active targets")
            if _mapping_snapshot(working) != mappings_before:
                raise WorkflowError("Pricing scope modified cardmarket mappings")
            if _personal_snapshot(working) != original_personal:
                raise WorkflowError("Collection/Wishlist changed during pricing transaction")
            _validate_database(working)
            working.commit()
            working.close()
            os.replace(temp_path, db_path)
            temp_path = None
            _fsync_path(db_path)
            post = _connect(db_path)
            try:
                _validate_database(post)
                if _personal_snapshot(post) != original_personal:
                    raise WorkflowError("Collection/Wishlist changed during pricing update")
                post_probe = WorkflowReport("post-apply-validation", scope, games, str(db_path.resolve()), started_at, wishlist_status=wishlist_status)
                post_works = _build_rows(post, games, snapshots, post_probe, manifest, collection_review, wishlist_status)
                _validate_proposed_state(post_works, post_probe, persisted=True)
                if _resolution_snapshot_outside_work(post, works) != protected_resolutions_before:
                    raise WorkflowError("Pricing scope changed a resolution outside its active targets")
                if _mapping_snapshot(post) != mappings_before:
                    raise WorkflowError("Pricing scope changed cardmarket mappings")
                for post_work in post_works:
                    if post_work.scope == "collection":
                        _validate_collection_persisted(post, post_work.rows_by_game)
                    elif post_work.scope == "wishlist":
                        _validate_wishlist_persisted(post, post_work.rows_by_game)
                report.post_apply_validation = dict(post_probe.proposed_state_validation)
            finally:
                post.close()
            report.transaction, report.collection_wishlist_unchanged, report.result = "COMMITTED", True, "SUCCESS"
    except Exception as exc:
        if working is not None:
            try:
                working.rollback()
                working.close()
            except sqlite3.Error:
                pass
        if mode == "apply" and backup is not None and backup.is_file():
            try:
                if temp_path is not None and temp_path.exists():
                    temp_path.unlink()
                _restore_backup(backup, db_path)
            except OSError as restore_exc:
                report.errors.append(f"Rollback restore failed: {restore_exc}")
        report.transaction = "ROLLED_BACK" if mode == "apply" else report.transaction
        report.result = "FAILED"
        report.errors.append(str(exc))
        code = getattr(exc, "exit_code", 1)
    else:
        code = 0
    finally:
        if temp_path is not None and temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass
        report.duration_seconds = round((dt.datetime.now(dt.timezone.utc) - clock).total_seconds(), 3)
        try:
            _write_log(report)
        except OSError as exc:
            report.errors.append(f"Could not write pricing log: {exc}")
            if code == 0:
                code, report.result = 1, "FAILED"
    return report, code


def _print_report(report: WorkflowReport) -> None:
    print("\nPRICE UPDATE COMPLETE")
    print(f"\nMode: {report.mode.upper()}")
    print(f"Scope: {report.scope}")
    for key, item in report.game_reports.items():
        title = item.game.replace('_', ' ').title()
        if key != item.game:
            title += f" [{item.scope}]"
        print(f"\n{title}\n------")
        for label, value in (("Printings checked", item.printings_checked), ("Collection items", item.collection_items), ("Collection units", item.collection_units), ("Wishlist items", item.wishlist_items), ("Wishlist units", item.wishlist_units), ("Write candidates", item.write_candidates), ("Current pricing changes", item.current_pricing_changes), ("Exact Cardmarket matches", item.exact), ("Ambiguous", item.ambiguous), ("Missing", item.missing), ("Unpriced", item.unpriced), ("Identity mismatches prevented", item.identity_mismatches_prevented), ("Low available", item.low_available), ("Trend available", item.trend_available), ("AVG7 available", item.avg7_available), ("Prices changed", item.prices_changed), ("Prices unchanged", item.prices_unchanged), ("Exact item coverage", item.collection_exact_item_coverage), ("Exact unit coverage", item.collection_exact_unit_coverage), ("Legacy value", item.collection_legacy_value), ("Resolved Low value", item.collection_low_value), ("Estimated value coverage", item.collection_value_coverage), ("Value without exact resolution", item.collection_value_without_exact)):
            print(f"{label}: {value}")
        print(f"History rows inserted: {item.history_rows_inserted}")
    print(f"\nTransaction: {report.transaction}\nIntegrity: {report.integrity}\nForeign keys: {report.foreign_keys}\nResult: {report.result}")
    if report.current_state_audit:
        print("\nCURRENT STATE AUDIT")
        for game, value in report.current_state_audit.items():
            print(f"{game}: {value}")
    if report.proposed_state_validation:
        print("\nPROPOSED STATE VALIDATION")
        for game, value in report.proposed_state_validation.items():
            print(f"{game}: {value}")
    if report.post_apply_validation:
        print("\nPOST-APPLY VALIDATION")
        for game, value in report.post_apply_validation.items():
            print(f"{game}: {value}")
    if report.backup:
        print(f"Backup: {report.backup}")
    for error in report.errors:
        print(f"Error: {error}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Update Cardmarket Low prices safely.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    parser.add_argument("--game", choices=("all", *SUPPORTED_GAMES), default="all")
    parser.add_argument("--scope", choices=("collection", "wishlist", "catalog", "all"), default="collection")
    parser.add_argument("--wishlist-status", choices=("wanted", "acquired", "removed", "all"), default="wanted")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--source-dir", type=Path)
    parser.add_argument("--collection-review", type=Path)
    parser.add_argument("--now")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    games = audit.GAME_ORDER if args.game == "all" else (args.game,)
    report, code = run_workflow(mode="dry-run" if args.dry_run else "apply", games=tuple(games), scope=args.scope, wishlist_status=args.wishlist_status, db_path=args.db, now=args.now, source_dir=args.source_dir, collection_review=args.collection_review)
    _print_report(report)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
