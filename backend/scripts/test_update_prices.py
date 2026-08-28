import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import update_prices
from downloader import DownloadResult


class FakeCardTrader:
    def fetch_marketplace_expansion(self, release_id, language):
        if language != "en":
            return []
        return [
            {
                "blueprint_id": 42,
                "user": {"id": seller},
                "on_vacation": False,
                "graded": False,
                "price": {"cents": cents, "currency": "EUR"},
                "properties_hash": {
                    "condition": "Near Mint",
                    "onepiece_language": "en",
                    "signed": False,
                    "altered": False,
                },
                "bundle_size": 1,
            }
            for seller, cents in ((1, 100), (2, 200), (3, 300), (4, 400), (5, 500))
        ]

    def fetch_marketplace_products(self, blueprint_id, language):
        return []


class UpdatePricesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db = self.root / "test.db"
        self.source = self.root / "source"
        self.source.mkdir()
        conn = sqlite3.connect(self.db)
        conn.executescript((Path(__file__).resolve().parents[1] / "db/schema.sql").read_text())
        conn.executescript((Path(__file__).resolve().parents[1] / "db/seed.sql").read_text())
        conn.execute("INSERT INTO expansions (id, game_id, cardmarket_id_expansion, name) VALUES (1, 3, 1, 'LTR')")
        conn.execute("INSERT INTO expansions (id, game_id, cardmarket_id_expansion, name) VALUES (2, 2, 2, 'OP01')")
        conn.execute(
            """INSERT INTO cards
               (id, game_id, expansion_id, card_number, name, printing_variant,
                language_id, set_code, finish, catalog_status)
               VALUES (1, 3, 1, '1', 'Magic Test', 'normal', 1, 'ltr', 'nonfoil', 'active')"""
        )
        conn.execute(
            """INSERT INTO cards
               (id, game_id, expansion_id, card_number, name, printing_variant,
                language_id, set_code, canonical_card_id, catalog_status)
               VALUES (2, 2, 2, 'OP01-001', 'One Piece Exact', 'normal', 1, 'op01', NULL, 'active')"""
        )
        conn.execute(
            """INSERT INTO cards
               (id, game_id, expansion_id, card_number, name, printing_variant,
                language_id, set_code, catalog_status)
               VALUES (3, 2, 2, 'OP01-002', 'One Piece Fallback', 'normal', 1, 'op01', 'active')"""
        )
        conn.execute(
            """INSERT INTO cards
               (id, game_id, expansion_id, card_number, name, printing_variant,
                language_id, set_code, catalog_status)
               VALUES (4, 2, 2, 'OP01-003', 'One Piece JP', 'normal', 2, 'op01', 'active')"""
        )
        conn.execute(
            """INSERT INTO cardmarket_products
               (id, cardmarket_id_product, raw_name, cardmarket_id_category,
                cardmarket_id_expansion, date_added, last_seen_at)
               VALUES (1, 500, 'Magic Test', 1, 1, '2026-01-01', '2026-01-01')"""
        )
        conn.execute(
            """INSERT INTO cardmarket_product_mappings
               (cardmarket_product_id, card_id, status) VALUES (1, 1, 'mapped')"""
        )
        conn.execute(
            """INSERT INTO printing_external_ids
               (card_id, source, external_id, language_id, language_scope, metadata)
               VALUES (2, 'cardtrader_blueprint', '41', 1, 'exact', '{"release_id":77}')"""
        )
        conn.execute(
            """INSERT INTO printing_external_ids
               (card_id, source, external_id, language_id, language_scope, metadata)
               VALUES (2, 'cardmarket_product', '100', 1, 'exact', '{}')"""
        )
        conn.execute(
            """INSERT INTO printing_external_ids
               (card_id, source, external_id, language_id, language_scope, metadata)
               VALUES (3, 'cardtrader_blueprint', '42', 1, 'exact', '{"release_id":77}')"""
        )
        conn.execute(
            """INSERT INTO printing_external_ids
               (card_id, source, external_id, language_id, language_scope, metadata)
               VALUES (4, 'cardtrader_blueprint', '43', 2, 'exact', '{"release_id":77}')"""
        )
        conn.commit()
        conn.close()
        self._write_sources()

    def tearDown(self):
        self.tmp.cleanup()

    def _write_sources(self):
        for game, game_id, price_guides in (
            ("magic", 1, [{"idProduct": 500, "low": 1.0, "avg": 1.5, "trend": 2.0}]),
            ("one_piece", 18, [{"idProduct": 100, "low": 8.0, "avg": 9.0, "trend": 9.0}]),
        ):
            products = self.source / f"{game}-products.json"
            prices = self.source / f"{game}-prices.json"
            products.write_text(json.dumps({"createdAt": "2026-08-28T00:00:00+00:00", "products": []}))
            prices.write_text(json.dumps({"createdAt": "2026-08-28T00:00:00+00:00", "priceGuides": price_guides}))

    def _download(self, games):
        result = {}
        ids = {"magic": 1, "one_piece": 18}
        for game in games:
            product_path = self.source / f"{game}-products.json"
            price_path = self.source / f"{game}-prices.json"
            result[f"{game}:products"] = DownloadResult("products", "fixture", product_path, True, product_path.stat().st_size, None)
            result[f"{game}:price_guide"] = DownloadResult("prices", "fixture", price_path, True, price_path.stat().st_size, None)
        return result

    def _run(self, mode, games=("magic", "one_piece"), now="2026-08-28T12:00:00+00:00"):
        with patch.object(update_prices, "LOG_DIR", self.root / "logs"), \
             patch.object(update_prices, "BACKUP_DIR", self.root / "backups"):
            return update_prices.run_workflow(
                mode=mode, games=tuple(games), db_path=self.db, now=now,
                download_fn=self._download, cardtrader_client=FakeCardTrader(),
            )

    def test_dry_run_does_not_write_database(self):
        before = self.db.read_bytes()
        report, code = self._run("dry-run")
        self.assertEqual(code, 0)
        self.assertEqual(report.result, "SUCCESS")
        self.assertEqual(before, self.db.read_bytes())
        self.assertEqual(sqlite3.connect(self.db).execute("SELECT COUNT(*) FROM market_price_history").fetchone()[0], 0)

    def test_apply_persists_exact_and_fallback_and_creates_backup(self):
        inode_before = self.db.stat().st_ino
        report, code = self._run("apply", games=("magic", "one_piece"))
        self.assertEqual(code, 0)
        self.assertEqual(report.transaction, "COMMITTED")
        self.assertTrue(Path(report.backup).is_file())
        self.assertEqual(self.db.stat().st_ino, inode_before)
        conn = sqlite3.connect(self.db)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM market_price_history").fetchone()[0], 1)
        methods = {row[0] for row in conn.execute("SELECT resolution_method FROM printing_price_resolutions")}
        self.assertEqual(methods, {"cardmarket_exact_language", "cardtrader_marketplace_low_median_5", "no_exact_language_price"})
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM collection_items").fetchone()[0], 0)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM wishlist_items").fetchone()[0], 0)
        conn.close()

    def test_game_filter_only_downloads_and_processes_selected_game(self):
        requested = []

        def download(games):
            requested.append(tuple(games))
            return self._download(games)

        with patch.object(update_prices, "LOG_DIR", self.root / "logs"), \
             patch.object(update_prices, "BACKUP_DIR", self.root / "backups"):
            report, code = update_prices.run_workflow(
                mode="dry-run", games=("magic",), db_path=self.db,
                now="2026-08-28T12:01:00+00:00", download_fn=download,
            )
        self.assertEqual(code, 0)
        self.assertEqual(requested, [("magic",)])
        self.assertEqual(set(report.game_reports), {"magic"})

    def test_failure_during_write_rolls_back_every_game(self):
        with patch.object(update_prices, "_write_one_piece", side_effect=RuntimeError("forced failure")):
            report, code = self._run("apply")
        self.assertEqual(code, 1)
        self.assertEqual(report.transaction, "ROLLED_BACK")
        conn = sqlite3.connect(self.db)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM market_price_history").fetchone()[0], 0)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM printing_price_resolutions").fetchone()[0], 0)
        conn.close()

    def test_lock_failure_does_not_apply(self):
        holder = sqlite3.connect(self.db)
        holder.execute("BEGIN IMMEDIATE")
        try:
            report, code = self._run("apply", games=("magic",))
        finally:
            holder.rollback()
            holder.close()
        self.assertEqual(code, 1)
        self.assertIn("write lock", report.errors[0])
        self.assertEqual(report.transaction, "ROLLED_BACK")

    def test_same_fingerprint_does_not_insert_second_snapshot(self):
        first, first_code = self._run("apply", games=("one_piece",))
        second, second_code = self._run("apply", games=("one_piece",))
        self.assertEqual((first_code, second_code), (0, 0))
        conn = sqlite3.connect(self.db)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM printing_price_resolutions").fetchone()[0], 3)
        conn.close()
        self.assertEqual(second.game_reports["one_piece"].history_rows_skipped, 3)

    def test_parser_requires_exactly_one_mode(self):
        with self.assertRaises(SystemExit):
            update_prices.build_parser().parse_args([])
        with self.assertRaises(SystemExit):
            update_prices.build_parser().parse_args(["--dry-run", "--apply"])
        args = update_prices.build_parser().parse_args(["--game", "magic", "--dry-run"])
        self.assertEqual(args.game, "magic")


if __name__ == "__main__":
    unittest.main()
