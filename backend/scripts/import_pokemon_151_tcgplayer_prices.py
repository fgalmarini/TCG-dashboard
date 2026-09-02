#!/usr/bin/env python3
"""Import audited Pokémon 151 TCGplayer observations.

The importer is deliberately cache-first.  Pokémon TCG API is the persistence
authority; TCGdex is only used to validate identity/finish and to produce a
cross-check report.  Secondary observations never participate in the primary
Cardmarket valuation path.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
import sqlite3
import statistics
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = ROOT / "backend/db/tcg_dashboard.db"
DEFAULT_SOURCE = ROOT / "reports/pokemon_151/finish_pricing_sources"
DEFAULT_CACHE = ROOT / "backend/scripts/.pokemon_151_finish_pricing_cache"
DEFAULT_OUTPUT = ROOT / "reports/pokemon_151/tcgplayer_pricing"
DEFAULT_BACKUP = DEFAULT_OUTPUT / "backups"
SET_CODE = "mew"
API_SET_ID = "sv3pt5"
DEX_SET_ID = "sv03.5"
EXPECTED_PHYSICAL = 362
EXPECTED_FINISH_COUNTS = {"normal": 128, "holo": 81, "reverse_holo": 153}
METRICS = {
    "low": ("low", "lowPrice"),
    "mid": ("mid", "midPrice"),
    "high": ("high", "highPrice"),
    "market": ("market", "marketPrice"),
    "direct_low": ("directLow", "directLowPrice"),
}
API_VARIANTS = {"normal": "normal", "holo": "holofoil", "reverse_holo": "reverseHolofoil"}
DEX_VARIANTS = {"normal": "normal", "holo": "holofoil", "reverse_holo": "reverse-holofoil"}
REPORT_FIELDS = [
    "card_id", "collector_number", "card_name", "finish", "source_provider", "market",
    "source_variant", "low", "mid", "high", "market_price", "direct_low", "currency",
    "source_updated_at", "observed_at", "snapshot_key", "pricing_status", "pricing_eligible",
    "would_insert", "would_update", "reason",
]
CROSSCHECK_FIELDS = [
    "card_id", "collector_number", "card_name", "finish", "pokemon_tcg_api_card_id",
    "pokemon_tcg_api_variant", "api_low", "api_market", "api_mid", "api_high",
    "api_updated_at", "tcgdex_card_id", "tcgdex_variant", "tcgdex_low", "tcgdex_market",
    "tcgdex_updated_at", "comparison_status", "difference_low", "difference_market",
    "identity_status", "finish_status", "eligible", "reason",
]


class ImportGate(RuntimeError):
    pass


def compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def norm_number(value: Any) -> str:
    raw = str(value or "").strip()
    digits = ""
    for char in raw:
        if char.isdigit():
            digits += char
        else:
            break
    return digits.zfill(3) if digits else raw


def norm_name(value: Any) -> str:
    return " ".join(str(value or "").casefold().split())


def positive(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0


def source_updated(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise ImportGate(f"missing audited report: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ImportGate(f"invalid cached JSON: {path}: {exc}") from exc


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: compact(row[field]) if isinstance(row.get(field), (dict, list)) else row.get(field, "") for field in fields})


def latest_entries(cache_dir: Path) -> dict[str, dict[str, Any]]:
    manifest_path = cache_dir / "manifest.json"
    if not manifest_path.exists():
        raise ImportGate(f"cache manifest not found: {manifest_path}")
    manifest = read_json(manifest_path)
    selected: dict[str, dict[str, Any]] = {}
    for entry in manifest.get("entries", []):
        if entry.get("status") != "OK":
            continue
        url = entry.get("url")
        if url:
            selected[url] = entry
    return selected


def find_cache(source_dir: Path) -> Path:
    candidates = [
        source_dir if (source_dir / "manifest.json").exists() else None,
        source_dir / "cache",
        DEFAULT_CACHE,
    ]
    for candidate in candidates:
        if candidate and (candidate / "manifest.json").exists():
            return candidate
    raise ImportGate("no audited cache manifest found; apply requires cached source data")


def load_sources(source_dir: Path) -> dict[str, Any]:
    report_manifest = source_dir / "source_manifest.json"
    if not report_manifest.exists():
        raise ImportGate(f"missing source_manifest.json: {report_manifest}")
    report_manifest_hash = sha256_file(report_manifest)
    cache_dir = find_cache(source_dir)
    entries = latest_entries(cache_dir)

    api_entry = next((entry for entry in entries.values() if entry.get("role") == "pokemon_tcg_api_cards"), None)
    if not api_entry:
        raise ImportGate("audited Pokémon TCG API bulk response is unavailable")
    api_payload = read_json(cache_dir / api_entry["cache_file"])
    api_rows = api_payload.get("data") if isinstance(api_payload, dict) else None
    if not isinstance(api_rows, list) or len(api_rows) != 207:
        raise ImportGate("audited Pokémon TCG API cache must contain exactly 207 records")

    dex_rows: list[dict[str, Any]] = []
    for entry in entries.values():
        if entry.get("role") != "tcgdex_card":
            continue
        payload = read_json(cache_dir / entry["cache_file"])
        if isinstance(payload, dict):
            dex_rows.append(payload)
    if len(dex_rows) != 207:
        raise ImportGate(f"audited TCGdex cache must contain exactly 207 records, got {len(dex_rows)}")

    documented_direct_low = False
    for entry in entries.values():
        if entry.get("role") != "pokemon_tcg_current_docs":
            continue
        content = (cache_dir / entry["cache_file"]).read_text(encoding="utf-8", errors="replace")
        if "directLow" in content or "direct low" in content.casefold():
            documented_direct_low = True
            break

    return {
        "api_rows": {norm_number(row.get("number")): row for row in api_rows},
        "dex_rows": {norm_number(row.get("localId")): row for row in dex_rows},
        "api_entry": api_entry,
        "cache_dir": str(cache_dir),
        "manifest_id": report_manifest_hash,
        "documented_direct_low": documented_direct_low,
    }


def load_catalog(conn: sqlite3.Connection, source_dir: Path) -> list[dict[str, Any]]:
    rows = [dict(row) for row in conn.execute("""
        SELECT c.id AS card_id, c.card_number AS collector_number, c.name AS card_name,
               c.finish, c.rarity, c.set_code, c.language_id, g.code AS game_code,
               c.catalog_status
          FROM cards c
          JOIN games g ON g.id = c.game_id
         WHERE g.code='pokemon' AND c.set_code=? AND c.catalog_status='active'
         ORDER BY CAST(c.card_number AS INTEGER), c.finish, c.id
    """, (SET_CODE,))]
    if len(rows) != EXPECTED_PHYSICAL:
        raise ImportGate(f"expected {EXPECTED_PHYSICAL} active physical printings, got {len(rows)}")
    counts = Counter(row["finish"] for row in rows)
    if dict(counts) != EXPECTED_FINISH_COUNTS:
        raise ImportGate(f"unexpected finish counts: {dict(counts)}")
    coverage = {row["card_id"]: row for row in read_csv(source_dir / "05_finish_price_coverage.csv")}
    for row in rows:
        audit = coverage.get(str(row["card_id"]))
        if audit is None:
            raise ImportGate(f"physical card {row['card_id']} missing from audited finish coverage")
        if audit["collector_number"] != norm_number(row["collector_number"]) or audit["finish"] != row["finish"]:
            raise ImportGate(f"audited physical identity mismatch for card_id={row['card_id']}")
    return rows


def identity_status(row: dict[str, Any] | None, number: str, name: str, set_id: str, number_key: str) -> tuple[str, str]:
    if not row:
        return "MISSING", "source record missing"
    actual_set = row.get("set", {}).get("id") if isinstance(row.get("set"), dict) else row.get("set")
    actual_number = row.get(number_key)
    actual_name = row.get("name")
    if str(actual_set) != set_id:
        return "MISMATCH", f"set {actual_set!r} != {set_id!r}"
    if norm_number(actual_number) != number:
        return "MISMATCH", f"number {actual_number!r} != {number!r}"
    if norm_name(actual_name) != norm_name(name):
        return "MISMATCH", f"name {actual_name!r} != {name!r}"
    return "EXACT", "set + collector number + name match"


def api_variant(row: dict[str, Any] | None, finish: str) -> dict[str, Any]:
    prices = ((row or {}).get("tcgplayer") or {}).get("prices") or {}
    key = API_VARIANTS[finish]
    payload = prices.get(key)
    return {"key": key, "exists": isinstance(payload, dict), "values": payload if isinstance(payload, dict) else {}, "updated_at": source_updated(((row or {}).get("tcgplayer") or {}).get("updatedAt"))}


def dex_variants(row: dict[str, Any] | None, finish: str) -> dict[str, Any]:
    key = DEX_VARIANTS[finish]
    candidates = []
    exists = False
    for variant in (row or {}).get("variants_detailed", []):
        family = {"normal": "normal", "holo": "holo", "reverse": "reverse_holo"}.get(variant.get("type"))
        if family != finish or variant.get("foil") not in (None, ""):
            continue
        pricing = (variant.get("pricing") or {}).get("tcgplayer") or {}
        if key in pricing:
            exists = True
            payload = pricing[key]
            if isinstance(payload, dict):
                candidates.append({
                    "values": payload,
                    "variant_id": variant.get("variantId"),
                    "product_id": payload.get("productId"),
                    "updated_at": source_updated(pricing.get("updated") or (row or {}).get("updated")),
                })
    candidates.sort(key=lambda item: (str(item.get("product_id") or ""), str(item.get("variant_id") or "")))
    chosen = candidates[0] if candidates else {"values": {}, "variant_id": None, "product_id": None, "updated_at": source_updated((row or {}).get("updated"))}
    return {"key": key, "exists": exists, "candidates": candidates, **chosen}


def metric_value(payload: dict[str, Any], metric: str, api: bool) -> float | None:
    key = METRICS[metric][0 if api else 1]
    value = payload.get(key)
    return float(value) if positive(value) else None


def relative_difference(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    return abs(left - right) / max(abs(left), abs(right)) if max(abs(left), abs(right)) else 0.0


def build_crosscheck(catalog: list[dict[str, Any]], sources: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    crosscheck: list[dict[str, Any]] = []
    pricing: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    differences: dict[str, list[float]] = {"low": [], "market": []}
    api_rows = sources["api_rows"]
    dex_rows = sources["dex_rows"]
    api_entry = sources["api_entry"]
    observed_at = api_entry.get("retrieved_at") or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    snapshot_key = api_entry["sha256"]
    for physical in catalog:
        number = norm_number(physical["collector_number"])
        name = physical["card_name"]
        api_row = api_rows.get(number)
        dex_row = dex_rows.get(number)
        api_identity, api_note = identity_status(api_row, number, name, API_SET_ID, "number")
        dex_identity, dex_note = identity_status(dex_row, number, name, DEX_SET_ID, "localId")
        av = api_variant(api_row, physical["finish"])
        dv = dex_variants(dex_row, physical["finish"])
        api_values = {metric: metric_value(av["values"], metric, True) for metric in METRICS}
        dex_values = {metric: metric_value(dv["values"], metric, False) for metric in METRICS}
        diffs = {metric: relative_difference(api_values[metric], dex_values[metric]) for metric in ("low", "market")}
        for metric, difference in diffs.items():
            if difference is not None:
                differences[metric].append(difference)
        dex_identity_conflict = dex_row is not None and dex_identity != "EXACT"
        dex_exact_variant_present = dex_row is not None and any(
            {"normal": "normal", "holo": "holo", "reverse": "reverse_holo"}.get(v.get("type")) == physical["finish"]
            and v.get("foil") in (None, "")
            for v in dex_row.get("variants_detailed", [])
        )
        dex_finish_conflict = dex_row is not None and not dex_exact_variant_present and any(
            {"normal": "normal", "holo": "holo", "reverse": "reverse_holo"}.get(v.get("type"))
            for v in dex_row.get("variants_detailed", [])
        )
        identity_conflict = dex_identity_conflict or dex_finish_conflict
        api_has_price = any(value is not None for value in api_values.values())
        api_currency = "USD"
        if api_identity != "EXACT":
            status = "IDENTITY_CONFLICT"
        elif identity_conflict:
            status = "IDENTITY_CONFLICT"
        elif not av["exists"]:
            status = "SOURCE_ONLY_TCGDEX" if dv["exists"] else "SOURCE_MISSING"
        elif not api_has_price:
            status = "PRICE_MISSING"
        elif not dv["exists"]:
            status = "SOURCE_ONLY_API"
        elif any(difference is not None and difference > 0.20 for difference in diffs.values()):
            status = "MATERIAL_DIFFERENCE"
        elif any(difference is not None and difference > 0 for difference in diffs.values()):
            status = "MINOR_DIFFERENCE"
        else:
            status = "MATCH"
        eligible = api_identity == "EXACT" and av["exists"] and api_has_price and api_currency == "USD" and not identity_conflict
        reasons = []
        if api_identity != "EXACT":
            reasons.append(f"Pokémon TCG API identity: {api_note}")
        if dex_identity_conflict:
            reasons.append(f"TCGdex identity: {dex_note}")
        if dex_finish_conflict:
            reasons.append("TCGdex finish variant is not exact")
        if not av["exists"]:
            reasons.append("API finish variant missing")
        elif not api_has_price:
            reasons.append("API finish payload has no positive metric")
        if status in {"MATERIAL_DIFFERENCE", "MINOR_DIFFERENCE"}:
            reasons.append("price discrepancy is diagnostic only; API remains authority")
        reason = "; ".join(reasons) or "exact identity and finish"
        dex_variant_label = dv["key"] if dv["exists"] else ""
        row = {
            "card_id": physical["card_id"], "collector_number": number, "card_name": name, "finish": physical["finish"],
            "pokemon_tcg_api_card_id": (api_row or {}).get("id", ""), "pokemon_tcg_api_variant": av["key"],
            "api_low": api_values["low"], "api_market": api_values["market"], "api_mid": api_values["mid"], "api_high": api_values["high"],
            "api_updated_at": av["updated_at"], "tcgdex_card_id": (dex_row or {}).get("id", ""), "tcgdex_variant": dex_variant_label,
            "tcgdex_low": dex_values["low"], "tcgdex_market": dex_values["market"], "tcgdex_updated_at": dv["updated_at"],
            "comparison_status": status, "difference_low": diffs["low"], "difference_market": diffs["market"],
            "identity_status": "EXACT" if api_identity == "EXACT" and not dex_identity_conflict else "CONFLICT",
            "finish_status": "EXACT" if av["exists"] and not dex_finish_conflict else "CONFLICT" if dex_finish_conflict else "MISSING",
            "eligible": eligible, "reason": reason,
        }
        crosscheck.append(row)
        valid_api_metrics = {metric: value for metric, value in api_values.items() if value is not None}
        if not sources["documented_direct_low"]:
            valid_api_metrics.pop("direct_low", None)
        pricing.append({
            "card_id": physical["card_id"], "collector_number": number, "card_name": name, "finish": physical["finish"],
            "source_provider": "pokemon_tcg_api" if eligible else "", "market": "tcgplayer" if eligible else "",
            "source_variant": av["key"] if eligible else "", **valid_api_metrics,
            "market_price": valid_api_metrics.get("market"), "currency": api_currency if eligible else "",
            "source_updated_at": av["updated_at"] if eligible else "", "observed_at": observed_at if eligible else "",
            "snapshot_key": snapshot_key if eligible else "", "pricing_status": status, "pricing_eligible": eligible,
            "reason": reason,
        })
        if eligible:
            provenance = {
                "provider": "pokemon_tcg_api", "market": "tcgplayer", "source_variant": av["key"],
                "source_card_id": (api_row or {}).get("id"), "source_snapshot_sha256": snapshot_key,
                "source_manifest_id": sources["manifest_id"], "observed_at": observed_at,
                "tcgdex_cross_check": {
                    "card_id": (dex_row or {}).get("id"), "variant": dex_variant_label, "comparison_status": status,
                    "difference_low": diffs["low"], "difference_market": diffs["market"],
                },
            }
            confidence = "medium"
            for metric, value in valid_api_metrics.items():
                observations.append({
                    "card_id": physical["card_id"], "provider": "pokemon_tcg_api", "market": "tcgplayer",
                    "metric": metric, "value": value, "currency": "USD", "source_updated_at": av["updated_at"],
                    "observed_at": observed_at, "snapshot_key": snapshot_key, "provenance": compact(provenance),
                    "confidence": confidence, "source_variant": av["key"], "source_updated_at_sort": av["updated_at"] or "",
                })
    stats = {}
    for metric, values in differences.items():
        stats[metric] = {
            "count": len(values), "p50": statistics.quantiles(values, n=100)[49] if len(values) >= 2 else (values[0] if values else None),
            "p75": statistics.quantiles(values, n=100)[74] if len(values) >= 2 else (values[0] if values else None),
            "p90": statistics.quantiles(values, n=100)[89] if len(values) >= 2 else (values[0] if values else None),
            "max": max(values) if values else None,
        }
    return crosscheck, pricing, observations, {"stats": stats, "observed_at": observed_at, "snapshot_key": snapshot_key}


def ensure_observation_schema(conn: sqlite3.Connection) -> None:
    schema = (ROOT / "backend/db/schema.sql").read_text(encoding="utf-8")
    conn.executescript(schema)
    conn.execute("PRAGMA foreign_keys=ON")


def database_digest(conn: sqlite3.Connection, exclude: set[str] | None = None) -> str:
    exclude = exclude or set()
    tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name") if row[0] not in exclude and not row[0].startswith("sqlite_")]
    digest = hashlib.sha256()
    for table in tables:
        digest.update(table.encode())
        cursor = conn.execute(f'SELECT * FROM "{table}"')
        for row in cursor:
            digest.update(compact(tuple(row)).encode())
    return digest.hexdigest()


def observation_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (row["card_id"], row["provider"], row["market"], row["metric"], row["currency"], row["snapshot_key"])


def existing_observation_keys(conn: sqlite3.Connection) -> set[tuple[Any, ...]]:
    return {observation_key(dict(row)) for row in conn.execute("SELECT card_id, provider, market, metric, currency, snapshot_key FROM market_price_observations")}


def persist_observations(conn: sqlite3.Connection, observations: list[dict[str, Any]]) -> tuple[int, int, list[dict[str, Any]]]:
    existing = existing_observation_keys(conn)
    to_insert = [row for row in observations if observation_key(row) not in existing]
    for row in to_insert:
        conn.execute("""
            INSERT INTO market_price_observations
              (card_id, provider, market, metric, value, currency, source_updated_at,
               observed_at, snapshot_key, provenance, confidence, source_variant)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, tuple(row[field] for field in ("card_id", "provider", "market", "metric", "value", "currency", "source_updated_at", "observed_at", "snapshot_key", "provenance", "confidence", "source_variant")))
    return len(to_insert), 0, to_insert


