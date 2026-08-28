"""Idempotent One Piece catalog import from CardTrader Blueprints.

Bandai is a validation source represented by the checked-in release registry; this
command never scrapes Bandai. Cardmarket joins are exact through Blueprint
``card_market_ids`` only. Fuzzy name matching is intentionally absent.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sqlite3
import sys
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.images.cardtrader import CardTraderClient
from backend.images.resolver import validate_remote_image_url
from backend.pricing import resolve_cardtrader_marketplace
from backend.providers import CatalogAdapter


ONE_PIECE_GAME_ID = 15
SINGLE_CATEGORIES = {192, 255}
TARGET_LANGUAGES = {"en", "jp"}
REGISTRY_PATH = Path(__file__).with_name("one_piece_release_registry.json")


@dataclass
class ImportReport:
    mode: str
    releases_seen: int = 0
    releases_imported: int = 0
    releases_excluded: list[dict] = field(default_factory=list)
    blueprints_seen: int = 0
    blueprints_imported: int = 0
    printings_inserted: int = 0
    printings_reused: int = 0
    printings_updated: int = 0
    en_printings: int = 0
    jp_printings: int = 0
    canonical_cards: int = 0
    reprint_printings: int = 0
    alternate_art_printings: int = 0
    image_resolved: int = 0
    image_missing: int = 0
    cardmarket_exact_prices: int = 0
    cardtrader_prices: int = 0
    mixed_prices_rejected: int = 0
    no_exact_price: int = 0
    missing_card_number: int = 0
    missing_language: int = 0
    missing_compat_expansion: int = 0
    legacy_candidate_conflicts: int = 0
    commercial_identity_conflict_groups: int = 0
    ambiguous_commercial_printings: int = 0
    canonical_name_conflicts: dict[str, list[str]] = field(default_factory=dict)
    unknown_variants: Counter = field(default_factory=Counter)

    def to_dict(self) -> dict:
        value = asdict(self)
        value["unknown_variants"] = dict(self.unknown_variants)
        return value


class OnePieceCatalogAdapter(CatalogAdapter):
    code = "one_piece"

    def __init__(self, client: CardTraderClient):
        self.client = client

    def fetch_releases(self):
        return self.client.fetch_expansions(ONE_PIECE_GAME_ID)

    def fetch_printings(self, release_external_id: int):
        return self.client.fetch_blueprints(release_external_id).blueprints


def normalized_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def language_property(blueprint: dict) -> tuple[str | None, list[str]]:
    for prop in blueprint.get("editable_properties") or []:
        if prop.get("name") == "onepiece_language":
            return prop.get("default_value"), list(prop.get("possible_values") or [])
    return None, []


def classify_variant(version: str | None, release_code: str, release_name: str) -> tuple[str, str, bool]:
    raw = (version or "").strip()
    value = raw.casefold()
    release_text = f"{release_code} {release_name}".casefold()
    if (
        "reprint" in value
        or "revision pack" in value
        or release_code.casefold().startswith("prb")
        or "premium booster" in release_text
    ):
        release_kind = "reprint"
    elif "promo" in value or "promo" in release_text or "tournament" in release_text or "championship" in release_text:
        release_kind = "promo"
    elif any(token in value for token in ("anniversary", "special rare", "treasure cup")):
        release_kind = "special"
    else:
        release_kind = "original"

    if "manga" in value:
        art_kind = "manga"
    elif any(token in value for token in ("alternate art", "full art", "full-art")):
        art_kind = "alternate_art"
    elif "parallel" in value:
        art_kind = "parallel"
    elif any(token in value for token in ("special rare", "jolly roger", "pirate foil", "textured foil", "stamp")):
        art_kind = "special"
    elif not raw or any(token in value for token in ("reprint", "foil", "non-foil", "secret rare", "box topper")):
        art_kind = "base"
    else:
        art_kind = "unknown"
    return release_kind, art_kind, art_kind == "unknown"


def release_is_available(release: dict, blueprints: list[dict], registry: dict, local_cm_ids: set[int], as_of: dt.date) -> tuple[bool, str]:
    override = (registry.get("overrides") or {}).get(release.get("code"), {})
    date_value = override.get("release_date")
    release_date = dt.date.fromisoformat(date_value) if date_value else None
    if override.get("status") == "unreleased" and (release_date is None or release_date > as_of):
        return False, "release_registry_unreleased"
    if override.get("status") == "released" and (release_date is None or release_date <= as_of):
        return True, "release_registry_released"
    cm_ids = {
        int(value)
        for blueprint in blueprints
        if blueprint.get("category_id") in SINGLE_CATEGORIES
        for value in (blueprint.get("card_market_ids") or [])
    }
    if cm_ids & local_cm_ids:
        return True, "current_cardmarket_catalog"
    return False, "no_released_cardmarket_evidence"


def source_data(adapter: OnePieceCatalogAdapter | None, fixture: Path | None) -> list[dict]:
    if fixture:
        payload = json.loads(fixture.read_text(encoding="utf-8"))
        return payload["expansions"]
    assert adapter is not None
    rows = []
    for release in adapter.fetch_releases():
        rows.append({**release, "blueprints": list(adapter.fetch_printings(release["id"]))})
    return rows


def legacy_index(conn: sqlite3.Connection, game_id: int) -> tuple[dict[int, list[sqlite3.Row]], set[int]]:
    result: dict[int, list[sqlite3.Row]] = defaultdict(list)
    local_cm_ids: set[int] = set()
    rows = conn.execute(
        """SELECT p.cardmarket_id_product, c.id AS card_id, c.expansion_id,
                  c.card_number, c.name, c.language_id, c.cardmarket_id_metacard
             FROM cardmarket_products p
             JOIN cardmarket_categories cc ON cc.cardmarket_id_category=p.cardmarket_id_category
             LEFT JOIN cardmarket_product_mappings m
                    ON m.cardmarket_product_id=p.id AND m.status='mapped'
             LEFT JOIN cards c ON c.id=m.card_id
            WHERE cc.game_id=?""",
        (game_id,),
    ).fetchall()
    for row in rows:
        cm_id = int(row["cardmarket_id_product"])
        local_cm_ids.add(cm_id)
        if row["card_id"] is not None:
            result[cm_id].append(row)
    return result, local_cm_ids


def exact_cardmarket_price_index(conn: sqlite3.Connection) -> dict[int, sqlite3.Row]:
    rows = conn.execute(
        """SELECT p.cardmarket_id_product, h.observed_at, h.trend, h.low, h.avg, h.avg30
             FROM cardmarket_products p
             JOIN market_price_history h ON h.cardmarket_product_id=p.id
            WHERE h.observed_at=(SELECT MAX(h2.observed_at) FROM market_price_history h2
                                  WHERE h2.cardmarket_product_id=h.cardmarket_product_id)"""
    ).fetchall()
    return {int(row["cardmarket_id_product"]): row for row in rows}


def upsert_set(conn: sqlite3.Connection, game_id: int, release: dict, registry: dict) -> int:
    override = (registry.get("overrides") or {}).get(release["code"], {})
    conn.execute(
        """INSERT INTO sets (game_id, code, name, release_date, release_status, metadata)
           VALUES (?, ?, ?, ?, 'released', ?)
           ON CONFLICT(game_id, code) DO UPDATE SET
               name=excluded.name, release_date=COALESCE(excluded.release_date, sets.release_date),
               release_status='released', metadata=excluded.metadata,
               updated_at=CURRENT_TIMESTAMP""",
        (game_id, release["code"], release["name"], override.get("release_date"),
         json.dumps({"registry_checked_at": registry.get("checked_at")})),
    )
    set_id = conn.execute(
        "SELECT id FROM sets WHERE game_id=? AND code=?", (game_id, release["code"])
    ).fetchone()[0]
    conn.execute(
        """INSERT INTO set_external_ids (set_id, source, external_id, metadata)
           VALUES (?, 'cardtrader_expansion', ?, ?)
           ON CONFLICT(source, external_id) DO UPDATE SET
               set_id=excluded.set_id, metadata=excluded.metadata""",
        (set_id, str(release["id"]), json.dumps({"code": release["code"], "name": release["name"]})),
    )
    return set_id


def representative_expansion(blueprints: list[dict], legacy_by_cm: dict[int, list[sqlite3.Row]]) -> int | None:
    counts: Counter[int] = Counter()
    for blueprint in blueprints:
        for cm_id in blueprint.get("card_market_ids") or []:
            for row in legacy_by_cm.get(int(cm_id), []):
                counts[int(row["expansion_id"])] += 1
    return counts.most_common(1)[0][0] if counts else None


def canonical_number_for(blueprint: dict, candidates: list[sqlite3.Row]) -> str | None:
    numbers = {str(row["card_number"]).strip().upper() for row in candidates if row["card_number"]}
    if len(numbers) == 1:
        return numbers.pop()
    value = (blueprint.get("fixed_properties") or {}).get("collector_number")
    return str(value).strip().upper() if value else None


def get_or_create_canonical(conn: sqlite3.Connection, game_id: int, number: str, name: str, conflict: bool) -> int:
    identity = f"one_piece:{number}"
    if conflict:
        identity += f":{normalized_name(name)}"
    conn.execute(
        """INSERT INTO canonical_cards
               (game_id, identity_key, canonical_number, name, normalized_name)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(game_id, identity_key) DO UPDATE SET
               name=excluded.name, canonical_number=excluded.canonical_number,
               normalized_name=excluded.normalized_name, updated_at=CURRENT_TIMESTAMP""",
        (game_id, identity, number, name, normalized_name(name)),
    )
    return conn.execute(
        "SELECT id FROM canonical_cards WHERE game_id=? AND identity_key=?", (game_id, identity)
    ).fetchone()[0]


def existing_printing(conn: sqlite3.Connection, blueprint_id: int, language_id: int) -> int | None:
    row = conn.execute(
        """SELECT card_id FROM printing_external_ids
            WHERE source='cardtrader_blueprint' AND external_id=? AND language_id=?
              AND language_scope='exact'""",
        (str(blueprint_id), language_id),
    ).fetchone()
    return row[0] if row else None


def upsert_image(conn: sqlite3.Connection, card_id: int, blueprint: dict, language: str, default_language: str | None, allowed_languages: list[str], now: str) -> bool:
    image_is_exact = default_language == language or allowed_languages == [language]
    image_url = validate_remote_image_url(
        blueprint.get("image_url"),
        {"cardtrader.com", "www.cardtrader.com"},
    ) if image_is_exact else None
    status = "resolved" if image_url else "missing"
    conn.execute(
        """INSERT INTO card_images
               (card_id, source, source_card_id, source_variant, source_collector_number,
                language, face_index, image_url_small, image_url_large,
                image_language_scope, is_language_fallback, match_quality, status,
                last_checked_at, updated_at)
           VALUES (?, 'cardtrader', ?, ?, ?, ?, 0, NULL, ?, ?, 0, 'exact', ?, ?, CURRENT_TIMESTAMP)
           ON CONFLICT(card_id, source, language, face_index) DO UPDATE SET
               source_card_id=excluded.source_card_id,
               source_variant=excluded.source_variant,
               source_collector_number=excluded.source_collector_number,
               image_url_large=excluded.image_url_large,
               image_language_scope=excluded.image_language_scope,
               is_language_fallback=0,
               match_quality='exact', status=excluded.status,
               last_checked_at=excluded.last_checked_at, updated_at=CURRENT_TIMESTAMP""",
        (card_id, str(blueprint["id"]), blueprint.get("version") or None,
         (blueprint.get("fixed_properties") or {}).get("collector_number"),
         language, image_url, language if image_url else "unknown", status, now),
    )
    return image_url is not None


def insert_price_resolution(conn: sqlite3.Connection, card_id: int, language_id: int, resolved_at: str,
                            method: str, source: str | None, external_id: str | None,
                            current_price: float | None, currency: str | None,
                            sample_size: int = 0, lowest: float | None = None,
                            median_value: float | None = None, confidence: str | None = None,
                            language_scope: str = "exact", metadata: dict | None = None) -> None:
    conn.execute(
        """INSERT INTO printing_price_resolutions
               (card_id, language_id, resolved_at, current_price, currency, source,
                price_type, resolution_method, external_id, sample_size, lowest_price,
                median_price, price_confidence, language_scope, metadata)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(card_id, language_id, resolved_at, resolution_method) DO UPDATE SET
               current_price=excluded.current_price, currency=excluded.currency,
               source=excluded.source, external_id=excluded.external_id,
               sample_size=excluded.sample_size, lowest_price=excluded.lowest_price,
               median_price=excluded.median_price, price_confidence=excluded.price_confidence,
               language_scope=excluded.language_scope, metadata=excluded.metadata""",
        (card_id, language_id, resolved_at, current_price, currency, source,
         "marketplace_low_median_5" if source == "cardtrader" else "trend",
         method, external_id, sample_size, lowest, median_value, confidence,
         language_scope, json.dumps(metadata or {}, sort_keys=True)),
    )


def mark_commercial_identity_conflicts(
    conn: sqlite3.Connection, game_id: int, report: ImportReport
) -> None:
    """Preserve colliding Blueprints but exclude them from the active catalog.

    A provider identifier is never used to invent an extra natural-identity field.
    Distinct Blueprints that collapse to the same canonical/release/variant/language
    therefore remain separate ``cards.id`` rows with explicit ambiguous status.
    """
    groups = conn.execute(
        """SELECT canonical_card_id, set_id,
                  COALESCE(NULLIF(source_variant, ''), art_kind) AS variant_identity,
                  language_id, COUNT(*) AS n
             FROM cards
            WHERE game_id=? AND catalog_status IN ('active', 'ambiguous')
              AND canonical_card_id IS NOT NULL AND set_id IS NOT NULL
              AND language_id IS NOT NULL
            GROUP BY canonical_card_id, set_id, variant_identity, language_id
           HAVING COUNT(*) > 1""",
        (game_id,),
    ).fetchall()
    ambiguous_ids: set[int] = set()
    for group in groups:
        rows = conn.execute(
            """SELECT id FROM cards
                WHERE game_id=? AND canonical_card_id=? AND set_id=?
                  AND COALESCE(NULLIF(source_variant, ''), art_kind)=?
                  AND language_id=? AND catalog_status IN ('active', 'ambiguous')""",
            (
                game_id,
                group["canonical_card_id"],
                group["set_id"],
                group["variant_identity"],
                group["language_id"],
            ),
        ).fetchall()
        ambiguous_ids.update(int(row["id"]) for row in rows)
    if ambiguous_ids:
        placeholders = ",".join("?" for _ in ambiguous_ids)
        conn.execute(
            f"UPDATE cards SET catalog_status='ambiguous' WHERE id IN ({placeholders})",
            sorted(ambiguous_ids),
        )
    report.commercial_identity_conflict_groups = len(groups)
    report.ambiguous_commercial_printings = len(ambiguous_ids)


def import_catalog(db_path: Path, *, fixture: Path | None = None, registry_path: Path = REGISTRY_PATH,
                   apply: bool = False, with_prices: bool = False,
                   as_of: dt.date | None = None, observed_at: str | None = None,
                   client: CardTraderClient | None = None) -> ImportReport:
    as_of = as_of or dt.date.today()
    observed_at = observed_at or dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    report = ImportReport(mode="apply" if apply else "dry-run")
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    adapter = None if fixture else OnePieceCatalogAdapter(client or CardTraderClient())
    releases = source_data(adapter, fixture)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    required = {"canonical_card_id", "catalog_status", "set_id"}
    if not required.issubset({row[1] for row in conn.execute("PRAGMA table_info(cards)")}):
        conn.close()
        raise RuntimeError("Run migrate_multi_tcg.py --apply before the One Piece import")
    game_id = conn.execute("SELECT id FROM games WHERE code='one_piece'").fetchone()[0]
    language_ids = {row["code"]: row["id"] for row in conn.execute("SELECT id,code FROM languages")}
    legacy_by_cm, local_cm_ids = legacy_index(conn, game_id)
    cardmarket_prices = exact_cardmarket_price_index(conn)
    report.releases_seen = len(releases)

    prepared: list[tuple[dict, list[dict], int, int]] = []
    names_by_number: dict[str, set[str]] = defaultdict(set)
    for release in releases:
        blueprints = [row for row in release.get("blueprints", []) if row.get("category_id") in SINGLE_CATEGORIES]
        report.blueprints_seen += len(blueprints)
        available, reason = release_is_available(release, blueprints, registry, local_cm_ids, as_of)
        if not available:
            report.releases_excluded.append({"code": release.get("code"), "reason": reason})
            continue
        compatibility_expansion = representative_expansion(blueprints, legacy_by_cm)
        if compatibility_expansion is None:
            report.releases_excluded.append({"code": release.get("code"), "reason": "missing_compat_expansion"})
            report.missing_compat_expansion += 1
            continue
        set_id = upsert_set(conn, game_id, release, registry)
        prepared.append((release, blueprints, set_id, compatibility_expansion))
        for blueprint in blueprints:
            candidates = [row for cm in blueprint.get("card_market_ids") or [] for row in legacy_by_cm.get(int(cm), [])]
            number = canonical_number_for(blueprint, candidates)
            if number:
                names_by_number[number].add(normalized_name(blueprint.get("name") or ""))

    used_legacy_cards: set[int] = set()
    marketplace_cache: dict[tuple[int, str], dict[int, list[dict]]] = {}
    api_client = client or (adapter.client if adapter else None)
    if with_prices and fixture is None:
        assert api_client is not None
        for release, _, _, _ in prepared:
            for language in sorted(TARGET_LANGUAGES):
                offers = api_client.fetch_marketplace_expansion(int(release["id"]), language)
                grouped: dict[int, list[dict]] = defaultdict(list)
                for offer in offers:
                    if offer.get("blueprint_id") is not None:
                        grouped[int(offer["blueprint_id"])].append(offer)
                marketplace_cache[(int(release["id"]), language)] = grouped
                time.sleep(0.11)

    try:
        for release, blueprints, set_id, compatibility_expansion in prepared:
            report.releases_imported += 1
            conn.execute("UPDATE expansions SET set_id=? WHERE id=?", (set_id, compatibility_expansion))
            for blueprint in blueprints:
                default_language, allowed_languages = language_property(blueprint)
                target_languages = sorted(TARGET_LANGUAGES.intersection(allowed_languages))
                if not target_languages:
                    report.missing_language += 1
                    continue
                candidates = [row for cm in blueprint.get("card_market_ids") or [] for row in legacy_by_cm.get(int(cm), [])]
                number = canonical_number_for(blueprint, candidates)
                if not number:
                    report.missing_card_number += 1
                    continue
                name = blueprint.get("name") or number
                name_conflict = len(names_by_number[number]) > 1
                if name_conflict:
                    report.canonical_name_conflicts[number] = sorted(names_by_number[number])
                canonical_id = get_or_create_canonical(conn, game_id, number, name, name_conflict)
                release_kind, art_kind, unknown_variant = classify_variant(
                    blueprint.get("version"), release["code"], release["name"]
                )
                if unknown_variant:
                    report.unknown_variants[(blueprint.get("version") or "<null>")] += 1
                if release_kind == "reprint": report.reprint_printings += len(target_languages)
                if art_kind in {"alternate_art", "parallel", "manga"}: report.alternate_art_printings += len(target_languages)

                for language in target_languages:
                    language_id = language_ids[language]
                    card_id = existing_printing(conn, int(blueprint["id"]), language_id)
                    inserted = False
                    if card_id is None:
                        eligible = {
                            int(row["card_id"]) for row in candidates
                            if row["language_id"] == language_id and int(row["card_id"]) not in used_legacy_cards
                        }
                        if len(eligible) == 1:
                            card_id = eligible.pop()
                            used_legacy_cards.add(card_id)
                            report.printings_reused += 1
                        else:
                            if len(eligible) > 1:
                                report.legacy_candidate_conflicts += 1
                            cur = conn.execute(
                                """INSERT INTO cards
                                       (game_id, expansion_id, card_number, name, printing_variant,
                                        variant_label, set_code, normalized_name, rarity, language_id,
                                        canonical_card_id, set_id, release_kind, art_kind,
                                        source_variant, catalog_status, catalog_source)
                                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', 'cardtrader')""",
                                (game_id, compatibility_expansion, number, name,
                                 "normal" if art_kind == "base" else "confirmed_parallel",
                                 blueprint.get("version") or None, release["code"], normalized_name(name),
                                 (blueprint.get("fixed_properties") or {}).get("onepiece_rarity"),
                                 language_id, canonical_id, set_id, release_kind, art_kind,
                                 (blueprint.get("version") or "Base").strip()),
                            )
                            card_id = int(cur.lastrowid)
                            inserted = True
                            report.printings_inserted += 1
                    conn.execute(
                        """UPDATE cards SET name=?, normalized_name=?, card_number=?, language_id=?,
                                  canonical_card_id=?, set_id=?, set_code=?, release_kind=?, art_kind=?,
                                  source_variant=?, variant_label=?, catalog_status='active',
                                  catalog_source='cardtrader', updated_at=CURRENT_TIMESTAMP
                            WHERE id=?""",
                        (name, normalized_name(name), number, language_id, canonical_id, set_id,
                         release["code"], release_kind, art_kind,
                         (blueprint.get("version") or "Base").strip(), blueprint.get("version") or None,
                         card_id),
                    )
                    if not inserted: report.printings_updated += 1
                    conn.execute(
                        """INSERT INTO printing_external_ids
                               (card_id, source, external_id, language_id, language_scope, metadata)
                           VALUES (?, 'cardtrader_blueprint', ?, ?, 'exact', ?)
                           ON CONFLICT DO NOTHING""",
                        (card_id, str(blueprint["id"]), language_id,
                         json.dumps({"version": blueprint.get("version"), "release_id": release["id"]})),
                    )
                    if upsert_image(conn, card_id, blueprint, language, default_language, allowed_languages, observed_at):
                        report.image_resolved += 1
                    else:
                        report.image_missing += 1

                    cm_ids = [int(value) for value in blueprint.get("card_market_ids") or []]
                    exact_cm_language = language if set(allowed_languages) == {language} else None
                    for cm_id in cm_ids:
                        conn.execute(
                            """INSERT INTO printing_external_ids
                                   (card_id, source, external_id, language_id, language_scope, metadata)
                               VALUES (?, 'cardmarket_product', ?, ?, ?, ?)
                               ON CONFLICT DO NOTHING""",
                            (card_id, str(cm_id), language_id,
                             "exact" if exact_cm_language else "mixed",
                             json.dumps({"allowed_languages": allowed_languages})),
                        )

                    if with_prices:
                        exact_prices = [
                            (cm, cardmarket_prices[cm])
                            for cm in cm_ids
                            if exact_cm_language and cm in cardmarket_prices
                            and cardmarket_prices[cm]["trend"] is not None
                        ]
                        if len(exact_prices) == 1:
                            exact_cm_id, price = exact_prices[0]
                            insert_price_resolution(
                                conn, card_id, language_id, observed_at,
                                "cardmarket_exact_language", "cardmarket", str(exact_cm_id),
                                float(price["trend"]), "EUR", confidence="high",
                                metadata={"source_observed_at": price["observed_at"]},
                            )
                            report.cardmarket_exact_prices += 1
                        else:
                            offers = marketplace_cache.get((int(release["id"]), language), {}).get(int(blueprint["id"]), [])
                            resolved = resolve_cardtrader_marketplace(offers, language)
                            if resolved.current_price is not None:
                                insert_price_resolution(
                                    conn, card_id, language_id, observed_at,
                                    "cardtrader_marketplace_low_median_5", "cardtrader",
                                    str(blueprint["id"]), resolved.current_price, resolved.currency,
                                    resolved.sample_size, resolved.lowest_price,
                                    resolved.median_price, resolved.confidence,
                                )
                                report.cardtrader_prices += 1
                            elif cm_ids:
                                insert_price_resolution(
                                    conn, card_id, language_id, observed_at,
                                    "mixed_price_rejected", "cardmarket", ",".join(map(str, cm_ids)),
                                    None, "EUR", language_scope="mixed",
                                    metadata={"reason": "Cardmarket product is not exact-language"},
                                )
                                report.mixed_prices_rejected += 1
                            else:
                                insert_price_resolution(
                                    conn, card_id, language_id, observed_at,
                                    "no_exact_language_price", None, str(blueprint["id"]),
                                    None, None,
                                )
                                report.no_exact_price += 1
                    if language == "en": report.en_printings += 1
                    if language == "jp": report.jp_printings += 1
                report.blueprints_imported += 1

        mark_commercial_identity_conflicts(conn, game_id, report)
        report.canonical_cards = conn.execute(
            "SELECT COUNT(*) FROM canonical_cards WHERE game_id=?", (game_id,)
        ).fetchone()[0]
        if apply:
            conn.commit()
            if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise RuntimeError("PRAGMA integrity_check failed")
            if conn.execute("PRAGMA foreign_key_check").fetchone() is not None:
                raise RuntimeError("PRAGMA foreign_key_check failed")
        else:
            conn.rollback()
        return report
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--registry", type=Path, default=REGISTRY_PATH)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--with-prices", action="store_true")
    parser.add_argument("--as-of", type=dt.date.fromisoformat)
    parser.add_argument("--observed-at")
    args = parser.parse_args()
    report = import_catalog(
        args.db, fixture=args.fixture, registry_path=args.registry,
        apply=args.apply, with_prices=args.with_prices,
        as_of=args.as_of, observed_at=args.observed_at,
    )
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
