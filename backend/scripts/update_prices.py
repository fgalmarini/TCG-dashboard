"""Safe, non-interactive orchestration of the project's market-price updates."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sqlite3
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
IMPORTER_ROOT = REPO_ROOT / "backend" / "importer"
for path in (REPO_ROOT, IMPORTER_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import downloader
import parser as cardmarket_parser
from config import ALT_SUFFIX
from price_mapping import map_price_guide_entry

from backend.images.cardtrader import CardTraderClient, CardTraderConfigurationError, load_cardtrader_token
from backend.pricing import MarketplacePrice, resolve_cardtrader_marketplace
from backend.scripts.import_one_piece_catalog import insert_price_resolution

DEFAULT_DB_PATH = REPO_ROOT / "backend" / "db" / "tcg_dashboard.db"
LOG_DIR = REPO_ROOT / "logs" / "pricing"
BACKUP_DIR = REPO_ROOT / "backups" / "pricing"
SUPPORTED_GAMES = ("magic", "one_piece")
EXPECTED_TABLES = {
    "games", "languages", "cards", "cardmarket_products", "cardmarket_product_mappings",
    "market_price_history", "printing_external_ids", "printing_price_resolutions",
    "collection_items", "wishlist_items",
}
PERSONAL_TABLES = ("collection_items", "wishlist_items")


class WorkflowError(RuntimeError):
    exit_code = 1


class ConfigurationError(WorkflowError):
    exit_code = 2


class LockError(WorkflowError):
    pass


@dataclass
class GameReport:
    game: str
    printings_checked: int = 0
    cardmarket_exact: int = 0
    cardtrader_fallback: int = 0
    mixed_rejected: int = 0
    no_exact_price: int = 0
    updated: int = 0
    missing: int = 0
    history_rows_inserted: int = 0
    history_rows_planned: int = 0
    history_rows_skipped: int = 0
    errors: list[str] = field(default_factory=list)
    confidence: Counter = field(default_factory=Counter)

    def to_dict(self) -> dict:
        value = asdict(self)
        value["confidence"] = dict(self.confidence)
        return value


@dataclass
class WorkflowReport:
    mode: str
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
    game_reports: dict[str, GameReport] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    collection_wishlist_unchanged: bool | None = None
    duration_seconds: float | None = None

    def to_dict(self) -> dict:
        return {
            "timestamp": self.started_at,
            "mode": self.mode,
            "games": list(self.games),
            "database": self.database,
            "providers": self.providers,
            "snapshots": self.snapshots,
            "printings": {key: value.to_dict() for key, value in self.game_reports.items()},
            "transaction": self.transaction,
            "backup": self.backup,
            "integrity": self.integrity,
            "foreign_keys": self.foreign_keys,
            "collection_wishlist_unchanged": self.collection_wishlist_unchanged,
            "errors": self.errors,
            "result": self.result,
            "duration_seconds": self.duration_seconds,
        }


@dataclass(frozen=True)
class MagicTarget:
    card_id: int | None
    product_id: int | None
    external_product_id: int | None


@dataclass(frozen=True)
class OnePieceTarget:
    card_id: int
    language_id: int
    language: str
    blueprint_id: int | None
    release_id: int | None
    cardmarket_ids: tuple[int, ...]
    mixed_cardmarket_ids: tuple[int, ...]


@dataclass(frozen=True)
class OnePieceDecision:
    target: OnePieceTarget
    method: str
    source: str | None
    external_id: str | None
    current_price: float | None
    currency: str | None
    sample_size: int
    lowest_price: float | None
    median_price: float | None
    confidence: str | None
    language_scope: str
    metadata: dict
    fingerprint: str


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="microseconds")


def _connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=0")
    return conn


def _validate_database(conn: sqlite3.Connection) -> tuple[str, list[str]]:
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
    configured_games = {row[0] for row in conn.execute("SELECT code FROM games")}
    missing_games = sorted(set(SUPPORTED_GAMES) - configured_games)
    if missing_games:
        raise WorkflowError(f"Database is missing configured games: {', '.join(missing_games)}")
    return integrity, []


def _personal_snapshot(conn: sqlite3.Connection) -> str:
    digest = hashlib.sha256()
    for table in PERSONAL_TABLES:
        columns = [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]
        digest.update(table.encode())
        digest.update("\0".join(columns).encode())
        for row in conn.execute(f"SELECT * FROM {table} ORDER BY id"):
            digest.update(json.dumps(tuple(row), default=str, separators=(",", ":")).encode())
            digest.update(b"\n")
    return digest.hexdigest()


def _load_cardmarket_sources(
    game_keys: tuple[str, ...],
    report: WorkflowReport,
    download_fn: Callable | None = None,
) -> dict[str, tuple[str, dict[int, dict]]]:
    try:
        results = (download_fn or downloader.download_all)(games=game_keys)
    except Exception as exc:
        raise WorkflowError(f"Cardmarket source download failed: {exc}") from exc

    sources: dict[str, tuple[str, dict[int, dict]]] = {}
    for game in game_keys:
        products = results.get(f"{game}:products")
        price_guide = results.get(f"{game}:price_guide")
        if products is None or price_guide is None or not products.ok or not price_guide.ok:
            failures = [
                f"{item.key}: {item.error}"
                for item in (products, price_guide)
                if item is not None and not item.ok
            ]
            raise WorkflowError(f"Cardmarket {game} source unavailable: {'; '.join(failures)}")
        try:
            _, _products = cardmarket_parser.load_products(products.path)
            observed_at, entries = cardmarket_parser.load_price_guide(price_guide.path)
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise WorkflowError(f"Cardmarket {game} source parse failed: {exc}") from exc
        sources[game] = (observed_at, cardmarket_parser.index_price_guide_by_product(entries))
        report.providers[f"cardmarket:{game}"] = "ok"
        report.snapshots[f"cardmarket:{game}"] = observed_at
    return sources


def _magic_targets(conn: sqlite3.Connection) -> list[MagicTarget]:
    rows = conn.execute(
        """SELECT c.id AS card_id, p.id AS product_id, p.cardmarket_id_product
             FROM cards c
             LEFT JOIN cardmarket_product_mappings m ON m.card_id=c.id AND m.status='mapped'
             LEFT JOIN cardmarket_products p ON p.id=m.cardmarket_product_id
            WHERE c.game_id=(SELECT id FROM games WHERE code='magic')
              AND c.catalog_status='active'
            ORDER BY c.id"""
    ).fetchall()
    by_card: dict[int, list[sqlite3.Row]] = defaultdict(list)
    for row in rows:
        by_card[int(row["card_id"])].append(row)
    targets: list[MagicTarget] = []
    for card_id, candidates in by_card.items():
        if len(candidates) == 1:
            row = candidates[0]
            if row["product_id"] is not None:
                targets.append(MagicTarget(card_id, int(row["product_id"]), int(row["cardmarket_id_product"])))
            else:
                targets.append(MagicTarget(card_id, None, None))
        else:
            # Zero or multiple mappings are intentionally not resolved by guessing.
            targets.append(MagicTarget(card_id, None, None))

    referenced = conn.execute(
        """SELECT DISTINCT ci.cardmarket_product_id AS product_id, p.cardmarket_id_product
             FROM collection_items ci
             JOIN cardmarket_products p ON p.id=ci.cardmarket_product_id
            WHERE ci.cardmarket_product_id IS NOT NULL
            UNION
           SELECT DISTINCT m.cardmarket_product_id, p.cardmarket_id_product
             FROM wishlist_items w
             JOIN cardmarket_product_mappings m ON m.card_id=w.card_id AND m.status='mapped'
             JOIN cardmarket_products p ON p.id=m.cardmarket_product_id"""
    ).fetchall()
    for row in referenced:
        product_id = int(row["product_id"])
        if not any(target.product_id == product_id for target in targets):
            targets.append(MagicTarget(None, product_id, int(row["cardmarket_id_product"])))
    return targets


def _prepare_magic(
    conn: sqlite3.Connection,
    price_index: dict[int, dict],
    observed_at: str,
    mode: str,
    report: GameReport,
) -> list[tuple[MagicTarget, dict, str]]:
    targets = _magic_targets(conn)
    report.printings_checked = len(targets)
    prepared = []
    for target in targets:
        if target.external_product_id is None:
            report.missing += 1
            continue
        entry = price_index.get(target.external_product_id)
        if entry is None:
            report.missing += 1
            continue
        mapped = map_price_guide_entry(entry, ALT_SUFFIX["magic"])
        fingerprint = hashlib.sha256(
            json.dumps(mapped, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        prepared.append((target, mapped, fingerprint))
        if mapped.get("trend") is not None and mapped.get("trend") != 0:
            report.cardmarket_exact += 1
            report.updated += 1
        else:
            report.missing += 1
    report.history_rows_planned = len(prepared)
    if mode == "dry-run":
        report.history_rows_skipped = len(prepared)
    return prepared


def _one_piece_targets(conn: sqlite3.Connection) -> list[OnePieceTarget]:
    rows = conn.execute(
        """SELECT c.id AS card_id, c.language_id, l.code AS language,
                  b.external_id AS blueprint_id, b.metadata AS blueprint_metadata,
                  cm.external_id AS cardmarket_id, cm.language_scope
             FROM cards c
             JOIN languages l ON l.id=c.language_id
             LEFT JOIN printing_external_ids b
               ON b.card_id=c.id AND b.source='cardtrader_blueprint' AND b.language_scope='exact'
             LEFT JOIN printing_external_ids cm
               ON cm.card_id=c.id AND cm.source='cardmarket_product'
              AND (cm.language_id=c.language_id OR cm.language_id IS NULL)
            WHERE c.game_id=(SELECT id FROM games WHERE code='one_piece')
              AND c.catalog_status='active'
            ORDER BY c.id, cm.language_scope, cm.external_id"""
    ).fetchall()
    grouped: dict[tuple[int, int, str], dict] = {}
    for row in rows:
        blueprint_key = str(row["blueprint_id"]) if row["blueprint_id"] is not None else "<missing>"
        key = (int(row["card_id"]), int(row["language_id"]), blueprint_key)
        item = grouped.setdefault(
            key,
            {
                "card_id": key[0],
                "language_id": key[1],
                "language": row["language"],
                "blueprint_id": int(row["blueprint_id"]) if row["blueprint_id"] is not None else None,
                "release_id": None,
                "cardmarket_ids": [],
                "mixed_cardmarket_ids": [],
            },
        )
        metadata = json.loads(row["blueprint_metadata"] or "{}")
        if isinstance(metadata, dict) and metadata.get("release_id") is not None:
            item["release_id"] = int(metadata["release_id"])
        if row["cardmarket_id"] is not None:
            if row["language_scope"] == "exact":
                item["cardmarket_ids"].append(int(row["cardmarket_id"]))
            elif row["language_scope"] == "mixed":
                item["mixed_cardmarket_ids"].append(int(row["cardmarket_id"]))
    return [
        OnePieceTarget(
            card_id=item["card_id"], language_id=item["language_id"], language=item["language"],
            blueprint_id=item["blueprint_id"], release_id=item["release_id"],
            cardmarket_ids=tuple(sorted(set(item["cardmarket_ids"]))),
            mixed_cardmarket_ids=tuple(sorted(set(item["mixed_cardmarket_ids"]))),
        )
        for item in grouped.values()
    ]


def _offer_fingerprint(offers: list[dict]) -> list[dict]:
    relevant = []
    for offer in offers:
        props = offer.get("properties_hash") or {}
        user = offer.get("user") or {}
        price = offer.get("price") or {}
        relevant.append({
            "seller": user.get("id"),
            "vacation": offer.get("on_vacation"),
            "graded": offer.get("graded"),
            "condition": props.get("condition"),
            "language": props.get("onepiece_language"),
            "signed": props.get("signed"),
            "altered": props.get("altered"),
            "bundle_size": offer.get("bundle_size"),
            "price_cents": offer.get("price_cents", price.get("cents")),
            "currency": offer.get("price_currency", price.get("currency")),
        })
    return sorted(relevant, key=lambda value: json.dumps(value, sort_keys=True, default=str))


def _fingerprint(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _fetch_marketplace(
    client: CardTraderClient,
    targets: list[OnePieceTarget],
) -> dict[tuple[int | None, str], list[dict]]:
    grouped_targets: dict[tuple[int | None, str], set[int]] = defaultdict(set)
    for target in targets:
        if target.blueprint_id is None:
            continue
        grouped_targets[(target.release_id, target.language)].add(target.blueprint_id)
    result: dict[tuple[int | None, str], list[dict]] = {}
    for (release_id, language), blueprint_ids in grouped_targets.items():
        if release_id is None:
            for blueprint_id in blueprint_ids:
                result[(blueprint_id, language)] = client.fetch_marketplace_products(blueprint_id, language)
        else:
            offers = client.fetch_marketplace_expansion(release_id, language)
            by_blueprint: dict[int, list[dict]] = defaultdict(list)
            for offer in offers:
                if offer.get("blueprint_id") is not None:
                    by_blueprint[int(offer["blueprint_id"])].append(offer)
            for blueprint_id in blueprint_ids:
                result[(release_id, language, blueprint_id)] = by_blueprint.get(blueprint_id, [])
    return result


def _existing_fingerprint(conn: sqlite3.Connection, decision: OnePieceDecision) -> bool:
    rows = conn.execute(
        """SELECT metadata FROM printing_price_resolutions
            WHERE card_id=? AND language_id=? AND resolution_method=?""",
        (decision.target.card_id, decision.target.language_id, decision.method),
    ).fetchall()
    for row in rows:
        try:
            metadata = json.loads(row["metadata"] or "{}")
        except json.JSONDecodeError:
            continue
        if metadata.get("snapshot_fingerprint") == decision.fingerprint:
            return True
    return False


def _prepare_one_piece(
    conn: sqlite3.Connection,
    price_index: dict[int, dict],
    cardmarket_observed_at: str,
    marketplace: dict,
    resolution_at: str,
    mode: str,
    report: GameReport,
) -> list[OnePieceDecision]:
    targets = _one_piece_targets(conn)
    report.printings_checked = len(targets)
    decisions: list[OnePieceDecision] = []
    for target in targets:
        exact_prices = [
            (product_id, price_index[product_id])
            for product_id in target.cardmarket_ids
            if product_id in price_index and price_index[product_id].get("trend") not in (None, 0)
        ]
        offers = []
        if target.blueprint_id is not None and target.release_id is not None:
            offers = marketplace.get((target.release_id, target.language, target.blueprint_id), [])
        elif target.blueprint_id is not None:
            offers = marketplace.get((target.blueprint_id, target.language), [])
        resolved: MarketplacePrice = resolve_cardtrader_marketplace(offers, target.language)
        if len(exact_prices) == 1:
            product_id, price = exact_prices[0]
            metadata = {
                "source_observed_at": cardmarket_observed_at,
                "snapshot_fingerprint": _fingerprint({
                    "source": "cardmarket", "product_id": product_id, "language": target.language,
                    "trend": price.get("trend"), "low": price.get("low"), "avg": price.get("avg"),
                }),
            }
            decision = OnePieceDecision(
                target, "cardmarket_exact_language", "cardmarket", str(product_id),
                float(price["trend"]), "EUR", 0, None, None, "high", "exact", metadata,
                metadata["snapshot_fingerprint"],
            )
            report.cardmarket_exact += 1
        elif resolved.current_price is not None:
            metadata = {
                "snapshot_fingerprint": _fingerprint({
                    "source": "cardtrader", "blueprint_id": target.blueprint_id,
                    "language": target.language, "offers": _offer_fingerprint(offers),
                }),
                "cardmarket_exact_candidates": list(target.cardmarket_ids),
            }
            decision = OnePieceDecision(
                target, "cardtrader_marketplace_low_median_5", "cardtrader", str(target.blueprint_id),
                resolved.current_price, resolved.currency, resolved.sample_size,
                resolved.lowest_price, resolved.median_price, resolved.confidence, "exact", metadata,
                metadata["snapshot_fingerprint"],
            )
            report.cardtrader_fallback += 1
            report.confidence[resolved.confidence] += 1
        elif target.mixed_cardmarket_ids:
            metadata = {
                "reason": "Cardmarket product is not exact-language",
                "snapshot_fingerprint": _fingerprint({
                    "source": "mixed", "ids": target.mixed_cardmarket_ids,
                    "language": target.language, "offers": _offer_fingerprint(offers),
                }),
            }
            decision = OnePieceDecision(
                target, "mixed_price_rejected", "cardmarket", ",".join(map(str, target.mixed_cardmarket_ids)),
                None, "EUR", 0, None, None, None, "mixed", metadata, metadata["snapshot_fingerprint"],
            )
            report.mixed_rejected += 1
        else:
            metadata = {
                "snapshot_fingerprint": _fingerprint({
                    "source": "none", "blueprint_id": target.blueprint_id,
                    "language": target.language, "offers": _offer_fingerprint(offers),
                }),
            }
            decision = OnePieceDecision(
                target, "no_exact_language_price", None, str(target.blueprint_id) if target.blueprint_id is not None else None,
                None, None, 0, None, None, None, "exact", metadata, metadata["snapshot_fingerprint"],
            )
            report.no_exact_price += 1
        decisions.append(decision)
        if decision.current_price is None:
            report.missing += 1
        else:
            report.updated += 1
    report.history_rows_planned = len(decisions)
    if mode == "dry-run":
        report.history_rows_skipped = len(decisions)
    return decisions


def _write_magic(conn: sqlite3.Connection, prepared, observed_at: str, imported_at: str, report: GameReport) -> None:
    for target, mapped, _fingerprint_value in prepared:
        cursor = conn.execute(
            """INSERT INTO market_price_history
                 (cardmarket_product_id, observed_at, low, avg, trend, avg1, avg7, avg30,
                  low_alt, avg_alt, trend_alt, avg1_alt, avg7_alt, avg30_alt, imported_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(cardmarket_product_id, observed_at) DO NOTHING""",
            (
                target.product_id, observed_at,
                mapped["low"], mapped["avg"], mapped["trend"], mapped["avg1"], mapped["avg7"], mapped["avg30"],
                mapped["low_alt"], mapped["avg_alt"], mapped["trend_alt"], mapped["avg1_alt"],
                mapped["avg7_alt"], mapped["avg30_alt"], imported_at,
            ),
        )
        report.history_rows_inserted += cursor.rowcount


def _write_one_piece(conn: sqlite3.Connection, decisions: list[OnePieceDecision], resolution_at: str, report: GameReport) -> None:
    for decision in decisions:
        if _existing_fingerprint(conn, decision):
            report.history_rows_skipped += 1
            continue
        insert_price_resolution(
            conn, decision.target.card_id, decision.target.language_id, resolution_at,
            decision.method, decision.source, decision.external_id, decision.current_price,
            decision.currency, decision.sample_size, decision.lowest_price,
            decision.median_price, decision.confidence, decision.language_scope,
            decision.metadata,
        )
        report.history_rows_inserted += 1


def _create_backup(conn: sqlite3.Connection, started_at: str) -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    safe_stamp = started_at.replace(":", "-").replace("+", "_")
    path = BACKUP_DIR / f"tcg_dashboard_{safe_stamp}.db"
    suffix = 1
    while path.exists():
        path = BACKUP_DIR / f"tcg_dashboard_{safe_stamp}_{suffix}.db"
        suffix += 1
    backup_conn = sqlite3.connect(path)
    try:
        conn.backup(backup_conn)
        backup_conn.commit()
    finally:
        backup_conn.close()
    return path


def _print_report(report: WorkflowReport) -> None:
    print("\nPRICE UPDATE COMPLETE")
    print(f"\nMode: {report.mode.upper()}")
    for game in report.games:
        item = report.game_reports.get(game)
        if item is None:
            continue
        print(f"\n{game.replace('_', ' ').title()}")
        print("------")
        print(f"Printings checked: {item.printings_checked}")
        print(f"Cardmarket exact: {item.cardmarket_exact}")
        if game == "one_piece":
            print(f"CardTrader fallback: {item.cardtrader_fallback}")
            print(f"Mixed rejected: {item.mixed_rejected}")
            print(f"No exact price: {item.no_exact_price}")
            print(f"Confidence: high={item.confidence.get('high', 0)} medium={item.confidence.get('medium', 0)} low={item.confidence.get('low', 0)}")
        print(f"Updated: {item.updated}")
        print(f"Missing: {item.missing}")
        print(f"History rows inserted: {item.history_rows_inserted}")
        if report.mode == "dry-run":
            print(f"History rows would insert: {item.history_rows_planned}")
        print(f"Errors: {len(item.errors)}")
    print("\nDatabase")
    print("--------")
    print(f"Transaction: {report.transaction}")
    print(f"Integrity: {report.integrity}")
    print(f"Foreign keys: {report.foreign_keys}")
    if report.backup:
        print(f"Backup: {report.backup}")
    if report.errors:
        print("\nErrors:")
        for error in report.errors:
            print(f"- {error}")
    print(f"\nResult: {report.result}")


def _write_log(report: WorkflowReport) -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = report.started_at.replace(":", "-").replace("+", "_")
    path = LOG_DIR / f"{stamp}.json"
    path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def run_workflow(
    *,
    mode: str,
    games: tuple[str, ...],
    db_path: Path = DEFAULT_DB_PATH,
    now: str | None = None,
    download_fn: Callable | None = None,
    cardtrader_client: CardTraderClient | None = None,
) -> tuple[WorkflowReport, int]:
    started_at = now or _utc_now()
    report = WorkflowReport(mode, games, str(db_path.resolve()), started_at)
    start_clock = dt.datetime.now(dt.timezone.utc)
    conn: sqlite3.Connection | None = None
    personal_before: str | None = None
    try:
        if not db_path.is_file():
            raise WorkflowError(f"Database does not exist: {db_path.resolve()}")
        validation_conn = _connect(db_path)
        try:
            integrity, _ = _validate_database(validation_conn)
            report.integrity = integrity.upper()
            report.foreign_keys = "OK"
        finally:
            validation_conn.close()

        if "one_piece" in games:
            try:
                if cardtrader_client is None:
                    load_cardtrader_token()
                report.providers["cardtrader"] = "configured"
            except CardTraderConfigurationError as exc:
                raise ConfigurationError(str(exc)) from exc

        sources = _load_cardmarket_sources(games, report, download_fn=download_fn)

        conn = _connect(db_path)
        _validate_database(conn)
        personal_before = _personal_snapshot(conn)

        prepared_magic = None
        prepared_one_piece = None
        if "magic" in games:
            magic_report = GameReport("magic")
            report.game_reports["magic"] = magic_report
            observed_at, price_index = sources["magic"]
            prepared_magic = _prepare_magic(conn, price_index, observed_at, mode, magic_report)
        if "one_piece" in games:
            one_piece_report = GameReport("one_piece")
            report.game_reports["one_piece"] = one_piece_report
            observed_at, price_index = sources["one_piece"]
            targets = _one_piece_targets(conn)
            client = cardtrader_client or CardTraderClient()
            marketplace = _fetch_marketplace(client, targets)
            report.providers["cardtrader"] = "ok"
            for key, offers in marketplace.items():
                report.snapshots[f"cardtrader:{key}"] = _fingerprint({"offers": _offer_fingerprint(offers)})
            prepared_one_piece = _prepare_one_piece(
                conn, price_index, observed_at, marketplace, started_at, mode, one_piece_report,
            )

        if mode == "dry-run":
            if _personal_snapshot(conn) != personal_before:
                raise WorkflowError("Collection/Wishlist changed during dry-run")
            report.transaction = "NOT_APPLIED"
            report.collection_wishlist_unchanged = True
            report.result = "SUCCESS"
        else:
            # The online backup is read-only. Create it before acquiring the write
            # transaction; holding BEGIN IMMEDIATE while backing up can make SQLite
            # wait on the backup connection indefinitely.
            report.backup = str(_create_backup(conn, started_at).resolve())
            try:
                conn.execute("BEGIN IMMEDIATE")
            except sqlite3.OperationalError as exc:
                if "locked" in str(exc).lower() or "busy" in str(exc).lower():
                    raise LockError("Could not acquire SQLite write lock; another operation is in progress") from exc
                raise
            imported_at = _utc_now()
            if prepared_magic is not None:
                _write_magic(conn, prepared_magic, sources["magic"][0], imported_at, report.game_reports["magic"])
            if prepared_one_piece is not None:
                _write_one_piece(conn, prepared_one_piece, started_at, report.game_reports["one_piece"])
            if _personal_snapshot(conn) != personal_before:
                raise WorkflowError("Collection/Wishlist changed during pricing transaction")
            integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
            foreign_keys = conn.execute("PRAGMA foreign_key_check").fetchall()
            if integrity != "ok":
                raise WorkflowError(f"PRAGMA integrity_check failed before commit: {integrity}")
            if foreign_keys:
                raise WorkflowError(f"PRAGMA foreign_key_check failed before commit with {len(foreign_keys)} rows")
            conn.commit()
            report.transaction = "COMMITTED"
            report.integrity = "OK"
            report.foreign_keys = "OK"
            report.collection_wishlist_unchanged = True
            post_conn = _connect(db_path)
            try:
                post_integrity = post_conn.execute("PRAGMA integrity_check").fetchone()[0]
                post_fks = post_conn.execute("PRAGMA foreign_key_check").fetchall()
                if post_integrity != "ok" or post_fks:
                    raise WorkflowError("Post-commit SQLite validation failed")
                if _personal_snapshot(post_conn) != personal_before:
                    raise WorkflowError("Collection/Wishlist changed during pricing update")
            finally:
                post_conn.close()
            report.result = "SUCCESS"
    except Exception as exc:
        if conn is not None and report.transaction != "COMMITTED":
            try:
                conn.rollback()
            except sqlite3.Error:
                pass
        report.transaction = "ROLLED_BACK" if mode == "apply" else report.transaction
        report.result = "FAILED"
        report.errors.append(str(exc))
        code = 2 if isinstance(exc, CardTraderConfigurationError) else getattr(exc, "exit_code", 1)
    else:
        code = 0
    finally:
        if conn is not None:
            conn.close()
        report.duration_seconds = round((dt.datetime.now(dt.timezone.utc) - start_clock).total_seconds(), 3)
        try:
            _write_log(report)
        except OSError as exc:
            report.errors.append(f"Could not write pricing log: {exc}")
            if code == 0:
                code = 1
                report.result = "FAILED"
    return report, code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Update Magic and One Piece market prices safely.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Resolve and report without writing the database.")
    mode.add_argument("--apply", action="store_true", help="Apply the resolved pricing in one transaction.")
    parser.add_argument("--game", choices=("all", *SUPPORTED_GAMES), default="all")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    games = SUPPORTED_GAMES if args.game == "all" else (args.game,)
    mode = "dry-run" if args.dry_run else "apply"
    print("TCG PRICE UPDATE")
    print(f"\nMode: {mode.upper()}")
    print(f"Games: {args.game}")
    print(f"Database: {DEFAULT_DB_PATH.resolve()}")
    report, code = run_workflow(mode=mode, games=tuple(games), db_path=DEFAULT_DB_PATH)
    _print_report(report)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