def persisted_rows_for_snapshot(conn: sqlite3.Connection, snapshot_key: str) -> list[dict[str, Any]]:
    return [dict(row) for row in conn.execute("""
        SELECT o.card_id, c.card_number AS collector_number, c.name AS card_name, c.finish,
               o.provider, o.market, o.metric, o.value, o.currency, o.source_updated_at,
               o.observed_at, o.provenance
          FROM market_price_observations o
          JOIN cards c ON c.id=o.card_id
         WHERE o.snapshot_key=?
         ORDER BY c.id, o.metric
    """, (snapshot_key,))]


def format_stat(value: float | None) -> str:
    return "—" if value is None else f"{value:.4f}"


def write_reports(output: Path, crosscheck: list[dict[str, Any]], pricing: list[dict[str, Any]], observations: list[dict[str, Any]], persisted: list[dict[str, Any]], stats: dict[str, Any], db_before: str, db_after: str | None, apply: bool, validation: dict[str, Any]) -> None:
    output.mkdir(parents=True, exist_ok=True)
    schema_lines = [
        "# Schema audit — TCGplayer secondary pricing", "",
        "`market_price_history` remains Cardmarket-specific and `printing_price_resolutions` remains the primary valuation path.",
        "The generic `market_price_observations` table stores one positive metric per physical printing and source snapshot.",
        "", "Uniqueness:", "`card_id + provider + market + metric + currency + snapshot_key`.",
        "", "Temporal semantics:", "`source_updated_at` is supplied by Pokémon TCG API; `observed_at` is the audited snapshot acquisition time.",
        "", f"Database SHA before: `{db_before}`", f"Database SHA after: `{db_after or 'not applied'}`", "",
    ]
    (output / "01_schema_audit.md").write_text("\n".join(schema_lines), encoding="utf-8")
    write_csv(output / "02_source_crosscheck.csv", crosscheck, CROSSCHECK_FIELDS)
    for row in pricing:
        row["would_insert"] = any(observation_key(observation) not in validation["existing_keys"] for observation in observations if observation["card_id"] == row["card_id"])
        row["would_update"] = False
    write_csv(output / "03_pricing_dry_run.csv", pricing, REPORT_FIELDS)
    imported = []
    for row in persisted:
        imported.append({
            "card_id": row["card_id"], "collector_number": row["collector_number"], "card_name": row["card_name"], "finish": row["finish"],
            "provider": row["provider"], "market": row["market"], "metric": row["metric"], "value": row["value"], "currency": row["currency"],
            "source_updated_at": row["source_updated_at"], "snapshot_date": row["observed_at"], "provenance": row["provenance"],
        })
    write_csv(output / "04_imported_prices.csv", imported, ["card_id", "collector_number", "card_name", "finish", "provider", "market", "metric", "value", "currency", "source_updated_at", "snapshot_date", "provenance"])
    unpriced = []
    for row in pricing:
        if row["pricing_eligible"]:
            continue
        status = row["pricing_status"]
        reason = "SOURCE_MISSING" if status == "SOURCE_MISSING" else "PRICE_MISSING" if status == "PRICE_MISSING" else "FINISH_MISMATCH" if status == "IDENTITY_CONFLICT" and "finish" in row["reason"].casefold() else "IDENTITY_AMBIGUOUS" if status == "IDENTITY_CONFLICT" else "SOURCE_MISSING" if status == "SOURCE_ONLY_TCGDEX" else "OTHER"
        unpriced.append({"card_id": row["card_id"], "collector_number": row["collector_number"], "card_name": row["card_name"], "finish": row["finish"], "reason": reason, "detail": row["reason"]})
    write_csv(output / "05_unpriced_printings.csv", unpriced, ["card_id", "collector_number", "card_name", "finish", "reason", "detail"])
    discrepancies = []
    for row in crosscheck:
        if row["comparison_status"] in {"MATERIAL_DIFFERENCE", "MINOR_DIFFERENCE", "IDENTITY_CONFLICT"}:
            discrepancies.append({
                "card_id": row["card_id"], "collector_number": row["collector_number"], "card_name": row["card_name"], "finish": row["finish"],
                "comparison_status": row["comparison_status"], "difference_low": row["difference_low"], "difference_market": row["difference_market"],
                "api_low": row["api_low"], "tcgdex_low": row["tcgdex_low"], "api_market": row["api_market"], "tcgdex_market": row["tcgdex_market"],
                "api_updated_at": row["api_updated_at"], "tcgdex_updated_at": row["tcgdex_updated_at"],
                "possible_cause": "refresh timing or source rounding" if "DIFFERENCE" in row["comparison_status"] else "identity/finish evidence conflict",
                "review_recommendation": "persist API authority and flag" if "DIFFERENCE" in row["comparison_status"] else "block persistence and review mapping",
            })
    write_csv(output / "06_source_discrepancies.csv", discrepancies, ["card_id", "collector_number", "card_name", "finish", "comparison_status", "difference_low", "difference_market", "api_low", "tcgdex_low", "api_market", "tcgdex_market", "api_updated_at", "tcgdex_updated_at", "possible_cause", "review_recommendation"])
    counts = Counter(row["finish"] for row in pricing if row["pricing_eligible"])
    status_counts = Counter(row["pricing_status"] for row in pricing)
    validation_lines = [
        "# Post-apply validation — TCGplayer secondary pricing", "", f"Pokémon physical printings: `{len(pricing)}`",
        f"TCGplayer secondary priced: `{sum(counts.values())}` physical printings", f"normal priced: `{counts['normal']} / 128`",
        f"holo priced: `{counts['holo']} / 81`", f"reverse priced: `{counts['reverse_holo']} / 153`",
        f"unpriced: `{len(unpriced)}`", "", "currency: `USD only`", "current_price changed: `NO`", "market_value changed: `NO`",
        "Cardmarket pricing changed: `NO`", "Cardmarket mappings changed: `NO`", "Magic changed: `NO`", "One Piece changed: `NO`",
        "Collection changed: `NO`", "Wishlist changed: `NO`", f"DB integrity: `{validation['integrity']}`",
        f"foreign keys: `{validation['foreign_keys']}`", f"second apply: `{'NO-OP' if validation['inserted'] == 0 else 'PENDING'}`", "",
        f"status counts: `{dict(status_counts)}`", "", "## Difference distribution", "",
        "The 20% value is recorded as `diagnostic_threshold_candidate`, not as a persistence gate.",
    ]
    for metric in ("low", "market"):
        metric_stats = stats["stats"][metric]
        validation_lines.append(f"- {metric}: n={metric_stats['count']}, p50={format_stat(metric_stats['p50'])}, p75={format_stat(metric_stats['p75'])}, p90={format_stat(metric_stats['p90'])}, max={format_stat(metric_stats['max'])}")
    (output / "07_post_apply_validation.md").write_text("\n".join(validation_lines) + "\n", encoding="utf-8")
    summary = [
        "# POKEMON-151-003 — TCGPLAYER SECONDARY PRICING", "", f"Physical printings: `{len(pricing)}`",
        f"TCGplayer eligible: `{sum(1 for row in pricing if row['pricing_eligible'])}`", f"TCGplayer priced: `{len(persisted)}` metric observations",
        f"Normal: `{counts['normal']} / 128`", f"Holo: `{counts['holo']} / 81`", f"Reverse Holo: `{counts['reverse_holo']} / 153`",
        "Pokémon TCG API used as authority: `YES`", "TCGdex used as cross-check: `YES`",
        f"Material discrepancies: `{sum(1 for row in crosscheck if row['comparison_status'] == 'MATERIAL_DIFFERENCE')}`",
        f"Unpriced: `{len(unpriced)}`", "Primary Cardmarket current_price populated: `0 new`", "Primary market_value populated: `0 new`",
        "TCGplayer currency: `USD`", "Silent EUR conversion: `NO`", "Magic modified: `NO`", "One Piece modified: `NO`",
        "Collection modified: `NO`", "Wishlist modified: `NO`", f"Import idempotent: `{'YES' if validation['inserted'] == 0 else 'YES after first apply'}`",
        "Ready for UI use: `YES`", "", "## Diagnostic distribution", "",
        "`20%` is a `diagnostic_threshold_candidate`; it does not block numerically discrepant exact mappings.",
    ]
    for metric in ("low", "market"):
        metric_stats = stats["stats"][metric]
        summary.append(f"- {metric}: p50={format_stat(metric_stats['p50'])}, p75={format_stat(metric_stats['p75'])}, p90={format_stat(metric_stats['p90'])}, max={format_stat(metric_stats['max'])}")
    (output / "08_summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")


