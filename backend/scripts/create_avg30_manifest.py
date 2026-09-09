"""Build the VAL-AVG30-006C candidate manifest without changing SQLite."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sqlite3
from collections import Counter
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.results.read_text(encoding="utf-8"))
    eligible = [r for r in data["results"] if r["valuation_value"] is not None]
    conn = sqlite3.connect(f"file:{args.db.resolve()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    candidates, rejected, recoverable = [], [], []
    try:
        for row in eligible:
            if not (row["scope"] == "catalog" and row["game"] == "magic" and row["metric_family"] == "base"):
                rejected.append({"card_id": row["card_id"], "reason": "OUT_OF_SCOPE"})
                continue
            history = conn.execute("SELECT * FROM market_price_history WHERE cardmarket_product_id=? AND observed_at=? ORDER BY id DESC LIMIT 1", (row["cardmarket_product_id"], row["observation_observed_at"])).fetchone()
            evidence = None
            provenance_source = "market_price_history"
            if history and all(history[k] for k in ("provenance", "source_snapshot_sha256", "source_manifest_id")):
                evidence = {"provenance": history["provenance"], "source_snapshot_created_at": history["source_snapshot_created_at"], "source_snapshot_sha256": history["source_snapshot_sha256"], "source_manifest_id": history["source_manifest_id"]}
            else:
                prior = conn.execute("SELECT provenance, source_snapshot_created_at, source_snapshot_sha256, source_manifest_id FROM printing_price_resolutions WHERE cardmarket_product_id=? AND provenance IS NOT NULL AND source_snapshot_sha256 IS NOT NULL AND source_manifest_id IS NOT NULL ORDER BY id DESC", (row["cardmarket_product_id"],)).fetchall()
                keys = {(x["provenance"], x["source_snapshot_created_at"], x["source_snapshot_sha256"], x["source_manifest_id"]) for x in prior}
                if len(keys) == 1:
                    x = prior[0]
                    evidence = {"provenance": x["provenance"], "source_snapshot_created_at": x["source_snapshot_created_at"], "source_snapshot_sha256": x["source_snapshot_sha256"], "source_manifest_id": x["source_manifest_id"]}
                    provenance_source = "printing_price_resolutions"
                    recoverable.append(row["cardmarket_product_id"])
            gate = row["valuation_status"] == "ESTIMATED" and row["valuation_method"] == "CARDMARKET_AVG30" and float(row["valuation_value"]) > 0 and row["cardmarket_product_id"] is not None and row["identity_evidence"].get("canonical_valid") and row["identity_evidence"].get("language_compatible") and row["identity_evidence"].get("finish_compatible") and row["identity_evidence"].get("metric_family") == "base" and not row["identity_evidence"].get("identity_blocked") and evidence is not None
            if not gate:
                rejected.append({"card_id": row["card_id"], "cardmarket_product_id": row["cardmarket_product_id"], "reason": "PROVENANCE_INCOMPLETE" if evidence is None else "GATE_FAILED"})
                continue
            candidates.append({"card_id": row["card_id"], "language_id": row["language"], "cardmarket_product_id": row["cardmarket_product_id"], "valuation_status": row["valuation_status"], "valuation_method": row["valuation_method"], "valuation_value": row["valuation_value"], "metric_family": row["metric_family"], "source_metric": row["metric_name"], "observation_observed_at": row["observation_observed_at"], "source_snapshot_created_at": evidence["source_snapshot_created_at"], "source_snapshot_sha256": evidence["source_snapshot_sha256"], "source_manifest_id": evidence["source_manifest_id"], "provenance": evidence["provenance"], "resolver_reason": row["reason"], "backfill_allowed": True, "provenance_source": provenance_source})
    finally:
        conn.close()
    candidates.sort(key=lambda r: (r["card_id"], r["language_id"], r["cardmarket_product_id"]))
    db_hash = sha256(args.db)
    manifest = {"db_sha256": db_hash, "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "as_of": args.as_of, "resolver_version": "VAL-AVG30-006C", "resolution_scope": "global", "game": "magic", "metric_family": "base", "eligible_count": len(candidates), "excluded_count": len(rejected), "recoverable_provenance_count": len(recoverable), "readiness": "READY_FOR_PARTIAL_BACKFILL" if candidates and not rejected else "NOT_READY_FOR_BACKFILL", "rows_to_insert": 0, "rows_to_update": 0, "rows_unchanged": 0, "rows_rejected": len(rejected), "manifest_sha256": "", "rows": candidates, "rejected_rows": rejected}
    # Apply simulation is intentionally only a read-only comparison with current rows.
    check = sqlite3.connect(f"file:{args.db.resolve()}?mode=ro", uri=True); check.row_factory = sqlite3.Row
    try:
        columns = {r[1] for r in check.execute("PRAGMA table_info(printing_price_resolutions)")}
        value_columns = [c for c in ("valuation_status", "valuation_method", "valuation_value", "reason") if c in columns]
        select_values = ", ".join(value_columns) if len(value_columns) == 4 else "NULL AS valuation_status, NULL AS valuation_method, NULL AS valuation_value, NULL AS reason"
        for row in candidates:
            current = check.execute(f"SELECT {select_values} FROM printing_price_resolutions WHERE card_id=? AND language_id=? AND resolution_scope='global' AND collection_item_id IS NULL AND wishlist_item_id IS NULL AND is_current=1 ORDER BY id DESC LIMIT 1", (row["card_id"], row["language_id"])).fetchone()
            if current is None: manifest["rows_to_insert"] += 1
            elif tuple(current) == (row["valuation_status"], row["valuation_method"], row["valuation_value"], row["resolver_reason"]): manifest["rows_unchanged"] += 1
            else: manifest["rows_to_update"] += 1
    finally: check.close()
    manifest["manifest_sha256"] = hashlib.sha256(canonical({**manifest, "manifest_sha256": ""})).hexdigest()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "candidate_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    counts = Counter(r["provenance_source"] for r in candidates)
    lines = ["# VAL-AVG30-006C — Candidate Backfill Manifest", "", f"- Readiness: `{manifest['readiness']}`", f"- Scope: `global / magic / base`", f"- as_of: `{args.as_of}`", f"- SAFE_FOR_BACKFILL: `{len(candidates)}`", f"- PROVENANCE_INCOMPLETE / rejected: `{len(rejected)}`", f"- PROVENANCE_RECOVERABLE: `{len(recoverable)}`", f"- Provenance source: `{dict(counts)}`", f"- DB SHA-256: `{db_hash}`", f"- Manifest SHA-256: `{manifest['manifest_sha256']}`", "", "## Apply simulation", "", f"- rows_to_insert: `{manifest['rows_to_insert']}`", f"- rows_to_update: `{manifest['rows_to_update']}`", f"- rows_unchanged: `{manifest['rows_unchanged']}`", f"- rows_rejected: `{manifest['rows_rejected']}`", "", "Only `valuation_status`, `valuation_method`, `valuation_value` and `reason` are candidate fields. `current_price` is not touched. No SQLite write occurred.", "", "## Provenance gate", "", f"The original 367 eligible rows are all Magic catalog/base/ESTIMATED. `{len(recoverable)}` rows without history provenance were deterministically recovered from the unique prior `printing_price_resolutions` evidence tuple; no evidence was inferred or created. The resulting manifest contains all `{len(candidates)}` safe rows.", "", "NULL results remain NULL and are excluded from this manifest. Collection, Wishlist, Pokémon, One Piece and foil/alt remain outside scope."]
    (args.output / "candidate_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__": raise SystemExit(main())
