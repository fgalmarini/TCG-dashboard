"""Guarded, manifest-only VAL-AVG30-007 apply."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path
from typing import Any


VALUATION_COLUMNS = {"valuation_status", "valuation_method", "valuation_value", "reason"}


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest_sha(manifest: dict[str, Any]) -> str:
    copy = dict(manifest)
    copy["manifest_sha256"] = ""
    return hashlib.sha256(json.dumps(copy, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def _ro(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    return conn


def _validate_manifest(manifest: dict[str, Any]) -> list[str]:
    errors = []
    if _manifest_sha(manifest) != manifest.get("manifest_sha256"):
        errors.append("MANIFEST_SHA_MISMATCH")
    for key, expected in (("eligible_count", 367), ("excluded_count", 0), ("resolution_scope", "global"), ("game", "magic"), ("metric_family", "base"), ("readiness", "READY_FOR_PARTIAL_BACKFILL")):
        if manifest.get(key) != expected:
            errors.append(f"MANIFEST_{key.upper()}_INVALID")
    rows = manifest.get("rows")
    if not isinstance(rows, list) or len(rows) != 367:
        errors.append("MANIFEST_ROW_COUNT_INVALID")
        rows = rows if isinstance(rows, list) else []
    for index, row in enumerate(rows):
        if row.get("backfill_allowed") is not True:
            errors.append(f"ROW_{index}_NOT_AUTHORIZED")
        if not (row.get("valuation_status") == "ESTIMATED" and row.get("valuation_method") == "CARDMARKET_AVG30" and row.get("metric_family") == "base" and isinstance(row.get("valuation_value"), (int, float)) and row["valuation_value"] > 0):
            errors.append(f"ROW_{index}_VALUATION_GATE_FAILED")
    return errors


def _validate_db_evidence(conn: sqlite3.Connection, row: dict[str, Any]) -> str | None:
    columns = {r[1] for r in conn.execute("PRAGMA table_info(printing_price_resolutions)")}
    if not VALUATION_COLUMNS.issubset(columns):
        return "SCHEMA_MISSING_VALUATION_COLUMNS"
    history = conn.execute("SELECT * FROM market_price_history WHERE cardmarket_product_id=? AND observed_at=? ORDER BY id DESC LIMIT 1", (row["cardmarket_product_id"], row["observation_observed_at"])).fetchone()
    if history is None or history["avg30"] != row["valuation_value"]:
        return "OBSERVATION_CHANGED"
    if any(history[key] != row[key] for key in ("source_snapshot_created_at", "source_snapshot_sha256", "source_manifest_id", "provenance") if key in history.keys()):
        # A recovered provenance tuple is allowed only when the market history row has no evidence.
        if any(history[key] for key in ("source_snapshot_created_at", "source_snapshot_sha256", "source_manifest_id", "provenance")):
            return "OBSERVATION_PROVENANCE_CHANGED"
    if row.get("provenance_source") == "printing_price_resolutions":
        prior = conn.execute("SELECT provenance, source_snapshot_created_at, source_snapshot_sha256, source_manifest_id FROM printing_price_resolutions WHERE cardmarket_product_id=? AND provenance IS NOT NULL AND source_snapshot_sha256 IS NOT NULL AND source_manifest_id IS NOT NULL ORDER BY id DESC", (row["cardmarket_product_id"],)).fetchall()
        keys = {(item["provenance"], item["source_snapshot_created_at"], item["source_snapshot_sha256"], item["source_manifest_id"]) for item in prior}
        matching = [item for item in prior if (item["provenance"], item["source_snapshot_created_at"], item["source_snapshot_sha256"], item["source_manifest_id"]) == (row["provenance"], row["source_snapshot_created_at"], row["source_snapshot_sha256"], row["source_manifest_id"])]
        if len(keys) != 1 or not matching:
            return "RECOVERED_PROVENANCE_CHANGED"
    mapping = conn.execute("SELECT card_id, status FROM cardmarket_product_mappings WHERE cardmarket_product_id=? ORDER BY id", (row["cardmarket_product_id"],)).fetchall()
    if len(mapping) != 1 or mapping[0]["status"] != "mapped" or mapping[0]["card_id"] != row["card_id"]:
        return "CANONICAL_MAPPING_CHANGED"
    card = conn.execute("SELECT c.id, c.canonical_card_id, c.finish, g.code game FROM cards c JOIN games g ON g.id=c.game_id WHERE c.id=?", (row["card_id"],)).fetchone()
    if card is None or card["game"] != "magic" or str(card["finish"] or "").casefold() == "foil":
        return "CARD_SCOPE_CHANGED"
    return None


def _current_valuation(conn: sqlite3.Connection, row: dict[str, Any]) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM printing_price_resolutions WHERE card_id=? AND language_id=? AND resolution_scope='global' AND collection_item_id IS NULL AND wishlist_item_id IS NULL AND valuation_method='CARDMARKET_AVG30' AND cardmarket_product_id=? AND source_snapshot_sha256=? AND source_manifest_id=? ORDER BY id DESC LIMIT 1", (row["card_id"], row["language_id"], row["cardmarket_product_id"], row["source_snapshot_sha256"], row["source_manifest_id"])).fetchone()


def _preflight(db: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    db_before = _sha(db)
    errors = _validate_manifest(manifest)
    if db_before != manifest.get("db_sha256"):
        errors.append("DB_SHA_MISMATCH")
    conn = _ro(db)
    rejected = []
    unchanged = 0
    try:
        for row in manifest.get("rows", []):
            error = _validate_db_evidence(conn, row)
            if error:
                rejected.append({"card_id": row.get("card_id"), "cardmarket_product_id": row.get("cardmarket_product_id"), "reason": error})
            elif _current_valuation(conn, row) is not None:
                unchanged += 1
    finally:
        conn.close()
    return {"db_sha_before": db_before, "errors": errors, "rejected": rejected, "unchanged": unchanged}


def _insert(conn: sqlite3.Connection, row: dict[str, Any]) -> None:
    metadata = json.dumps({"valuation_observation_observed_at": row["observation_observed_at"], "resolver_version": "VAL-AVG30-006C"}, sort_keys=True)
    conn.execute("""INSERT INTO printing_price_resolutions
        (card_id, language_id, resolution_scope, resolved_at, current_price, currency, source, price_type,
         resolution_method, external_id, price_confidence, language_scope, metadata,
         cardmarket_product_id, match_status, is_current, valuation_status,
         valuation_method, valuation_value, reason, source_currency,
         source_snapshot_created_at, source_snapshot_sha256, source_manifest_id, provenance)
        VALUES (?, ?, 'global', ?, NULL, 'EUR', 'cardmarket', 'avg30', 'no_exact_language_price',
                ?, NULL, 'exact', ?, ?, 'UNPRICED', 0, ?, ?, ?, ?, 'EUR', ?, ?, ?, ?)""",
        (row["card_id"], row["language_id"], row["observation_observed_at"], str(row["cardmarket_product_id"]), metadata, row["cardmarket_product_id"], row["valuation_status"], row["valuation_method"], row["valuation_value"], row["resolver_reason"], row["source_snapshot_created_at"], row["source_snapshot_sha256"], row["source_manifest_id"], row["provenance"]))


def _snapshot_legacy(conn: sqlite3.Connection, max_id: int | None = None) -> bytes:
    clause = " WHERE id <= ?" if max_id is not None else ""
    params = (max_id,) if max_id is not None else ()
    rows = conn.execute(f"SELECT id, current_price, cardmarket_low, selected_metric, price_type, is_current FROM printing_price_resolutions{clause} ORDER BY id", params).fetchall()
    return json.dumps([tuple(row) for row in rows], sort_keys=True).encode()


def apply(db: Path, manifest_path: Path, do_apply: bool, output: Path) -> Path:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    preflight = _preflight(db, manifest)
    prior_result_path = output / "apply_result.json"
    if "DB_SHA_MISMATCH" in preflight["errors"] and prior_result_path.exists():
        prior = json.loads(prior_result_path.read_text(encoding="utf-8"))
        if prior.get("status") == "PARTIAL_BACKFILL_APPLIED" and prior.get("manifest_sha256") == manifest.get("manifest_sha256") and prior.get("db_sha_after") == preflight["db_sha_before"]:
            # Explicit idempotence policy: accept only the exact DB produced by
            # this manifest's preceding successful apply.
            preflight["errors"].remove("DB_SHA_MISMATCH")
    result = {"manifest_sha256": manifest.get("manifest_sha256"), "db_sha_before": preflight["db_sha_before"], "requested": len(manifest.get("rows", [])), "validated": 0, "inserted": 0, "updated": 0, "unchanged": 0, "rejected": preflight["rejected"], "errors": preflight["errors"], "scope": manifest.get("resolution_scope"), "game": manifest.get("game"), "metric_family": manifest.get("metric_family"), "valuation_method": "CARDMARKET_AVG30", "mode": "apply" if do_apply else "dry-run", "status": "BACKFILL_ABORTED"}
    if result["errors"] or result["rejected"]:
        return _write_result(output, result)
    result["validated"] = result["requested"]
    if not do_apply:
        result["status"] = "DRY_RUN_VALID"
        result["unchanged"] = preflight["unchanged"]
        result["db_sha_after"] = result["db_sha_before"]
        return _write_result(output, result)
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(prefix="tcg-avg30-", suffix=".db", dir=db.parent, delete=False) as handle:
            temp_name = handle.name
        shutil.copy2(db, temp_name)
        temp = Path(temp_name)
        conn = sqlite3.connect(temp)
        conn.execute("PRAGMA foreign_keys=ON")
        max_legacy_id = conn.execute("SELECT COALESCE(MAX(id), 0) FROM printing_price_resolutions").fetchone()[0]
        before_legacy = _snapshot_legacy(conn, max_legacy_id)
        conn.execute("BEGIN")
        for row in manifest["rows"]:
            if _current_valuation(conn, row) is None:
                _insert(conn, row)
                result["inserted"] += 1
            else:
                result["unchanged"] += 1
        conn.commit()
        after_legacy = _snapshot_legacy(conn, max_legacy_id)
        result["legacy_unchanged"] = before_legacy == after_legacy
        result["integrity_check"] = conn.execute("PRAGMA integrity_check").fetchone()[0]
        result["foreign_key_check"] = [tuple(r) for r in conn.execute("PRAGMA foreign_key_check").fetchall()]
        result["expected_valuations"] = len(manifest["rows"])
        result["present_valuations"] = conn.execute("SELECT COUNT(*) FROM printing_price_resolutions WHERE valuation_status='ESTIMATED' AND valuation_method='CARDMARKET_AVG30' AND resolution_scope='global' AND is_current=0").fetchone()[0]
        result["unexpected_valuations"] = max(0, result["present_valuations"] - result["expected_valuations"])
        result["db_sha_after"] = _sha(temp)
        conn.close()
        if not result["legacy_unchanged"] or result["integrity_check"] != "ok" or result["foreign_key_check"]:
            result["errors"].append("POSTFLIGHT_FAILED")
            return _write_result(output, result)
        os.replace(temp, db)
        result["status"] = "PARTIAL_BACKFILL_APPLIED"
        result["db_sha_after"] = _sha(db)
    except Exception as exc:
        result["errors"].append(f"UNEXPECTED_ROLLBACK:{type(exc).__name__}")
    finally:
        if temp_name and Path(temp_name).exists(): Path(temp_name).unlink()
    return _write_result(output, result)


def _write_result(output: Path, result: dict[str, Any]) -> Path:
    output.mkdir(parents=True, exist_ok=True)
    (output / "apply_result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = ["# VAL-AVG30-007 — Guarded Partial Backfill Apply", "", f"- status: `{result['status']}`", f"- mode: `{result['mode']}`", f"- requested: `{result['requested']}`", f"- validated: `{result['validated']}`", f"- inserted: `{result['inserted']}`", f"- updated: `{result['updated']}`", f"- unchanged: `{result['unchanged']}`", f"- rejected: `{len(result['rejected'])}`", f"- expected valuations: `{result.get('expected_valuations')}`", f"- present valuations: `{result.get('present_valuations')}`", f"- unexpected valuations: `{result.get('unexpected_valuations')}`", f"- DB SHA before: `{result['db_sha_before']}`", f"- DB SHA after: `{result.get('db_sha_after')}`", f"- manifest SHA: `{result['manifest_sha256']}`", "", "The apply is manifest-only, global/Magic/base, and does not modify `current_price`, legacy metrics, `is_current`, Collection, Wishlist, Overview, P/L or ROI."]
    if result["errors"]: lines += ["", "## Errors", ""] + [f"- `{error}`" for error in result["errors"]]
    if result["rejected"]: lines += ["", "## Rejected rows", ""] + [f"- card `{row.get('card_id')}`, product `{row.get('cardmarket_product_id')}`: `{row['reason']}`" for row in result["rejected"]]
    (output / "apply_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("reports/valuation/avg30_backfill/2026-09-09"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    if args.apply and args.dry_run: parser.error("use --apply or --dry-run, not both")
    result_path = apply(args.db, args.manifest, args.apply, args.output)
    result = json.loads((result_path / "apply_result.json").read_text(encoding="utf-8"))
    print(f"Result written to: {result_path} ({result['status']})")
    return 0 if result["status"] in {"DRY_RUN_VALID", "PARTIAL_BACKFILL_APPLIED"} else 1


if __name__ == "__main__": raise SystemExit(main())
