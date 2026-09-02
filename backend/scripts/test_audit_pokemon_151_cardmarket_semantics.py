import hashlib
import json
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

import audit_pokemon_151_cardmarket_semantics as audit
from pokemon_151_test_sources import make_cardmarket_sources


ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "backend/db/tcg_dashboard.db"
MAPPING_DIR = ROOT / "reports/pokemon_151/cardmarket_metric_mapping"
CACHE = ROOT / "backend/scripts/.pokemon_151_cardmarket_semantics_cache"


class Pokemon151CardmarketSemanticsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db = self.root / "catalog.db"
        shutil.copy2(DB, self.db)
        self.products, self.prices = make_cardmarket_sources(self.root, ROOT / "reports/pokemon_151/identity_discovery")

    def tearDown(self):
        self.tmp.cleanup()

    def test_apply_requires_offline(self):
        with self.assertRaises(audit.SemanticsGateError):
            audit.run(self.db, self.products, self.prices, MAPPING_DIR, self.root / "reports", CACHE, False, False, True)

    def test_offline_apply_uses_cached_evidence_and_changes_only_metric_relation(self):
        before = hashlib.sha256(self.db.read_bytes()).hexdigest()
        result = audit.run(self.db, self.products, self.prices, MAPPING_DIR, self.root / "reports", CACHE, True, False, True)
        self.assertEqual(result["canonical_exact_products"], 137)
        self.assertEqual(result["metric_mappings_reviewed"], 270)
        self.assertEqual(result["prices_applied"], 0)
        conn = sqlite3.connect(self.db)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM cardmarket_product_metric_mappings").fetchone()[0], 270)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM cardmarket_product_metric_mappings WHERE metric_mapping_status='SUPPORTED'").fetchone()[0], 0)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM cardmarket_product_metric_mappings WHERE pricing_eligible=1 OR card_id IS NOT NULL").fetchone()[0], 0)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM market_price_history WHERE cardmarket_product_id IN (SELECT id FROM cardmarket_products WHERE cardmarket_id_expansion=5328)").fetchone()[0], 0)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM printing_price_resolutions WHERE card_id IN (SELECT id FROM cards WHERE game_id=1)").fetchone()[0], 0)
        self.assertEqual(conn.execute("PRAGMA integrity_check").fetchone()[0], "ok")
        self.assertEqual(conn.execute("PRAGMA foreign_key_check").fetchall(), [])
        conn.close()
        self.assertNotEqual(hashlib.sha256(self.db.read_bytes()).hexdigest(), before)

    def test_dry_run_reports_410_and_403_without_promoting(self):
        result = audit.run(self.db, self.products, self.prices, MAPPING_DIR, self.root / "reports", CACHE, True, False, False)
        self.assertEqual(result["exact"], 0)
        self.assertEqual(result["pricing_eligible"], 0)
        manifest = json.loads((self.root / "reports/02_source_manifest.json").read_text())
        statuses = {entry["status"] for entry in manifest["external_sources"]}
        self.assertIn("LEGACY_GONE", statuses)
        self.assertIn("BLOCKED", statuses)

    def test_metric_mapping_status_supports_supported(self):
        audit.run(self.db, self.products, self.prices, MAPPING_DIR, self.root / "reports", CACHE, True, False, True)
        conn = sqlite3.connect(self.db)
        conn.execute("UPDATE cardmarket_product_metric_mappings SET metric_mapping_status='SUPPORTED' WHERE id=1")
        conn.commit()
        conn.close()


if __name__ == "__main__":
    unittest.main()
