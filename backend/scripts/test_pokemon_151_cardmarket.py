import hashlib
import sqlite3
import tempfile
import unittest
from pathlib import Path

import import_pokemon_151
import resolve_pokemon_151_cardmarket as resolver
from pokemon_151_test_sources import make_cardmarket_sources


ROOT = Path(__file__).resolve().parents[2]
DISCOVERY = ROOT / "reports/pokemon_151/identity_discovery"


class Pokemon151CardmarketResolutionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db = self.root / "catalog.db"
        conn = sqlite3.connect(self.db)
        conn.executescript((ROOT / "backend/db/schema.sql").read_text())
        conn.executescript((ROOT / "backend/db/seed.sql").read_text())
        conn.commit(); conn.close()
        import_pokemon_151.run(self.db, DISCOVERY, self.root / "catalog-reports", self.root / "catalog-backups", True)
        self.products, self.prices = make_cardmarket_sources(self.root, DISCOVERY)

    def tearDown(self):
        self.tmp.cleanup()

    def test_dry_run_is_evidence_driven_and_does_not_write(self):
        before = hashlib.sha256(self.db.read_bytes()).hexdigest()
        result = resolver.run(self.db, self.products, self.prices, DISCOVERY, self.root / "reports", self.root / "backups", False)
        self.assertEqual(result["products_reviewed"], 210)
        self.assertEqual(result["exact"], 137)
        self.assertEqual(result["ambiguous"], 73)
        self.assertEqual(result["new_product_rows"], 210)
        self.assertEqual(result["new_mapping_rows"], 137)
        self.assertEqual(hashlib.sha256(self.db.read_bytes()).hexdigest(), before)

    def test_apply_persists_canonical_scope_without_forcing_physical_finish_or_price(self):
        result = resolver.run(self.db, self.products, self.prices, DISCOVERY, self.root / "reports", self.root / "backups", True)
        self.assertEqual(result["authoritative_mappings"], 137)
        conn = sqlite3.connect(self.db)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM cardmarket_products WHERE cardmarket_id_expansion=5328").fetchone()[0], 210)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM cardmarket_product_mappings WHERE status='mapped'").fetchone()[0], 137)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM cardmarket_product_printing_scopes WHERE mapping_status='EXACT'").fetchone()[0], 137)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM cardmarket_product_printing_scopes WHERE card_id IS NOT NULL").fetchone()[0], 0)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM cardmarket_product_printing_scopes WHERE pricing_eligible=1").fetchone()[0], 0)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM cardmarket_product_printing_scopes WHERE mapping_status<>'EXACT'").fetchone()[0], 0)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM market_price_history WHERE cardmarket_product_id IN (SELECT id FROM cardmarket_products WHERE cardmarket_id_expansion=5328)").fetchone()[0], 0)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM printing_price_resolutions WHERE card_id IN (SELECT id FROM cards WHERE game_id=1)").fetchone()[0], 0)
        self.assertEqual(conn.execute("PRAGMA foreign_key_check").fetchall(), [])
        conn.close()

        second = resolver.run(self.db, self.products, self.prices, DISCOVERY, self.root / "reports2", self.root / "backups2", False)
        self.assertEqual(second["new_product_rows"], 0)
        self.assertEqual(second["new_mapping_rows"], 0)

    def test_ambiguous_same_name_products_remain_unpersisted(self):
        resolver.run(self.db, self.products, self.prices, DISCOVERY, self.root / "reports", self.root / "backups", True)
        conn = sqlite3.connect(self.db)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM cardmarket_product_printing_scopes WHERE cardmarket_product_id IN (SELECT id FROM cardmarket_products WHERE cardmarket_id_product IN (719442,719448,719661))").fetchone()[0], 0)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM cardmarket_product_mappings WHERE cardmarket_product_id IN (SELECT id FROM cardmarket_products WHERE cardmarket_id_product IN (719442,719448,719661))").fetchone()[0], 0)
        conn.close()


if __name__ == "__main__":
    unittest.main()
