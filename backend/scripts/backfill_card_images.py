"""Backfill normalized remote card image metadata.

The scope is DISTINCT collection card_id. Scryfall remains primary; CardTrader is
an exact fallback for the LOTR Art Series catalog and never participates in pricing.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.images.cardtrader import CardTraderCatalog, CardTraderClient
from backend.images.resolver import ImageResolution, resolve_scryfall_card, resolve_scryfall_raw

DB_PATH = Path(__file__).resolve().parent.parent / "db" / "tcg_dashboard.db"
SCRYFALL_TIMEOUT_SECONDS = 10
SCRYFALL_DELAY_SECONDS = 0.15
SCRYFALL_BACKOFF_SECONDS = (1.0, 2.0)

CARD_IMAGES_SCHEMA = """
CREATE TABLE IF NOT EXISTS card_images (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id                 INTEGER NOT NULL REFERENCES cards (id),
    source                  TEXT NOT NULL CHECK (source IN ('scryfall', 'cardtrader', 'manual')),
    source_card_id          TEXT,
    source_variant          TEXT,
    source_collector_number TEXT,
    language                TEXT NOT NULL,
    face_index              INTEGER NOT NULL CHECK (face_index >= 0),
    image_url_small         TEXT,
    image_url_large         TEXT,
    image_language_scope    TEXT NOT NULL DEFAULT 'unknown',
    is_language_fallback    INTEGER NOT NULL DEFAULT 0 CHECK (is_language_fallback IN (0, 1)),
    match_quality           TEXT NOT NULL CHECK (match_quality IN ('exact', 'representative', 'manual')),
    status                  TEXT NOT NULL CHECK (status IN ('resolved', 'ambiguous', 'missing', 'error')),
    last_checked_at         TEXT NOT NULL,
    created_at              TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (card_id, source, language, face_index)
);
"""


@dataclass(frozen=True)
class CardScope:
    card_id: int
    name: str
    scryfall_raw: str | None
    cardmarket_ids: tuple[int, ...]
    collection_rows: int
    collection_copies: int


@dataclass
class BackfillReport:
    total_canonical_cards: int = 0
    collection_rows_total: int = 0
    collection_copies_total: int = 0
    collection_rows_without_card_id: int = 0
    collection_copies_without_card_id: int = 0
    existing_exact: int = 0
    scryfall_existing_exact: int = 0
    cardtrader_existing_exact: int = 0
    resolved_exact: int = 0
    cardtrader_exact_candidates: int = 0
    gold_stamped_candidates: int = 0
    cardtrader_valid_image_candidates: int = 0
    gold_stamped_valid_image_candidates: int = 0
    representative: int = 0
    multi_face: int = 0
    ambiguous: list[tuple[int, str]] = field(default_factory=list)
    missing: list[tuple[int, str]] = field(default_factory=list)
    errors: list[tuple[int, str]] = field(default_factory=list)
    cardtrader_ambiguous: list[tuple[int, str]] = field(default_factory=list)
    cardtrader_missing: list[tuple[int, str]] = field(default_factory=list)
    cardtrader_errors: list[tuple[int, str]] = field(default_factory=list)
    invalid_urls: int = 0
    resolved_without_network: int = 0
    network_requests: int = 0
    scryfall_network_requests: int = 0
    cardtrader_network_requests: int = 0
    resolved_from_network: int = 0
    would_request_network: int = 0
    image_card_ids: set[int] = field(default_factory=set)
    dry_run: bool = True

    @property
    def missing_count(self) -> int:
        return len(self.missing)

    @property
    def ambiguous_count(self) -> int:
        return len(self.ambiguous)

    @property
    def error_count(self) -> int:
        return len(self.errors)

    def print_summary(self, scopes: list[CardScope]) -> None:
        rows_with_image = sum(scope.collection_rows for scope in scopes if scope.card_id in self.image_card_ids)
        copies_with_image = sum(scope.collection_copies for scope in scopes if scope.card_id in self.image_card_ids)
        print("=" * 72)
        print("REPORTE DE CARD IMAGES")
        print("=" * 72)
        print(f"Modo: {'dry-run' if self.dry_run else 'apply'}")
        print(f"Canonical cards inspeccionadas: {self.total_canonical_cards}")
        print(f"Collection rows impactadas: {self.collection_rows_total}")
        print(f"Collection copies impactadas: {self.collection_copies_total}")
        print(f"Rows sin card_id: {self.collection_rows_without_card_id}")
        print(f"Copies sin card_id: {self.collection_copies_without_card_id}")
        print("")
        print(f"Exact Scryfall existentes: {self.scryfall_existing_exact}")
        print(f"Exact CardTrader existentes: {self.cardtrader_existing_exact}")
        print(f"CardTrader exact candidates: {self.cardtrader_exact_candidates}")
        print(f"Gold-Stamped candidates: {self.gold_stamped_candidates}")
        print(f"CardTrader candidates con image_url válida: {self.cardtrader_valid_image_candidates}")
        print(f"Gold-Stamped candidates con image_url válida: {self.gold_stamped_valid_image_candidates}")
        print(f"Canonical cards con imagen/candidate exacto: {len(self.image_card_ids)}")
        print(f"Collection rows con imagen/candidate exacto: {rows_with_image}")
        print(f"Collection copies con imagen/candidate exacto: {copies_with_image}")
        print("")
        print(f"Exact resueltas/persistidas: {self.resolved_exact}")
        print(f"Representative: {self.representative}")
        print(f"Multi-face canonical cards: {self.multi_face}")
        print(f"Scryfall missing/error: {len(self.missing)} / {len(self.errors)}")
        print(f"Scryfall ambiguous: {len(self.ambiguous)}")
        print(f"CardTrader missing: {len(self.cardtrader_missing)}")
        print(f"CardTrader ambiguous: {len(self.cardtrader_ambiguous)}")
        print(f"CardTrader invalid URLs/errors: {len(self.cardtrader_errors)}")
        print(f"Invalid URLs: {self.invalid_urls}")
        print("")
        print(f"Network requests realizadas: {self.network_requests}")
        print(f"  Scryfall: {self.scryfall_network_requests}")
        print(f"  CardTrader: {self.cardtrader_network_requests}")
        print(f"Network requests requeridas/no ejecutadas: {self.would_request_network}")
        print("=" * 72)


def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _source_check_values(table_sql: str | None) -> set[str] | None:
    if not table_sql:
        return None
    match = re.search(r"source\s+IN\s*\(([^)]*)\)", table_sql, re.IGNORECASE)
    if not match:
        return None
    return {value.strip().strip("'\"").lower() for value in match.group(1).split(",")}


def _card_images_snapshot(conn: sqlite3.Connection, table: str, columns: tuple[str, ...]) -> list[tuple]:
    quoted = ", ".join(f'"{column}"' for column in columns)
    return [tuple(row) for row in conn.execute(f'SELECT {quoted} FROM "{table}" ORDER BY id')]


def _rebuild_card_images(conn: sqlite3.Connection, old_columns: tuple[str, ...]) -> None:
    legacy_table = "card_images__legacy_migration"
    if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (legacy_table,)).fetchone():
        raise RuntimeError(f"tabla temporal inesperada existente: {legacy_table}")

    old_rows = _card_images_snapshot(conn, "card_images", old_columns)
    old_indexes = []
    for row in conn.execute("PRAGMA index_list(card_images)").fetchall():
        index_sql = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='index' AND name=?", (row[1],)
        ).fetchone()
        if row[3] != "pk" and index_sql and index_sql[0]:
            old_indexes.append((row[1], index_sql[0]))

    conn.execute(f'ALTER TABLE "card_images" RENAME TO "{legacy_table}"')
    for index_name, _ in old_indexes:
        conn.execute(f'DROP INDEX "{index_name}"')
    conn.execute(CARD_IMAGES_SCHEMA)

    common_columns = tuple(column for column in old_columns if column in {
        "id", "card_id", "source", "source_card_id", "language", "face_index",
        "image_url_small", "image_url_large", "image_language_scope", "is_language_fallback",
        "match_quality", "status",
        "last_checked_at", "created_at", "updated_at",
    })
    quoted = ", ".join(f'"{column}"' for column in common_columns)
    conn.execute(f'INSERT INTO "card_images" ({quoted}) SELECT {quoted} FROM "{legacy_table}"')
    if old_rows != _card_images_snapshot(conn, "card_images", old_columns):
        raise RuntimeError("card_images migration changed existing rows")

    conn.execute(f'DROP TABLE "{legacy_table}"')
    for _, index_sql in old_indexes:
        conn.execute(index_sql.replace(legacy_table, "card_images"))


def ensure_schema(conn: sqlite3.Connection) -> None:
    table_row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='card_images'"
    ).fetchone()
    if table_row is None:
        conn.execute(CARD_IMAGES_SCHEMA)
        return

    existing_columns = tuple(row[1] for row in conn.execute("PRAGMA table_info(card_images)"))
    source_values = _source_check_values(table_row[0])
    if source_values is not None and "cardtrader" not in source_values:
        _rebuild_card_images(conn, existing_columns)
        return

    if "source_variant" not in existing_columns:
        conn.execute("ALTER TABLE card_images ADD COLUMN source_variant TEXT")
    if "source_collector_number" not in existing_columns:
        conn.execute("ALTER TABLE card_images ADD COLUMN source_collector_number TEXT")
    if "image_language_scope" not in existing_columns:
        conn.execute("ALTER TABLE card_images ADD COLUMN image_language_scope TEXT NOT NULL DEFAULT 'unknown'")
    if "is_language_fallback" not in existing_columns:
        conn.execute("ALTER TABLE card_images ADD COLUMN is_language_fallback INTEGER NOT NULL DEFAULT 0")


def fetch_scope(conn: sqlite3.Connection) -> list[CardScope]:
    rows = conn.execute(
        """SELECT c.id AS card_id, c.name, c.scryfall_raw,
                  GROUP_CONCAT(DISTINCT cp.cardmarket_id_product) AS product_ids,
                  COUNT(ci.id) AS collection_rows,
                  COALESCE(SUM(ci.quantity), 0) AS collection_copies
             FROM collection_items ci
             JOIN cards c ON c.id = ci.card_id
             LEFT JOIN cardmarket_products cp ON cp.id = ci.cardmarket_product_id
            WHERE ci.card_id IS NOT NULL
            GROUP BY c.id, c.name, c.scryfall_raw
            ORDER BY c.id"""
    ).fetchall()
    return [
        CardScope(
            card_id=row["card_id"],
            name=row["name"],
            scryfall_raw=row["scryfall_raw"],
            cardmarket_ids=tuple(sorted(int(value) for value in (row["product_ids"] or "").split(",") if value)),
            collection_rows=row["collection_rows"],
            collection_copies=row["collection_copies"],
        )
        for row in rows
    ]


def fetch_manual_impact(conn: sqlite3.Connection) -> tuple[int, int]:
    row = conn.execute(
        "SELECT COUNT(*) AS rows_total, COALESCE(SUM(quantity), 0) AS copies_total FROM collection_items WHERE card_id IS NULL"
    ).fetchone()
    return row["rows_total"], row["copies_total"]


def has_exact_image(conn: sqlite3.Connection, card_id: int, source: str) -> bool:
    row = conn.execute(
        """SELECT 1 FROM card_images
            WHERE card_id = ? AND source = ? AND status = 'resolved'
              AND match_quality = 'exact'
              AND (image_url_small IS NOT NULL OR image_url_large IS NOT NULL)
            LIMIT 1""",
        (card_id, source),
    ).fetchone()
    return row is not None


def exact_image_variant(conn: sqlite3.Connection, card_id: int, source: str) -> str | None:
    row = conn.execute(
        """SELECT source_variant FROM card_images
            WHERE card_id = ? AND source = ? AND status = 'resolved'
              AND match_quality = 'exact'
              AND (image_url_small IS NOT NULL OR image_url_large IS NOT NULL)
            ORDER BY face_index LIMIT 1""",
        (card_id, source),
    ).fetchone()
    return row[0] if row else None


def fetch_scryfall_card(cardmarket_id_product: int) -> tuple[dict | None, str | None]:
    request = urllib.request.Request(
        f"https://api.scryfall.com/cards/cardmarket/{cardmarket_id_product}",
        headers={
            "User-Agent": "TCGDashboard/1.0 (personal collection tool; card images backfill)",
            "Accept": "application/json;q=0.9,*/*;q=0.8",
        },
    )
    for attempt in range(1 + len(SCRYFALL_BACKOFF_SECONDS)):
        try:
            with urllib.request.urlopen(request, timeout=SCRYFALL_TIMEOUT_SECONDS) as response:
                return json.loads(response.read()), None
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None, "HTTP 404"
            if exc.code in {429, 503} and attempt < len(SCRYFALL_BACKOFF_SECONDS):
                time.sleep(SCRYFALL_BACKOFF_SECONDS[attempt])
                continue
            return None, f"HTTP {exc.code}"
        except urllib.error.URLError as exc:
            return None, f"network error: {exc}"
        except (OSError, json.JSONDecodeError) as exc:
            return None, f"{type(exc).__name__}: {exc}"
    return None, "exhausted retries"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def upsert_resolution(conn: sqlite3.Connection, card_id: int, resolution: ImageResolution, checked_at: str) -> None:
    faces = resolution.faces or [type("EmptyFace", (), {"face_index": 0, "small_url": None, "large_url": None})()]
    for face in faces:
        conn.execute(
            """INSERT INTO card_images
                   (card_id, source, source_card_id, source_variant, source_collector_number,
                    language, face_index, image_url_small, image_url_large,
                    image_language_scope, is_language_fallback, match_quality, status, last_checked_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(card_id, source, language, face_index) DO UPDATE SET
                   source_card_id = excluded.source_card_id,
                   source_variant = excluded.source_variant,
                   source_collector_number = excluded.source_collector_number,
                   image_url_small = excluded.image_url_small,
                   image_url_large = excluded.image_url_large,
                   image_language_scope = excluded.image_language_scope,
                   is_language_fallback = excluded.is_language_fallback,
                   match_quality = excluded.match_quality,
                   status = excluded.status,
                   last_checked_at = excluded.last_checked_at,
                   updated_at = CURRENT_TIMESTAMP""",
            (
                card_id, resolution.source, resolution.source_card_id, resolution.source_variant,
                resolution.source_collector_number, resolution.language, face.face_index,
                face.small_url, face.large_url,
                resolution.actual_image_language or resolution.language,
                int(resolution.is_language_fallback), resolution.match_quality,
                resolution.status, checked_at,
            ),
        )


def _is_exact(resolution: ImageResolution | None) -> bool:
    return bool(resolution and resolution.status == "resolved" and resolution.match_quality == "exact" and resolution.faces)


def _record_resolution(report: BackfillReport, scope: CardScope, resolution: ImageResolution, from_network: bool) -> None:
    if _is_exact(resolution):
        report.resolved_exact += 1
        report.image_card_ids.add(scope.card_id)
        if len(resolution.faces) > 1:
            report.multi_face += 1
        if from_network:
            report.resolved_from_network += 1
        else:
            report.resolved_without_network += 1
        return
    if resolution.match_quality == "representative":
        report.representative += 1
    reason = resolution.reason or resolution.status
    if resolution.status == "ambiguous":
        report.ambiguous.append((scope.card_id, reason))
    elif resolution.status == "missing":
        report.missing.append((scope.card_id, reason))
    else:
        report.errors.append((scope.card_id, reason))
        if "validation" in reason.lower():
            report.invalid_urls += 1


def _record_cardtrader_result(report: BackfillReport, scope: CardScope, resolution: ImageResolution) -> None:
    if _is_exact(resolution):
        report.cardtrader_exact_candidates += 1
        report.cardtrader_valid_image_candidates += 1
        report.image_card_ids.add(scope.card_id)
        if resolution.source_variant == "Gold-Stamped":
            report.gold_stamped_candidates += 1
            report.gold_stamped_valid_image_candidates += 1
        return
    reason = resolution.reason or resolution.status
    if resolution.status == "ambiguous":
        report.cardtrader_ambiguous.append((scope.card_id, reason))
    elif resolution.status == "missing":
        report.cardtrader_missing.append((scope.card_id, reason))
    else:
        report.cardtrader_errors.append((scope.card_id, reason))
        if "validation" in reason.lower():
            report.invalid_urls += 1


def resolve_cardtrader_scope(catalog: CardTraderCatalog, scope: CardScope) -> ImageResolution:
    matches = []
    for product_id in scope.cardmarket_ids:
        matches.extend(catalog.by_cardmarket_id.get(product_id, ()))
    unique_matches = {blueprint.get("id"): blueprint for blueprint in matches}
    if not unique_matches:
        return ImageResolution(
            source="cardtrader", source_card_id=None, language="unknown", match_quality="exact",
            status="missing", reason=f"no CardTrader Blueprint for cardmarket_ids={scope.cardmarket_ids}",
        )
    if len(unique_matches) > 1:
        return ImageResolution(
            source="cardtrader", source_card_id=None, language="unknown", match_quality="exact",
            status="ambiguous", reason=f"multiple CardTrader Blueprints for cardmarket_ids={scope.cardmarket_ids}: {sorted(unique_matches)}",
        )
    blueprint = next(iter(unique_matches.values()))
    product_id = next(product_id for product_id in scope.cardmarket_ids if blueprint in catalog.by_cardmarket_id.get(product_id, ()))
    return catalog.resolve_product_id(product_id)


def run_backfill(
    db_path: Path = DB_PATH,
    apply_changes: bool = False,
    allow_network: bool = False,
    fetcher: Callable[[int], tuple[dict | None, str | None]] = fetch_scryfall_card,
    cardtrader_catalog: CardTraderCatalog | None = None,
    cardtrader_client: CardTraderClient | None = None,
    allow_cardtrader_network: bool = False,
) -> tuple[BackfillReport, list[CardScope]]:
    report = BackfillReport(dry_run=not apply_changes)
    conn = connect(db_path)
    try:
        ensure_schema(conn)
        scopes = fetch_scope(conn)
        manual_rows, manual_copies = fetch_manual_impact(conn)
        report.total_canonical_cards = len(scopes)
        report.collection_rows_without_card_id = manual_rows
        report.collection_copies_without_card_id = manual_copies
        report.collection_rows_total = sum(scope.collection_rows for scope in scopes) + manual_rows
        report.collection_copies_total = sum(scope.collection_copies for scope in scopes) + manual_copies
        checked_at = _now()
        catalog = cardtrader_catalog

        for scope in scopes:
            if has_exact_image(conn, scope.card_id, "scryfall"):
                report.existing_exact += 1
                report.scryfall_existing_exact += 1
                report.image_card_ids.add(scope.card_id)
                continue

            if scope.scryfall_raw:
                scryfall_resolution = resolve_scryfall_raw(scope.scryfall_raw)
                _record_resolution(report, scope, scryfall_resolution, from_network=False)
                if _is_exact(scryfall_resolution):
                    if apply_changes:
                        upsert_resolution(conn, scope.card_id, scryfall_resolution, checked_at)
                    continue

            if has_exact_image(conn, scope.card_id, "cardtrader"):
                report.existing_exact += 1
                report.cardtrader_existing_exact += 1
                report.cardtrader_exact_candidates += 1
                report.cardtrader_valid_image_candidates += 1
                if exact_image_variant(conn, scope.card_id, "cardtrader") == "Gold-Stamped":
                    report.gold_stamped_candidates += 1
                    report.gold_stamped_valid_image_candidates += 1
                report.image_card_ids.add(scope.card_id)
                continue

            if apply_changes and allow_network and len(scope.cardmarket_ids) == 1:
                data, error = fetcher(scope.cardmarket_ids[0])
                time.sleep(SCRYFALL_DELAY_SECONDS)
                report.network_requests += 1
                report.scryfall_network_requests += 1
                if data is not None:
                    scryfall_resolution = resolve_scryfall_card(data)
                    _record_resolution(report, scope, scryfall_resolution, from_network=True)
                    if _is_exact(scryfall_resolution):
                        upsert_resolution(conn, scope.card_id, scryfall_resolution, checked_at)
                        continue
                else:
                    scryfall_resolution = ImageResolution(
                        source="scryfall", source_card_id=None, language="unknown", match_quality="exact",
                        status="missing" if error == "HTTP 404" else "error",
                        reason=f"direct Scryfall lookup failed for cardmarket_id_product={scope.cardmarket_ids[0]}: {error}",
                    )
                    _record_resolution(report, scope, scryfall_resolution, from_network=True)
                    upsert_resolution(conn, scope.card_id, scryfall_resolution, checked_at)

            if not allow_cardtrader_network and catalog is None:
                report.would_request_network += 1
                continue

            if catalog is None:
                catalog = (cardtrader_client or CardTraderClient()).fetch_blueprints()
                report.network_requests += 1
                report.cardtrader_network_requests += 1

            cardtrader_resolution = resolve_cardtrader_scope(catalog, scope)
            _record_cardtrader_result(report, scope, cardtrader_resolution)
            if _is_exact(cardtrader_resolution) and apply_changes:
                upsert_resolution(conn, scope.card_id, cardtrader_resolution, checked_at)
                report.resolved_exact += 1

        if apply_changes:
            conn.commit()
        else:
            conn.rollback()
    finally:
        conn.close()
    return report, scopes


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill normalized card image metadata.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Report without SQLite writes or Scryfall network lookups.")
    mode.add_argument("--apply", action="store_true", help="Write exact image metadata and allow Scryfall/CardTrader lookups.")
    parser.add_argument("--db", type=Path, default=DB_PATH, help="SQLite DB path.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    report, scopes = run_backfill(
        db_path=args.db,
        apply_changes=args.apply,
        allow_network=args.apply,
        allow_cardtrader_network=True,
    )
    report.print_summary(scopes)
