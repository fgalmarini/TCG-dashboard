import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

import import_pokemon_151
import resolve_pokemon_151_cardmarket as canonical_resolver
import resolve_pokemon_151_metric_mappings as metric_resolver
from pokemon_151_test_sources import make_cardmarket_sources


ROOT = Path(__file__).resolve().parents[2]
DISCOVERY = ROOT / "reports/pokemon_151/identity_discovery"


class Pokemon151MetricMappingTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db = self.root / "catalog.db"
        conn = sqlite3.connect(self.db)
        conn.executescript((ROOT / "backend/db/schema.sql").read_text())
        conn.executescript((ROOT / "backend/db/seed.sql").read_text())
        conn.commit()
        conn.close()
        import_pokemon_151.run(self.db, DISCOVERY, self.root / "catalog-reports", self.root / "catalog-backups", True)
        self.products, self.prices = make_cardmarket_sources(self.root, DISCOVERY)
        canonical_resolver.run(self.db, self.products, self.prices, DISCOVERY, self.root / "mapping-reports", self.root / "mapping-backups", True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_dry_run_is_read_only_and_uses_real_metric_columns(self):
        before = hashlib.sha256(self.db.read_bytes()).hexdigest()
        result = metric_resolver.run(self.db, self.products, self.prices, DISCOVERY, self.root / "reports", self.root / "backups", False)
        self.assertEqual(result["canonical_exact_products"], 137)
        self.assertEqual(result["canonical_ambiguous_products_excluded"], 73)
        self.assertEqual(result["metric_mappings_reviewed"], 270)
        self.assertEqual(result["base_mappings_reviewed"], 137)
        self.assertEqual(result["foil_mappings_reviewed"], 133)
        self.assertEqual(result["metric_exact"], 0)
        self.assertEqual(result["metric_ambiguous"], 266)
        self.assertEqual(result["metric_unresolved"], 4)
        self.assertEqual(result["pricing_eligible"], 0)
        self.assertEqual(hashlib.sha256(self.db.read_bytes()).hexdigest(), before)
        report = (self.root / "reports/02_metric_mapping_dry_run.csv").read_text()
        self.assertIn("low-holo", report)
        self.assertNotIn("current_price", report)

    def test_apply_persists_only_metric_relationships(self):
        result = metric_resolver.run(self.db, self.products, self.prices, DISCOVERY, self.root / "reports", self.root / "backups", True)
        self.assertEqual(result["metric_rows"], 270)
        self.assertEqual(result["metric_exact"], 0)
        self.assertEqual(result["metric_ambiguous"], 266)
        self.assertEqual(result["metric_unresolved"], 4)
        conn = sqlite3.connect(self.db)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM cardmarket_product_metric_mappings").fetchone()[0], 270)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM cardmarket_product_metric_mappings WHERE pricing_eligible=1").fetchone()[0], 0)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM cardmarket_product_metric_mappings WHERE card_id IS NOT NULL").fetchone()[0], 0)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM cardmarket_product_metric_mappings WHERE metric_mapping_status='EXACT'").fetchone()[0], 0)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM market_price_history WHERE cardmarket_product_id IN (SELECT id FROM cardmarket_products WHERE cardmarket_id_expansion=5328)").fetchone()[0], 0)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM printing_price_resolutions WHERE card_id IN (SELECT id FROM cards WHERE game_id=1)").fetchone()[0], 0)
        self.assertEqual(conn.execute("PRAGMA integrity_check").fetchone()[0], "ok")
        self.assertEqual(conn.execute("PRAGMA foreign_key_check").fetchall(), [])
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM cardmarket_product_metric_mappings WHERE metric_family NOT IN ('base','foil')").fetchone()[0], 0)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM cardmarket_product_metric_mappings GROUP BY cardmarket_product_id, metric_family HAVING COUNT(*) <> 1").fetchall(), [])
        conn.close()

    def test_ambiguous_canonical_products_are_untouched(self):
        metric_resolver.run(self.db, self.products, self.prices, DISCOVERY, self.root / "reports", self.root / "backups", True)
        mapping_rows = list(csv_rows(DISCOVERY / "03_cardmarket_mapping.csv"))
        ambiguous_ids = {int(row["cardmarket_product_id"]) for row in mapping_rows if row["mapping_status"] == "AMBIGUOUS"}
        conn = sqlite3.connect(self.db)
        found = conn.execute("""
            SELECT p.cardmarket_id_product
              FROM cardmarket_product_metric_mappings m
              JOIN cardmarket_products p ON p.id=m.cardmarket_product_id
             WHERE p.cardmarket_id_product IN ({})
        """.format(",".join("?" for _ in ambiguous_ids)), tuple(ambiguous_ids)).fetchall()
        self.assertEqual(found, [])
        conn.close()

    def test_second_apply_is_idempotent(self):
        metric_resolver.run(self.db, self.products, self.prices, DISCOVERY, self.root / "reports", self.root / "backups", True)
        second = metric_resolver.run(self.db, self.products, self.prices, DISCOVERY, self.root / "reports-2", self.root / "backups-2", False)
        self.assertEqual(second["new_metric_rows"], 0)


def csv_rows(path):
    import csv
    with path.open(encoding="utf-8", newline="") as handle:
        yield from csv.DictReader(handle)


if __name__ == "__main__":
    unittest.main()
