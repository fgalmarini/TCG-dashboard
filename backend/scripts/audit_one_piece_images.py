"""Read-only audit for One Piece image provenance and display fallbacks."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.images.one_piece import find_fallback_decisions


def _connect_read_only(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _load_blueprints(path: Path | None) -> dict[str, dict]:
    if path is None:
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload if isinstance(payload, list) else payload.get("blueprints", payload.get("data", []))
    return {str(row["id"]): row for row in rows if isinstance(row, dict) and row.get("id") is not None}


def _effective_language(row: sqlite3.Row) -> str | None:
    scope = row["image_language_scope"]
    return scope if scope not in (None, "unknown") else row["image_language"]


def _read_rows(conn: sqlite3.Connection) -> tuple[list[sqlite3.Row], list[sqlite3.Row]]:
    image_columns = {row[1] for row in conn.execute("PRAGMA table_info(card_images)")}
    scope = "ci.image_language_scope" if "image_language_scope" in image_columns else "'unknown'"
    fallback = "ci.is_language_fallback" if "is_language_fallback" in image_columns else "0"
    cards = conn.execute(
        """SELECT c.id, c.card_number, c.name, c.canonical_card_id, c.set_id,
                      c.release_kind, c.art_kind, c.source_variant, c.catalog_status,
                      l.code AS language, s.code AS set_code
                 FROM cards c
                 JOIN games g ON g.id=c.game_id
                 LEFT JOIN languages l ON l.id=c.language_id
                 LEFT JOIN sets s ON s.id=c.set_id
                WHERE g.code='one_piece'
                ORDER BY c.id"""
    ).fetchall()
    images = conn.execute(
        f"""SELECT ci.card_id, ci.source, ci.source_card_id,
                      ci.source_variant, ci.source_collector_number,
                      ci.language AS image_language, {scope} AS image_language_scope,
                      {fallback} AS is_language_fallback, ci.face_index,
                      ci.image_url_small, ci.image_url_large, ci.match_quality, ci.status
                 FROM card_images ci
                 JOIN cards c ON c.id=ci.card_id
                 JOIN games g ON g.id=c.game_id
                WHERE g.code='one_piece'
                ORDER BY ci.card_id, ci.source, ci.face_index"""
    ).fetchall()
    return cards, images


def _image_state(card: sqlite3.Row, rows: list[sqlite3.Row]) -> dict:
    requested = card["language"]
    exact = [row for row in rows if row["status"] == "resolved" and row["match_quality"] == "exact"
             and not row["is_language_fallback"] and (row["image_url_small"] or row["image_url_large"])
             and (requested is None or _effective_language(row) == requested)]
    fallback = [row for row in rows if row["status"] == "resolved" and row["match_quality"] == "exact"
                and row["is_language_fallback"] and (row["image_url_small"] or row["image_url_large"])]
    selected = exact[0] if exact else (fallback[0] if fallback else None)
    return {
        "has_exact": bool(exact),
        "has_fallback": bool(fallback),
        "stored_record": bool(rows),
        "api_image": selected is not None,
        "selected": selected,
    }


def _candidate_categories(card: sqlite3.Row) -> list[str]:
    categories: list[str] = []
    if card["art_kind"] == "base":
        categories.append("base")
    if card["art_kind"] == "alternate_art":
        categories.append("alternate_art")
    if card["art_kind"] == "parallel":
        categories.append("parallel")
    if card["release_kind"] == "promo":
        categories.append("promo")
    if card["release_kind"] == "reprint":
        categories.append("reprint")
    if card["art_kind"] in {"manga", "special"} or card["release_kind"] == "special":
        categories.append("manga_special")
    return categories


def audit(db_path: Path, blueprint_path: Path | None = None) -> dict:
    conn = _connect_read_only(db_path)
    try:
        cards, images = _read_rows(conn)
        blueprints = _load_blueprints(blueprint_path)
        by_card: dict[int, list[sqlite3.Row]] = defaultdict(list)
        for row in images:
            by_card[row["card_id"]].append(row)
        blueprint_by_card: dict[int, set[str]] = defaultdict(set)
        for row in conn.execute(
            """SELECT pei.card_id, pei.external_id
                 FROM printing_external_ids pei
                 JOIN cards c ON c.id=pei.card_id
                 JOIN games g ON g.id=c.game_id
                WHERE g.code='one_piece' AND pei.source='cardtrader_blueprint'"""
        ):
            blueprint_by_card[row["card_id"]].add(str(row["external_id"]))
        fallback_decisions = find_fallback_decisions(conn)
        decision_by_card = {decision.jp_card_id: decision for decision in fallback_decisions}
        unresolved_decisions = [
            decision for decision in fallback_decisions
            if decision.status in {"missing", "ambiguous"}
        ]
        ambiguous_decisions = [
            decision for decision in unresolved_decisions
            if decision.status == "ambiguous" or "not unique" in (decision.reason or "")
        ]

        languages = ["en", "jp"]
        status_counts: dict[tuple[str, str], dict[str, int]] = {}
        source_breakdown: Counter[tuple[str, str, str, str, str, int]] = Counter()
        status_breakdown: Counter[tuple[str, str, str]] = Counter()
        catalog_status_breakdown: Counter[tuple[str, str]] = Counter()
        blueprint_breakdown: Counter[tuple[str, str]] = Counter()
        examples_by_category: dict[str, list[dict]] = defaultdict(list)
        items_by_card: dict[int, dict] = {}
        unresolved_jp_with_blueprint = []
        for card in cards:
            if card["language"] not in languages:
                continue
            state = _image_state(card, by_card.get(card["id"], []))
            language = card["language"]
            catalog_status_breakdown[(language, card["catalog_status"])] += 1
            bucket = status_counts.setdefault((language, card["catalog_status"]), {"total_printings": 0, "exact_images": 0, "fallback_images": 0, "missing_images": 0, "ambiguous_images": 0})
            bucket["total_printings"] += 1
            bucket["exact_images"] += int(state["has_exact"])
            bucket["fallback_images"] += int(state["has_fallback"])
            bucket["missing_images"] += int(not state["has_exact"] and not state["has_fallback"])
            bucket["ambiguous_images"] += int(any(row["status"] == "ambiguous" for row in by_card.get(card["id"], [])))
            for row in by_card.get(card["id"], []):
                source_breakdown[(language, card["catalog_status"], row["source"], row["status"], _effective_language(row) or "unknown", int(row["is_language_fallback"]))] += 1
                status_breakdown[(language, row["status"], row["match_quality"])] += 1
            blueprint_ids = sorted(blueprint_by_card.get(card["id"], set()))
            source_urls = [blueprints[bp].get("image_url") for bp in blueprint_ids if bp in blueprints and blueprints[bp].get("image_url")]
            blueprint_breakdown[(language, "present")] += int(bool(blueprint_ids))
            blueprint_breakdown[(language, "image_url_present")] += int(bool(source_urls))
            if language == "jp" and card["catalog_status"] == "active" and not state["has_exact"] and not state["has_fallback"] and blueprint_ids:
                unresolved_jp_with_blueprint.append(card["id"])
            item = {
                "card_id": card["id"], "card_number": card["card_number"], "name": card["name"],
                "set_code": card["set_code"], "language": language, "release_kind": card["release_kind"],
                "art_kind": card["art_kind"], "source_variant": card["source_variant"],
                "catalog_status": card["catalog_status"], "blueprint_ids": blueprint_ids,
                "blueprint_present": bool(blueprint_ids),
                "blueprint_image_url_present": None if blueprint_path is None else bool(source_urls),
                "stored_image_record": state["stored_record"], "api_image_present": state["api_image"],
                "frontend_image_present": state["api_image"],
                "selected_image": None if state["selected"] is None else {
                    "source": state["selected"]["source"],
                    "actual_image_language": _effective_language(state["selected"]),
                    "is_language_fallback": bool(state["selected"]["is_language_fallback"]),
                },
            }
            decision = decision_by_card.get(card["id"])
            if decision and decision.status in {"missing", "ambiguous"}:
                item["fallback_decision"] = {
                    "status": decision.status,
                    "reason": decision.reason,
                }
            items_by_card[card["id"]] = item
            if card["catalog_status"] == "active" and card["language"] == "jp":
                for category in _candidate_categories(card):
                    if len(examples_by_category[category]) < 4:
                        examples_by_category[category].append(item)

        examples = []
        seen: set[int] = set()
        for category in ("base", "alternate_art", "parallel", "promo", "reprint", "manga_special"):
            for item in examples_by_category.get(category, []):
                if item["language"] == "jp" and item["card_id"] not in seen:
                    item = {**item, "sample_categories": [category]}
                    examples.append(item)
                    seen.add(item["card_id"])
        for decision in unresolved_decisions[:1]:
            item = items_by_card.get(decision.jp_card_id)
            if item and item["card_id"] not in seen:
                examples.append(item)
                seen.add(item["card_id"])
        for card in cards:
            if len(examples) >= 20:
                break
            if card["language"] == "jp" and card["id"] not in seen:
                item = items_by_card.get(card["id"])
                if item:
                    examples.append(item)
                    seen.add(card["id"])
        counts = {language: status_counts.get((language, "active"), {"total_printings": 0, "exact_images": 0, "fallback_images": 0, "missing_images": 0, "ambiguous_images": 0}) for language in ("en", "jp")}
        all_counts: dict[str, dict[str, int]] = {language: {"total_printings": 0, "exact_images": 0, "fallback_images": 0, "missing_images": 0, "ambiguous_images": 0} for language in ("en", "jp")}
        for (language, _status), bucket in status_counts.items():
            for key in all_counts[language]:
                all_counts[language][key] += bucket[key]
        for language, bucket in all_counts.items():
            total = bucket["total_printings"] or 1
            bucket["exact_coverage_pct"] = round(bucket["exact_images"] * 100 / total, 2)
            bucket["visual_coverage_pct"] = round((bucket["exact_images"] + bucket["fallback_images"]) * 100 / total, 2)
            bucket["missing_coverage_pct"] = round(bucket["missing_images"] * 100 / total, 2)
        for language, bucket in counts.items():
            total = bucket["total_printings"] or 1
            bucket["exact_coverage_pct"] = round(bucket["exact_images"] * 100 / total, 2)
            bucket["visual_coverage_pct"] = round((bucket["exact_images"] + bucket["fallback_images"]) * 100 / total, 2)
            bucket["missing_coverage_pct"] = round(bucket["missing_images"] * 100 / total, 2)
        return {
            "db": str(db_path),
            "read_only": True,
            "counts_by_language": counts,
            "counts_by_language_all_statuses": all_counts,
            "source_breakdown": [
                {"language": language, "catalog_status": catalog_status, "source": source, "status": status, "actual_image_language": actual,
                 "is_language_fallback": bool(is_fallback), "count": count}
                for (language, catalog_status, source, status, actual, is_fallback), count in sorted(source_breakdown.items())
            ],
            "match_breakdown": [
                {"language": language, "status": status, "match_quality": quality, "count": count}
                for (language, status, quality), count in sorted(status_breakdown.items())
            ],
            "catalog_status_breakdown": [
                {"language": language, "catalog_status": status, **bucket}
                for (language, status), bucket in sorted(status_counts.items())
            ],
            "blueprint_breakdown": [
                {"language": language, "metric": metric, "count": count}
                for (language, metric), count in sorted(blueprint_breakdown.items())
            ],
            "fallback_summary": {
                "safe_fallback_images_active_jp": counts["jp"]["fallback_images"],
                "unresolved_jp_printings_with_blueprint": len(unresolved_jp_with_blueprint),
                "ambiguous_jp_printings": len(ambiguous_decisions),
                "unresolved_decisions": [
                    {"jp_card_id": decision.jp_card_id, "status": decision.status, "reason": decision.reason}
                    for decision in unresolved_decisions
                ],
                "blueprint_image_url_status": "unknown_without_raw_blueprint_export",
            },
            "sample_categories_available": {category: len(examples_by_category.get(category, [])) for category in ("base", "alternate_art", "parallel", "promo", "reprint", "manga_special")},
            "validation_examples": examples,
            "blueprint_export_supplied": blueprint_path is not None,
        }
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--blueprints", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit(args.db, args.blueprints)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
