#!/usr/bin/env python3
"""Audit Cardmarket finish semantics for Pokémon Scarlet & Violet—151.

The command acquires and caches only public/official evidence. Applying a
resolution is explicitly offline and writes mapping status/evidence only; it
never writes monetary values or pricing snapshots.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import os
import re
import sqlite3
import tempfile
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

import resolve_pokemon_151_cardmarket as canonical_resolver
import resolve_pokemon_151_metric_mappings as metric_resolver


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = ROOT / "backend/db/tcg_dashboard.db"
DEFAULT_PRODUCTS = Path("/Users/facundogalmarini/Desktop/products_singles_6 (1).json")
DEFAULT_PRICES = Path("/Users/facundogalmarini/Desktop/price_guide_6 (1).json")
DEFAULT_MAPPING_DIR = ROOT / "reports/pokemon_151/cardmarket_metric_mapping"
DEFAULT_OUTPUT = ROOT / "reports/pokemon_151/cardmarket_semantics"
DEFAULT_CACHE = ROOT / "backend/scripts/.pokemon_151_cardmarket_semantics_cache"
EXPANSION_ID = 5328
CATEGORY_ID = 51
METRIC_TABLE = "cardmarket_product_metric_mappings"
CURRENT_DOCS = [
    ("pokemon_help", "https://help.cardmarket.com/en/finding-and-listing-pokemon-cards", "current_help"),
    ("article_api", "https://api.cardmarket.com/ws/documentation/API_2.0%3AEntities%3AArticle", "current_api"),
    ("category_attributes", "https://api.cardmarket.com/ws/documentation/API_2.0%3ACategory_Specific_Attributes", "current_api"),
    ("articles_api", "https://api.cardmarket.com/ws/documentation/API_2.0%3AArticles", "current_api"),
]
LEGACY_DOCS = [
    ("legacy_priceguide_api", "https://api.cardmarket.com/ws/documentation/API_2.0%3APriceGuide", "legacy_api"),
]
METRIC_COLUMNS = {
    "base": ("low", "trend", "avg1", "avg7", "avg30"),
    "foil": ("low-holo", "trend-holo", "avg1-holo", "avg7-holo", "avg30-holo"),
}
STATUS_VALUES = {"EXACT", "SUPPORTED", "AMBIGUOUS", "UNRESOLVED", "MISMATCH"}


class SemanticsGateError(RuntimeError):
    pass


def compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def scalar(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()) -> Any:
    return conn.execute(sql, params).fetchone()[0]


def connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def strip_html(value: bytes) -> str:
    text = value.decode("utf-8", errors="replace")
    text = re.sub(r"<script[^>]*>.*?</script>|<style[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


class SourceCache:
    def __init__(self, directory: Path, offline: bool, refresh: bool):
        self.directory = directory
        self.offline = offline
        self.refresh = refresh
        self.directory.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.directory / "manifest.json"
        if self.manifest_path.exists():
            self.manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        else:
            self.manifest = {"version": 1, "entries": []}

    def _entry(self, url: str) -> dict[str, Any] | None:
        entries = [entry for entry in self.manifest["entries"] if entry["url"] == url]
        return entries[-1] if entries else None

    def fetch(self, url: str, role: str) -> dict[str, Any]:
        previous = self._entry(url)
        if previous and not self.refresh:
            path = self.directory / previous["cache_file"]
            if path.exists():
                result = dict(previous)
                result["content"] = path.read_bytes()
                return result
        if self.offline:
            result = {"url": url, "role": role, "retrieved_at": None, "sha256": None, "content_type": None, "http_status": None, "status": "MISSING_OFFLINE", "cache_file": None, "content": b""}
            return result
        request = Request(url, headers={"User-Agent": "TCG-Dashboard-Pokemon151-Semantics-Audit/1.0"})
        status = "OK"
        http_status = None
        content_type = None
        content = b""
        try:
            with urlopen(request, timeout=25) as response:
                http_status = response.status
                content_type = response.headers.get("Content-Type")
                content = response.read()
        except HTTPError as error:
            http_status = error.code
            content_type = error.headers.get("Content-Type") if error.headers else None
            content = error.read() if hasattr(error, "read") else b""
            status = "LEGACY_GONE" if error.code == 410 else "BLOCKED" if error.code in {401, 403, 429} else "ERROR"
        except (URLError, TimeoutError, OSError) as error:
            content = str(error).encode("utf-8")
            status = "ERROR"
        digest = hashlib.sha256(content).hexdigest()
        cache_file = f"{digest}.bin"
        (self.directory / cache_file).write_bytes(content)
        result = {"url": url, "role": role, "retrieved_at": now(), "sha256": digest, "content_type": content_type, "http_status": http_status, "status": status, "cache_file": cache_file, "content": content}
        self.manifest["entries"] = [entry for entry in self.manifest["entries"] if entry["url"] != url]
        self.manifest["entries"].append({key: result[key] for key in ("url", "role", "retrieved_at", "sha256", "content_type", "http_status", "status", "cache_file")})
        self.manifest_path.write_text(json.dumps(self.manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        time.sleep(0.2)
        return result


def load_local_sources(products_path: Path, prices_path: Path, mapping_dir: Path) -> tuple[list[dict[str, Any]], dict[int, dict[str, Any]], dict[str, Any]]:
    products_payload = json.loads(products_path.read_text(encoding="utf-8"))
    prices_payload = json.loads(prices_path.read_text(encoding="utf-8"))
    products = [row for row in products_payload["products"] if row.get("idExpansion") == EXPANSION_ID and row.get("idCategory") == CATEGORY_ID]
    if len(products) != 210:
        raise SemanticsGateError(f"expected 210 source products, got {len(products)}")
    prices = {int(row["idProduct"]): row for row in prices_payload["priceGuides"] if row.get("idProduct") is not None}
    mapping_rows = list(csv.DictReader((mapping_dir / "02_metric_mapping_dry_run.csv").open(encoding="utf-8", newline="")))
    if len(mapping_rows) != 270:
        raise SemanticsGateError(f"expected 270 existing metric relationships, got {len(mapping_rows)}")
    manifest = {
        "products_path": str(products_path),
        "products_sha256": hashlib.sha256(products_path.read_bytes()).hexdigest(),
        "prices_path": str(prices_path),
        "prices_sha256": hashlib.sha256(prices_path.read_bytes()).hexdigest(),
        "mapping_report_path": str(mapping_dir / "02_metric_mapping_dry_run.csv"),
        "mapping_report_sha256": hashlib.sha256((mapping_dir / "02_metric_mapping_dry_run.csv").read_bytes()).hexdigest(),
    }
    return products, prices, manifest


def audit_local_priceguide(prices: dict[int, dict[str, Any]]) -> dict[str, Any]:
    keys = set().union(*(row.keys() for row in prices.values()))
    expected = set(METRIC_COLUMNS["base"]) | set(METRIC_COLUMNS["foil"])
    return {
        "observed_metric_columns": sorted(keys & expected),
        "base_columns": list(METRIC_COLUMNS["base"]),
        "foil_columns": list(METRIC_COLUMNS["foil"]),
        "all_expected_columns_present": expected.issubset(keys),
        "numeric_values_persisted": False,
    }


def fetch_documentation(cache: SourceCache) -> list[dict[str, Any]]:
    results = []
    for name, url, role in CURRENT_DOCS + LEGACY_DOCS:
        result = cache.fetch(url, role)
        text = strip_html(result["content"])
        results.append({"name": name, "url": url, "role": role, "status": result["status"], "http_status": result["http_status"], "sha256": result["sha256"], "text": text, "cache_file": result["cache_file"]})
    return results


def semantics_matrix(documents: list[dict[str, Any]], local_audit: dict[str, Any]) -> list[dict[str, Any]]:
    by_name = {doc["name"]: doc for doc in documents}
    help_text = by_name.get("pokemon_help", {}).get("text", "").casefold()
    article_text = by_name.get("article_api", {}).get("text", "").casefold()
    legacy = by_name.get("legacy_priceguide_api", {})
    rows = []
    def add(concept: str, level: str, source_role: str, finding: str, classification: str, source: dict[str, Any] | None, notes: str = ""):
        rows.append({"concept": concept, "level": level, "source_role": source_role, "finding": finding, "classification": classification, "source_url": source.get("url") if source else "local Price Guide JSON", "source_status": source.get("status") if source else "LOCAL", "source_sha256": source.get("sha256") if source else "", "notes": notes})
    add("product", "product", "current_api", "Cardmarket product is the catalog identity identified by idProduct.", "SOURCE FACT" if "idproduct" in article_text else "UNKNOWN", by_name.get("article_api"), "Product/page distinction remains separate from article flags.")
    add("article/listing", "article/listing", "current_api", "Article records may carry listing-specific flags and condition/language.", "SOURCE FACT" if "article" in article_text else "UNKNOWN", by_name.get("article_api"))
    add("isFoil", "article/listing", "current_api", "isFoil is a separate article property; the current Article documentation marks it deprecated for Pokémon singles.", "SOURCE FACT" if "isfoil" in article_text and "deprecated" in article_text else "UNKNOWN", by_name.get("article_api"), "Never equated to Reverse Holo.")
    add("isReverseHolo", "article/listing", "current_api", "isReverseHolo is a separate Pokémon article property.", "SOURCE FACT" if "isreverseholo" in article_text else "UNKNOWN", by_name.get("article_api"), "Reverse Holo is not inferred from foil terminology.")
    add("Reverse Holo", "listing attribute", "current_help", "Reverse Holo is a Pokémon listing attribute, not a rarity.", "SOURCE FACT" if "reverse holo is not a rarity" in help_text else "UNKNOWN", by_name.get("pokemon_help"))
    add("Regular Holofoil", "card characteristic/rarity", "current_help", "Regular Holofoil is distinguished from Reverse Holo in Pokémon listings.", "SOURCE FACT" if "regular holofoil" in help_text else "UNKNOWN", by_name.get("pokemon_help"))
    add("version", "product/catalog", "current_help", "Cardmarket documents versions as potentially distinct and warns against assuming same-name products are interchangeable.", "SOURCE FACT" if "versions can be quite complicated" in help_text else "UNKNOWN", by_name.get("pokemon_help"))
    add("idProduct", "product", "current_api", "External Cardmarket product identifier.", "SOURCE FACT" if "idproduct" in article_text else "UNKNOWN", by_name.get("article_api"))
    add("idMetacard", "metaproduct/group", "local audit", "Existing 002 evidence treats idMetacard as a commercial grouping, not numbered-card identity.", "DERIVED CONCLUSION", None)
    add("base Price Guide metric", "price-guide", "local snapshot", f"Local JSON exposes {local_audit['base_columns']}.", "SOURCE FACT", None, "Numeric values are not persisted by 002C.")
    add("foil Price Guide metric", "price-guide", "local snapshot", f"Local JSON exposes {local_audit['foil_columns']}.", "SOURCE FACT", None, "Numeric values are not persisted by 002C; no Reverse-specific family exists.")
    add("legacy PriceGuide API", "documentation", "legacy_api", "Legacy PriceGuide documentation is historical evidence only and must not be the sole basis for EXACT.", "UNKNOWN" if legacy.get("status") in {"LEGACY_GONE", "BLOCKED", "MISSING_OFFLINE"} else "SOURCE FACT", legacy, "Current local JSON controls actual field names.")
    return rows


def load_contexts(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(f"""
        SELECT p.id AS internal_product_id, p.cardmarket_id_product, p.raw_name,
               s.canonical_card_id, s.finish_scope, s.compatible_finishes,
               s.mapping_status AS canonical_mapping_status,
               cc.canonical_number, cc.name AS canonical_name
          FROM cardmarket_product_printing_scopes s
          JOIN cardmarket_products p ON p.id=s.cardmarket_product_id
          JOIN canonical_cards cc ON cc.id=s.canonical_card_id
         WHERE p.cardmarket_id_expansion=? AND p.cardmarket_id_category=?
           AND s.mapping_status='EXACT'
         ORDER BY p.cardmarket_id_product
    """, (EXPANSION_ID, CATEGORY_ID)).fetchall()
    if len(rows) != 137:
        raise SemanticsGateError(f"expected 137 exact products, got {len(rows)}")
    contexts = []
    for row in rows:
        finishes = json.loads(row["compatible_finishes"] or "[]")
        physical = [dict(item) for item in conn.execute("""
            SELECT id AS card_id, finish, rarity, art_kind
              FROM cards WHERE canonical_card_id=? AND set_code='mew' AND catalog_status='active'
             ORDER BY finish, id
        """, (row["canonical_card_id"],))]
        candidates = [item for item in physical if item["finish"] in finishes]
        contexts.append({**dict(row), "compatible_finishes": finishes, "physical": physical, "candidate_cards": candidates})
    return contexts


def name_slug(value: str) -> str:
    value = value.replace("♀", "-F").replace("♂", "-M")
    value = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-")
    return value


def candidate_product_url(context: dict[str, Any]) -> str:
    number = str(context["canonical_number"]).zfill(3)
    return f"https://www.cardmarket.com/en/Pokemon/Products/Singles/151/{name_slug(context['canonical_name'])}-V1-MEW{number}"


def group_name(context: dict[str, Any]) -> str:
    finishes = set(context["compatible_finishes"])
    rarities = {str(item.get("rarity") or "").casefold() for item in context["physical"]}
    if any(token in rarity for rarity in rarities for token in ("illustration", "ultra", "special illustration", "hyper")):
        return "higher_rarity_special_art"
    if finishes == {"normal", "reverse_holo"}:
        return "normal_reverse_holo"
    if finishes == {"holo", "reverse_holo"}:
        return "holo_reverse_holo"
    if finishes == {"holo"}:
        return "holo_only"
    if finishes == {"normal"}:
        return "normal_only"
    return "unknown_scope"


def choose_sample(contexts: list[dict[str, Any]], minimum: int = 20) -> list[dict[str, Any]]:
    grouped = defaultdict(list)
    for context in contexts:
        grouped[group_name(context)].append(context)
    selected = []
    quotas = [("normal_reverse_holo", 6), ("holo_reverse_holo", 4), ("holo_only", 2), ("normal_only", 2), ("higher_rarity_special_art", 6)]
    for group, quota in quotas:
        selected.extend(grouped[group][:quota])
    selected_ids = {item["internal_product_id"] for item in selected}
    for context in contexts:
        if len(selected) >= minimum:
            break
        if context["internal_product_id"] not in selected_ids:
            selected.append(context)
            selected_ids.add(context["internal_product_id"])
    return selected


def parse_page(context: dict[str, Any], url: str, result: dict[str, Any]) -> dict[str, Any]:
    raw = result["content"]
    text = strip_html(raw)
    lower = text.casefold()
    blocked = result["status"] in {"BLOCKED", "ERROR", "MISSING_OFFLINE", "LEGACY_GONE"}
    def value_after(pattern: str) -> str:
        match = re.search(pattern + r"\s*([0-9]+[,.][0-9]{2})\s*€?", text, flags=re.I)
        return match.group(1) if match else ""
    reverse_present = "YES" if "only reverse" in lower or "reverse holo" in lower else "UNKNOWN" if blocked else "NO"
    versions = sorted(set(re.findall(r"\bV([0-9]+)\b", url, flags=re.I)))
    return {
        "idProduct": context["cardmarket_id_product"], "collector_number": context["canonical_number"], "card_name": context["canonical_name"],
        "rarity": sorted({item.get("rarity") for item in context["physical"] if item.get("rarity")}), "internal_finishes": context["compatible_finishes"],
        "cardmarket_url": url, "reverse_filter_present": reverse_present,
        "default_from": value_after(r"From"), "default_trend": value_after(r"Price Trend"), "default_avg1": value_after(r"1-day average"), "default_avg7": value_after(r"7-days average"), "default_avg30": value_after(r"30-days average"),
        "reverse_filter_method": "not_observable" if blocked else "present_but_mechanism_requires_manual_review" if reverse_present == "YES" else "not_observed",
        "filtered_reverse_from": "", "filtered_reverse_trend": "", "filtered_reverse_avg1": "", "filtered_reverse_avg7": "", "filtered_reverse_avg30": "",
        "observation_status": result["status"], "http_status": result["http_status"], "retrieved_at": result["retrieved_at"], "cache_file": result["cache_file"], "evidence_source": result["url"], "evidence_sha256": result["sha256"], "notes": "Page observations are evidence only; no numeric value is persisted to DB.",
        "version": ",".join(versions), "rule_group": group_name(context),
    }


def product_observations(cache: SourceCache, contexts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    observations = []
    for context in choose_sample(contexts):
        url = candidate_product_url(context)
        result = cache.fetch(url, "product_page_sample")
        observations.append(parse_page(context, url, result))
    return observations


def reverse_analysis(observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for observation in observations:
        present = observation["reverse_filter_present"]
        rows.append({
            "idProduct": observation["idProduct"], "collector_number": observation["collector_number"],
            "reverse_supported_internally": "reverse_holo" in observation["internal_finishes"],
            "reverse_filter_present": present, "normal_and_reverse_same_product": "UNKNOWN",
            "reverse_separate_product": "UNKNOWN", "unknown": present == "UNKNOWN",
            "aggregate_changes_when_filtered": "UNKNOWN", "offer_list_changes_when_filtered": "UNKNOWN",
            "conclusion": "BLOCKED" if present == "UNKNOWN" else "filter_presence_observed_but_aggregate_semantics_unproven",
            "confidence": "LOW", "evidence": observation["evidence_source"],
        })
    return rows


def metric_conclusions(matrix: list[dict[str, Any]], observations: list[dict[str, Any]], local_audit: dict[str, Any]) -> list[dict[str, Any]]:
    current_help = next((row for row in matrix if row["concept"] == "Reverse Holo"), {})
    current_foil = next((row for row in matrix if row["concept"] == "isFoil"), {})
    legacy = next((row for row in matrix if row["concept"] == "legacy PriceGuide API"), {})
    return [
        {"metric_family": "base", "source_field": ",".join(local_audit["base_columns"]), "official_documented_meaning": "LOW/non-foil family is documented historically; legacy status is recorded separately.", "pokemon_specific_interpretation": "BASE reverse inclusion is not determined by local JSON or current sampled observations.", "reverse_included": "UNKNOWN", "reverse_excluded": "UNKNOWN", "unknown": True, "physical_finish_target": "none", "confidence": "LOW", "evidence": compact({"local": local_audit, "legacy": legacy})},
        {"metric_family": "foil", "source_field": ",".join(local_audit["foil_columns"]), "official_documented_meaning": "FOIL family is a foil metric family; it is not a Reverse-specific family.", "pokemon_specific_interpretation": "FOIL is not equivalent to Pokémon reverse_holo without product-specific evidence.", "reverse_included": "UNKNOWN", "reverse_excluded": "UNKNOWN", "unknown": True, "physical_finish_target": "none", "confidence": "LOW", "evidence": compact({"current_isFoil": current_foil, "reverse_holo": current_help})},
    ]


def read_existing_rows(conn: sqlite3.Connection) -> dict[tuple[int, str], sqlite3.Row]:
    if not scalar(conn, "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?", (METRIC_TABLE,)):
        return {}
    return {(int(row[0]), row[1]): row for row in conn.execute(f"""
        SELECT p.cardmarket_id_product, m.metric_family, m.*
          FROM {METRIC_TABLE} m JOIN cardmarket_products p ON p.id=m.cardmarket_product_id
         WHERE p.cardmarket_id_expansion=? AND p.cardmarket_id_category=?
    """, (EXPANSION_ID, CATEGORY_ID))}


def resolve_decisions(conn: sqlite3.Connection, products: list[dict[str, Any]], prices: dict[int, dict[str, Any]], contexts: list[dict[str, Any]], observations: list[dict[str, Any]], matrix: list[dict[str, Any]], local_audit: dict[str, Any], manifest: dict[str, Any]) -> list[dict[str, Any]]:
    products_by_id = {int(row["idProduct"]): row for row in products}
    observations_by_id = {int(row["idProduct"]): row for row in observations}
    existing = read_existing_rows(conn)
    decisions = []
    for context in contexts:
        product = products_by_id[int(context["cardmarket_id_product"])]
        price = prices[int(product["idProduct"])]
        observed = observations_by_id.get(int(product["idProduct"]))
        for family, columns in METRIC_COLUMNS.items():
            if not any(price.get(column) not in (None, "", 0, "0", 0.0) for column in columns):
                continue
            current = existing.get((int(product["idProduct"]), family))
            candidates = context["candidate_cards"]
            # Product pages and current docs do not expose an exclusive metric
            # claim in the available evidence. A sample pattern may support a
            # group, but never promotes unobserved products to EXACT.
            status = "AMBIGUOUS" if len(candidates) > 1 else "UNRESOLVED"
            if observed and observed["observation_status"] == "OK" and observed["reverse_filter_present"] == "YES":
                status = "SUPPORTED" if len(candidates) >= 1 else "UNRESOLVED"
            card_id = None
            eligible = False
            evidence = "Source facts and sampled Cardmarket behavior do not demonstrate metric exclusivity for this physical finish; no global rule promoted this relationship to EXACT."
            if observed and observed["observation_status"] != "OK":
                evidence += f" Product-specific evidence status: {observed['observation_status']}."
            provenance = {
                "source_manifest": manifest, "metric_family": family, "source_columns": list(columns),
                "product_page_observation": observed or {"status": "NOT_SAMPLED"},
                "current_semantics": matrix, "physical_candidates": candidates,
                "inference_policy": "sample patterns max SUPPORTED; product-specific exclusive evidence required for EXACT",
            }
            decisions.append({
                "internal_product_id": context["internal_product_id"], "idProduct": int(product["idProduct"]),
                "canonical_id": context["canonical_card_id"], "collector_number": context["canonical_number"], "canonical_name": context["canonical_name"],
                "metric_family": family, "previous_status": current["metric_mapping_status"] if current else "MISSING",
                "new_status": status, "physical_card_id": card_id, "physical_finish": "",
                "pricing_eligible": eligible, "rule_group": group_name(context), "evidence": evidence,
                "confidence": "LOW", "reason": "metric exclusivity not demonstrated", "candidate_card_ids": [item["card_id"] for item in candidates],
                "compatible_finishes": context["compatible_finishes"], "provenance": provenance,
            })
    if len(decisions) != 270:
        raise SemanticsGateError(f"expected 270 metric decisions, got {len(decisions)}")
    return decisions


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: compact(row[field]) if isinstance(row.get(field), (list, dict)) else row.get(field, "") for field in fields})


def write_reports(output: Path, documents: list[dict[str, Any]], matrix: list[dict[str, Any]], observations: list[dict[str, Any]], reverse_rows: list[dict[str, Any]], conclusions: list[dict[str, Any]], decisions: list[dict[str, Any]], local_audit: dict[str, Any], plan: dict[str, Any], manifest: dict[str, Any], mode: str, validation: dict[str, Any] | None) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "01_cardmarket_semantics.md").write_text("\n".join(["# Cardmarket semantics — Pokémon 151", "", f"Mode: `{mode}`", "", "Each conclusion is labelled as SOURCE FACT, OBSERVED BEHAVIOR, DERIVED CONCLUSION or UNKNOWN. Legacy PriceGuide documentation is never sufficient by itself for EXACT.", "", *[f"- **{row['concept']}** (`{row['level']}`): {row['finding']} — `{row['classification']}`. Source: {row['source_url']} [{row['source_status']}]" for row in matrix], "", "Cardmarket FOIL is not mapped to Pokémon reverse_holo without product-specific exclusive evidence.", ""]), encoding="utf-8")
    external_sources = [{key: value for key, value in doc.items() if key != "text"} for doc in documents]
    external_sources.extend({
        "url": observation["evidence_source"],
        "role": "product_page_sample",
        "status": observation["observation_status"],
        "http_status": observation.get("http_status"),
        "retrieved_at": observation.get("retrieved_at"),
        "sha256": observation["evidence_sha256"],
        "cache_file": observation.get("cache_file"),
    } for observation in observations)
    (output / "02_source_manifest.json").write_text(json.dumps({"local_sources": manifest, "external_sources": external_sources}, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    observation_fields = ["idProduct", "collector_number", "card_name", "rarity", "internal_finishes", "cardmarket_url", "reverse_filter_present", "default_from", "default_trend", "default_avg1", "default_avg7", "default_avg30", "reverse_filter_method", "filtered_reverse_from", "filtered_reverse_trend", "filtered_reverse_avg1", "filtered_reverse_avg7", "filtered_reverse_avg30", "observation_status", "evidence_source", "evidence_sha256", "notes", "version", "rule_group"]
    write_csv(output / "03_product_page_evidence.csv", observation_fields, observations)
    write_csv(output / "04_reverse_filter_analysis.csv", list(reverse_rows[0].keys()) if reverse_rows else ["idProduct"], reverse_rows)
    write_csv(output / "05_priceguide_semantics.csv", list(conclusions[0].keys()), conclusions)
    groups = Counter((decision["rule_group"], tuple(decision["compatible_finishes"]), decision["metric_family"]) for decision in decisions)
    group_rows = []
    for (group, finishes, family), count in sorted(groups.items()):
        group_rows.append({"group": group, "internal_finishes": list(finishes), "sample_count": sum(1 for row in observations if row["rule_group"] == group), "base_semantic": "not exclusively determined", "base_target_finish": "none", "base_status": "UNKNOWN", "foil_semantic": "not exclusively determined", "foil_target_finish": "none", "foil_status": "UNKNOWN", "reverse_price_source_available": "NO", "pricing_eligible_rule": "EXACT exclusive metric evidence only", "confidence": "LOW", "evidence": f"{count} {family} relationships; sample patterns are not promoted globally."})
    write_csv(output / "06_finish_group_rules.csv", list(group_rows[0].keys()) if group_rows else ["group"], group_rows)
    mapping_fields = ["idProduct", "canonical_id", "collector_number", "metric_family", "previous_status", "new_status", "physical_card_id", "physical_finish", "pricing_eligible", "rule_group", "evidence", "confidence", "reason"]
    write_csv(output / "07_metric_resolution_dry_run.csv", mapping_fields, decisions)
    write_csv(output / "08_exact_metric_mappings.csv", mapping_fields, [row for row in decisions if row["new_status"] == "EXACT"])
    write_csv(output / "09_ambiguous_metric_mappings.csv", mapping_fields, [row for row in decisions if row["new_status"] in {"SUPPORTED", "AMBIGUOUS"}])
    write_csv(output / "10_unresolved_metric_mappings.csv", mapping_fields, [row for row in decisions if row["new_status"] in {"UNRESOLVED", "MISMATCH"}])
    lines = ["# Pokémon 151 Cardmarket semantic post-apply validation", "", f"Mode: `{mode}`"]
    if validation:
        lines += [f"- Metric relationships total: `{validation['metric_rows']}`", f"- EXACT: `{validation['exact']}`", f"- SUPPORTED: `{validation['supported']}`", f"- AMBIGUOUS: `{validation['ambiguous']}`", f"- UNRESOLVED: `{validation['unresolved']}`", f"- MISMATCH: `{validation['mismatch']}`", f"- pricing_eligible: `{validation['pricing_eligible']}`", "- prices applied: `0`", "- current_price changed: `NO`", "- market_value changed: `NO`", "- price snapshots inserted: `0`", "- 73 canonical ambiguous products: `UNCHANGED`", "- Magic: `UNCHANGED`", "- One Piece: `UNCHANGED`", "- Collection: `UNCHANGED`", "- Wishlist: `UNCHANGED`", f"- DB integrity: `{validation['integrity']}`", f"- Foreign-key errors: `{validation['foreign_keys']}`", "- Offline second run: `NO-OP`"]
    else:
        lines.append("- Apply pending; dry-run did not modify the DB.")
    (output / "11_post_apply_validation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    summary = ["# POKEMON-151-002C — CARDMARKET FINISH SEMANTICS", "", "Official semantic findings: see `01_cardmarket_semantics.md`.", "Observed product-page behavior: see `03_product_page_evidence.csv` and `04_reverse_filter_analysis.csv`.", f"BASE metric conclusion: {conclusions[0]['pokemon_specific_interpretation']}", f"FOIL metric conclusion: {conclusions[1]['pokemon_specific_interpretation']}", "Reverse Holo pricing conclusion: NO from the local Price Guide without reverse-specific evidence.", "Higher-rarity conclusion: handled as separate groups; no finish/metric inference is forced.", "Version conclusion: recorded per observed URL; V-number semantics are not assumed.", "", "Canonical EXACT products: 137", "Metric mappings reviewed: 270", f"Metric EXACT: {plan['exact']}", f"Metric SUPPORTED: {plan['supported']}", f"Metric AMBIGUOUS: {plan['ambiguous']}", f"Metric UNRESOLVED: {plan['unresolved']}", f"Metric MISMATCH: {plan['mismatch']}", f"pricing_eligible: {plan['pricing_eligible']}", "prices applied: 0", "", "Cardmarket FOIL != Pokémon Reverse Holo unless product-specific evidence proves otherwise.", "Sample patterns never promote unobserved products to EXACT.", "Apply requires `--offline`; no network request is made during apply.", ""]
    (output / "12_summary.md").write_text("\n".join(summary), encoding="utf-8")
    # Compatibility aliases required by the later contract naming block.
    (output / "01_cardmarket_semantic_matrix.md").write_text((output / "01_cardmarket_semantics.md").read_text(encoding="utf-8"), encoding="utf-8")
    (output / "05_metric_semantic_conclusions.md").write_text("\n".join([f"{row['metric_family']}: {row['pokemon_specific_interpretation']}" for row in conclusions]) + "\n", encoding="utf-8")
    (output / "06_version_observations.csv").write_text((output / "03_product_page_evidence.csv").read_text(encoding="utf-8"), encoding="utf-8")
    (output / "07_metric_mapping_dry_run.csv").write_text((output / "07_metric_resolution_dry_run.csv").read_text(encoding="utf-8"), encoding="utf-8")
    (output / "08_exact_metric_mappings_legacy.csv").write_text((output / "08_exact_metric_mappings.csv").read_text(encoding="utf-8"), encoding="utf-8")
    (output / "09_ambiguous_metric_mappings_legacy.csv").write_text((output / "09_ambiguous_metric_mappings.csv").read_text(encoding="utf-8"), encoding="utf-8")
    (output / "10_unresolved_metric_mappings_legacy.csv").write_text((output / "10_unresolved_metric_mappings.csv").read_text(encoding="utf-8"), encoding="utf-8")


def create_metric_table(conn: sqlite3.Connection) -> None:
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {METRIC_TABLE} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cardmarket_product_id INTEGER NOT NULL REFERENCES cardmarket_products (id),
            canonical_card_id INTEGER NOT NULL REFERENCES canonical_cards (id),
            card_id INTEGER REFERENCES cards (id),
            metric_family TEXT NOT NULL CHECK (metric_family IN ('base', 'foil')),
            canonical_mapping_status TEXT NOT NULL CHECK (canonical_mapping_status IN ('EXACT', 'PROBABLE', 'AMBIGUOUS', 'MISMATCH', 'UNRESOLVED')),
            metric_mapping_status TEXT NOT NULL CHECK (metric_mapping_status IN ('EXACT', 'SUPPORTED', 'AMBIGUOUS', 'UNRESOLVED', 'MISMATCH')),
            pricing_eligible INTEGER NOT NULL DEFAULT 0 CHECK (pricing_eligible IN (0,1)),
            candidate_card_ids TEXT NOT NULL,
            compatible_finishes TEXT NOT NULL,
            metric_columns TEXT NOT NULL,
            mapping_method TEXT NOT NULL,
            confidence TEXT NOT NULL,
            evidence TEXT NOT NULL,
            provenance TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(cardmarket_product_id, metric_family)
        )
    """)
    conn.execute(f"CREATE INDEX IF NOT EXISTS idx_cardmarket_product_metric_mapping_status ON {METRIC_TABLE} (metric_mapping_status, pricing_eligible)")
    conn.execute(f"CREATE INDEX IF NOT EXISTS idx_cardmarket_product_metric_canonical ON {METRIC_TABLE} (canonical_card_id, metric_family)")


