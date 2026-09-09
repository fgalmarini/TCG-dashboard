"""Generate the additive Avg30 consumption report without changing the DB."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from backend.api import queries


def _read_only(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    return conn


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _portfolio(rows: list[Any], quantity_field: str) -> dict[str, Any]:
    legacy = 0.0
    proposed = 0.0
    valued_units = 0
    unvalued_units = 0
    for row in rows:
        quantity = int(getattr(row, quantity_field))
        legacy_value = row.market_trend if quantity_field == "quantity" else row.current_price
        if legacy_value is not None:
            legacy += float(legacy_value) * quantity
        if row.valuation_value is not None:
            proposed += float(row.valuation_value) * quantity
            valued_units += quantity
        else:
            unvalued_units += quantity
    difference = proposed - legacy
    return {
        "legacy_portfolio_value": round(legacy, 2),
        "proposed_valuation_value": round(proposed, 2),
        "absolute_difference": round(difference, 2),
        "percentage_difference": round(difference / legacy * 100, 2) if legacy else None,
        "percentage_difference_reason": None if legacy else "LEGACY_VALUE_ZERO_OR_NULL",
        "valued_units": valued_units,
        "unvalued_units": unvalued_units,
        "coverage_percent": round(valued_units / (valued_units + unvalued_units) * 100, 2)
        if valued_units + unvalued_units else 0,
    }


def _row_payload(row: Any, scope: str, quantity_field: str) -> dict[str, Any]:
    quantity = int(getattr(row, quantity_field))
    return {
        "scope": scope,
        "item_id": row.id,
        "card_id": row.card_id,
        "game": row.game_code,
        "quantity": quantity,
        "legacy_value": row.market_trend if scope == "collection" else row.current_price,
        "valuation_status": row.valuation_status,
        "valuation_method": row.valuation_method,
        "valuation_value": row.valuation_value,
        "valuation_reason": row.valuation_reason,
        "valuation_currency": row.valuation_currency,
        "valuation_source": row.valuation_source,
    }


def _group(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    eligible = [row for row in rows if row["valuation_value"] is not None]
    units = sum(row["quantity"] for row in rows)
    valued_units = sum(row["quantity"] for row in eligible)
    return {
        "total": total,
        "estimated": sum(row["valuation_status"] == "ESTIMATED" for row in rows),
        "exact": sum(row["valuation_status"] == "EXACT" for row in rows),
        "null": sum(row["valuation_value"] is None for row in rows),
        "eligible_rows": len(eligible),
        "ineligible_rows": total - len(eligible),
        "coverage_percent": round(len(eligible) / total * 100, 2) if total else 0,
        "valued_units": valued_units,
        "unvalued_units": units - valued_units,
        "unit_coverage_percent": round(valued_units / units * 100, 2) if units else 0,
        "reasons": dict(sorted(Counter(row["valuation_reason"] for row in rows if row["valuation_value"] is None).items())),
    }


def build_report(db: Path, as_of: str) -> dict[str, Any]:
    before_hash = _sha256(db)
    conn = _read_only(db)
    try:
        collection = queries.fetch_collection_rows(conn)
        wishlist = queries.fetch_wishlist_rows(conn, status="wanted")
        global_count = conn.execute(
            """SELECT COUNT(*) FROM printing_price_resolutions
               WHERE resolution_scope='global' AND collection_item_id IS NULL
                 AND wishlist_item_id IS NULL
                 AND valuation_status IN ('ESTIMATED','EXACT')
                 AND valuation_value IS NOT NULL AND valuation_value > 0"""
        ).fetchone()[0]
        scoped_count = conn.execute(
            """SELECT COUNT(*) FROM printing_price_resolutions
               WHERE resolution_scope IN ('collection','wishlist')
                 AND valuation_status IN ('ESTIMATED','EXACT')
                 AND valuation_value IS NOT NULL AND valuation_value > 0"""
        ).fetchone()[0]
    finally:
        conn.close()

    rows = [
        _row_payload(row, "collection", "quantity") for row in collection
    ] + [_row_payload(row, "wishlist", "quantity_wanted") for row in wishlist]
    by_scope = {scope: _group([row for row in rows if row["scope"] == scope]) for scope in ("collection", "wishlist")}
    by_game = {game: _group([row for row in rows if row["game"] == game]) for game in sorted({row["game"] for row in rows})}
    portfolio = {
        "collection": _portfolio(collection, "quantity"),
        "wishlist_wanted": _portfolio(wishlist, "quantity_wanted"),
    }
    return {
        "run": {
            "as_of": as_of,
            "db": str(db.resolve()),
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "read_only": True,
            "db_sha256_before": before_hash,
        },
        "counts": {
            "global_before": global_count,
            "global_after": global_count,
            "scoped_before": scoped_count,
            "scoped_after": scoped_count,
            "created_scoped_valuations": 0,
        },
        "by_scope": by_scope,
        "by_game": by_game,
        "portfolio": portfolio,
        "results": rows,
        "db_sha256_after": _sha256(db),
        "legacy_unchanged": before_hash == _sha256(db),
        "recommendation": "VALUATION_FIELDS_AVAILABLE_ADDITIVELY",
    }


def _markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# VAL-AVG30-008 — Global Valuation Consumption",
        "",
        "Read-only report. `current_price`/`market_value` and productive totals were not changed.",
        "",
        f"- as_of: `{payload['run']['as_of']}`",
        f"- global valuations: `{payload['counts']['global_before']} → {payload['counts']['global_after']}`",
        f"- scoped valuations: `{payload['counts']['scoped_before']} → {payload['counts']['scoped_after']}`",
        f"- created by 008: `{payload['counts']['created_scoped_valuations']}`",
        f"- DB unchanged: `{payload['legacy_unchanged']}`",
        "",
        "## Coverage",
        "",
        "| Group | Total | ESTIMATED | EXACT | NULL | Eligible | Coverage | Valued units | Unvalued units |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    groups = {**{f"scope:{k}": v for k, v in payload["by_scope"].items()}, **{f"game:{k}": v for k, v in payload["by_game"].items()}}
    for name, data in groups.items():
        lines.append(f"| {name} | {data['total']} | {data['estimated']} | {data['exact']} | {data['null']} | {data['eligible_rows']} | {data['coverage_percent']}% | {data['valued_units']} | {data['unvalued_units']} |")
    lines += ["", "## Portfolio simulation", "", "| Group | Legacy | Proposed valuation | Difference | Difference % |", "|---|---:|---:|---:|---:|"]
    for name, data in payload["portfolio"].items():
        percentage = "NULL" if data["percentage_difference"] is None else f"{data['percentage_difference']}%"
        lines.append(f"| {name} | EUR {data['legacy_portfolio_value']:.2f} | EUR {data['proposed_valuation_value']:.2f} | EUR {data['absolute_difference']:.2f} | {percentage} |")
    lines += ["", "## NULL reasons", "", "La distribución exacta por scope y juego está en `results.json`. Los NULL permanecen NULL y no participan de la simulación propuesta.", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output or Path("reports/valuation/avg30_consumption") / args.as_of
    payload = build_report(args.db, args.as_of)
    output.mkdir(parents=True, exist_ok=True)
    (output / "results.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output / "summary.md").write_text(_markdown(payload), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
