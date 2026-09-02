#!/usr/bin/env python3
"""Generate a read-only human review artifact from existing Pokémon reports."""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = ROOT / "backend/db/tcg_dashboard.db"
DEFAULT_DIR = ROOT / "reports/pokemon_151/cardmarket_manual_resolution"
CONFIDENCE_ORDER = {"STRONG": 0, "MEDIUM": 1, "WEAK": 2, "NONE": 3}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in fields} for row in rows)


def compact(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def candidate_context(conn: sqlite3.Connection, number: str) -> dict[str, object]:
    row = conn.execute("""
        SELECT cc.id, cc.metadata
          FROM canonical_cards cc JOIN games g ON g.id=cc.game_id
         WHERE g.code='pokemon' AND cc.identity_key=?
    """, (f"pokemon:mew:{number}",)).fetchone()
    if not row:
        raise ValueError(f"missing canonical candidate {number}")
    metadata = json.loads(row[1] or "{}").get("pokemon", {})
    return {
        "artist": metadata.get("artist", ""), "hp": metadata.get("hp", ""),
        "types": ", ".join(metadata.get("types", []) or []),
        "category": metadata.get("category", ""),
    }


def action(confidence: str, recommendation: str) -> str:
    if confidence == "STRONG" and recommendation:
        return "APPROVE"
    if confidence in {"STRONG", "MEDIUM"}:
        return "REVIEW CAREFULLY"
    return "LEAVE UNRESOLVED"


def make_artifacts(db: Path, report_dir: Path) -> dict[str, int]:
    workspace = read_csv(report_dir / "01_review_workspace.csv")
    evidence = read_csv(report_dir / "02_candidate_evidence.csv")
    review = read_csv(report_dir / "03_manual_review.csv")
    if len(workspace) != 73 or len(review) != 73:
        raise ValueError("expected exactly 73 workspace and review rows")
    if any(row.get("approved", "").casefold() not in {"false", "0", ""} for row in review):
        raise ValueError("human review artifact expects all current rows to remain pending")
    evidence_by_key = {(row["idProduct"], row["candidate_collector_number"]): row for row in evidence}
    conn = sqlite3.connect(db)
    try:
        entries: list[dict[str, object]] = []
        for row in workspace:
            candidates = []
            for index in range(1, 4):
                number = row.get(f"candidate_{index}_collector_number", "")
                if not number:
                    continue
                evidence_row = evidence_by_key[(row["idProduct"], number)]
                candidates.append({
                    "number": number, "name": row[f"candidate_{index}_card_name"],
                    "rarity": row.get(f"candidate_{index}_rarity", "") or "not available",
                    "image": row.get(f"candidate_{index}_image", ""),
                    **candidate_context(conn, number), "evidence": evidence_row,
                })
            confidence = row.get("recommendation_confidence", "NONE") or "NONE"
            entries.append({
                "idProduct": row["idProduct"], "idMetacard": row["idMetacard"],
                "product_name": row["product_name"], "version": f"idExpansion=5328; idMetacard={row['idMetacard']}; no product-specific version/finish field",
                "confidence": confidence, "recommended": row.get("recommended_candidate", ""),
                "reason": row.get("ambiguity_reason", ""), "evidence_available": row.get("evidence_available", ""),
                "candidates": candidates, "suggested_action": action(confidence, row.get("recommended_candidate", "")),
            })
    finally:
        conn.close()

    entries.sort(key=lambda item: (CONFIDENCE_ORDER.get(str(item["confidence"]), 99), len(item["candidates"]), int(str(item["idProduct"]))))
    counts = Counter(str(item["confidence"]) for item in entries)
    actions = Counter(str(item["suggested_action"]) for item in entries)
    summary_rows = [{
        "review_number": index, "idProduct": item["idProduct"], "confidence": item["confidence"],
        "candidate_count": len(item["candidates"]),
        "highest_evidence_score": max((int(c["evidence"].get("evidence_score", 0) or 0) for c in item["candidates"]), default=0),
        "recommended_candidate": item["recommended"], "suggested_action": item["suggested_action"], "product_name": item["product_name"],
    } for index, item in enumerate(entries, 1)]
    write_csv(report_dir / "10_human_review_summary.csv", ["review_number", "idProduct", "confidence", "candidate_count", "highest_evidence_score", "recommended_candidate", "suggested_action", "product_name"], summary_rows)

    lines = [
        "# POKEMON 151 CARDMARKET HUMAN REVIEW", "",
        "This artifact is presentation-only. It was generated from the existing workspace, candidate evidence and catalog DB.",
        "It does not edit `03_manual_review.csv`, approve rows, apply mappings or modify the DB.", "",
        "## Batch summary", "",
        f"- Pending total: **{len(entries)}**", "",
        f"- STRONG: **{counts['STRONG']}**", f"- MEDIUM: **{counts['MEDIUM']}**", f"- WEAK: **{counts['WEAK']}**", f"- NONE: **{counts['NONE']}**", "",
        f"- Suggested APPROVE: **{actions['APPROVE']}**", f"- Suggested REVIEW CAREFULLY: **{actions['REVIEW CAREFULLY']}**", f"- Suggested LEAVE UNRESOLVED: **{actions['LEAVE UNRESOLVED']}**", "",
        "Confidence is product-level. Candidate evidence scores are diagnostic only and never approve a mapping.",
        "Every displayed image is the exact internal TCGdex image for its own collector number.", "",
    ]
    for index, item in enumerate(entries, 1):
        lines += [f"## REVIEW #{index}", "", f"**Confidence:** {item['confidence']}", "", "### Cardmarket", "", f"- idProduct: `{item['idProduct']}`", f"- idMetacard: `{item['idMetacard']}`", f"- Product name: `{item['product_name']}`", f"- Cardmarket version if known: {item['version']}", "", "### Recommended", "", "- Collector number: —", "- Card: —", "- Rarity: —", "- Reason: No deterministic recommendation in the audited evidence.", ""]
        for candidate_index, candidate in enumerate(item["candidates"], 1):
            evidence_row = candidate["evidence"]
            details = ", ".join(filter(None, [f"HP {candidate['hp']}" if candidate["hp"] else "", candidate["types"], candidate["category"]])) or "not available"
            lines += [f"### Candidate {candidate_index}: {candidate['name']} #{candidate['number']}", "", f"- Collector number: `{candidate['number']}`", f"- Card name: `{candidate['name']}`", f"- Rarity: `{candidate['rarity']}`", f"- Artist: `{candidate['artist'] or 'not available'}`", f"- HP/type/category: `{details}`", f"- Image: ![{candidate['name']} #{candidate['number']}]({candidate['image']})", f"- Evidence: exact TCGdex image; TCGdex ID `{evidence_row.get('tcgdex_id', '')}`; Pokémon TCG API ID `{evidence_row.get('pokemon_tcg_api_id', '')}`; name match `{evidence_row.get('name_match', '')}`; diagnostic score `{evidence_row.get('evidence_score', '')}`.", ""]
        lines += ["### Why ambiguous", "", f"{item['reason']}.", f"Available evidence: {item['evidence_available']}.", "", "### What distinguishes the recommendation", "", "No recommendation is presented. The audited source has no Cardmarket-specific artwork, rarity or version discriminator linking this product to one candidate; candidate images are shown separately for human comparison only.", "", f"### Suggested action: {item['suggested_action']}", "", "Do not set `approved=true` from this artifact. If evidence remains insufficient, leave unresolved.", ""]
    (report_dir / "09_human_review.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"pending": len(entries), **{key.lower(): counts[key] for key in ("STRONG", "MEDIUM", "WEAK", "NONE")}, "approve": actions["APPROVE"], "review_carefully": actions["REVIEW CAREFULLY"], "leave_unresolved": actions["LEAVE UNRESOLVED"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_DIR)
    args = parser.parse_args()
    print(json.dumps(make_artifacts(args.db, args.report_dir), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