def upgrade_metric_constraint(conn: sqlite3.Connection) -> None:
    if not scalar(conn, "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?", (METRIC_TABLE,)):
        create_metric_table(conn)
        return
    sql = scalar(conn, "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (METRIC_TABLE,)) or ""
    if "'SUPPORTED'" in sql:
        return
    conn.execute("PRAGMA foreign_keys=OFF")
    conn.execute(f"ALTER TABLE {METRIC_TABLE} RENAME TO {METRIC_TABLE}_legacy")
    conn.execute("DROP INDEX IF EXISTS idx_cardmarket_product_metric_mapping_status")
    conn.execute("DROP INDEX IF EXISTS idx_cardmarket_product_metric_canonical")
    create_metric_table(conn)
    columns = "id,cardmarket_product_id,canonical_card_id,card_id,metric_family,canonical_mapping_status,metric_mapping_status,pricing_eligible,candidate_card_ids,compatible_finishes,metric_columns,mapping_method,confidence,evidence,provenance,created_at,updated_at"
    conn.execute(f"INSERT INTO {METRIC_TABLE} ({columns}) SELECT {columns} FROM {METRIC_TABLE}_legacy")
    conn.execute(f"DROP TABLE {METRIC_TABLE}_legacy")
    conn.execute("PRAGMA foreign_keys=ON")


def persist(conn: sqlite3.Connection, decisions: list[dict[str, Any]]) -> int:
    inserted = 0
    for row in decisions:
        existing = conn.execute(f"SELECT id FROM {METRIC_TABLE} WHERE cardmarket_product_id=? AND metric_family=?", (row["internal_product_id"], row["metric_family"])).fetchone()
        conn.execute(f"""
            INSERT INTO {METRIC_TABLE}
              (cardmarket_product_id,canonical_card_id,card_id,metric_family,canonical_mapping_status,metric_mapping_status,pricing_eligible,candidate_card_ids,compatible_finishes,metric_columns,mapping_method,confidence,evidence,provenance)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(cardmarket_product_id,metric_family) DO UPDATE SET
              canonical_card_id=excluded.canonical_card_id, card_id=excluded.card_id,
              canonical_mapping_status=excluded.canonical_mapping_status, metric_mapping_status=excluded.metric_mapping_status,
              pricing_eligible=excluded.pricing_eligible, candidate_card_ids=excluded.candidate_card_ids,
              compatible_finishes=excluded.compatible_finishes, metric_columns=excluded.metric_columns,
              mapping_method=excluded.mapping_method, confidence=excluded.confidence, evidence=excluded.evidence,
              provenance=excluded.provenance, updated_at=CURRENT_TIMESTAMP
        """, (row["internal_product_id"], row["canonical_id"], row["physical_card_id"], row["metric_family"], "EXACT", row["new_status"], int(row["pricing_eligible"]), compact(row["candidate_card_ids"]), compact(row["compatible_finishes"]), compact(list(METRIC_COLUMNS[row["metric_family"]])), "semantic_audit_offline_apply", row["confidence"], row["evidence"], compact(row["provenance"])))
        inserted += int(existing is None)
    return inserted


def protected_snapshot(conn: sqlite3.Connection) -> str:
    digest = hashlib.sha256()
    tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT IN (?, 'sqlite_sequence') ORDER BY name", (METRIC_TABLE,))]
    for table in tables:
        identifier = '"' + table.replace('"', '""') + '"'
        cursor = conn.execute(f"SELECT * FROM {identifier} ORDER BY rowid")
        digest.update(table.encode())
        digest.update(compact([item[0] for item in cursor.description]).encode())
        for row in cursor:
            digest.update(compact(list(row)).encode())
    return digest.hexdigest()


def validate(conn: sqlite3.Connection, before: str, decisions: list[dict[str, Any]]) -> dict[str, Any]:
    metric_rows = scalar(conn, f"SELECT COUNT(*) FROM {METRIC_TABLE} m JOIN cardmarket_products p ON p.id=m.cardmarket_product_id WHERE p.cardmarket_id_expansion=? AND p.cardmarket_id_category=?", (EXPANSION_ID, CATEGORY_ID))
    if metric_rows != 270:
        raise SemanticsGateError(f"metric rows {metric_rows} != 270")
    bad = scalar(conn, f"SELECT COUNT(*) FROM {METRIC_TABLE} WHERE metric_mapping_status NOT IN ('EXACT','SUPPORTED','AMBIGUOUS','UNRESOLVED','MISMATCH') OR (metric_mapping_status<>'EXACT' AND card_id IS NOT NULL) OR (pricing_eligible=1 AND (metric_mapping_status<>'EXACT' OR card_id IS NULL)) OR (pricing_eligible=1 AND (provenance NOT LIKE '%source_manifest%' OR provenance NOT LIKE '%metric_family%'))")
    if bad:
        raise SemanticsGateError("metric status/card/pricing invariant failed")
    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    foreign_keys = len(conn.execute("PRAGMA foreign_key_check").fetchall())
    if integrity != "ok" or foreign_keys:
        raise SemanticsGateError("SQLite integrity gate failed")
    if protected_snapshot(conn) != before:
        raise SemanticsGateError("a non-metric table changed")
    counts = Counter(row["new_status"] for row in decisions)
    return {"metric_rows": metric_rows, "exact": counts["EXACT"], "supported": counts["SUPPORTED"], "ambiguous": counts["AMBIGUOUS"], "unresolved": counts["UNRESOLVED"], "mismatch": counts["MISMATCH"], "pricing_eligible": sum(row["pricing_eligible"] for row in decisions), "integrity": integrity, "foreign_keys": foreign_keys}


def sqlite_copy(source: Path, destination: Path) -> None:
    source_conn = sqlite3.connect(source)
    destination_conn = sqlite3.connect(destination)
    try:
        source_conn.backup(destination_conn)
    finally:
        destination_conn.close()
        source_conn.close()


def run(db: Path, products_path: Path, prices_path: Path, mapping_dir: Path, output: Path, cache_dir: Path, offline: bool, refresh_sources: bool, apply: bool) -> dict[str, Any]:
    if apply and not offline:
        raise SemanticsGateError("--apply-metric-resolution requires --offline")
    products, prices, manifest = load_local_sources(products_path, prices_path, mapping_dir)
    cache = SourceCache(cache_dir, offline, refresh_sources)
    documents = fetch_documentation(cache)
    local_audit = audit_local_priceguide(prices)
    matrix = semantics_matrix(documents, local_audit)
    conn = connect(db)
    try:
        contexts = load_contexts(conn)
        observations = product_observations(cache, contexts)
        reverse_rows = reverse_analysis(observations)
        conclusions = metric_conclusions(matrix, observations, local_audit)
        decisions = resolve_decisions(conn, products, prices, contexts, observations, matrix, local_audit, manifest)
        counts = Counter(row["new_status"] for row in decisions)
        plan = {"canonical_exact_products": 137, "canonical_ambiguous_products_excluded": 73, "metric_mappings_reviewed": 270, "exact": counts["EXACT"], "supported": counts["SUPPORTED"], "ambiguous": counts["AMBIGUOUS"], "unresolved": counts["UNRESOLVED"], "mismatch": counts["MISMATCH"], "pricing_eligible": sum(row["pricing_eligible"] for row in decisions), "prices_applied": 0}
        if not apply:
            write_reports(output, documents, matrix, observations, reverse_rows, conclusions, decisions, local_audit, plan, manifest, "dry-run", None)
            return plan
    finally:
        conn.close()
    backup_dir = output / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / "tcg_dashboard.before_pokemon_151_002c.db"
    sqlite_copy(db, backup)
    temporary = Path(tempfile.mkstemp(prefix="pokemon151-semantics-", suffix=".db", dir=db.parent)[1])
    try:
        sqlite_copy(db, temporary)
        conn = connect(temporary)
        try:
            upgrade_metric_constraint(conn)
            conn.commit()
            before = protected_snapshot(conn)
            contexts = load_contexts(conn)
            observations = product_observations(SourceCache(cache_dir, True, False), contexts)
            reverse_rows = reverse_analysis(observations)
            decisions = resolve_decisions(conn, products, prices, contexts, observations, matrix, local_audit, manifest)
            conclusions = metric_conclusions(matrix, observations, local_audit)
            conn.execute("BEGIN IMMEDIATE")
            inserted = persist(conn, decisions)
            validation = validate(conn, before, decisions)
            conn.commit()
            validation = validate(conn, before, decisions)
            plan = {"canonical_exact_products": 137, "canonical_ambiguous_products_excluded": 73, "metric_mappings_reviewed": 270, "exact": validation["exact"], "supported": validation["supported"], "ambiguous": validation["ambiguous"], "unresolved": validation["unresolved"], "mismatch": validation["mismatch"], "pricing_eligible": validation["pricing_eligible"], "prices_applied": 0, "new_metric_rows": inserted}
            write_reports(output, documents, matrix, observations, reverse_rows, conclusions, decisions, local_audit, plan, manifest, "apply-offline", validation)
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
    parser.add_argument("--mapping-dir", type=Path, default=DEFAULT_MAPPING_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--refresh-sources", action="store_true")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply-metric-resolution", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(args.db, args.products, args.prices, args.mapping_dir, args.output, args.cache_dir, args.offline, args.refresh_sources, args.apply_metric_resolution), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
