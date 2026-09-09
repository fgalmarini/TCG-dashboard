"""Run the local, read-only VAL-AVG30-006 resolver dry-run."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from valuation.avg30_resolver import (  # noqa: E402
    NULL_REASONS, ValuationDecision, build_identity_evidence, latest_observations,
    resolve_valuation,
)


def _read_only(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only = ON")
    return conn


def _one(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> dict[str, Any] | None:
    row = conn.execute(sql, params).fetchone()
    return dict(row) if row else None


def _load_rows(conn: sqlite3.Connection, as_of: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    collection = conn.execute("""SELECT ci.id item_id, 'collection' scope, ci.card_id, ci.cardmarket_product_id, ci.quantity units, c.* , g.code game
                                  FROM collection_items ci LEFT JOIN cards c ON c.id=ci.card_id LEFT JOIN games g ON g.id=c.game_id
                                  ORDER BY ci.id""").fetchall()
    wishlist = conn.execute("""SELECT wi.id item_id, 'wishlist' scope, wi.card_id, NULL cardmarket_product_id, wi.quantity_wanted units, c.*, g.code game
                                FROM wishlist_items wi JOIN cards c ON c.id=wi.card_id JOIN games g ON g.id=c.game_id
                                ORDER BY wi.id""").fetchall()
    catalogs = conn.execute("""SELECT c.id card_id, NULL item_id, 'catalog' scope, NULL cardmarket_product_id, 1 units, c.*, g.code game
                               FROM cards c JOIN games g ON g.id=c.game_id
                              WHERE (g.code='pokemon' AND lower(COALESCE(c.set_code,''))='mew')
                                 OR (g.code='magic' AND lower(COALESCE(c.set_code,'')) IN ('ltr','ltc'))
                              ORDER BY g.code, c.id""").fetchall()
    rows.extend(dict(row) for row in collection)
    rows.extend(dict(row) for row in wishlist)
    rows.extend(dict(row) for row in catalogs)
    return rows


def _product_id(conn: sqlite3.Connection, row: dict[str, Any]) -> int | None:
    if row.get("cardmarket_product_id"):
        return int(row["cardmarket_product_id"])
    if row["scope"] == "collection":
        scoped = _one(conn, "SELECT cardmarket_product_id FROM printing_price_resolutions WHERE collection_item_id=? AND is_current=1 ORDER BY id DESC LIMIT 1", (row["item_id"],))
    elif row["scope"] == "wishlist":
        scoped = _one(conn, "SELECT cardmarket_product_id FROM printing_price_resolutions WHERE wishlist_item_id=? AND is_current=1 ORDER BY id DESC LIMIT 1", (row["item_id"],))
    else:
        scoped = None
    if scoped and scoped.get("cardmarket_product_id"):
        return int(scoped["cardmarket_product_id"])
    if row["scope"] == "catalog":
        scoped = _one(conn, "SELECT cardmarket_product_id FROM printing_price_resolutions WHERE card_id=? AND is_current=1 ORDER BY id DESC LIMIT 1", (row.get("card_id"),))
        if scoped and scoped.get("cardmarket_product_id"):
            return int(scoped["cardmarket_product_id"])
    mappings = conn.execute("SELECT cardmarket_product_id FROM cardmarket_product_mappings WHERE card_id=? AND status='mapped' ORDER BY cardmarket_product_id", (row.get("card_id"),)).fetchall()
    ids = {int(item["cardmarket_product_id"]) for item in mappings}
    return next(iter(ids)) if len(ids) == 1 else None


def _decision_row(conn: sqlite3.Connection, row: dict[str, Any], observations: dict[int, dict[str, Any]], as_of: str) -> dict[str, Any]:
    product_id = _product_id(conn, row)
    product = _one(conn, "SELECT * FROM cardmarket_products WHERE id=?", (product_id,)) if product_id else None
    product_mapping_rows = conn.execute("SELECT * FROM cardmarket_product_mappings WHERE cardmarket_product_id=? ORDER BY id", (product_id,)).fetchall() if product_id else []
    product_mapping = dict(product_mapping_rows[0]) if len(product_mapping_rows) == 1 else None
    scope_mapping = _one(conn, "SELECT * FROM cardmarket_product_printing_scopes WHERE cardmarket_product_id=?", (product_id,)) if product_id else None
    finish = str(row.get("finish") or "").casefold()
    family = "foil" if finish == "foil" else "base"
    metric_mapping = _one(conn, "SELECT * FROM cardmarket_product_metric_mappings WHERE cardmarket_product_id=? AND metric_family=?", (product_id, family)) if product_id else None
    language = _one(conn, "SELECT 1 FROM printing_external_ids WHERE card_id=? AND source='cardmarket_product' AND language_id=? AND language_scope='exact' LIMIT 1", (row.get("card_id"), row.get("language_id"))) if row.get("card_id") else None
    language_exact = bool(language) or (row.get("scope") == "catalog" and str(row.get("game") or "") == "magic")
    evidence = build_identity_evidence(card=row, product=product, product_mapping=product_mapping, scope_mapping=scope_mapping, metric_mapping=metric_mapping, language_exact=language_exact)
    observation = observations.get(product_id) if product_id else None
    decision: ValuationDecision = resolve_valuation(card=row, product=product, observation=observation, identity_evidence=evidence, as_of=as_of)
    legacy = None
    if row["scope"] == "collection":
        legacy = _one(conn, "SELECT current_price FROM printing_price_resolutions WHERE collection_item_id=? AND is_current=1 ORDER BY id DESC LIMIT 1", (row["item_id"],))
    elif row["scope"] == "wishlist":
        legacy = _one(conn, "SELECT current_price FROM printing_price_resolutions WHERE wishlist_item_id=? AND is_current=1 ORDER BY id DESC LIMIT 1", (row["item_id"],))
    if legacy is None and product is not None:
        legacy = {"current_price": product.get("current_price")}
    legacy_value = legacy.get("current_price") if legacy else None
    proposed = decision.valuation_value
    absolute = abs(float(proposed) - float(legacy_value)) if proposed is not None and legacy_value is not None else None
    percentage = absolute / abs(float(legacy_value)) if absolute is not None and float(legacy_value) != 0 else None
    return {
        "scope": row["scope"], "game": row.get("game"), "card_id": row.get("card_id"), "item_id": row.get("item_id"),
        "units": int(row.get("units") or 0), "card_name": row.get("name"), "card_number": row.get("card_number"),
        "set_code": row.get("set_code"), "language": row.get("language_id"), "finish": row.get("finish"),
        "cardmarket_product_id": product_id, "metric_family": decision.metric_family, "metric_name": decision.metric_name,
        "valuation_status": decision.valuation_status, "valuation_method": decision.valuation_method,
        "valuation_value": decision.valuation_value, "reason": decision.reason,
        "observation_observed_at": observation.get("observed_at") if observation else None,
        "as_of": as_of, "observation_age_days": _age_days(observation.get("observed_at"), as_of) if observation else None,
        "observation_metrics": {key: observation.get(key) for key in ("low", "trend", "avg1", "avg7", "avg30", "low_alt", "trend_alt", "avg1_alt", "avg7_alt", "avg30_alt")} if observation else None,
        "observation_source": observation.get("source") if observation else None,
        "legacy_current_price": legacy_value, "absolute_difference": absolute, "percentage_difference": percentage,
        "identity_evidence": evidence,
    }


def _age_days(observed: str | None, as_of: str) -> int | None:
    if not observed:
        return None
    try:
        return (dt.date.fromisoformat(as_of) - dt.date.fromisoformat(str(observed)[:10])).days
    except ValueError:
        return None


def _summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for result in results:
        grouped[(result["scope"], result["game"] or "unknown")].append(result)
    for (scope, game), items in sorted(grouped.items()):
        counts = Counter("NULL" if item["valuation_value"] is None else item["valuation_status"] for item in items)
        nulls = Counter(item["reason"] for item in items if item["valuation_value"] is None)
        eligible = counts.get("ESTIMATED", 0) + counts.get("EXACT", 0)
        ages = [item["observation_age_days"] for item in items if item["observation_age_days"] is not None]
        summary[f"{scope}:{game}"] = {"total": len(items), "ESTIMATED": counts.get("ESTIMATED", 0), "EXACT": counts.get("EXACT", 0), "NULL": counts.get("NULL", 0), "eligible_rows": eligible, "ineligible_rows": len(items) - eligible, "coverage_percent": round(eligible / len(items) * 100, 2) if items else 0, "observation_age_days": {"min": min(ages) if ages else None, "max": max(ages) if ages else None}, "null_reasons": dict(sorted(nulls.items()))}
    return summary


def _portfolio(results: list[dict[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for scope in ("collection", "wishlist"):
        items = [row for row in results if row["scope"] == scope]
        legacy = sum(float(row["legacy_current_price"]) * row["units"] for row in items if row["legacy_current_price"] is not None)
        proposed = sum(float(row["valuation_value"]) * row["units"] for row in items if row["valuation_value"] is not None)
        valued = sum(row["units"] for row in items if row["valuation_value"] is not None)
        units = sum(row["units"] for row in items)
        difference = proposed - legacy if legacy or proposed else 0.0
        output[scope] = {"legacy_portfolio_value": round(legacy, 2), "proposed_estimated_portfolio_value": round(proposed, 2), "absolute_difference": round(difference, 2), "percentage_difference": round(difference / abs(legacy) * 100, 2) if legacy else None, "percentage_difference_reason": None if legacy else "LEGACY_VALUE_NULL_OR_ZERO", "valued_units": valued, "unvalued_units": units - valued, "coverage_percent": round(valued / units * 100, 2) if units else 0}
    return output


def run(db: Path, as_of: str, output_root: Path) -> Path:
    dt.date.fromisoformat(as_of)
    conn = _read_only(db)
    try:
        observations = latest_observations(conn, as_of)
        results = [_decision_row(conn, row, observations, as_of) for row in _load_rows(conn, as_of)]
    finally:
        conn.close()
    summary = _summarize(results)
    portfolio = _portfolio(results)
    eligible = [row for row in results if row["valuation_value"] is not None]
    technical_correct = bool(results) and all((row["valuation_value"] is not None and row["valuation_status"] in {"ESTIMATED", "EXACT"}) or (row["valuation_value"] is None and row["reason"] in NULL_REASONS) for row in results)
    scope_recommendations = {}
    for key, item in summary.items():
        scope_recommendations[key] = "READY_FOR_BACKFILL" if technical_correct and item["eligible_rows"] > 0 else "NOT_READY_FOR_BACKFILL"
    proposed_scopes = sorted(summary)
    recommendation = "READY_FOR_BACKFILL" if technical_correct and proposed_scopes and all(scope_recommendations[key] == "READY_FOR_BACKFILL" for key in proposed_scopes) else "NOT_READY_FOR_BACKFILL"
    payload = {"generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "as_of": as_of, "read_only": True, "db": str(db.resolve()), "summary": summary, "portfolio": portfolio, "eligible_rows": len(eligible), "ineligible_rows": len(results) - len(eligible), "affected_scopes": sorted({row["scope"] for row in results if row["valuation_value"] is None}), "affected_games": sorted({row["game"] for row in results if row["valuation_value"] is None and row["game"]}), "technical_resolver_correct": technical_correct, "backfill_usefulness": {"proposed_scopes": proposed_scopes, "scope_recommendations": scope_recommendations, "eligible_rows": len(eligible), "ineligible_rows": len(results) - len(eligible)}, "recommendation": recommendation, "results": results}
    output = output_root / as_of
    output.mkdir(parents=True, exist_ok=True)
    (output / "results.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = ["# VAL-AVG30-006 — Avg30 resolver dry-run", "", f"- as_of: `{as_of}`", "- read-only: `YES`", f"- recommendation: `{recommendation}`", f"- eligible rows: `{len(eligible)}`", f"- ineligible rows: `{len(results) - len(eligible)}`", "", "## Technical correctness vs usefulness", "", f"- technical resolver correctness: `{'PASS' if payload['technical_resolver_correct'] else 'FAIL'}`", "- backfill usefulness requires at least one eligible valuation in the proposed scope; no minimum coverage percentage is imposed.", "", "## Coverage by scope and game", "", "| Scope / game | Total | ESTIMATED | EXACT | NULL | Eligible | Coverage |", "|---|---:|---:|---:|---:|---:|---:|"]
    for key, item in summary.items():
        lines.append(f"| {key} | {item['total']} | {item['ESTIMATED']} | {item['EXACT']} | {item['NULL']} | {item['eligible_rows']} | {item['coverage_percent']}% |")
    lines += ["", "Observation age (days; min/max by group):", ""]
    for key, item in summary.items():
        age = item["observation_age_days"]
        lines.append(f"- `{key}`: `{age['min']}` / `{age['max']}`")
    lines += ["", "## NULL reasons", ""]
    reasons = Counter(row["reason"] for row in results if row["reason"])
    for reason in sorted(NULL_REASONS):
        lines.append(f"- `{reason}`: {reasons.get(reason, 0)}")
    lines += ["", "## Portfolio simulation", "", "| Scope | Legacy value | Proposed Avg30 value | Valued units | Unvalued units | Coverage |", "|---|---:|---:|---:|---:|---:|"]
    for scope, item in portfolio.items():
        lines.append(f"| {scope} | EUR {item['legacy_portfolio_value']:.2f} | EUR {item['proposed_estimated_portfolio_value']:.2f} | {item['valued_units']} | {item['unvalued_units']} | {item['coverage_percent']}% |")
    lines += ["", "## Backfill usefulness by scope", ""]
    for key in proposed_scopes:
        lines.append(f"- `{key}`: `{scope_recommendations[key]}`")
    lines += ["", "## Audited examples", ""]
    examples = [
        ("ESTIMATED", lambda row: row["valuation_status"] == "ESTIMATED"),
        ("POKEMON_FINISH_UNRESOLVED", lambda row: row["game"] == "pokemon" and row["reason"] == "FINISH_UNRESOLVED"),
        ("ONE_PIECE_LANGUAGE_UNRESOLVED", lambda row: row["game"] == "one_piece" and row["reason"] == "LANGUAGE_UNRESOLVED"),
        ("MAGIC_NONFOIL", lambda row: row["game"] == "magic" and row["finish"] != "foil" and row["valuation_value"] is not None),
        ("MAGIC_FOIL_RESOLVED", lambda row: row["game"] == "magic" and row["finish"] == "foil" and row["valuation_value"] is not None),
        ("MAGIC_FOIL_BLOCKED", lambda row: row["game"] == "magic" and row["finish"] == "foil" and row["reason"] == "FINISH_UNRESOLVED"),
        ("MISSING_AVG30", lambda row: row["reason"] == "MISSING_AVG30"),
    ]
    for label, predicate in examples:
        example = next((row for row in results if predicate(row)), None)
        lines.append(f"- `{label}`: {example['game']} / {example['card_name']} / product `{example['cardmarket_product_id']}`" if example else f"- `{label}`: no encontrado en este run")
    (output / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--as-of", required=True, dest="as_of")
    parser.add_argument("--output-root", type=Path, default=ROOT / "reports" / "valuation" / "avg30_resolver")
    args = parser.parse_args(argv)
    output = run(args.db, args.as_of, args.output_root)
    print(f"Report written to: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
