import hashlib
import json
import sqlite3

from scripts.apply_avg30_backfill import _manifest_sha, apply


def _fixture(tmp_path):
    db = tmp_path / "fixture.db"
    conn = sqlite3.connect(db)
    conn.executescript("""
      CREATE TABLE games (id INTEGER PRIMARY KEY, code TEXT);
      CREATE TABLE cards (id INTEGER PRIMARY KEY, canonical_card_id INTEGER, finish TEXT, game_id INTEGER);
      CREATE TABLE cardmarket_products (id INTEGER PRIMARY KEY);
      CREATE TABLE cardmarket_product_mappings (id INTEGER PRIMARY KEY, cardmarket_product_id INTEGER, card_id INTEGER, status TEXT);
      CREATE TABLE market_price_history (id INTEGER PRIMARY KEY, cardmarket_product_id INTEGER, observed_at TEXT, avg30 REAL, source_snapshot_created_at TEXT, source_snapshot_sha256 TEXT, source_manifest_id TEXT, provenance TEXT);
      CREATE TABLE printing_price_resolutions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, card_id INTEGER, language_id INTEGER, resolved_at TEXT,
        current_price REAL, cardmarket_low REAL, selected_metric TEXT, price_type TEXT, is_current INTEGER,
        collection_item_id INTEGER, wishlist_item_id INTEGER, resolution_scope TEXT, valuation_status TEXT,
        valuation_method TEXT, valuation_value REAL, reason TEXT, cardmarket_product_id INTEGER,
        source_currency TEXT, source_snapshot_created_at TEXT, source_snapshot_sha256 TEXT, source_manifest_id TEXT, provenance TEXT,
        currency TEXT, source TEXT, resolution_method TEXT, external_id TEXT, price_confidence TEXT, match_status TEXT,
        language_scope TEXT, metadata TEXT
      );
    """)
    conn.execute("INSERT INTO games VALUES (1, 'magic')")
    conn.executemany("INSERT INTO cards VALUES (?, ?, NULL, 1)", [(n, n, ) for n in range(1, 368)])
    conn.executemany("INSERT INTO cardmarket_products VALUES (?)", [(n,) for n in range(1, 368)])
    conn.executemany("INSERT INTO cardmarket_product_mappings VALUES (?, ?, ?, 'mapped')", [(n, n, n) for n in range(1, 368)])
    conn.executemany("INSERT INTO market_price_history VALUES (?, ?, '2026-09-03T00:00:00+00:00', ?, '2026-09-03', ?, 'manifest', '{\"source\":\"local\"}')", [(n, n, 12.5 + n, f'hash-{n}') for n in range(1, 368)])
    conn.executemany("INSERT INTO printing_price_resolutions (card_id,language_id,resolved_at,current_price,cardmarket_low,selected_metric,price_type,is_current,collection_item_id,wishlist_item_id,resolution_scope,valuation_status,valuation_method,valuation_value,reason,cardmarket_product_id,source_snapshot_created_at,source_snapshot_sha256,source_manifest_id,provenance,currency,source,resolution_method,external_id,language_scope) VALUES (?,1,'2026-09-03',5,5,'Low','low',1,NULL,NULL,'global',NULL,NULL,NULL,NULL,?,NULL,NULL,NULL,NULL,'EUR','cardmarket','cardmarket_exact_language',?,'exact')", [(n, n, str(n)) for n in range(1, 368)])
    conn.commit(); conn.close()
    return db


def _manifest(db):
    rows = [{"card_id": n, "language_id": 1, "cardmarket_product_id": n, "valuation_status": "ESTIMATED", "valuation_method": "CARDMARKET_AVG30", "valuation_value": 12.5 + n, "metric_family": "base", "source_metric": "avg30", "observation_observed_at": "2026-09-03T00:00:00+00:00", "source_snapshot_created_at": "2026-09-03", "source_snapshot_sha256": f"hash-{n}", "source_manifest_id": "manifest", "provenance": '{"source":"local"}', "resolver_reason": None, "backfill_allowed": True, "provenance_source": "market_price_history"} for n in range(1, 368)]
    manifest = {"db_sha256": hashlib.sha256(db.read_bytes()).hexdigest(), "generated_at": "2026-09-09T00:00:00+00:00", "as_of": "2026-09-08", "resolver_version": "VAL-AVG30-006C", "resolution_scope": "global", "game": "magic", "metric_family": "base", "eligible_count": 367, "excluded_count": 0, "recoverable_provenance_count": 0, "readiness": "READY_FOR_PARTIAL_BACKFILL", "rows_to_insert": 0, "rows_to_update": 0, "rows_unchanged": 0, "rows_rejected": 0, "manifest_sha256": "", "rows": rows, "rejected_rows": []}
    manifest["manifest_sha256"] = _manifest_sha(manifest)
    return manifest


def test_manifest_hash_and_apply_are_idempotent(tmp_path):
    db = _fixture(tmp_path); manifest_path = tmp_path / "manifest.json"; manifest_path.write_text(json.dumps(_manifest(db)))
    out = tmp_path / "report"
    assert apply(db, manifest_path, False, out)
    first = json.loads((out / "apply_result.json").read_text()); assert first["status"] == "DRY_RUN_VALID"; assert first["inserted"] == 0
    assert apply(db, manifest_path, True, out)
    applied = json.loads((out / "apply_result.json").read_text()); assert applied["status"] == "PARTIAL_BACKFILL_APPLIED"; assert applied["inserted"] == 367; assert applied["legacy_unchanged"] is True
    assert apply(db, manifest_path, True, out)
    second = json.loads((out / "apply_result.json").read_text()); assert second["status"] == "PARTIAL_BACKFILL_APPLIED"; assert second["inserted"] == 0; assert second["unchanged"] == 367
    conn = sqlite3.connect(db); assert conn.execute("SELECT current_price FROM printing_price_resolutions WHERE id=1").fetchone()[0] == 5; assert conn.execute("SELECT COUNT(*) FROM printing_price_resolutions WHERE valuation_status='ESTIMATED'").fetchone()[0] == 367; assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"; conn.close()


def test_manifest_sha_mismatch_aborts_without_write(tmp_path):
    db = _fixture(tmp_path); manifest = _manifest(db); manifest["manifest_sha256"] = "bad"; path = tmp_path / "manifest.json"; path.write_text(json.dumps(manifest)); out = tmp_path / "report"
    apply(db, path, True, out)
    result = json.loads((out / "apply_result.json").read_text()); assert result["status"] == "BACKFILL_ABORTED"; assert "MANIFEST_SHA_MISMATCH" in result["errors"]
