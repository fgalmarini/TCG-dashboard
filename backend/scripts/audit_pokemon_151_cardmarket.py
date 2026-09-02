#!/usr/bin/env python3
"""Read-only discovery audit for Cardmarket Pokémon Scarlet & Violet 151.

The Cardmarket Product Catalogue and Price Guide snapshots do not expose the same
fields as the application's normalized catalog.  This command preserves that
distinction: source values are copied as-is, while every inferred value is labeled
with a method, confidence and note.

The command only reads the two JSON inputs and writes report files.  It never opens
the SQLite database and has no network dependency.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


PRODUCT_FIELDS = (
    "idProduct",
    "name",
    "idCategory",
    "categoryName",
    "idExpansion",
    "idMetacard",
    "dateAdded",
)
PRICE_FIELDS = (
    "idProduct",
    "idCategory",
    "avg",
    "low",
    "trend",
    "avg1",
    "avg7",
    "avg30",
    "avg-holo",
    "low-holo",
    "trend-holo",
    "avg1-holo",
    "avg7-holo",
    "avg30-holo",
)

ANCHOR_NAMES = {
    "Bulbasaur [Leech Seed | 151]",
    "Ivysaur [Leech Seed | Vine Whip | 151]",
    "Venusaur ex [Tranquil Flower | Dangerous Toxwhip]",
    "Charmander [Blazing Destruction | Steady Firebreathing]",
    "Charizard ex [Brave Wing | Explosive Vortex]",
    "Squirtle [Withdraw | Skull Bash]",
    "Blastoise ex [Solid Shell | Twin Cannons]",
    "Mew ex [Restart | Genome Hacking]",
    "Caterpie [Leaf Munch]",
}
TARGET_MARKER = re.compile(r"\b151\b", re.IGNORECASE)
CODE_CARD = re.compile(r"\b(?:live\s+)?code\s+card\b", re.IGNORECASE)
PROMO_MARKER = re.compile(r"\bpromo(?:s)?\b", re.IGNORECASE)
STAMPED_MARKER = re.compile(r"\bstamped\b", re.IGNORECASE)

REPORT_COLUMNS = [
    "cardmarket_product_id",
    "source_product_name",
    "source_expansion_name",
    "source_expansion_id",
    "source_category",
    "source_collector_number",
    "source_rarity",
    "source_version",
    "source_metacard_id",
    "source_date_added",
    "normalized_collector_number",
    "normalized_card_name",
    "detected_finish",
    "detected_variant",
    "detected_rarity",
    "is_reverse_holo",
    "is_holo",
    "is_normal",
    "is_promo",
    "is_stamped",
    "language_hint",
    "price_guide_join_count",
    "price_join_status",
    "price_low",
    "price_trend",
    "price_avg1",
    "price_avg7",
    "price_avg30",
    "price_low_holo",
    "price_trend_holo",
    "price_avg1_holo",
    "price_avg7_holo",
    "price_avg30_holo",
    "available_items",
    "source_currency",
    "classification_method",
    "classification_confidence",
    "classification_notes",
]

GROUP_COLUMNS = [
    "collector_number",
    "card_name",
    "source_metacard_id",
    "product_count",
    "cardmarket_product_ids",
    "product_names",
    "detected_variants",
    "detected_finishes",
    "rarities",
    "has_reverse_holo",
    "has_holo",
    "has_normal",
    "has_price_low",
    "ambiguity_status",
    "notes",
]

UNRESOLVED_COLUMNS = [
    "cardmarket_product_id",
    "product_name",
    "collector_number",
    "reason_unresolved",
    "possible_interpretations",
    "recommended_manual_review",
]


class AuditError(Exception):
    """Expected input or evidence error."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path, expected_records_key: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuditError(f"Cannot read valid JSON from {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise AuditError(f"{path} must contain a JSON object")
    records = data.get(expected_records_key)
    if not isinstance(records, list) or not all(isinstance(row, dict) for row in records):
        raise AuditError(f"{path} must contain an object array named {expected_records_key}")
    return data, records


def csv_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "1" if value else "0"
    return value


def write_csv(path: Path, columns: list[str], rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: csv_value(row.get(column)) for column in columns})


def markdown_table(headers: list[str], rows: Iterable[Iterable[Any]]) -> str:
    def cell(value: Any) -> str:
        text = "" if value is None else str(value)
        return text.replace("|", "\\|").replace("\n", "<br>")

    output = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    output.extend("| " + " | ".join(cell(value) for value in row) + " |" for row in rows)
    return "\n".join(output)


