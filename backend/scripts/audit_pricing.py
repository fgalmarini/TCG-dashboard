"""Read-only Cardmarket pricing and identity audit.

The audit deliberately lives outside the importer and the pricing updater.  It only
reads SQLite and public Cardmarket Product Catalogue / Price Guide snapshots; reports
are the only persistent output of the command.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import re
import sqlite3
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
IMPORTER_ROOT = REPO_ROOT / "backend" / "importer"
for _path in (REPO_ROOT, IMPORTER_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from config import CARDMARKET_BASE_URL, GAMES  # noqa: E402
from downloader import download_all  # noqa: E402
from parser import parse_one_piece_name  # noqa: E402


GAME_ORDER = ("one_piece", "magic")
SOURCE_KINDS = ("products", "price_guide")
SOURCE_URLS = {
    (game, kind): f"{CARDMARKET_BASE_URL}/{segment}/{filename}_{GAMES[game]['cardmarket_game_id']}.json"
    for game in GAME_ORDER
    for kind, segment, filename in (
        ("price_guide", "priceGuide", "price_guide"),
        ("products", "productList", "products_singles"),
    )
}
METRICS = ("low", "trend", "avg1", "avg7", "avg30")
FOIL_METRICS = ("low_alt", "trend_alt", "avg1_alt", "avg7_alt", "avg30_alt")
CAUSES = (
    "wrong_reprint", "wrong_expansion", "wrong_language", "wrong_version",
    "wrong_finish", "wrong_treatment", "blueprint_collision", "wrong_cardmarket_id",
    "missing_cardmarket_id", "stale_price", "currency_mismatch", "metric_mismatch",
    "ambiguous_identity", "missing_product", "unknown",
)


class AuditError(RuntimeError):
    """Expected, user-actionable audit failure."""


@dataclass(frozen=True)
class SourceSnapshot:
    game: str
    kind: str
    url: str
    path: Path
    created_at: str
    version: Any
    records: list[dict]
    size_bytes: int
    sha256: str

    def manifest(self, audited_at: str) -> dict:
        return {
            "game": self.game,
            "source_type": self.kind,
            "audit_timestamp": audited_at,
            "url": self.url,
            "filename": self.path.name,
            "path": str(self.path.resolve()),
            "file_size": self.size_bytes,
            "createdAt": self.created_at,
            "sha256": self.sha256,
            "record_count": len(self.records),
            "schema_version": self.version,
        }


@dataclass
class IdentityResult:
    status: str
    resolved_id: int | None
    stored_ids: list[int]
    candidates: list[int]
    reason: str
    evidence: dict
    primary_cause: str | None = None


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def parse_timestamp(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    raw = str(value).strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        result = dt.datetime.fromisoformat(raw)
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S%z"):
            try:
                result = dt.datetime.strptime(str(value), fmt)
                break
            except ValueError:
                continue
        else:
            return None
    if result.tzinfo is None:
        result = result.replace(tzinfo=dt.timezone.utc)
    return result.astimezone(dt.timezone.utc)


def normalize(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "", text.casefold())


def normalize_number(value: Any) -> str:
    return normalize(value).upper()


def extract_version(value: Any) -> str | None:
    match = re.search(r"(?:\(\s*|\b)V\.?\s*(\d+)\s*\)?", str(value or ""), re.IGNORECASE)
    return f"V.{match.group(1)}" if match else None


def parse_product_identity(game: str, product: dict) -> dict:
    raw_name = str(product.get("name") or "")
    if game == "one_piece":
        number, name = parse_one_piece_name(raw_name)
    else:
        number, name = None, raw_name
        match = re.search(r"\(([^()]*)\)\s*$", raw_name)
        if match and re.fullmatch(r"[A-Za-z0-9/ -]+", match.group(1)):
            number = match.group(1).strip()
            name = raw_name[:match.start()].strip()
    return {
        "idProduct": int(product["idProduct"]),
        "name": raw_name,
        "parsed_name": name,
        "card_number": number,
        "version": extract_version(raw_name),
        "idExpansion": product.get("idExpansion"),
        "idCategory": product.get("idCategory"),
        "idMetacard": product.get("idMetacard"),
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AuditError(f"No se pudo leer JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise AuditError(f"Snapshot incompatible (raíz no es objeto): {path}")
    return value


def _expected_category_ids(conn: sqlite3.Connection) -> dict[str, set[int]]:
    rows = conn.execute(
        """SELECT g.code, cc.cardmarket_id_category
             FROM cardmarket_categories cc JOIN games g ON g.id=cc.game_id
            WHERE g.code IN ('one_piece', 'magic')"""
    ).fetchall()
    return {game: {int(row[1]) for row in rows if row[0] == game} for game in GAME_ORDER}


def _candidate_source_files(source_dir: Path, game: str, kind: str, category_ids: set[int]) -> list[tuple[Path, dict, list[dict]]]:
    if not source_dir.is_dir():
        raise AuditError(f"--source-dir no existe o no es un directorio: {source_dir}")
    key = "products" if kind == "products" else "priceGuides"
    candidates = []
    for path in sorted(source_dir.rglob("*.json")):
        payload = _load_json(path)
        records = payload.get(key)
        if not isinstance(records, list) or not records:
            continue
        if not isinstance(payload.get("createdAt"), str) or not payload["createdAt"].strip():
            continue
        if not all(isinstance(row, dict) and row.get("idProduct") is not None for row in records):
            continue
        record_categories = {int(row["idCategory"]) for row in records if row.get("idCategory") is not None}
        path_raw = path.as_posix().casefold()
        path_hint = normalize(path_raw)
        explicit_game = (
            (game == "magic" and "magic" in path_raw)
            or (game == "one_piece" and ("one-piece" in path_raw or "one_piece" in path_raw or "onepiece" in path_hint))
        )
        other_game = (
            (game == "magic" and ("one-piece" in path_raw or "one_piece" in path_raw or "onepiece" in path_hint))
            or (game == "one_piece" and "magic" in path_raw)
        )
        game_id_token = re.search(rf"(?:^|[_-]){GAMES[game]['cardmarket_game_id']}(?:$|[_.-])", path_raw) is not None
        game_hint = (explicit_game or (game_id_token and not other_game))
        if category_ids and record_categories.intersection(category_ids):
            game_hint = True
        if game_hint:
            candidates.append((path, payload, records))
    return candidates


def load_snapshots(source_dir: Path, games: tuple[str, ...], conn: sqlite3.Connection, audited_at: str) -> tuple[dict[str, dict[str, SourceSnapshot]], dict]:
    category_ids = _expected_category_ids(conn)
    snapshots: dict[str, dict[str, SourceSnapshot]] = {}
    manifest = {"audit_timestamp": audited_at, "sources": []}
    for game in games:
        snapshots[game] = {}
        for kind in SOURCE_KINDS:
            candidates = _candidate_source_files(source_dir, game, kind, category_ids.get(game, set()))
            if len(candidates) != 1:
                expected = f"{game}/{kind}"
                if not candidates:
                    raise AuditError(f"Falta snapshot compatible para {expected} en {source_dir}")
                raise AuditError(f"Hay múltiples snapshots compatibles para {expected} en {source_dir}")
            path, payload, records = candidates[0]
            if kind == "products":
                required = ("idProduct", "idCategory", "idExpansion", "name")
            else:
                required = ("idProduct", "low")
            if kind == "products":
                missing = [field for field in required if not all(field in row and row[field] is not None for row in records)]
            else:
                # A Price Guide legitimately contains products with no usable
                # Trend.  The field must exist in the schema somewhere; those
                # individual rows are reported as UNPRICED instead of guessed.
                missing = [field for field in required if not any(field in row for row in records)]
            if missing:
                raise AuditError(f"Snapshot incompatible para {game}/{kind}: faltan campos {missing}")
            snapshot = SourceSnapshot(
                game, kind, SOURCE_URLS[(game, kind)], path, payload["createdAt"],
                payload.get("version"), records, path.stat().st_size, sha256_file(path),
            )
            snapshots[game][kind] = snapshot
            manifest["sources"].append(snapshot.manifest(audited_at))
        product_records = snapshots[game]["products"].records
        guide_records = snapshots[game]["price_guide"].records
        product_ids = {int(row["idProduct"]) for row in product_records}
        guide_ids = {int(row["idProduct"]) for row in guide_records}
        if not product_ids.intersection(guide_ids):
            raise AuditError(f"Snapshots incompatibles para {game}: no comparten idProduct")
        category_names = {normalize(row.get("categoryName")) for row in product_records if row.get("categoryName")}
        expected_category_token = "magic" if game == "magic" else "onepiece"
        if category_names and not all(expected_category_token in name for name in category_names):
            raise AuditError(f"Snapshot incompatible para {game}: categoryName no corresponde al juego esperado")
    return snapshots, manifest


def acquire_sources(source_dir: Path | None, games: tuple[str, ...], conn: sqlite3.Connection, audited_at: str) -> tuple[dict[str, dict[str, SourceSnapshot]], dict]:
    if source_dir is None:
        try:
            download_all(games=games)
        except Exception as exc:
            raise AuditError(f"Descarga oficial de Cardmarket falló: {exc}") from exc
        source_dir = REPO_ROOT / "price-history"
    return load_snapshots(source_dir, games, conn, audited_at)


def connect_read_only(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise AuditError(f"DB no existe: {path.resolve()}")
    uri = f"file:{path.resolve()}?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True)
    except sqlite3.Error as exc:
        raise AuditError(f"No se pudo abrir DB en modo read-only: {exc}") from exc
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA query_only=ON")
        conn.execute("PRAGMA foreign_keys=ON")
        _assert_read_only(conn)
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise AuditError(f"PRAGMA integrity_check falló: {integrity}")
        if conn.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise AuditError("PRAGMA foreign_key_check encontró errores")
    except Exception:
        conn.close()
        raise
    return conn


def _assert_read_only(conn: sqlite3.Connection) -> None:
    """Fail closed unless the audit connection is explicitly query-only."""
    value = conn.execute("PRAGMA query_only").fetchone()[0]
    if value != 1:
        raise AuditError("Reporte read-only rechazado: SQLite PRAGMA query_only no está en ON")


def load_cards(
    conn: sqlite3.Connection,
    games: tuple[str, ...],
    card_ids: set[int] | None = None,
    include_inactive: bool = False,
) -> list[dict]:
    placeholders = ",".join("?" for _ in games)
    clauses = [f"g.code IN ({placeholders})"]
    params: list[Any] = list(games)
    if not include_inactive:
        clauses.append("c.catalog_status='active'")
    if card_ids is not None:
        if not card_ids:
            return []
        card_placeholders = ",".join("?" for _ in card_ids)
        clauses.append(f"c.id IN ({card_placeholders})")
        params.extend(sorted(card_ids))
    rows = conn.execute(
        f"""SELECT c.*, g.code AS game, l.code AS language,
                    e.name AS expansion_name, e.cardmarket_id_expansion,
                    e.set_code AS expansion_set_code,
                    COALESCE(s.code, c.set_code, e.set_code) AS resolved_set_code,
                    COALESCE(s.name, e.name) AS resolved_set_name,
                    cc.identity_key AS canonical_identity,
                    cc.canonical_number, cc.name AS canonical_name
               FROM cards c
               JOIN games g ON g.id=c.game_id
               LEFT JOIN languages l ON l.id=c.language_id
               LEFT JOIN expansions e ON e.id=c.expansion_id
               LEFT JOIN sets s ON s.id=c.set_id
               LEFT JOIN canonical_cards cc ON cc.id=c.canonical_card_id
              WHERE {' AND '.join(clauses)}
              ORDER BY CASE g.code WHEN 'one_piece' THEN 0 ELSE 1 END, c.id""",
        params,
    ).fetchall()
    return [dict(row) for row in rows]


def load_external_ids(conn: sqlite3.Connection) -> dict[int, list[dict]]:
    rows = conn.execute(
        """SELECT x.card_id, x.source, x.external_id, x.language_id, x.language_scope, x.metadata
             FROM printing_external_ids x ORDER BY x.card_id, x.source, x.external_id"""
    ).fetchall()
    result: dict[int, list[dict]] = defaultdict(list)
    for row in rows:
        item = dict(row)
        try:
            item["metadata"] = json.loads(item["metadata"] or "{}")
        except json.JSONDecodeError:
            item["metadata"] = {}
        result[int(row["card_id"])].append(item)
    return result


def load_mappings(conn: sqlite3.Connection) -> dict[int, list[dict]]:
    rows = conn.execute(
        """SELECT m.card_id, m.status, m.cardmarket_product_id AS local_product_id,
                    p.cardmarket_id_product, p.raw_name,
                    p.cardmarket_id_expansion
             FROM cardmarket_product_mappings m
             JOIN cardmarket_products p ON p.id=m.cardmarket_product_id
            WHERE m.card_id IS NOT NULL
            ORDER BY m.card_id, p.cardmarket_id_product"""
    ).fetchall()
    result: dict[int, list[dict]] = defaultdict(list)
    for row in rows:
        result[int(row["card_id"])].append(dict(row))
    return result


def latest_rows(rows: Iterable[sqlite3.Row | dict], key_fields: tuple[str, ...], timestamp_field: str) -> dict[tuple, dict]:
    result: dict[tuple, dict] = {}
    for raw in rows:
        row = dict(raw)
        key = tuple(row[field] for field in key_fields)
        current = result.get(key)
        if current is None or ((str(row.get(timestamp_field) or ""), int(row.get("id") or 0)) >
                               (str(current.get(timestamp_field) or ""), int(current.get("id") or 0))):
            result[key] = row
    return result


def load_current_prices(conn: sqlite3.Connection) -> tuple[dict[tuple[int, int], dict], dict[int, list[dict]]]:
    # Once the repair sprint has run, the current row is authoritative even when
    # its price is NULL.  Keep a compatibility fallback only for pre-repair
    # databases that have no current-state column at all.
    columns = {row[1] for row in conn.execute("PRAGMA table_info(printing_price_resolutions)")}
    all_resolution_rows = conn.execute("SELECT * FROM printing_price_resolutions").fetchall()
    if "collection_item_id" in columns:
        all_resolution_rows = [row for row in all_resolution_rows if row["collection_item_id"] is None]
    if "wishlist_item_id" in columns:
        all_resolution_rows = [row for row in all_resolution_rows if row["wishlist_item_id"] is None]
    if "is_current" in columns:
        current_rows = [row for row in all_resolution_rows if row["is_current"] == 1]
        current_keys = {(row["card_id"], row["language_id"]) for row in current_rows}
        legacy_rows = [row for row in all_resolution_rows if (row["card_id"], row["language_id"]) not in current_keys]
        resolution_rows = current_rows + legacy_rows
    else:
        resolution_rows = all_resolution_rows
    resolutions = latest_rows(resolution_rows, ("card_id", "language_id"), "resolved_at")
    history_rows = conn.execute("SELECT * FROM market_price_history").fetchall()
    histories = latest_rows(history_rows, ("cardmarket_product_id",), "observed_at")
    return resolutions, histories


def load_collection_current_prices(conn: sqlite3.Connection) -> dict[int, dict]:
    """Load only current Collection-scoped resolutions, including NULL prices."""
    columns = {row[1] for row in conn.execute("PRAGMA table_info(printing_price_resolutions)")}
    if "collection_item_id" not in columns or "is_current" not in columns:
        return {}
    wishlist_clause = " AND wishlist_item_id IS NULL" if "wishlist_item_id" in columns else ""
    rows = conn.execute(
        f"""SELECT * FROM printing_price_resolutions
             WHERE collection_item_id IS NOT NULL{wishlist_clause} AND is_current=1
             ORDER BY collection_item_id, id"""
    ).fetchall()
    return {int(row["collection_item_id"]): dict(row) for row in rows}


def load_wishlist_current_prices(conn: sqlite3.Connection) -> dict[int, dict]:
    """Load only current Wishlist-scoped resolutions, including NULL prices."""
    columns = {row[1] for row in conn.execute("PRAGMA table_info(printing_price_resolutions)")}
    if "wishlist_item_id" not in columns or "is_current" not in columns:
        return {}
    rows = conn.execute(
        """SELECT * FROM printing_price_resolutions
             WHERE wishlist_item_id IS NOT NULL
               AND collection_item_id IS NULL
               AND is_current=1
             ORDER BY wishlist_item_id, id"""
    ).fetchall()
    return {int(row["wishlist_item_id"]): dict(row) for row in rows}


def load_expansion_names(conn: sqlite3.Connection) -> dict[int, str | None]:
    rows = conn.execute("SELECT cardmarket_id_expansion, name FROM expansions").fetchall()
    return {int(row[0]): row[1] for row in rows}


def load_wishlist(conn: sqlite3.Connection, games: tuple[str, ...], status: str = "wanted") -> list[dict]:
    """Load Wishlist work items without changing their status."""
    if status not in {"wanted", "acquired", "removed", "all"}:
        raise AuditError(f"Unknown Wishlist status: {status}")
    placeholders = ",".join("?" for _ in games)
    params: list[Any] = list(games)
    status_clause = ""
    if status != "all":
        status_clause = " AND wi.status = ?"
        params.append(status)
    rows = conn.execute(
        f"""SELECT wi.id AS wishlist_item_id, wi.card_id, wi.quantity_wanted,
                    wi.priority, wi.target_price, wi.max_price, wi.currency,
                    wi.status, wi.created_at, wi.updated_at
               FROM wishlist_items wi
               JOIN cards c ON c.id = wi.card_id
               JOIN games g ON g.id = c.game_id
              WHERE g.code IN ({placeholders}){status_clause}
              ORDER BY wi.id""",
        params,
    ).fetchall()
    return [dict(row) for row in rows]


def wishlist_audit_rows(
    conn: sqlite3.Connection,
    games: tuple[str, ...],
    snapshots: dict[str, dict[str, SourceSnapshot]],
    status: str = "wanted",
) -> tuple[dict[str, list[dict]], dict[int, dict], list[dict]]:
    """Audit Wishlist items at item grain using the shared identity resolver."""
    wishlist = load_wishlist(conn, games, status)
    card_ids = {int(item["card_id"]) for item in wishlist}
    cards = {int(card["id"]): card for card in load_cards(conn, games, card_ids=card_ids, include_inactive=True)}
    external = load_external_ids(conn)
    mappings = load_mappings(conn)
    resolutions, histories = load_current_prices(conn)
    wishlist_resolutions = load_wishlist_current_prices(conn)
    expansion_names = load_expansion_names(conn)
    blueprint_info = blueprint_diagnostics(conn)
    result = {game: [] for game in games}
    for item in wishlist:
        card = cards.get(int(item["card_id"]))
        if card is None:
            continue
        game = str(card["game"])
        product_snapshot = snapshots[game]["products"]
        price_snapshot = snapshots[game]["price_guide"]
        products, _ = build_product_indexes(product_snapshot, game)
        prices = {int(raw["idProduct"]): normalize_price_entry(dict(raw)) for raw in price_snapshot.records}
        row = audit_card(
            card, game, products, prices, external, mappings, resolutions, histories,
            expansion_names, blueprint_info, price_snapshot.created_at, "EUR",
            wishlist_item_id=int(item["wishlist_item_id"]),
            wishlist_resolutions=wishlist_resolutions,
        )
        row.update({
            "wishlist_item_id": int(item["wishlist_item_id"]),
            "wishlist_status": item["status"],
            "wishlist_quantity": int(item["quantity_wanted"]),
            "wishlist_priority": item["priority"],
            "wishlist_target_price": item["target_price"],
            "wishlist_max_price": item["max_price"],
        })
        if not row.get("cardmarket_candidates"):
            diagnostic_ids = diagnostic_candidate_ids(card, products, expansion_names)
            if diagnostic_ids:
                row["cardmarket_candidates"] = ",".join(map(str, diagnostic_ids))
                row["evidence"] = json.dumps({**json.loads(row.get("evidence") or "{}"), "diagnostic_candidates": diagnostic_ids}, sort_keys=True)
        result.setdefault(game, []).append(row)
    return result, cards, wishlist


def build_product_indexes(snapshot: SourceSnapshot, game: str) -> tuple[dict[int, dict], dict[int, dict]]:
    products = {int(row["idProduct"]): parse_product_identity(game, row) for row in snapshot.records}
    return products, {int(row["idProduct"]): dict(row) for row in snapshot.records}


def usable(value: Any) -> bool:
    try:
        return value is not None and float(value) > 0
    except (TypeError, ValueError):
        return False


def metric_values(price: dict | None, foil: bool) -> dict:
    if not price:
        return {name: None for name in (METRICS + FOIL_METRICS)}
    return {name: price.get(name) for name in (METRICS + FOIL_METRICS)}


def normalize_price_entry(price: dict) -> dict:
    """Expose Cardmarket's ``-foil`` keys under the audit's stable alt names."""
    result = dict(price)
    for field in METRICS:
        result[f"{field}_alt"] = price.get(f"{field}-foil", price.get(f"{field}_alt"))
    return result


def _language_exact(item: dict, local_language: str | None) -> bool:
    metadata = item.get("metadata") or {}
    allowed = metadata.get("allowed_languages")
    if item.get("language_scope") != "exact":
        return False
    if isinstance(allowed, list) and allowed:
        return [str(value).casefold() for value in allowed] == [str(local_language).casefold()]
    return item.get("language_id") is not None


def _cardmarket_candidate_ids(card: dict, external: dict[int, list[dict]], mappings: dict[int, list[dict]], products: dict[int, dict], game: str) -> tuple[list[int], list[int], dict]:
    stored: set[int] = set()
    provenance: list[dict] = []
    for item in external.get(int(card["id"]), []):
        if item["source"] == "cardmarket_product":
            try:
                product_id = int(item["external_id"])
            except (TypeError, ValueError):
                continue
            stored.add(product_id)
            provenance.append({"id": product_id, "scope": item["language_scope"], "exact_language": _language_exact(item, card.get("language")), "metadata": item.get("metadata")})
    for item in mappings.get(int(card["id"]), []):
        if item["status"] == "mapped" and item.get("cardmarket_id_product") is not None:
            stored.add(int(item["cardmarket_id_product"]))
    raw_cardmarket_id = None
    if game == "magic" and card.get("scryfall_raw"):
        try:
            raw_cardmarket_id = json.loads(card["scryfall_raw"]).get("cardmarket_id")
        except (TypeError, json.JSONDecodeError):
            raw_cardmarket_id = None
        if raw_cardmarket_id is not None:
            stored.add(int(raw_cardmarket_id))
    valid_stored = sorted(product_id for product_id in stored if product_id in products)
    return valid_stored, sorted(stored), {"external_provenance": provenance, "scryfall_cardmarket_id": raw_cardmarket_id}


def _product_matches_card(card: dict, product: dict, game: str, expansion_names: dict[int, str | None] | None = None) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if card.get("cardmarket_id_expansion") is not None and product.get("idExpansion") is not None:
        if int(card["cardmarket_id_expansion"]) != int(product["idExpansion"]):
            local_expansion = normalize(card.get("expansion_name"))
            product_expansion = normalize((expansion_names or {}).get(int(product["idExpansion"])))
            # The bulk Product Catalogue only carries the numeric expansion id.
            # An id absent from the local expansion reference is not evidence of
            # a different set; classify it conservatively from the other fields.
            if local_expansion and product_expansion and local_expansion != product_expansion:
                reasons.append("wrong_expansion")
    local_number = normalize_number(card.get("card_number"))
    product_number = normalize_number(product.get("card_number"))
    if local_number and product_number and local_number != product_number:
        reasons.append("wrong_cardmarket_id")
    local_name = normalize(card.get("name"))
    product_name = normalize(product.get("parsed_name") or product.get("name"))
    if local_name and product_name and local_name != product_name:
        reasons.append("wrong_cardmarket_id")
    local_version = extract_version(card.get("variant_label") or card.get("source_variant"))
    product_version = product.get("version")
    if local_version and product_version and local_version.casefold() != str(product_version).casefold():
        reasons.append("wrong_version")
    if game == "magic":
        try:
            raw = json.loads(card.get("scryfall_raw") or "{}")
        except json.JSONDecodeError:
            raw = {}
        finishes = {str(value).casefold() for value in raw.get("finishes") or []}
        finish = str(card.get("finish") or "").casefold()
        if finish and finishes and finish not in finishes:
            reasons.append("wrong_finish")
        treatment = str(card.get("treatment") or "").casefold()
        promo_types = {str(value).casefold() for value in raw.get("promo_types") or []}
        frame_effects = {str(value).casefold() for value in raw.get("frame_effects") or []}
        if "surge" in treatment and "surgefoil" not in promo_types:
            reasons.append("wrong_treatment")
        if "showcase" in treatment and "showcase" not in frame_effects:
            reasons.append("wrong_treatment")
        # Cardmarket's bulk product record does not expose these treatment
        # dimensions.  A direct id is still useful evidence, but it cannot
        # prove that an etched/surge/promotional treatment is represented by
        # the same product without an explicit product-name signal.
        product_text = normalize(product.get("name"))
        special_finish = finish in {"etched", "surgefoil", "surge foil"}
        special_treatment = treatment and treatment not in {"normal", "regular", "none"}
        if special_finish and finish not in product_text:
            reasons.append("unproven_finish")
        if special_treatment and treatment.replace(" ", "") not in product_text:
            reasons.append("unproven_treatment")
    return not reasons, sorted(set(reasons))


def resolve_identity(card: dict, game: str, products: dict[int, dict], external: dict[int, list[dict]], mappings: dict[int, list[dict]], expansion_names: dict[int, str | None] | None = None) -> IdentityResult:
    valid_stored, all_stored, provenance = _cardmarket_candidate_ids(card, external, mappings, products, game)
    evidence: dict[str, Any] = {"stored_ids": all_stored, **provenance, "validated_stored_ids": valid_stored}
    mismatch_reasons: list[str] = []
    mapped_ids = sorted({int(item["cardmarket_id_product"]) for item in mappings.get(int(card["id"]), [])
                         if item["status"] == "mapped" and item.get("cardmarket_id_product") is not None})
    raw_id = provenance.get("scryfall_cardmarket_id")
    if game == "magic" and raw_id is not None and mapped_ids and any(mapped_id != int(raw_id) for mapped_id in mapped_ids):
        evidence["mapped_ids"] = mapped_ids
        evidence["mapping_conflicts_with_scryfall_id"] = True
        return IdentityResult("MISMATCH", None, all_stored, valid_stored, "current mapping differs from stored Scryfall Cardmarket id", evidence, "wrong_cardmarket_id")
    valid_matches = []
    for product_id in valid_stored:
        matches, reasons = _product_matches_card(card, products[product_id], game, expansion_names)
        if matches:
            valid_matches.append(product_id)
        else:
            mismatch_reasons.extend(reasons)
    exact_language_ids = []
    for item in provenance["external_provenance"]:
        if item["exact_language"] and item["id"] in valid_matches:
            exact_language_ids.append(item["id"])
        if item["scope"] == "exact" and not item["exact_language"] and item["id"] in valid_matches:
            mismatch_reasons.append("wrong_language")
    if game == "magic":
        candidates = valid_matches
        if len(candidates) == 1 and not mismatch_reasons:
            resolved = candidates[0]
            price_reason = "validated scryfall/mapping id"
            return IdentityResult("EXACT", resolved, all_stored, candidates, price_reason, evidence)
        hard_mismatch_reasons = [reason for reason in mismatch_reasons if reason not in {"unproven_finish", "unproven_treatment"}]
        if hard_mismatch_reasons:
            return IdentityResult("MISMATCH", None, all_stored, valid_stored, "stored product identity conflicts with local printing", {**evidence, "mismatch_reasons": sorted(set(mismatch_reasons))}, "wrong_cardmarket_id")
        if mismatch_reasons:
            return IdentityResult("AMBIGUOUS", None, all_stored, valid_stored, "Cardmarket bulk data does not prove finish/treatment", {**evidence, "ambiguity_reasons": sorted(set(mismatch_reasons))}, "ambiguous_identity")
        if len(candidates) > 1:
            return IdentityResult("AMBIGUOUS", None, all_stored, candidates, "multiple Cardmarket products remain", evidence, "ambiguous_identity")
    else:
        if len(exact_language_ids) == 1 and len(valid_matches) == 1:
            return IdentityResult("EXACT", exact_language_ids[0], all_stored, valid_matches, "validated exact-language Cardmarket id", evidence)
        if mismatch_reasons and all_stored:
            return IdentityResult("MISMATCH", None, all_stored, valid_matches, "stored Cardmarket product conflicts with local printing", {**evidence, "mismatch_reasons": sorted(set(mismatch_reasons))}, "wrong_cardmarket_id")
        if valid_matches:
            return IdentityResult("AMBIGUOUS", None, all_stored, valid_matches, "Cardmarket product language/version is not provably exact", evidence, "ambiguous_identity")

    # Product Catalogue-only resolution is deliberately conservative.  It may produce
    # candidates for diagnostics, but One Piece still needs explicit language evidence.
    candidates = []
    for product_id, product in products.items():
        if card.get("cardmarket_id_expansion") is not None and product.get("idExpansion") != card["cardmarket_id_expansion"]:
            continue
        if game == "one_piece":
            if normalize_number(product.get("card_number")) != normalize_number(card.get("card_number")):
                continue
            if normalize(product.get("parsed_name")) != normalize(card.get("name")):
                continue
        elif normalize(product.get("parsed_name") or product.get("name")) != normalize(card.get("name")):
            continue
        candidates.append(product_id)
    candidates = sorted(set(candidates))
    evidence["catalog_candidates"] = candidates
    if len(candidates) == 1 and game == "magic":
        return IdentityResult("EXACT", candidates[0], all_stored, candidates, "unique validated Product Catalogue id", evidence)
    if len(candidates) > 1:
        return IdentityResult("AMBIGUOUS", None, all_stored, candidates, "multiple Product Catalogue candidates", evidence, "ambiguous_identity")
    if len(candidates) == 1:
        return IdentityResult("AMBIGUOUS", None, all_stored, candidates, "language/version cannot be proven from bulk Cardmarket data", evidence, "ambiguous_identity")
    if all_stored:
        return IdentityResult("MISSING", None, all_stored, [], "stored Cardmarket id absent from Product Catalogue", evidence, "missing_product")
    return IdentityResult("MISSING", None, all_stored, [], "no Cardmarket product candidate", evidence, "missing_cardmarket_id")


def current_for_card(
    card: dict,
    game: str,
    resolutions: dict[tuple[int, int], dict],
    histories: dict[tuple[int], dict],
    mappings: dict[int, list[dict]],
    collection_item_id: int | None = None,
    collection_resolutions: dict[int, dict] | None = None,
    wishlist_item_id: int | None = None,
    wishlist_resolutions: dict[int, dict] | None = None,
) -> dict:
    if collection_item_id is not None and collection_resolutions and collection_item_id in collection_resolutions:
        value = collection_resolutions[collection_item_id]
        return {
            "current_price": value.get("current_price"), "current_currency": value.get("currency"),
            "current_source": value.get("source"), "current_source_product_id": value.get("external_id"),
            "current_timestamp": value.get("resolved_at"), "current_confidence": value.get("price_confidence"),
            "current_provenance": value.get("provenance") or value.get("metadata"),
            "dashboard_metric": value.get("selected_metric") or "Low",
        }
    if wishlist_item_id is not None:
        # Wishlist scope is target-authoritative: an absent current Wishlist
        # resolution must not fall through to a global resolution, mapping or
        # historical source.  This also preserves a current NULL price as an
        # intentional block against fallback pricing.
        if wishlist_resolutions and wishlist_item_id in wishlist_resolutions:
            value = wishlist_resolutions[wishlist_item_id]
            return {
                "current_price": value.get("current_price"), "current_currency": value.get("currency"),
                "current_source": value.get("source"), "current_source_product_id": value.get("external_id"),
                "current_timestamp": value.get("resolved_at"), "current_confidence": value.get("price_confidence"),
                "current_provenance": value.get("provenance") or value.get("metadata"),
                "dashboard_metric": value.get("selected_metric") or "Low",
            }
        return {
            "current_price": None, "current_currency": None, "current_source": None,
            "current_source_product_id": None, "current_timestamp": None,
            "current_confidence": None, "current_provenance": None,
            "dashboard_metric": None,
        }
    value = resolutions.get((int(card["id"]), int(card.get("language_id") or 0)))
    if value is not None:
        return {
            "current_price": value.get("current_price"), "current_currency": value.get("currency"),
            "current_source": value.get("source"), "current_source_product_id": value.get("external_id"),
            "current_timestamp": value.get("resolved_at"), "current_confidence": value.get("price_confidence"),
            "current_provenance": value.get("metadata"), "dashboard_metric": value.get("selected_metric") or "Low",
        }
    if game == "one_piece":
        return {"current_price": None, "current_currency": None, "current_source": None,
                "current_source_product_id": None, "current_timestamp": None,
                "current_confidence": None, "current_provenance": None,
                "dashboard_metric": "current_price_resolution"}
    mapped = [item for item in mappings.get(int(card["id"]), []) if item["status"] == "mapped"]
    ids = sorted({int(item["cardmarket_id_product"]) for item in mapped if item.get("cardmarket_id_product") is not None})
    if len(ids) != 1:
        return {"current_price": None, "current_currency": "EUR", "current_source": "cardmarket" if ids else None,
                "current_source_product_id": ",".join(map(str, ids)) or None, "current_timestamp": None,
                "current_confidence": None, "current_provenance": {"mapped_product_ids": ids}, "dashboard_metric": None}
    local_product_id = int(mapped[0]["local_product_id"])
    history = histories.get((local_product_id,)) or {}
    is_foil = str(card.get("finish") or "").casefold() == "foil"
    base = history.get("low_alt") if is_foil else history.get("low")
    dashboard_price = base if usable(base) else None
    dashboard_metric = "Foil Low" if is_foil and dashboard_price is not None else ("Low" if dashboard_price is not None else None)
    return {
        "current_price": dashboard_price, "current_currency": "EUR", "current_source": "cardmarket",
        "current_source_product_id": str(ids[0]), "current_timestamp": history.get("observed_at"),
        "current_confidence": "high" if dashboard_price is not None else None,
        "current_provenance": {"cardmarket_product_id": ids[0], "history_id": history.get("id")},
        "dashboard_metric": dashboard_metric,
    }


def cardmarket_price(product_id: int | None, prices: dict[int, dict], card: dict, game: str) -> tuple[dict, str | None]:
    raw = normalize_price_entry(dict(prices.get(product_id, {}))) if product_id is not None else {}
    foil = game == "magic" and str(card.get("finish") or "").casefold() == "foil"
    selected = "low_alt" if foil else "low"
    return raw, selected


def blueprint_diagnostics(conn: sqlite3.Connection) -> dict[str, dict]:
    rows = conn.execute(
        """SELECT x.external_id, c.id, c.set_code, c.card_number, c.language_id,
                    c.source_variant, c.treatment, c.release_kind, c.art_kind
             FROM printing_external_ids x JOIN cards c ON c.id=x.card_id
            WHERE x.source='cardtrader_blueprint' AND c.catalog_status='active'"""
    ).fetchall()
    by_blueprint: dict[str, list[tuple]] = defaultdict(list)
    for row in rows:
        by_blueprint[str(row[0])].append(tuple(row[1:]))
    result = {}
    for blueprint, items in by_blueprint.items():
        # Language is deliberately excluded here: EN/JP rows may legitimately
        # share one broad CardTrader blueprint for the same commercial printing.
        # A collision means that the blueprint spans different set/variant or
        # treatment identities, not merely different localized rows.
        commercial = {(item[1], item[2], item[4], item[5], item[6], item[7]) for item in items}
        result[blueprint] = {
            "card_ids": sorted({item[0] for item in items}),
            "commercial_identities": len(commercial),
            "broad": len(commercial) > 1,
        }
    return result


def classify_primary(identity: IdentityResult, card: dict, current: dict, secondary: list[str]) -> str | None:
    if identity.status == "MISMATCH":
        reasons = set(identity.evidence.get("mismatch_reasons") or [])
        for cause in ("wrong_expansion", "wrong_language", "wrong_version", "wrong_finish", "wrong_treatment", "wrong_reprint", "wrong_cardmarket_id"):
            if cause in reasons:
                return cause
        return identity.primary_cause or "wrong_cardmarket_id"
    # Identity uncertainty takes precedence over secondary observations such
    # as stale timestamps or broad CardTrader blueprints.
    if identity.status == "AMBIGUOUS":
        return "ambiguous_identity"
    if identity.status == "MISSING":
        return "missing_product" if identity.reason.startswith("stored") else "missing_cardmarket_id"
    if identity.status == "UNPRICED":
        return "missing_product"
    if "blueprint_collision" in secondary:
        return "blueprint_collision"
    if current.get("currency_mismatch"):
        return "currency_mismatch"
    if "metric_mismatch" in secondary:
        return "metric_mismatch"
    if "stale_price" in secondary:
        return "stale_price"
    return None


def audit_card(
    card: dict,
    game: str,
    products: dict[int, dict],
    prices: dict[int, dict],
    external: dict[int, list[dict]],
    mappings: dict[int, list[dict]],
    resolutions: dict[tuple[int, int], dict],
    histories: dict[tuple],
    expansion_names: dict[int, str | None],
    blueprint_info: dict[str, dict],
    source_created_at: str,
    display_currency: str,
    collection_item_id: int | None = None,
    collection_resolutions: dict[int, dict] | None = None,
    wishlist_item_id: int | None = None,
    wishlist_resolutions: dict[int, dict] | None = None,
) -> dict:
    identity = resolve_identity(card, game, products, external, mappings, expansion_names)
    current = current_for_card(
        card, game, resolutions, histories, mappings,
        collection_item_id, collection_resolutions,
        wishlist_item_id, wishlist_resolutions,
    )
    cm, selected_metric = cardmarket_price(identity.resolved_id, prices, card, game)
    cm_low = cm.get(selected_metric) if selected_metric else None
    trend_metric = "trend_alt" if selected_metric == "low_alt" else "trend"
    cm_trend = cm.get(trend_metric)
    secondary: list[str] = []
    if game == "one_piece":
        blueprint_ids = [item["external_id"] for item in external.get(int(card["id"]), []) if item["source"] == "cardtrader_blueprint"]
        if any(blueprint_info.get(str(value), {}).get("broad") for value in blueprint_ids):
            secondary.append("blueprint_collision")
    current_currency = current.get("current_currency") or ""
    currency_mismatch = bool(current.get("current_price") is not None and (current_currency.casefold() != "eur" or display_currency.casefold() != "eur"))
    current["currency_mismatch"] = currency_mismatch
    expected_dashboard_metric = {"low": "Low", "low_alt": "Foil Low"}.get(selected_metric)
    if game == "magic" and current.get("current_price") is not None and expected_dashboard_metric and current.get("dashboard_metric") != expected_dashboard_metric:
        secondary.append("metric_mismatch")
    current_time = parse_timestamp(current.get("current_timestamp"))
    source_time = parse_timestamp(source_created_at)
    if current_time and source_time and current_time < source_time and current.get("current_source") == "cardmarket":
        secondary.append("stale_price")
    if identity.status == "EXACT" and not usable(cm_low):
        identity.status = "UNPRICED"
        identity.reason = "exact Cardmarket product has no usable selected Low metric"
        identity.primary_cause = "missing_product"
    comparable = identity.status == "EXACT" and current.get("current_price") is not None and usable(cm_low) and not currency_mismatch
    signed_difference = (float(current["current_price"]) - float(cm_low)) if comparable else None
    absolute_difference = abs(signed_difference) if signed_difference is not None else None
    percentage = absolute_difference / float(cm_low) if absolute_difference is not None and usable(cm_low) else None
    ratio = float(current["current_price"]) / float(cm_low) if comparable and usable(cm_low) else None
    low_vs_trend_difference = (float(cm_low) - float(cm_trend)) if usable(cm_low) and usable(cm_trend) else None
    low_vs_trend_percentage = abs(low_vs_trend_difference) / float(cm_trend) if low_vs_trend_difference is not None and usable(cm_trend) else None
    low_vs_trend_ratio = float(cm_low) / float(cm_trend) if usable(cm_low) and usable(cm_trend) else None
    severity = price_severity(percentage, identity.status == "MISMATCH")
    cause = classify_primary(identity, card, current, secondary)
    if cause is None and identity.status == "EXACT" and not comparable and current.get("current_price") is not None:
        cause = "unknown"
    report_product_id = identity.resolved_id
    if report_product_id is None:
        report_product_id = next((product_id for product_id in identity.candidates if product_id in products), None)
    report_product = products.get(report_product_id, {}) if report_product_id is not None else {}
    report_price = cm if report_product_id == identity.resolved_id else normalize_price_entry(dict(prices.get(report_product_id, {})))
    cm_expansion_id = report_product.get("idExpansion")
    row = {
        "local_printing_id": card["id"], "game": game, "card_name": card.get("name"),
        "card_number": card.get("card_number"), "local_set_code": card.get("resolved_set_code"),
        "set_name": card.get("resolved_set_name"), "language": card.get("language"),
        "local_version": card.get("variant_label") or card.get("source_variant"),
        "rarity": card.get("rarity"), "finish": card.get("finish"), "treatment": card.get("treatment"),
        "canonical_id": card.get("canonical_card_id"), "canonical_identity": card.get("canonical_identity"),
        "blueprint_id": next((item["external_id"] for item in external.get(int(card["id"]), []) if item["source"] == "cardtrader_blueprint"), None),
        "cardtrader_ids": ",".join(item["external_id"] for item in external.get(int(card["id"]), []) if item["source"] == "cardtrader_blueprint"),
        "scryfall_id": card.get("scryfall_id"), "stored_cardmarket_id": ",".join(map(str, identity.stored_ids)) or None,
        "resolved_cardmarket_id": identity.resolved_id, "cardmarket_candidates": ",".join(map(str, identity.candidates)) or None,
        "cardmarket_product_name": report_product.get("name") or None,
        "cardmarket_expansion_id": cm_expansion_id,
        "cardmarket_expansion": expansion_names.get(int(cm_expansion_id)) if cm_expansion_id is not None else None,
        "cardmarket_version": report_product.get("version"),
        "cardmarket_number": report_product.get("card_number"),
        "cardmarket_language_scope": "exact" if identity.status == "EXACT" else ("mixed/unknown" if identity.candidates else None),
        **metric_values(report_price, str(card.get("finish") or "").casefold() == "foil"),
        "cardmarket_metric_used": "Low" if selected_metric == "low" else ("Foil Low" if selected_metric == "low_alt" else None), "current_price": current.get("current_price"),
        "current_currency": current_currency or None, "display_currency": display_currency,
        "current_source": current.get("current_source"), "current_source_product_id": current.get("current_source_product_id"),
        "current_confidence": current.get("current_confidence"), "current_metric": current.get("dashboard_metric"), "current_timestamp": current.get("current_timestamp"),
        "current_provenance": json.dumps(current.get("current_provenance"), sort_keys=True, default=str),
        "match_status": identity.status, "match_reason": identity.reason,
        "identity_mismatch": identity.status == "MISMATCH", "currency_mismatch": currency_mismatch,
        "metric_mismatch": "metric_mismatch" in secondary, "price_difference": signed_difference,
        "absolute_difference": absolute_difference, "percentage_difference": percentage, "ratio": ratio,
        "low_difference": signed_difference, "low_percentage_difference": percentage, "low_ratio": ratio,
        "low_severity": severity, "low_vs_trend_difference": low_vs_trend_difference,
        "low_vs_trend_percentage": low_vs_trend_percentage, "low_vs_trend_ratio": low_vs_trend_ratio,
        "price_severity": severity, "primary_cause": cause,
        "secondary_tags": ",".join(sorted(set(secondary))), "evidence": json.dumps(identity.evidence, sort_keys=True, default=str),
    }
    if collection_item_id is not None:
        row["collection_item_id"] = collection_item_id
    if wishlist_item_id is not None:
        row["wishlist_item_id"] = wishlist_item_id
    return row


def load_collection(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """SELECT ci.id AS collection_item_id, ci.card_id, ci.cardmarket_product_id,
                    ci.language_id, ci.quantity, c.name, c.card_number, g.code AS game
             FROM collection_items ci LEFT JOIN cards c ON c.id=ci.card_id
             LEFT JOIN games g ON g.id=c.game_id ORDER BY ci.id"""
    ).fetchall()
    return [dict(row) for row in rows]


def collection_unresolved_row(item: dict) -> dict:
    """Create a report row for a collection item without a linked printing."""
    return {
        "local_printing_id": item.get("card_id"), "collection_item_id": item["collection_item_id"],
        "game": item.get("game"), "card_name": item.get("name"), "card_number": None,
        "local_set_code": None, "set_name": None, "language": None, "local_version": None,
        "rarity": None, "finish": None, "treatment": None, "canonical_id": None,
        "canonical_identity": None, "blueprint_id": None, "cardtrader_ids": None,
        "scryfall_id": None, "stored_cardmarket_id": None, "resolved_cardmarket_id": None,
        "cardmarket_candidates": None, "cardmarket_product_name": None,
        "cardmarket_expansion_id": None, "cardmarket_expansion": None, "cardmarket_version": None,
        "cardmarket_number": None, "cardmarket_language_scope": None,
        **{field: None for field in METRICS + FOIL_METRICS},
        "cardmarket_metric_used": None, "current_price": None, "current_currency": None,
        "display_currency": "EUR", "current_source": None, "current_source_product_id": None,
        "current_confidence": None, "current_metric": None, "current_timestamp": None,
        "current_provenance": None, "match_status": "MISSING",
        "match_reason": "collection item has no linked local printing", "identity_mismatch": False,
        "currency_mismatch": False, "metric_mismatch": False, "price_difference": None,
        "absolute_difference": None, "percentage_difference": None, "ratio": None,
        "low_difference": None, "low_percentage_difference": None, "low_ratio": None,
        "low_severity": "NO_COMPARISON", "low_vs_trend_difference": None,
        "low_vs_trend_percentage": None, "low_vs_trend_ratio": None,
        "price_severity": "NO_COMPARISON", "primary_cause": "missing_cardmarket_id",
        "secondary_tags": None, "evidence": json.dumps({"collection_item_id": item["collection_item_id"]}),
        "collection_quantity": int(item.get("quantity") or 0),
        "collection_current_contribution": None, "collection_cardmarket_contribution": None,
        "collection_difference": None,
    }


def diagnostic_candidate_ids(card: dict, products: dict[int, dict], expansion_names: dict[int, str | None]) -> list[int]:
    """Return review-only candidates when a stored ID hides useful evidence.

    This function never resolves identity.  It only makes the manual report
    complete for cases such as EB02-061 versus PRB02-061.
    """
    local_name = normalize(card.get("name"))
    local_number = normalize_number(card.get("card_number"))
    base_number = re.sub(r"[A-Z]+$", "", local_number)
    result = []
    for product_id, product in products.items():
        product_name = normalize(product.get("parsed_name") or product.get("name"))
        product_number = normalize_number(product.get("card_number"))
        product_base = re.sub(r"[A-Z]+$", "", product_number)
        if local_name and product_name != local_name:
            continue
        if local_number and product_number not in {local_number, base_number} and product_base != base_number:
            continue
        result.append(int(product_id))
    return sorted(set(result))


def collection_audit_rows(
    conn: sqlite3.Connection,
    games: tuple[str, ...],
    snapshots: dict[str, dict[str, SourceSnapshot]],
    collection_resolutions: dict[int, dict],
) -> tuple[dict[str, list[dict]], list[dict]]:
    """Audit every collection item at item grain, including inactive printings."""
    collection = load_collection(conn)
    collection_items = [item for item in collection if item.get("game") in games]
    card_ids = {int(item["card_id"]) for item in collection_items if item.get("card_id") is not None}
    cards = {int(card["id"]): card for card in load_cards(conn, games, card_ids=card_ids, include_inactive=True)}
    external = load_external_ids(conn)
    mappings = load_mappings(conn)
    resolutions, histories = load_current_prices(conn)
    expansion_names = load_expansion_names(conn)
    blueprints = blueprint_diagnostics(conn)
    result = {game: [] for game in games}
    for item in collection_items:
        game = item["game"]
        card = cards.get(int(item["card_id"])) if item.get("card_id") is not None else None
        if card is None:
            row = collection_unresolved_row(item)
        else:
            product_snapshot = snapshots[game]["products"]
            guide_snapshot = snapshots[game]["price_guide"]
            products, _ = build_product_indexes(product_snapshot, game)
            prices = {int(raw["idProduct"]): normalize_price_entry(dict(raw)) for raw in guide_snapshot.records}
            row = audit_card(
                card, game, products, prices, external, mappings, resolutions, histories,
                expansion_names, blueprints, guide_snapshot.created_at, "EUR",
                collection_item_id=int(item["collection_item_id"]),
                collection_resolutions=collection_resolutions,
            )
            if not row.get("cardmarket_candidates"):
                diagnostic_ids = diagnostic_candidate_ids(card, products, expansion_names)
                if diagnostic_ids:
                    row["cardmarket_candidates"] = ",".join(map(str, diagnostic_ids))
                    row["evidence"] = json.dumps({**json.loads(row.get("evidence") or "{}"), "diagnostic_candidates": diagnostic_ids}, sort_keys=True)
            # A validated manual Collection approval is a persisted EXACT
            # resolution.  It must be visible to the post-apply audit even if
            # the automatic bulk resolver still cannot prove the treatment.
            persisted = collection_resolutions.get(int(item["collection_item_id"]))
            if persisted and persisted.get("match_status") == "EXACT" and persisted.get("external_id"):
                try:
                    persisted_id = int(persisted["external_id"])
                except (TypeError, ValueError):
                    persisted_id = None
                if persisted_id in products:
                    persisted_product = products[persisted_id]
                    persisted_price = prices.get(persisted_id, {})
                    row.update({
                        "match_status": "EXACT", "resolved_cardmarket_id": persisted_id,
                        "cardmarket_candidates": str(persisted_id), "cardmarket_product_name": persisted_product.get("name"),
                        "cardmarket_expansion_id": persisted_product.get("idExpansion"),
                        "cardmarket_version": persisted_product.get("version"), "cardmarket_number": persisted_product.get("card_number"),
                        "cardmarket_metric_used": persisted.get("selected_metric") or row.get("cardmarket_metric_used"),
                        "match_reason": "persisted validated Collection resolution", "primary_cause": None,
                        "identity_mismatch": False,
                    })
                    for field in METRICS + FOIL_METRICS:
                        row[field] = persisted_price.get(field)
            row["collection_quantity"] = int(item.get("quantity") or 0)
            refresh_collection_contributions([row])
        result.setdefault(game, []).append(row)
    return result, collection


def collection_metric_key(row: dict) -> str | None:
    """Return only the Cardmarket Low field selected by the printing finish."""
    metric = row.get("cardmarket_metric_used")
    if metric == "Low":
        return "low"
    if metric == "Foil Low":
        return "low_alt"
    return None


def collection_metric_available(row: dict) -> bool:
    """Whether the exact row has its selected Cardmarket Low metric."""
    key = collection_metric_key(row)
    return bool(
        row.get("match_status") == "EXACT"
        and not row.get("currency_mismatch")
        and key is not None
        and usable(row.get(key))
    )


def collection_unpriced(row: dict) -> bool:
    """Count exact identities with no usable selected Low as unpriced."""
    return bool(
        row.get("match_status") == "UNPRICED"
        or (
            row.get("match_status") == "EXACT"
            and row.get("resolved_cardmarket_id") is not None
            and not collection_metric_available(row)
        )
    )


def refresh_collection_contributions(rows: list[dict]) -> None:
    """Recompute Collection contributions after every identity/price overlay."""
    for row in rows:
        quantity = int(row.get("collection_quantity") or 0)
        row["collection_current_contribution"] = (
            round(float(row["current_price"]) * quantity, 4)
            if usable(row.get("current_price")) else None
        )
        metric_key = collection_metric_key(row)
        row["collection_cardmarket_contribution"] = (
            round(float(row[metric_key]) * quantity, 4)
            if collection_metric_available(row) else None
        )
        row["collection_difference"] = (
            round(
                float(row["collection_current_contribution"] or 0)
                - float(row["collection_cardmarket_contribution"] or 0),
                4,
            )
            if row["collection_cardmarket_contribution"] is not None else None
        )


def apply_collection_metrics(rows: list[dict], collection: list[dict], histories: dict[tuple], current_by_card: dict[int, dict], product_prices: dict[int, dict], audit_by_card: dict[int, dict]) -> None:
    by_card: dict[int, list[dict]] = defaultdict(list)
    for item in collection:
        if item.get("card_id") is not None:
            by_card[int(item["card_id"])].append(item)
    for row in rows:
        items = by_card.get(int(row["local_printing_id"]), [])
        quantity = sum(int(item.get("quantity") or 0) for item in items)
        current_value = 0.0
        low_value = 0.0
        comparable_units = 0
        for item in items:
            item_current = current_by_card.get(int(row["local_printing_id"]), {}).get("current_price")
            if row["game"] == "magic" and int(row["local_printing_id"]) not in current_by_card and item.get("cardmarket_product_id") is not None:
                history = histories.get((int(item["cardmarket_product_id"]),)) or {}
                item_current = history.get("low") if usable(history.get("low")) else history.get("low_alt")
            if usable(item_current):
                current_value += float(item_current) * int(item.get("quantity") or 0)
            if row["match_status"] == "EXACT" and not row["currency_mismatch"] and usable(row.get("low" if row["cardmarket_metric_used"] == "Low" else "low_alt")) and usable(item_current):
                low = row.get("low" if row["cardmarket_metric_used"] == "Low" else "low_alt")
                low_value += float(low) * int(item.get("quantity") or 0)
                comparable_units += int(item.get("quantity") or 0)
        row["collection_quantity"] = quantity or None
        row["collection_current_contribution"] = round(current_value, 4) if items else None
        row["collection_cardmarket_contribution"] = round(low_value, 4) if comparable_units else None
        row["collection_difference"] = round(current_value - low_value, 4) if comparable_units else None


def csv_value(value: Any) -> Any:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return value


def write_csv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = fields or (list(rows[0].keys()) if rows else ["local_printing_id"])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: csv_value(row.get(field)) for field in fields})


def format_money(value: Any) -> str:
    return "—" if value is None else f"€{float(value):,.2f}"


def top_rows(rows: list[dict], key: str, reverse: bool = True, limit: int = 50) -> list[dict]:
    return sorted((row for row in rows if row.get(key) is not None), key=lambda row: (float(row[key]), int(row["local_printing_id"])), reverse=reverse)[:limit]


def price_severity(percentage: float | None, identity_mismatch: bool = False) -> str:
    if identity_mismatch:
        return "CRITICAL"
    if percentage is None:
        return "NO_COMPARISON"
    if percentage <= 0.15:
        return "OK"
    if percentage <= 0.30:
        return "REVIEW"
    if percentage <= 0.75:
        return "HIGH"
    return "CRITICAL"


def markdown_table(rows: list[dict], columns: list[tuple[str, str]]) -> str:
    if not rows:
        return "_Sin filas._\n"
    result = ["| " + " | ".join(label for label, _ in columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in rows:
        result.append("| " + " | ".join(str(row.get(key) if row.get(key) is not None else "—").replace("|", "\\|") for _, key in columns) + " |")
    return "\n".join(result) + "\n"


def collection_summary(rows: list[dict], collection: list[dict]) -> dict:
    if not any("collection_item_id" in row for row in rows):
        total_units = sum(int(item.get("quantity") or 0) for item in collection)
        current_total = 0.0
        comparable_current = 0.0
        comparable_trend = 0.0
        comparable_units = 0
        for row in rows:
            current = row.get("collection_current_contribution")
            trend = row.get("collection_cardmarket_contribution")
            if current is not None:
                current_total += float(current)
            if trend is not None:
                comparable_trend += float(trend)
                comparable_current += float(current or 0)
                comparable_units += int(row.get("collection_quantity") or 0)
        return {
            "items_total": len(collection), "units_total": total_units,
            "exact_items": None, "exact_units": comparable_units,
            "item_coverage_percent": None,
            "unit_coverage_percent": round(comparable_units / total_units * 100, 2) if total_units else 0,
            "current_total": round(current_total, 2), "resolved_low_total": round(comparable_trend, 2),
            "estimated_value_coverage_percent": None,
            "value_without_exact_resolution": None,
            "comparable_units": comparable_units,
            "coverage_percent": round(comparable_units / total_units * 100, 2) if total_units else 0,
            "non_comparable_units": total_units - comparable_units,
            "comparable_current": round(comparable_current, 2),
            "comparable_trend": round(comparable_trend, 2),
            "comparable_difference": round(comparable_current - comparable_trend, 2),
            "dealer_cash": None, "trade_value": None,
        }
    total_items = len(rows)
    total_units = sum(int(row.get("collection_quantity") or 0) for row in rows)
    current_total = sum(float(row["collection_current_contribution"]) for row in rows if row.get("collection_current_contribution") is not None)
    low_total = sum(float(row["collection_cardmarket_contribution"]) for row in rows if row.get("collection_cardmarket_contribution") is not None)
    exact_items = sum(1 for row in rows if row.get("match_status") == "EXACT")
    exact_units = sum(int(row.get("collection_quantity") or 0) for row in rows if row.get("match_status") == "EXACT")
    comparable_current = sum(
        float(row["collection_current_contribution"])
        for row in rows
        if row.get("collection_cardmarket_contribution") is not None and row.get("collection_current_contribution") is not None
    )
    comparable_trend = sum(
        float(row["collection_cardmarket_contribution"])
        for row in rows if row.get("collection_cardmarket_contribution") is not None
    )
    comparable_units = sum(
        int(row.get("collection_quantity") or 0)
        for row in rows if row.get("collection_cardmarket_contribution") is not None
    )
    unresolved_legacy_value = sum(
        float(row["collection_current_contribution"])
        for row in rows
        if row.get("match_status") != "EXACT" and row.get("collection_current_contribution") is not None
    )
    estimated_denominator = low_total + unresolved_legacy_value
    return {
        "items_total": total_items, "units_total": total_units,
        "exact_items": exact_items, "exact_units": exact_units,
        "item_coverage_percent": round(exact_items / total_items * 100, 2) if total_items else 0,
        "unit_coverage_percent": round(exact_units / total_units * 100, 2) if total_units else 0,
        "current_total": round(current_total, 2), "resolved_low_total": round(low_total, 2),
        "estimated_value_coverage_percent": round(low_total / estimated_denominator * 100, 2) if estimated_denominator else None,
        "value_without_exact_resolution": round(unresolved_legacy_value, 2),
        "comparable_units": comparable_units,
        "coverage_percent": round(comparable_units / total_units * 100, 2) if total_units else 0,
        "non_comparable_units": total_units - comparable_units,
        "comparable_current": round(comparable_current, 2),
        "comparable_trend": round(comparable_trend, 2),
        "comparable_difference": round(comparable_current - comparable_trend, 2),
        "dealer_cash": round(low_total * 0.70, 2),
        "dealer_cash_min": round(low_total * 0.60, 2),
        "dealer_cash_max": round(low_total * 0.75, 2),
        "trade_value": round(low_total * 0.80, 2),
        "trade_value_min": round(low_total * 0.70, 2),
        "trade_value_max": round(low_total * 0.85, 2),
    }


def cause_breakdown(rows: list[dict]) -> list[dict]:
    total = len(rows) or 1
    counters = Counter(row["primary_cause"] for row in rows if row.get("primary_cause"))
    impacts = defaultdict(float)
    for row in rows:
        cause = row.get("primary_cause")
        if cause:
            impacts[cause] += float(row.get("collection_difference") or 0)
    return [{"cause": cause, "count": count, "percent": round(count / total * 100, 2), "collection_impact": round(impacts[cause], 2)}
            for cause, count in sorted(counters.items(), key=lambda item: (-item[1], item[0]))]


def collection_review_hash(row: dict, manifest_id: str) -> str:
    """Hash identity/evidence inputs, excluding the approval decision."""
    printing_id = row.get("printing_id") or row.get("local_printing_id")
    candidate_raw = row.get("candidate_cardmarket_product_id")
    if candidate_raw in (None, ""):
        candidate_raw = row.get("cardmarket_candidates")
    payload = {
        "collection_item_id": row.get("collection_item_id"),
        "printing_id": printing_id, "game": row.get("game"),
        "card_name": row.get("card_name"), "set": row.get("set") or row.get("local_set_code"),
        "card_number": row.get("card_number"), "language": row.get("language"),
        "variant": row.get("variant") or row.get("local_version"), "finish": row.get("finish"),
        "treatment": row.get("treatment"),
        "candidate_ids": sorted(int(value) for value in str(candidate_raw or "").replace(",", "|").split("|") if value.strip().isdigit()),
        "candidate_product_name": row.get("candidate_product_name"),
        "candidate_expansion": row.get("candidate_expansion"), "manifest_id": manifest_id,
    }
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def collection_review_rows(rows: list[dict], products: dict[int, dict], manifest_id: str) -> list[dict]:
    result = []
    for row in rows:
        if row.get("match_status") == "EXACT":
            continue
        candidate_ids = [int(value) for value in str(row.get("cardmarket_candidates") or "").split(",") if value.strip().isdigit()]
        candidate_products = [products[value] for value in candidate_ids if value in products]
        review = {
            "collection_item_id": row.get("collection_item_id"), "printing_id": row.get("local_printing_id"),
            "game": row.get("game"), "card_name": row.get("card_name"), "set": row.get("local_set_code"),
            "card_number": row.get("card_number"), "collector_number": row.get("card_number"),
            "language": row.get("language"), "variant": row.get("local_version"),
            "finish": row.get("finish"), "treatment": row.get("treatment"),
            "candidate_cardmarket_product_id": "|".join(map(str, candidate_ids)) or None,
            "candidate_product_name": "|".join(str(item.get("name") or "") for item in candidate_products) or None,
            "candidate_expansion": "|".join(str(item.get("idExpansion") or "") for item in candidate_products) or None,
            "evidence": row.get("evidence"), "proposed_status": row.get("match_status"),
            "approved": "false", "selected_cardmarket_product_id": None, "manifest_id": manifest_id,
        }
        review["row_hash"] = collection_review_hash({**row, **review}, manifest_id)
        result.append(review)
    return result


def write_samples(path: Path, rows: list[dict]) -> None:
    comparable = [row for row in rows if row.get("price_severity") in {"OK", "REVIEW", "HIGH", "CRITICAL"} and row.get("price_difference") is not None]
    over = sorted((row for row in comparable if float(row["price_difference"]) > 0), key=lambda row: (-float(row["absolute_difference"]), int(row["local_printing_id"])))[:50]
    under = sorted((row for row in comparable if float(row["price_difference"]) < 0), key=lambda row: (float(row["price_difference"]), int(row["local_printing_id"])))[:50]
    ratios = sorted((row for row in comparable if row.get("ratio") not in (None, 0)), key=lambda row: (-max(float(row["ratio"]), 1 / float(row["ratio"])), int(row["local_printing_id"])))[:50]
    ok = sorted((row for row in rows if row.get("price_severity") == "OK"), key=lambda row: int(row["local_printing_id"]))[:50]
    mismatches = [row for row in rows if row.get("identity_mismatch")]
    ambiguous = [row for row in rows if row.get("match_status") == "AMBIGUOUS"]
    cols = [("ID", "local_printing_id"), ("Carta", "card_name"), ("Set", "local_set_code"), ("Idioma", "language"), ("Actual", "current_price"), ("Low", "low"), ("Trend", "trend"), ("Estado", "match_status"), ("Severidad", "price_severity"), ("Causa", "primary_cause")]
    lines = ["# Pricing audit samples\n", "Las muestras están ordenadas de forma determinista.\n"]
    for title, sample in (("Top 50 sobrevaloraciones", over), ("Top 50 infravaloraciones", under), ("Top 50 ratios extremos", ratios), ("50 filas OK", ok), ("Identity mismatches", mismatches)):
        lines.extend([f"## {title}\n", markdown_table(sample, cols), "\n"])
    lines.append("## Ambiguous\n\n")
    if len(ambiguous) > 200:
        lines.append(f"Se omitió la tabla ({len(ambiguous)} filas) para mantener el Markdown manejable. Ver `*_ambiguous.csv`, que contiene el conjunto completo.\n")
    else:
        lines.append(markdown_table(ambiguous, cols) + "\n")
    path.write_text("\n".join(lines), encoding="utf-8")


def eb02_section(conn: sqlite3.Connection, products: dict[int, dict], prices: dict[int, dict], rows: list[dict], external: dict[int, list[dict]], mappings: dict[int, list[dict]]) -> str:
    locals_rows = conn.execute(
        """SELECT c.*, g.code AS game, l.code AS language, e.name AS expansion_name,
                    e.cardmarket_id_expansion, COALESCE(s.code,c.set_code,e.set_code) AS resolved_set_code
             FROM cards c JOIN games g ON g.id=c.game_id LEFT JOIN languages l ON l.id=c.language_id
             LEFT JOIN expansions e ON e.id=c.expansion_id LEFT JOIN sets s ON s.id=c.set_id
            WHERE g.code='one_piece' AND upper(c.card_number)='EB02-061' ORDER BY c.id"""
    ).fetchall()
    if not locals_rows:
        return "## EB02-061\n\nNo se encontraron filas locales.\n"
    row_by_id = {int(row["local_printing_id"]): row for row in rows}
    table_rows = []
    relevant_products = [product for product in products.values() if normalize_number(product.get("card_number")) == "EB02061" and normalize(product.get("parsed_name")) == "monkeydluffy"]
    for raw in locals_rows:
        local_id = int(raw["id"])
        audited = row_by_id.get(local_id, {})
        stored_ids = [item["external_id"] for item in external.get(local_id, []) if item["source"] == "cardmarket_product"]
        candidate_ids = sorted(set(int(value) for value in stored_ids if str(value).isdigit()))
        if not candidate_ids:
            candidate_ids = [int(product["idProduct"]) for product in relevant_products if product.get("idExpansion") == raw["cardmarket_id_expansion"]]
        if not candidate_ids:
            candidate_ids = [None]
        for product_id in candidate_ids:
            product = products.get(product_id, {}) if product_id is not None else {}
            price = prices.get(product_id, {}) if product_id is not None else {}
            table_rows.append({
                "local ID": local_id, "local set": raw["resolved_set_code"], "language": raw["language"],
                "local version": raw["variant_label"] or raw["source_variant"], "current price": audited.get("current_price"),
                "current source": audited.get("current_source"), "current source product ID": audited.get("current_source_product_id"),
                "Cardmarket idProduct": product_id, "Cardmarket expansion": product.get("idExpansion"),
                "Cardmarket version": product.get("version") or "not exposed in bulk name",
                "Low": price.get("low"), "Trend": price.get("trend"), "AVG7": price.get("avg7"),
                "match status": audited.get("match_status") or "OUT_OF_SCOPE", "primary cause": audited.get("primary_cause"),
            })
    cols = [(key, key) for key in table_rows[0].keys()]
    lines = ["## EB02-061\n", "Todos los productos se mantienen separados por `idProduct`; la Product Catalogue bulk no expone una versión V1/V2/V3 cuando no aparece en el nombre.\n", markdown_table(table_rows, cols), "\n"]
    lines.append("### Acceptance checks\n")
    def ids_for(set_code: str, language: str) -> set[int]:
        return {int(item["Cardmarket idProduct"]) for item in table_rows
                if normalize(item["local set"]) == normalize(set_code)
                and str(item["language"]).casefold() == language.casefold()
                and item["Cardmarket idProduct"] is not None}

    eb_jp = ids_for("eb02", "jp")
    eb_en = ids_for("eb02", "en")
    prb_jp = ids_for("prb02", "jp")
    has_v2 = any("v.2" in normalize(str(item["local version"])) or "v2" in normalize(str(item["local version"])) for item in table_rows)
    if eb_jp and prb_jp and eb_jp.isdisjoint(prb_jp):
        lines.append(f"- `EB02 JP V2 != PRB02 JP V2`: PASS por `idProduct` disjuntos ({sorted(eb_jp)} vs {sorted(prb_jp)}); V2 explícito: {'yes' if has_v2 else 'no'}.\n")
    else:
        lines.append("- `EB02 JP V2 != PRB02 JP V2`: NOT_PROVABLE; no se fuerza equivalencia entre candidatos.\n")
    if has_v2 and eb_jp and eb_en and eb_jp.isdisjoint(eb_en):
        lines.append(f"- `EB02 JP V2 != EB02 EN V2`: PASS por `idProduct` disjuntos ({sorted(eb_jp)} vs {sorted(eb_en)}).\n")
    else:
        lines.append("- `EB02 JP V2 != EB02 EN V2`: NOT_PROVABLE; el bulk no demuestra alcance lingüístico/versiones V2 exactos.\n")
    if has_v2:
        lines.append("- `EB02 JP V2 != EB02 V1/V3`: NOT_PROVABLE; no se encontraron versiones alternativas explícitas suficientes en el bulk.\n")
    else:
        lines.append("- `EB02 JP V2 != EB02 V1/V3`: NOT_PROVABLE; V1/V2/V3 no están expuestos explícitamente en los snapshots usados.\n")
    return "\n".join(lines)


def verdicts(rows: list[dict]) -> tuple[str, str]:
    identity = "SAFE" if not any(row.get("identity_mismatch") or (row.get("match_status") == "AMBIGUOUS" and row.get("current_price") is not None) for row in rows) else "UNSAFE"
    mechanism_causes = {"wrong_reprint", "wrong_expansion", "wrong_language", "wrong_version", "wrong_finish", "wrong_treatment", "blueprint_collision", "wrong_cardmarket_id", "stale_price", "currency_mismatch", "metric_mismatch"}
    critical_mechanism = any(row.get("price_severity") == "CRITICAL" and (row.get("identity_mismatch") or row.get("primary_cause") in mechanism_causes) for row in rows)
    parity = "UNSAFE" if critical_mechanism else ("REVIEW" if any(row.get("price_severity") in {"REVIEW", "HIGH", "CRITICAL"} for row in rows) else "SAFE")
    return identity, parity


def write_summary(path: Path, game: str, rows: list[dict], collection: dict, manifest: dict, eb02: str | None = None) -> tuple[str, str]:
    counts = Counter(row["match_status"] for row in rows)
    unpriced_count = sum(1 for row in rows if collection_unpriced(row)) if any("collection_item_id" in row for row in rows) else counts["UNPRICED"]
    price_counts = Counter(row["price_severity"] for row in rows)
    causes = cause_breakdown(rows)
    identity, parity = verdicts(rows)
    current_cardtrader = sum(1 for row in rows if row.get("current_source") == "cardtrader" and row.get("current_price") is not None)
    mismatches = sum(1 for row in rows if row.get("identity_mismatch"))
    currency = sum(1 for row in rows if row.get("currency_mismatch"))
    lines = [f"# {game.replace('_', ' ').title()} pricing audit\n", "## Scope and sources\n", f"- Total printings: **{len(rows)}**\n", f"- Snapshot timestamp: **{manifest['audit_timestamp']}**\n", "- Sources: `source_manifest.json`\n", "\n## Matching\n", f"- Exact Cardmarket: **{counts['EXACT']}**\n", f"- Ambiguous: **{counts['AMBIGUOUS']}**\n", f"- Mismatch: **{counts['MISMATCH']}**\n", f"- Missing: **{counts['MISSING']}**\n", f"- Unpriced: **{unpriced_count}**\n", f"- Current Cardmarket exact coverage: **{counts['EXACT'] / len(rows) * 100:.2f}%**\n" if rows else "- Current Cardmarket exact coverage: **0%**\n", f"- Current CardTrader-priced: **{current_cardtrader}**\n", f"- Identity mismatches: **{mismatches}**\n", f"- Currency mismatches: **{currency}**\n", "\n## Price comparison\n", f"- OK: **{price_counts['OK']}**\n", f"- Review: **{price_counts['REVIEW']}**\n", f"- High: **{price_counts['HIGH']}**\n", f"- Critical: **{price_counts['CRITICAL']}**\n", "\n## Causes\n", markdown_table(causes, [("Cause", "cause"), ("Count", "count"), ("Percent", "percent"), ("Collection impact", "collection_impact")]), "\n## Collection\n", f"- Current total value: **{format_money(collection['current_total'])}**\n", f"- Comparable units: **{collection['comparable_units']} / {collection['units_total']}**\n", f"- Comparable coverage: **{collection['coverage_percent']}%**\n", f"- Comparable current value: **{format_money(collection['comparable_current'])}**\n", f"- Comparable Cardmarket Low value: **{format_money(collection['comparable_trend'])}**\n", f"- Comparable difference: **{format_money(collection['comparable_difference'])}**\n", "\n## Verdict\n", f"- {game.replace('_', ' ').title()} identity: **{identity}**\n", f"- {game.replace('_', ' ').title()} pricing parity: **{parity}**\n"]
    if eb02:
        lines.extend(["\n", eb02])
    path.write_text("\n".join(lines), encoding="utf-8")
    return identity, parity


def write_collection_summary(path: Path, game: str, rows: list[dict], metrics: dict, manifest: dict) -> None:
    counts = Counter(row.get("match_status") for row in rows)
    unpriced_count = sum(1 for row in rows if collection_unpriced(row))
    low_count = sum(1 for row in rows if collection_metric_available(row))
    trend_count = sum(1 for row in rows if usable(row.get("trend" if row.get("cardmarket_metric_used") == "Low" else "trend_alt")))
    lines = [
        f"# Collection {game.replace('_', ' ').title()} pricing audit\n",
        "- Scope efectivo: **collection**\n",
        f"- Items / units: **{metrics['items_total']} / {metrics['units_total']}**\n",
        f"- EXACT / AMBIGUOUS / MISMATCH / MISSING / UNPRICED: **{counts['EXACT']} / {counts['AMBIGUOUS']} / {counts['MISMATCH']} / {counts['MISSING']} / {unpriced_count}**\n",
        f"- Exact item coverage: **{metrics['item_coverage_percent']}%**\n",
        f"- Exact unit coverage: **{metrics['unit_coverage_percent']}%**\n",
        f"- Low / Trend disponible: **{low_count} / {trend_count}**\n",
        "\n## Economic coverage\n",
        f"- Total current legacy value: **{format_money(metrics['current_total'])}**\n",
        f"- Total resolved Cardmarket Low value: **{format_money(metrics['resolved_low_total'])}**\n",
        f"- Dealer cash estimado: **{format_money(metrics.get('dealer_cash'))}** (60–75%: {format_money(metrics.get('dealer_cash_min'))}–{format_money(metrics.get('dealer_cash_max'))})\n",
        f"- Trade value estimado: **{format_money(metrics.get('trade_value'))}** (70–85%: {format_money(metrics.get('trade_value_min'))}–{format_money(metrics.get('trade_value_max'))})\n",
        f"- Estimated value coverage: **{metrics['estimated_value_coverage_percent'] if metrics['estimated_value_coverage_percent'] is not None else '—'}%**\n",
        f"- Value without exact resolution: **{format_money(metrics['value_without_exact_resolution'])}**\n",
        f"- Comparable units: **{metrics['comparable_units']} / {metrics['units_total']}**\n",
        f"- Source manifest: `{manifest['manifest_id']}`\n",
        "\nEl estado legacy es diagnóstico; no bloquea por sí solo el estado propuesto.\n",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def write_manual_review_report(path: Path, game: str, rows: list[dict], products: dict[int, dict], prices: dict[int, dict], expansion_names: dict[int, str | None], manifest_id: str) -> dict[str, int]:
    """Write a deterministic human-review report without approving any row."""
    pending = [row for row in rows if row.get("match_status") != "EXACT"]
    if game == "magic":
        pending.sort(key=lambda row: (-float(row.get("current_price") or 0), len(_review_candidate_ids(row)), str(row.get("treatment") or ""), int(row.get("collection_item_id") or 0)))
    else:
        pending.sort(key=lambda row: (-float(row.get("current_price") or 0), int(row.get("collection_item_id") or 0)))
    lines = [f"# Manual review — Collection {game.replace('_', ' ').title()}\n", f"- Items requiring review: **{len(pending)}**\n", "- Automatic approval: **none**\n", f"- Manifest: `{manifest_id}`\n"]
    for number, row in enumerate(pending, 1):
        candidate_ids = _review_candidate_ids(row)
        lines.extend([
            f"\n## {number}. {row.get('card_name') or 'Unnamed'} — item {row.get('collection_item_id')}\n",
            f"- Printing ID: `{row.get('local_printing_id') or '—'}`\n- Set / number: `{row.get('local_set_code') or '—'}` / `{row.get('card_number') or '—'}`\n- Language / variant: `{row.get('language') or '—'}` / `{row.get('local_version') or '—'}`\n- Finish / treatment: `{row.get('finish') or '—'}` / `{row.get('treatment') or '—'}`\n- Legacy price: **{format_money(row.get('current_price'))}** ({row.get('current_source') or '—'})\n- Status: **{row.get('match_status')}** — {row.get('match_reason') or '—'}\n- Recommendation: **NO RECOMMENDATION**\n",
            "### Cardmarket candidates\n",
        ])
        candidate_rows = []
        for candidate_id in candidate_ids:
            product = products.get(candidate_id, {})
            price = prices.get(candidate_id, {})
            expansion = expansion_names.get(int(product["idExpansion"])) if product.get("idExpansion") is not None else None
            if expansion is None and product.get("idExpansion") is not None:
                expansion = f"idExpansion={product['idExpansion']}"
            metric = "low_alt" if game == "magic" and str(row.get("finish") or "").casefold() == "foil" else "low"
            trend_metric = "trend_alt" if metric == "low_alt" else "trend"
            low = price.get(metric)
            candidate_rows.append({
                "id": candidate_id, "product": product.get("name"),
                "expansion": expansion,
                "version": product.get("version"), "number": product.get("card_number"),
                "low": low, "trend": price.get(trend_metric),
                "difference": float(low) - float(row["current_price"]) if usable(low) and usable(row.get("current_price")) else None,
            })
        lines.append(markdown_table(candidate_rows, [("idProduct", "id"), ("Product", "product"), ("Expansion", "expansion"), ("Version", "version"), ("Number", "number"), ("Low", "low"), ("Trend", "trend"), ("Low - legacy", "difference")]))
        try:
            evidence = json.dumps(json.loads(row.get("evidence") or "{}"), ensure_ascii=False, sort_keys=True)
        except json.JSONDecodeError:
            evidence = row.get("evidence") or "{}"
        lines.extend(["\n### Evidence and blocker\n", f"- Evidence: `{evidence}`\n", f"- Blocker: `{row.get('match_reason') or 'identity evidence is insufficient'}`\n", "- Verify the physical printing against one exact Cardmarket product; never use price as selector.\n"])
    path.write_text("\n".join(lines), encoding="utf-8")
    return {"required": len(pending), "safe_recommendations": 0, "genuinely_ambiguous": len(pending)}


def _review_candidate_ids(row: dict) -> list[int]:
    return [int(value) for value in str(row.get("cardmarket_candidates") or "").split(",") if value.strip().isdigit()]


def audit(*, db_path: Path, source_dir: Path | None, output_dir: Path, games: tuple[str, ...], display_currency: str, now: str | None, scope: str = "catalog") -> dict:
    if scope not in {"collection", "catalog", "all"}:
        raise AuditError(f"Scope no soportado por la auditoría: {scope}")
    audited_at = now or utc_now()
    before_hash = sha256_file(db_path)
    conn = connect_read_only(db_path)
    try:
        snapshots, manifest = acquire_sources(source_dir, games, conn, audited_at)
        stable_manifest = {"sources": [{key: value for key, value in source.items() if key != "audit_timestamp"} for source in manifest["sources"]]}
        manifest["manifest_id"] = hashlib.sha256(json.dumps(stable_manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        external = load_external_ids(conn)
        mappings = load_mappings(conn)
        resolutions, histories = load_current_prices(conn)
        expansion_names = load_expansion_names(conn)
        blueprint_info = blueprint_diagnostics(conn)
        if scope == "collection":
            collection_resolutions = load_collection_current_prices(conn)
            audit_rows, collection = collection_audit_rows(conn, games, snapshots, collection_resolutions)
        else:
            cards = load_cards(conn, games)
            collection = load_collection(conn)
            audit_rows: dict[str, list[dict]] = {game: [] for game in games}
            for game in GAME_ORDER:
                if game not in games:
                    continue
                product_snapshot = snapshots[game]["products"]
                price_snapshot = snapshots[game]["price_guide"]
                products, _raw_products = build_product_indexes(product_snapshot, game)
                prices = {int(row["idProduct"]): normalize_price_entry(dict(row)) for row in price_snapshot.records}
                game_cards = [card for card in cards if card["game"] == game]
                for card in game_cards:
                    row = audit_card(card, game, products, prices, external, mappings, resolutions, histories, expansion_names, blueprint_info, price_snapshot.created_at, display_currency)
                    audit_rows[game].append(row)
                by_card = {int(row["local_printing_id"]): row for row in audit_rows[game]}
                apply_collection_metrics(audit_rows[game], collection, histories, {card_id: {"current_price": by_card[card_id].get("current_price")} for card_id in by_card}, prices, by_card)
        manifest["scope"] = scope
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "source_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        verdict_data = {}
        all_collection_reviews: list[dict] = []
        for game in games:
            rows = audit_rows[game]
            prefix = "one_piece" if game == "one_piece" else "magic"
            write_csv(output_dir / f"{prefix}_full.csv", rows)
            write_csv(output_dir / f"{prefix}_mismatches.csv", [row for row in rows if row.get("identity_mismatch")])
            write_csv(output_dir / f"{prefix}_critical.csv", [row for row in rows if row.get("price_severity") == "CRITICAL"])
            write_csv(output_dir / f"{prefix}_ambiguous.csv", [row for row in rows if row.get("match_status") == "AMBIGUOUS"])
            write_samples(output_dir / f"{prefix}_samples.md", rows)
            summary_extra = eb02_section(conn, build_product_indexes(snapshots[game]["products"], game)[0], {int(row["idProduct"]): normalize_price_entry(dict(row)) for row in snapshots[game]["price_guide"].records}, rows, external, mappings) if game == "one_piece" else None
            collection_metrics = collection_summary(rows, [item for item in collection if item.get("game") == game])
            if scope == "collection":
                collection_fields = list(rows[0].keys()) if rows else ["collection_item_id"]
                write_csv(output_dir / f"collection_{prefix}_full.csv", rows, collection_fields)
                write_collection_summary(output_dir / f"collection_{prefix}_summary.md", game, rows, collection_metrics, manifest)
                review_rows = []
                if game in snapshots:
                    products, _ = build_product_indexes(snapshots[game]["products"], game)
                    review_rows = collection_review_rows(rows, products, manifest["manifest_id"])
                review_fields = ["collection_item_id", "printing_id", "game", "card_name", "set", "card_number", "collector_number", "language", "variant", "finish", "treatment", "candidate_cardmarket_product_id", "candidate_product_name", "candidate_expansion", "evidence", "proposed_status", "row_hash", "approved", "selected_cardmarket_product_id", "manifest_id"]
                write_csv(output_dir / f"collection_{prefix}_unresolved.csv", review_rows, review_fields)
                all_collection_reviews.extend(review_rows)
                write_manual_review_report(output_dir / f"collection_{prefix}_manual_review.md", game, rows, products, {int(value["idProduct"]): normalize_price_entry(dict(value)) for value in snapshots[game]["price_guide"].records}, load_expansion_names(conn), manifest["manifest_id"])
            identity, parity = write_summary(output_dir / f"{prefix}_summary.md", game, rows, collection_metrics, manifest, summary_extra)
            verdict_data[game] = {"identity": identity, "pricing_parity": parity}
        if scope == "collection":
            review_fields = ["collection_item_id", "printing_id", "game", "card_name", "set", "card_number", "collector_number", "language", "variant", "finish", "treatment", "candidate_cardmarket_product_id", "candidate_product_name", "candidate_expansion", "evidence", "proposed_status", "row_hash", "approved", "selected_cardmarket_product_id", "manifest_id"]
            write_csv(output_dir / "collection_manual_review.csv", all_collection_reviews, review_fields)
        all_safe = all(data["identity"] == "SAFE" and data["pricing_parity"] != "UNSAFE" for data in verdict_data.values()) if len(verdict_data) == 2 else False
        manifest["verdict"] = verdict_data
        manifest["safe_to_run_update_prices_apply"] = "YES" if all_safe else "NO"
        (output_dir / "source_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        after_hash = sha256_file(db_path)
        if before_hash != after_hash:
            raise AuditError("La DB cambió durante la auditoría")
        integrity_check = conn.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_key_check = conn.execute("PRAGMA foreign_key_check").fetchone()
        if integrity_check != "ok":
            raise AuditError(f"PRAGMA integrity_check falló al finalizar: {integrity_check}")
        if foreign_key_check is not None:
            raise AuditError("PRAGMA foreign_key_check encontró errores al finalizar")
        _assert_read_only(conn)
        manifest["database"] = {
            "path": str(db_path.resolve()), "sha256_before": before_hash,
            "sha256_after": after_hash, "unchanged": True,
            "sqlite_open_mode": "uri_mode=ro",
            "read_only": True,
            "query_only": conn.execute("PRAGMA query_only").fetchone()[0],
            "integrity_check": integrity_check,
            "foreign_key_check": "ok" if foreign_key_check is None else list(foreign_key_check),
        }
        (output_dir / "source_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        return manifest
    finally:
        conn.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only Cardmarket pricing audit")
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--source-dir", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--game", choices=("all", *GAME_ORDER), default="all")
    parser.add_argument("--scope", choices=("collection", "catalog", "all"), default="collection")
    parser.add_argument("--display-currency", default="EUR")
    parser.add_argument("--now")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    games = GAME_ORDER if args.game == "all" else (args.game,)
    try:
        manifest = audit(db_path=args.db, source_dir=args.source_dir, output_dir=args.output_dir, games=tuple(games), display_currency=args.display_currency, now=args.now, scope=args.scope)
    except AuditError as exc:
        print(f"AUDIT FAILED: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"output_dir": str(args.output_dir.resolve()), "verdict": manifest.get("verdict"), "safe_to_run_update_prices_apply": manifest.get("safe_to_run_update_prices_apply")}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