def validate_integrity(conn: sqlite3.Connection) -> tuple[str, str]:
    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    foreign_keys = conn.execute("PRAGMA foreign_key_check").fetchall()
    return integrity, "OK" if not foreign_keys else compact([tuple(row) for row in foreign_keys])


def run(db: Path, source_dir: Path, output: Path, backup_dir: Path, apply: bool) -> dict[str, Any]:
    if not db.exists():
        raise ImportGate(f"database not found: {db}")
    sources = load_sources(source_dir)
    original = sqlite3.connect(db)
    original.row_factory = sqlite3.Row
    original.execute("PRAGMA foreign_keys=ON")
    try:
        db_before = sha256_file(db)
        catalog = load_catalog(original, source_dir)
        before_digest = database_digest(original, {"market_price_observations"})
    finally:
        original.close()
    with tempfile.TemporaryDirectory(prefix="pokemon151-tcgplayer-") as tmp:
        work_db = Path(tmp) / db.name
        shutil.copy2(db, work_db)
        conn = sqlite3.connect(work_db)
        conn.row_factory = sqlite3.Row
        try:
            ensure_observation_schema(conn)
            crosscheck, pricing, observations, stats = build_crosscheck(catalog, sources)
            existing_keys = existing_observation_keys(conn)
            planned_insertions = [row for row in observations if observation_key(row) not in existing_keys]
            inserted = 0
            if apply:
                conn.execute("BEGIN IMMEDIATE")
                inserted, _, _ = persist_observations(conn, observations)
                conn.commit()
            integrity, foreign_keys = validate_integrity(conn)
            if integrity != "ok" or foreign_keys != "OK":
                raise ImportGate(f"working database integrity failure: {integrity}; foreign keys: {foreign_keys}")
            after_digest = database_digest(conn, {"market_price_observations"})
            if before_digest != after_digest:
                raise ImportGate("out-of-scope database rows changed during secondary import")
            persisted = persisted_rows_for_snapshot(conn, stats["snapshot_key"])
            validation = {"integrity": integrity, "foreign_keys": foreign_keys, "inserted": inserted, "existing_keys": existing_keys}
            write_reports(output, crosscheck, pricing, observations, persisted, stats, db_before, None, apply, validation)
            if apply:
                backup_dir.mkdir(parents=True, exist_ok=True)
                backup = backup_dir / f"tcg_dashboard.before_pokemon_151_003_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.db"
                shutil.copy2(db, backup)
                shutil.copy2(work_db, db)
                db_after = sha256_file(db)
                output_validation = dict(validation)
                final_conn = sqlite3.connect(db)
                final_conn.row_factory = sqlite3.Row
                try:
                    final_persisted = persisted_rows_for_snapshot(final_conn, stats["snapshot_key"])
                finally:
                    final_conn.close()
                write_reports(output, crosscheck, pricing, observations, final_persisted, stats, db_before, db_after, apply, output_validation)
            else:
                db_after = None
        finally:
            conn.close()
    eligible_by_finish = Counter(row["finish"] for row in pricing if row["pricing_eligible"])
    result = {
        "physical_printings_checked": len(pricing), "eligible": sum(eligible_by_finish.values()),
        "eligible_by_finish": dict(eligible_by_finish), "observations_to_insert": len(planned_insertions),
        "observations_inserted": inserted, "unpriced": sum(1 for row in pricing if not row["pricing_eligible"]),
        "material_discrepancies": sum(1 for row in crosscheck if row["comparison_status"] == "MATERIAL_DIFFERENCE"),
        "db_before": db_before, "db_after": db_after, "output": str(output),
    }
    print(f"physical printings checked: {result['physical_printings_checked']}")
    print("TCGplayer eligible:")
    for finish in ("normal", "holo", "reverse_holo"):
        print(f"{finish}: {result['eligible_by_finish'].get(finish, 0)}")
    print(f"unpriced: {result['unpriced']}")
    print(f"prices to insert: {result['observations_to_insert']}")
    print("prices to update: 0")
    print("current_price changes: 0")
    print("market_value changes: 0")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--backup-dir", type=Path, default=DEFAULT_BACKUP)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if args.dry_run == args.apply:
        parser.error("choose exactly one of --dry-run or --apply")
    try:
        run(args.db, args.source_dir, DEFAULT_OUTPUT, args.backup_dir, args.apply)
    except ImportGate as exc:
        print(f"IMPORT BLOCKED: {exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