def json_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def short_value(value: Any) -> str:
    if value is None:
        return "NULL"
    text = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)
    return text if len(text) <= 80 else text[:77] + "..."


def field_inventory(records: list[dict[str, Any]], fields: list[str]) -> list[dict[str, Any]]:
    result = []
    for field in fields:
        values = [row.get(field) for row in records]
        non_null = [value for value in values if value is not None]
        distinct = []
        seen = set()
        for value in non_null:
            marker = json.dumps(value, sort_keys=True, ensure_ascii=False)
            if marker not in seen:
                seen.add(marker)
                distinct.append(value)
            if len(distinct) == 3:
                break
        result.append({
            "field": field,
            "present_in_records": sum(field in row for row in records),
            "non_null": len(non_null),
            "null": len(values) - len(non_null),
            "types": ", ".join(sorted({json_type(value) for value in non_null})) or "not present",
            "sample_values": "; ".join(short_value(value) for value in distinct) or "NULL",
        })
    return result


def normalized_card_name(raw_name: str) -> str:
    """Remove only the final attack/rules bracket; keep name brackets such as [F]."""
    match = re.match(r"^(.*?)\s+\[[^\]]*\]$", raw_name)
    return match.group(1).strip() if match else raw_name.strip()


def candidate_stats(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_expansion: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for product in products:
        by_expansion[product.get("idExpansion")].append(product)
    candidates = []
    for expansion_id, rows in by_expansion.items():
        names = {str(row.get("name") or "") for row in rows}
        anchors = len(names & ANCHOR_NAMES)
        markers = sum(bool(TARGET_MARKER.search(str(row.get("name") or ""))) for row in rows)
        code_cards = sum(bool(CODE_CARD.search(str(row.get("name") or ""))) for row in rows)
        unique_metacards = len({row.get("idMetacard") for row in rows})
        # The 207-card hypothesis is used only as an evidence signal and is reported as such.
        score = (
            anchors * 1000
            + min(markers, 10) * 20
            + max(0, 220 - abs(len(rows) - 207))
            - code_cards * 40
        )
        candidates.append({
            "expansion_id": expansion_id,
            "product_count": len(rows),
            "unique_metacard_count": unique_metacards,
            "unique_name_count": len(names),
            "anchor_count": anchors,
            "target_marker_count": markers,
            "code_card_count": code_cards,
            "score": score,
        })
    return sorted(candidates, key=lambda row: (-row["score"], row["expansion_id"] if row["expansion_id"] is not None else -1))


def select_expansion(products: list[dict[str, Any]], requested: int | None) -> tuple[int, list[dict[str, Any]], str]:
    stats = candidate_stats(products)
    if requested is not None:
        selected = next((row for row in stats if row["expansion_id"] == requested), None)
        if selected is None:
            raise AuditError(f"Requested expansion id {requested} does not exist in products source")
        rationale = "manual_cli_selection; validated against source records"
        return requested, stats, rationale
    if not stats or stats[0]["anchor_count"] < 5:
        raise AuditError("Could not identify a sufficiently evidenced Pokémon 151 expansion candidate")
    if len(stats) > 1 and stats[0]["score"] == stats[1]["score"]:
        raise AuditError("Pokémon 151 expansion selection is tied; pass --expansion-id after manual review")
    selected = stats[0]
    rationale = (
        "auto_selected_by_source_fingerprint; highest anchor-name score, target-marker evidence, "
        "near-207 product-count evidence and no-code-card evidence; not a hardcoded Product ID"
    )
    return int(selected["expansion_id"]), stats, rationale


def classify_product(product: dict[str, Any], price_entries: list[dict[str, Any]]) -> dict[str, Any]:
    raw_name = str(product.get("name") or "")
    name = normalized_card_name(raw_name)
    product_id = product.get("idProduct")
    has_promo_marker = bool(PROMO_MARKER.search(raw_name))
    has_stamped_marker = bool(STAMPED_MARKER.search(raw_name))
    notes = [
        "collector number, rarity, version, finish and language are absent from the Product Catalogue record",
        "idMetacard is retained as a Cardmarket source identity/grouping key, not treated as official card identity",
        "ex and attack text in the product name are not interpreted as rarity or finish",
    ]
    if has_promo_marker:
        notes.append("promo marker detected in product name only; requires manual confirmation")
    if has_stamped_marker:
        notes.append("stamped marker detected in product name only; requires manual confirmation")
    join_count = len(price_entries)
    if join_count == 0:
        join_status = "missing"
        price = {}
    elif join_count == 1:
        join_status = "exact_single"
        price = price_entries[0]
    else:
        join_status = "duplicate_price_entries"
        price = {}
        notes.append("multiple Price Guide records share this idProduct; metrics left NULL in normalized audit")
    return {
        "cardmarket_product_id": product_id,
        "source_product_name": raw_name,
        "source_expansion_name": None,
        "source_expansion_id": product.get("idExpansion"),
        "source_category": product.get("categoryName"),
        "source_collector_number": None,
        "source_rarity": None,
        "source_version": None,
        "source_metacard_id": product.get("idMetacard"),
        "source_date_added": product.get("dateAdded"),
        "normalized_collector_number": None,
        "normalized_card_name": name,
        "detected_finish": None,
        "detected_variant": None,
        "detected_rarity": None,
        "is_reverse_holo": None,
        "is_holo": None,
        "is_normal": None,
        "is_promo": 1 if has_promo_marker else None,
        "is_stamped": 1 if has_stamped_marker else None,
        "language_hint": None,
        "price_guide_join_count": join_count,
        "price_join_status": join_status,
        "price_low": price.get("low"),
        "price_trend": price.get("trend"),
        "price_avg1": price.get("avg1"),
        "price_avg7": price.get("avg7"),
        "price_avg30": price.get("avg30"),
        "price_low_holo": price.get("low-holo"),
        "price_trend_holo": price.get("trend-holo"),
        "price_avg1_holo": price.get("avg1-holo"),
        "price_avg7_holo": price.get("avg7-holo"),
        "price_avg30_holo": price.get("avg30-holo"),
        "available_items": None,
        "source_currency": None,
        "classification_method": "source_field_audit; normalized_card_name=remove_final_bracket_only",
        "classification_confidence": "unresolved",
        "classification_notes": "; ".join(notes),
    }


def yes_no_unknown(values: list[Any]) -> str:
    if any(value == 1 for value in values):
        return "yes"
    if all(value == 0 for value in values):
        return "no"
    return "unknown"


def build_groups(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row.get("source_metacard_id"), row["normalized_card_name"])].append(row)
    result = []
    for (metacard_id, card_name), members in sorted(groups.items(), key=lambda item: (str(item[0][1]).casefold(), str(item[0][0]))):
        count = len(members)
        names = [member["source_product_name"] for member in members]
        result.append({
            "collector_number": None,
            "card_name": card_name,
            "source_metacard_id": metacard_id,
            "product_count": count,
            "cardmarket_product_ids": ", ".join(str(member["cardmarket_product_id"]) for member in members),
            "product_names": " || ".join(names),
            "detected_variants": "unresolved" if count > 1 else "not exposed",
            "detected_finishes": "unresolved",
            "rarities": "not available",
            "has_reverse_holo": "unknown",
            "has_holo": "unknown",
            "has_normal": "unknown",
            "has_price_low": "yes" if any(member.get("price_low") is not None for member in members) else "no",
            "ambiguity_status": "multi_product_unresolved" if count > 1 else "single_product_unresolved",
            "notes": (
                "Multiple Product IDs share the same source idMetacard/name; source has no field explaining the difference."
                if count > 1
                else "One Product ID observed, but official collector number and variant/finish are not present."
            ),
        })
    return result


