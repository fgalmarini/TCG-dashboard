import sqlite3
import shutil
import tempfile
import unittest
from pathlib import Path

from backend.scripts import import_pokemon_151_tcgplayer_prices as importer


class Pokemon151TcgplayerImportTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[2]
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "catalog.db"
        shutil.copy2(self.root / "backend/db/tcg_dashboard.db", self.db)
        conn = sqlite3.connect(self.db)
        conn.executescript((self.root / "backend/db/schema.sql").read_text())
        conn.execute("DELETE FROM market_price_observations")
        conn.commit()
        conn.close()
        self.source = self.root / "reports/pokemon_151/finish_pricing_sources"
        self.output = Path(self.tmp.name) / "pricing-reports"
        self.backups = Path(self.tmp.name) / "pricing-backups"

    def tearDown(self):
        self.tmp.cleanup()

    def test_dry_run_is_read_only_and_apply_is_idempotent(self):
        before = importer.sha256_file(self.db)
        conn = sqlite3.connect(self.db)
        before_primary = conn.execute("SELECT COUNT(*), COALESCE(SUM(current_price), 0) FROM printing_price_resolutions").fetchone()
        before_history = conn.execute("SELECT COUNT(*) FROM market_price_history").fetchone()[0]
        conn.close()
        dry = importer.run(self.db, self.source, self.output, self.backups, False)
        self.assertEqual(dry["physical_printings_checked"], 362)
        self.assertEqual(dry["eligible"], 339)
        self.assertEqual(dry["observations_to_insert"], 1676)
        self.assertEqual(before, importer.sha256_file(self.db))

        first = importer.run(self.db, self.source, self.output, self.backups, True)
        self.assertEqual(first["observations_inserted"], 1676)
        conn = sqlite3.connect(self.db)
        try:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM market_price_observations").fetchone()[0], 1676)
            self.assertEqual(conn.execute("SELECT COUNT(*), COALESCE(SUM(current_price), 0) FROM printing_price_resolutions").fetchone(), before_primary)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM market_price_history").fetchone()[0], before_history)
            self.assertEqual(conn.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(conn.execute("PRAGMA foreign_key_check").fetchall(), [])
        finally:
            conn.close()

        second = importer.run(self.db, self.source, self.output, self.backups, True)
        self.assertEqual(second["observations_inserted"], 0)
        conn = sqlite3.connect(self.db)
        try:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM market_price_observations").fetchone()[0], 1676)
        finally:
            conn.close()

    def test_finish_mapping_and_direct_low_are_separate_metrics(self):
        importer.run(self.db, self.source, self.output, self.backups, True)
        conn = sqlite3.connect(self.db)
        try:
            rows = conn.execute("""
                SELECT c.finish, o.source_variant, GROUP_CONCAT(o.metric), GROUP_CONCAT(o.currency)
                  FROM market_price_observations o
                  JOIN cards c ON c.id=o.card_id
                 GROUP BY o.card_id
                 ORDER BY o.card_id
            """).fetchall()
            self.assertTrue(rows)
            for finish, source_variant, metrics, currencies in rows:
                self.assertEqual(source_variant, {"normal": "normal", "holo": "holofoil", "reverse_holo": "reverseHolofoil"}[finish])
                self.assertIn("low", metrics)
                self.assertIn("market", metrics)
                self.assertIn("USD", currencies)
            self.assertNotEqual(conn.execute("SELECT COUNT(*) FROM market_price_observations WHERE metric='direct_low'").fetchone()[0], 0)
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