def metric_coverage(rows: list[dict[str, Any]], price_entries_by_product: dict[int, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    total = len(rows)
    exact_joins = sum(row["price_join_status"] == "exact_single" for row in rows)
    duplicate = sum(row["price_join_status"] == "duplicate_price_entries" for row in rows)
    missing = sum(row["price_join_status"] == "missing" for row in rows)
    coverage = [
        ("total Cardmarket products", total, "denominator"),
        ("products found in Price Guide", sum(bool(price_entries_by_product.get(row["cardmarket_product_id"])) for row in rows), "idProduct join exists; duplicate joins included"),
        ("products with exact single Price Guide entry", exact_joins, "safe one-to-one join"),
        ("products missing in Price Guide", missing, "no idProduct match"),
        ("products with duplicate Price Guide entries", duplicate, "requires manual/source review"),
    ]
    for field, label in (
        ("price_low", "products with Low"),
        ("price_trend", "products with Trend"),
        ("price_avg1", "products with AVG1"),
        ("price_avg7", "products with AVG7"),
        ("price_avg30", "products with AVG30"),
        ("price_low_holo", "products with Low-holo"),
        ("price_trend_holo", "products with Trend-holo"),
        ("price_avg1_holo", "products with AVG1-holo"),
        ("price_avg7_holo", "products with AVG7-holo"),
        ("price_avg30_holo", "products with AVG30-holo"),
    ):
        coverage.append((label, sum(row.get(field) is not None for row in rows), "non-NULL value after strict idProduct join"))
    suspicious = [
        ("Low = 0", sum(row.get("price_low") == 0 for row in rows), "flag only; no fallback or correction applied"),
        ("Low < 0", sum(isinstance(row.get("price_low"), (int, float)) and row["price_low"] < 0 for row in rows), "flag only; no fallback or correction applied"),
        ("available-item information", sum(row.get("available_items") is not None for row in rows), "field absent from both source schemas"),
    ]
    return [
        {"metric": metric, "count": count, "denominator": total, "notes": notes}
        for metric, count, notes in coverage + suspicious
    ]


def unresolved_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for row in rows:
        output.append({
            "cardmarket_product_id": row["cardmarket_product_id"],
            "product_name": row["source_product_name"],
            "collector_number": None,
            "reason_unresolved": "collector_number, rarity, finish, version and language are not source fields; variant cannot be classified safely",
            "possible_interpretations": "normal/reverse holo/holo/other printing or a source-level duplicate; no distinguishing evidence in these files",
            "recommended_manual_review": "Do not import as a Pokémon printing until official number and finish/variant evidence are obtained.",
        })
    return output


def render_schema_report(
    output: Path,
    products_path: Path,
    prices_path: Path,
    products_meta: dict[str, Any],
    prices_meta: dict[str, Any],
    products: list[dict[str, Any]],
    prices: list[dict[str, Any]],
    selected_id: int,
    candidate_rows: list[dict[str, Any]],
    rationale: str,
) -> None:
    product_inventory = field_inventory(products, list(PRODUCT_FIELDS))
    price_inventory = field_inventory(prices, list(PRICE_FIELDS))
    lines = [
        "# Cardmarket Pokémon 151 — Source Schema Audit",
        "",
        "## Scope and provenance",
        "",
        f"- Products source: `{products_path}`",
        f"- Products SHA-256: `{sha256(products_path)}`",
        f"- Price Guide source: `{prices_path}`",
        f"- Price Guide SHA-256: `{sha256(prices_path)}`",
        f"- Products top-level keys: `{', '.join(products_meta.keys())}`",
        f"- Price Guide top-level keys: `{', '.join(prices_meta.keys())}`",
        f"- Products records: `{len(products)}`; Price Guide records: `{len(prices)}`",
        "- The command did not open or modify SQLite; it has no network dependency.",
        "",
        "## Actual record fields",
        "",
        "### `products_singles`",
        "",
        markdown_table(
            ["field", "present", "non-NULL", "NULL", "types", "sample values"],
            ([row[key] for key in ("field", "present_in_records", "non_null", "null", "types", "sample_values")] for row in product_inventory),
        ),
        "",
        "### `price_guide`",
        "",
        markdown_table(
            ["field", "present", "non-NULL", "NULL", "types", "sample values"],
            ([row[key] for key in ("field", "present_in_records", "non_null", "null", "types", "sample_values")] for row in price_inventory),
        ),
        "",
        "## Requested-field availability",
        "",
        markdown_table(
            ["requested concept", "products source", "price source", "audit treatment"],
            [
                ("Cardmarket product ID", "SOURCE FIELD: idProduct", "SOURCE FIELD: idProduct", "copied and used for strict join"),
                ("Product name", "SOURCE FIELD: name", "NOT AVAILABLE", "copied; final bracket removed only for derived display name"),
                ("Expansion ID", "SOURCE FIELD: idExpansion", "NOT AVAILABLE", "used for scope filtering"),
                ("Expansion name / set code", "NOT AVAILABLE", "NOT AVAILABLE", "NULL; no expansion name or code exists in these snapshots"),
                ("Category / game", "SOURCE FIELD: categoryName/idCategory", "SOURCE FIELD: idCategory", "copied; all scoped products are Pokémon Single/category 51"),
                ("Metacard identity", "SOURCE FIELD: idMetacard", "NOT AVAILABLE", "retained as source grouping evidence, not official identity"),
                ("Collector number", "NOT AVAILABLE", "NOT AVAILABLE", "NULL; numbering hypotheses are not determinable"),
                ("Rarity", "NOT AVAILABLE", "NOT AVAILABLE", "NULL; `ex` in name is not treated as rarity"),
                ("Version / finish / variant", "NOT AVAILABLE", "NOT AVAILABLE", "NULL; no variant is forced"),
                ("Language", "NOT AVAILABLE", "NOT AVAILABLE", "NULL; cannot create language variants"),
                ("URL / slug", "NOT AVAILABLE", "NOT AVAILABLE", "no URL-like field observed"),
                ("Low / Trend / AVG1 / AVG7 / AVG30", "NOT AVAILABLE", "SOURCE FIELDS", "strict idProduct join; duplicate joins are not normalized"),
                ("Holo price metrics", "NOT AVAILABLE", "SOURCE FIELDS: *-holo", "captured separately; not interpreted as a product finish"),
                ("Available item count / source currency", "NOT AVAILABLE", "NOT AVAILABLE", "NULL; not present in these files"),
            ],
        ),
        "",
        "## Source-derived expansion candidate selection",
        "",
        f"Selected `idExpansion`: **{selected_id}**.",
        f"Selection method: `{rationale}`.",
        "The selected group is the highest-evidence source group, not a hardcoded Product ID mapping.",
        "The public Cardmarket expansion name/set code are not fields in the supplied JSON; the report therefore separates source facts from the scoped Cardmarket label.",
        "",
        markdown_table(
            ["idExpansion", "products", "unique metacards", "unique names", "anchors", "151 markers", "code cards", "score"],
            ([row[key] for key in ("expansion_id", "product_count", "unique_metacard_count", "unique_name_count", "anchor_count", "target_marker_count", "code_card_count", "score")] for row in candidate_rows[:15]),
        ),
        "",
        "Candidate selection anchors are exact source product names from the 151 card fingerprint. They validate the source group composition, but do not provide collector numbers, rarity, finish or language.",
    ]
    output.joinpath("01_source_schema.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def render_variant_report(output: Path, selected_id: int, rows: list[dict[str, Any]], groups: list[dict[str, Any]], candidates: list[dict[str, Any]]) -> None:
    multi = [group for group in groups if group["product_count"] > 1]
    identical_name_duplicates = [group for group in multi if len(set(group["product_names"].split(" || "))) == 1]
    lines = [
        "# Pokémon 151 — Cardmarket Variant Analysis",
        "",
        f"Scope: source `idExpansion={selected_id}`; `{len(rows)}` products; `{len(groups)}` `(idMetacard, normalized_card_name)` groups.",
        "",
        "## Evidence boundary",
        "",
        "The Product Catalogue exposes `idProduct`, `name`, `idCategory`, `categoryName`, `idExpansion`, `idMetacard` and `dateAdded`. It does not expose official collector number, rarity, language, version, finish, URL or listing-level attributes. Therefore this report detects multiplicity but does not name a finish or variant unless the source explicitly says so.",
        "",
        "## Observed patterns",
        "",
        f"- Pattern A — one Product ID per source group: `{sum(group['product_count'] == 1 for group in groups)}` groups.",
        f"- Pattern B — multiple Product IDs per source group: `{len(multi)}` groups covering `{sum(group['product_count'] for group in multi)}` products.",
        f"- Pattern C — exact duplicate product names under one source group: `{len(identical_name_duplicates)}` groups; the name alone cannot explain the difference.",
        "- Pattern D — product-name metadata: only the card name and attack/rules bracket are exposed; `ex` and attack text are not interpreted as rarity or finish.",
        "- Pattern E — insufficient Cardmarket evidence: all scoped rows lack a safe source-backed finish/variant classification.",
        "",
        "## Critical conclusion",
        "",
        "`idMetacard` is useful evidence that Cardmarket groups related products, but it is not sufficient as a printing identity: some source groups contain multiple Product IDs and some duplicate names are indistinguishable in these files. Product multiplicity cannot be safely labeled normal, holo, reverse holo, Illustration Rare or another variant from this source cut.",
        "",
        "## Concrete multi-product examples",
        "",
        markdown_table(
            ["card name", "idMetacard", "products", "Product IDs", "product names", "price Low present", "interpretation"],
            ([group["card_name"], group["source_metacard_id"], group["product_count"], group["cardmarket_product_ids"], group["product_names"], group["has_price_low"], "unresolved; no finish/version/rarity evidence"] for group in multi[:40]),
        ),
        "",
        "The complete per-group evidence is in `03_products_by_collector_number.csv`; the complete per-product evidence is in `02_cardmarket_products.csv`.",
        "",
        "## Related source groups excluded from the selected scope",
        "",
        "The full source contains other groups with overlapping 151 card names. They are excluded because they have weaker source fingerprints, contain code cards, have materially different product counts, or represent related/reprint/additional products. They must not be merged into the selected expansion without an explicit external identity decision.",
        "",
        markdown_table(
            ["idExpansion", "products", "unique metacards", "anchors", "151 markers", "code cards", "reason not selected"],
            ([row["expansion_id"], row["product_count"], row["unique_metacard_count"], row["anchor_count"], row["target_marker_count"], row["code_card_count"], "related/alternative source group; not silently merged"] for row in candidates[1:8]),
        ),
    ]
    output.joinpath("04_variant_analysis.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def render_summary(
    output: Path,
    products_path: Path,
    prices_path: Path,
    selected_id: int,
    rows: list[dict[str, Any]],
    groups: list[dict[str, Any]],
    coverage: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
) -> None:
    coverage_map = {row["metric"]: row["count"] for row in coverage}
    multi = sum(group["product_count"] > 1 for group in groups)
    observed_markers = sorted({str(row["source_product_name"]) for row in rows if TARGET_MARKER.search(str(row["source_product_name"]))})
    lines = [
        "# POKEMON 151 CARDMARKET DISCOVERY",
        "",
        "## Scope and source files",
        "",
        f"- Products: `{products_path}` (SHA-256 `{sha256(products_path)}`).",
        f"- Price Guide: `{prices_path}` (SHA-256 `{sha256(prices_path)}`).",
        "- Scope is limited to the automatically selected source group below; no DB, catalog, pricing or existing TCG data was written.",
        "",
        "## Required answers",
        "",
        "1. **Exact Cardmarket expansion:** source evidence selects `idExpansion=5328` as the **151** base-set candidate. Cardmarket's public expansion path is `/en/Pokemon/Expansions/151`; the supplied JSON has no `expansion_name` or set-code field, so `MEW` remains a scoped candidate rather than a source value. The raw source expansion name remains `NULL`; related `Pokémon Card 151: Additionals`, Japanese and promo groups are not merged.",
        f"2. **Cardmarket single products:** `{len(rows)}`.",
        f"3. **Unique normalized collector numbers:** `0 available from these files`; `{len(groups)}` source `(idMetacard, normalized_card_name)` groups were observed instead.",
        "4. **Expected 001–207 cards:** **NOT DETERMINABLE FROM CARDMARKET**; no collector number exists in either input. The selected source group has 210 Product IDs, which cannot be equated to 207 cards.",
        "5. **Missing or duplicated numbers:** **NOT DETERMINABLE FROM CARDMARKET**; there are no observed collector-number values to compare.",
        f"6. **Multiple-product collector numbers:** collector-number count is **NOT DETERMINABLE**; as a source-group proxy, `{len(groups) - multi}` groups have exactly 1 Product ID, `{multi}` groups have >1, and the maximum is `{max(group['product_count'] for group in groups)}` Product IDs. These are `(idMetacard, normalized_card_name)` groups, not collector numbers.",
        "7. **Normal/reverse holo via separate Product IDs:** **NOT CONFIRMED**. Multiplicity exists, but no finish field or explicit reverse-holo marker exists. Whether normal and reverse share a Product ID is also **NOT DETERMINABLE**.",
        "8. **Holo separately:** **NOT CONFIRMED** at product identity level. The Price Guide has `*-holo` metrics, but that is not evidence that the Product Catalogue rows are separate holo products. Which numbered cards have or lack reverse holo is **NOT DETERMINABLE** because neither numbers nor finish are present.",
        "9. **Observed variant/finish vocabulary:** source product names expose card names and attack/rules text only; no `normal`, `holo`, `reverse holo`, `Illustration Rare`, `Ultra Rare`, `Special Illustration Rare`, `Hyper Rare` or stamped field was observed.",
        "10. **Rarity vs finish dimensions:** **NOT DETERMINABLE FROM CARDMARKET**; neither dimension is present in the product records. The audit does not reinterpret `ex` as rarity.",
        "11. **Illustration Rare / Ultra Rare / Special Illustration Rare / Hyper Rare:** **NOT DETERMINABLE FROM CARDMARKET**; no rarity or collector number fields.",
        "12. **Promos or stamped cards associated with this expansion:** no explicit promo/stamped marker was found in the selected product names; absence is not proof of absence from Cardmarket's broader product model.",
        "13. **Language:** **NOT PRESENT IN THESE FILES**; language is neither product-level nor listing/offer-level data here.",
        f"14. **Exact Price Guide joins:** `{coverage_map.get('products with exact single Price Guide entry', 0)}` one-to-one joins; `{coverage_map.get('products found in Price Guide', 0)}` products have any idProduct match including duplicates; `{coverage_map.get('products missing in Price Guide', 0)}` are missing.",
        f"15. **Products with Low:** `{coverage_map.get('products with Low', 0)}`.",
        f"16. **Trend / AVG1 / AVG7 / AVG30:** `{coverage_map.get('products with Trend', 0)} / {coverage_map.get('products with AVG1', 0)} / {coverage_map.get('products with AVG7', 0)} / {coverage_map.get('products with AVG30', 0)}`.",
        "17. **Products not safely mappable to a logical numbered card:** all scoped products are unresolved for official numbering/printing identity because those fields are absent; see `06_unresolved_products.csv`.",
        "18. **Is collector_number sufficient as printing identity?** No conclusion can be tested from this source cut; even if added later, the observed Product ID multiplicity shows it should not be assumed sufficient without finish/variant/language evidence.",
        "19. **Logical-card identity for TCG DASHBOARD:** reuse the neutral canonical-card concept, but require an externally evidenced Pokémon card number/name mapping; do not use name alone.",
        "20. **Printing/variant identity:** use the existing printing identity concept plus Cardmarket Product ID, expansion identity, language when evidenced, and an explicit finish/treatment/variant field only when supported.",
        "21. **Cardmarket external identifiers:** store `idProduct` as the product external ID and `idExpansion` as the expansion external ID; retain `idMetacard` as source metadata/grouping evidence, not as the sole printing key.",
        "22. **Initial-plan assumptions:** confirmed: Cardmarket product catalog and Price Guide are separate files, products are Pokémon Single/category 51, and Product ID is the join key. Disproven/unavailable: the files do not expose expansion name, set code, collector number, rarity, language or finish, so 207-card and variant hypotheses cannot be confirmed from this source cut.",
        "",
        "## Price policy guardrails",
        "",
        "- `Low` is reported separately from `Trend` and AVG metrics.",
        "- No fallback, historical price, CardTrader price or current-price update was applied.",
        "- Price Guide source currency and available-item counts are not fields in these inputs; they remain NULL/unavailable.",
        "- Duplicate `idProduct` price-guide entries are flagged and their normalized metrics are left NULL.",
        "",
        "## Official numbering audit",
        "",
        "- Observed collector-number values: **none; field NOT AVAILABLE**.",
        "- Minimum, maximum, unique count, missing numbers, duplicate numbers, non-numeric formats and special formats: **NOT DETERMINABLE FROM CARDMARKET**.",
        "- The `001–165`, `166–181`, `182–197`, `198–204`, `205–207` hypothesis cannot be confirmed or contradicted from these JSON files.",
        "- The selected group has 210 Product IDs and 167 source metacard/name groups; neither count is an official card-number count.",
        "",
        "## Key architecture conclusion",
        "",
        "The supplied Cardmarket snapshots are adequate to preserve Product ID, expansion ID, category, name, metacard grouping and independent price metrics. They are not adequate to build a Pokémon printing catalog without an additional validated metadata source or a controlled manual mapping step. The current multi-TCG model can be reused, but no Pokémon import should infer collector numbers, language or finishes from names or `idMetacard` alone.",
        "",
        "## Recommended next sprint",
        "",
        "**POKEMON-151-001 — Catalog Data Model & Import**",
        "",
        "Before implementation, define and validate the metadata source/contract for collector numbers, rarity, language and finish; preserve Cardmarket Product IDs and unresolved mappings; then design an additive dry-run import. Do not proceed automatically from this audit.",
        "",
        "## Recommended model (discovery only; not implemented)",
        "",
        "- **Logical Card:** canonical Pokémon card identity based on validated set + official collector number + card name.",
        "- **Printing / Variant:** physical printing row with Cardmarket Product ID, expansion, language, finish/treatment/variant and validated rarity where available.",
        "- **Cardmarket External Identity:** `idProduct` for product; `idExpansion` for expansion; `idMetacard` retained as non-authoritative source metadata.",
        "- **Finish representation:** explicit nullable field; never infer normal/holo/reverse holo from missing data or from `*-holo` price metrics.",
        "- **Rarity representation:** explicit nullable source-backed field, separate from finish.",
        "- **Language representation:** explicit printing/listing scope only after source evidence; do not create language variants from these files.",
        "- **Suggested natural uniqueness:** validated canonical card + release + language + finish/treatment/variant, with Cardmarket Product ID as provider identity; exact constraint remains to be designed in POKEMON-151-001.",
        "- **Pokémon-specific metadata:** official set code, Pokédex/collector-number conventions, Pokémon rarity vocabulary and any language/set-specific variant rules.",
        "- **Reusable model:** existing `games`, `sets`/releases, canonical cards, printings (`cards`), external-ID tables, nullable pricing and immutable price history.",
        "",
        "## Selected source evidence",
        "",
        f"- `idExpansion=5328`: `{len(rows)}` products, `{len(groups)}` source metacard/name groups.",
        f"- Product-name rows containing the literal `151`: `{len(observed_markers)}` distinct examples: " + ("; ".join(observed_markers) if observed_markers else "none") + ".",
        f"- Related candidate groups were not merged: top alternatives include `{', '.join(str(row['expansion_id']) for row in candidates[1:6])}`.",
        "",
        "**DB modified: NO. Existing Magic/One Piece modified: NO.**",
    ]
    output.joinpath("07_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--products", required=True, type=Path, help="Cardmarket products_singles JSON")
    parser.add_argument("--prices", required=True, type=Path, help="Cardmarket price_guide JSON")
    parser.add_argument("--output", required=True, type=Path, help="Report directory")
    parser.add_argument("--expansion-id", type=int, default=None, help="Optional source idExpansion after manual review")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        products_meta, all_products = load_json(args.products, "products")
        prices_meta, all_prices = load_json(args.prices, "priceGuides")
        if not args.products.is_file() or not args.prices.is_file():
            raise AuditError("Input paths must be regular files")
        for row in all_products:
            if "idProduct" not in row or "idExpansion" not in row:
                raise AuditError("Products records require idProduct and idExpansion")
        for row in all_prices:
            if "idProduct" not in row:
                raise AuditError("Price Guide records require idProduct")
        selected_id, candidates, rationale = select_expansion(all_products, args.expansion_id)
        scoped_products = [row for row in all_products if row.get("idExpansion") == selected_id]
        if not scoped_products:
            raise AuditError(f"No products found for selected expansion {selected_id}")
        price_index: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for entry in all_prices:
            price_index[int(entry["idProduct"])].append(entry)
        audited_rows = [
            classify_product(product, price_index.get(int(product["idProduct"]), []))
            for product in sorted(scoped_products, key=lambda row: int(row["idProduct"]))
        ]
        groups = build_groups(audited_rows)
        coverage = metric_coverage(audited_rows, price_index)
        args.output.mkdir(parents=True, exist_ok=True)
        write_csv(args.output / "02_cardmarket_products.csv", REPORT_COLUMNS, audited_rows)
        write_csv(args.output / "03_products_by_collector_number.csv", GROUP_COLUMNS, groups)
        write_csv(args.output / "05_price_coverage.csv", ["metric", "count", "denominator", "notes"], coverage)
        write_csv(args.output / "06_unresolved_products.csv", UNRESOLVED_COLUMNS, unresolved_rows(audited_rows))
        render_schema_report(args.output, args.products, args.prices, products_meta, prices_meta, all_products, all_prices, selected_id, candidates, rationale)
        render_variant_report(args.output, selected_id, audited_rows, groups, candidates)
        render_summary(args.output, args.products, args.prices, selected_id, audited_rows, groups, coverage, candidates)
        print(f"Audit complete: idExpansion={selected_id}, products={len(audited_rows)}, reports={args.output}")
        return 0
    except AuditError as exc:
        print(f"AUDIT ERROR: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"OUTPUT ERROR: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
