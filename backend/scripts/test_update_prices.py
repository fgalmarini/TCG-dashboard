import json
import csv
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
            product_id = price_guides[0]["idProduct"]
            product_name = "Magic Test (1)" if game == "magic" else "One Piece Exact (OP01-001)"
            products.write_text(json.dumps({"createdAt": "2026-08-28T00:00:00+00:00", "products": [{"idProduct": product_id, "name": product_name, "idCategory": 1, "idExpansion": 1 if game == "magic" else 2, "idMetacard": 1}]}))
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

    def _run(self, mode, games=("magic", "one_piece"), now="2026-08-28T12:00:00+00:00", scope="all", wishlist_status="wanted", wishlist_review=None):
        with patch.object(update_prices, "LOG_DIR", self.root / "logs"), \
             patch.object(update_prices, "BACKUP_DIR", self.root / "backups"):
            return update_prices.run_workflow(
                mode=mode, games=tuple(games), db_path=self.db, now=now,
                download_fn=self._download, cardtrader_client=FakeCardTrader(), scope=scope,
                wishlist_status=wishlist_status,
                wishlist_review=wishlist_review,
            )

    def _seed_legacy_unsafe_magic_price(self):
        """Create legacy CardTrader state that the repair must replace."""
        conn = sqlite3.connect(self.db)
        conn.execute(
            """INSERT INTO market_price_history
               (cardmarket_product_id, observed_at, low, imported_at)
               VALUES (1, '2026-08-27T00:00:00+00:00', 99.0,
                       '2026-08-27T00:00:00+00:00')"""
        )
        conn.execute(
            """INSERT INTO printing_price_resolutions
               (card_id, language_id, resolved_at, current_price, currency,
                source, price_type, resolution_method, external_id,
                price_confidence, match_status, is_current)
               VALUES (1, 1, '2026-08-27T00:00:00+00:00', 99.0, 'EUR',
                       'cardmarket', 'trend',
                       'cardmarket_exact_language', '500', 'high',
                       'MISMATCH', 1)"""
        )
        conn.commit()
        conn.close()

    def test_dry_run_does_not_write_database(self):
        before = self.db.read_bytes()
        report, code = self._run("dry-run")
        self.assertEqual(code, 0)
        self.assertEqual(report.result, "SUCCESS")
        self.assertEqual(before, self.db.read_bytes())
        self.assertEqual(sqlite3.connect(self.db).execute("SELECT COUNT(*) FROM market_price_history").fetchone()[0], 0)

    def test_unsafe_current_state_does_not_block_safe_proposed_state(self):
        self._seed_legacy_unsafe_magic_price()
        report, code = self._run("dry-run", games=("magic",))
        self.assertEqual(code, 0)
        self.assertIn("UNSAFE", report.current_state_audit["magic"])
        self.assertEqual(report.proposed_state_validation["magic"], "SAFE")

    def test_apply_replaces_unsafe_current_state_and_validates_post_apply(self):
        self._seed_legacy_unsafe_magic_price()
        report, code = self._run("apply", games=("magic",))
        self.assertEqual(code, 0)
        self.assertIn("UNSAFE", report.current_state_audit["magic"])
        self.assertEqual(report.proposed_state_validation["magic"], "SAFE")
        self.assertEqual(report.post_apply_validation["magic"], "SAFE")
        conn = sqlite3.connect(self.db)
        current = conn.execute(
            "SELECT current_price, source, match_status FROM printing_price_resolutions WHERE card_id=1 AND is_current=1"
        ).fetchone()
        self.assertEqual(tuple(current), (1.0, "cardmarket", "EXACT"))
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM market_price_history WHERE cardmarket_product_id=1").fetchone()[0], 2)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM printing_price_resolutions WHERE source='cardtrader' AND is_current=1").fetchone()[0], 0)
        conn.close()

    def test_apply_persists_exact_and_fallback_and_creates_backup(self):
        report, code = self._run("apply", games=("magic", "one_piece"))
        self.assertEqual(code, 0)
        self.assertEqual(report.transaction, "COMMITTED")
        self.assertTrue(Path(report.backup).is_file())
        conn = sqlite3.connect(self.db)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM market_price_history").fetchone()[0], 2)
        methods = {row[0] for row in conn.execute("SELECT resolution_method FROM printing_price_resolutions")}
        self.assertEqual(methods, {"cardmarket_exact_language", "no_exact_language_price"})
        rows = conn.execute("SELECT match_status, current_price, source FROM printing_price_resolutions ORDER BY card_id").fetchall()
        self.assertTrue(all(row[2] == "cardmarket" and row[1] is None for row in rows if row[0] != "EXACT"))
        exact = conn.execute("SELECT current_price, selected_metric, cardmarket_low, cardmarket_trend FROM printing_price_resolutions WHERE card_id=1 AND is_current=1").fetchone()
        self.assertEqual(tuple(exact), (1.0, "Low", 1.0, 2.0))
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM collection_items").fetchone()[0], 0)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM wishlist_items").fetchone()[0], 0)
        conn.close()

    def test_catalog_apply_is_allowed_for_the_productive_database_gate(self):
        with patch.object(update_prices, "DEFAULT_DB_PATH", self.db):
            report, code = self._run("apply", games=("magic",), scope="catalog")
        self.assertEqual(code, 0)
        self.assertEqual(report.transaction, "COMMITTED")
        self.assertEqual(report.game_reports["magic"].printings_checked, 1)
        conn = sqlite3.connect(self.db)
        try:
            row = conn.execute(
                "SELECT current_price, resolution_scope, collection_item_id, wishlist_item_id FROM printing_price_resolutions WHERE card_id=1 AND is_current=1"
            ).fetchone()
            self.assertEqual(tuple(row), (1.0, "global", None, None))
        finally:
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
        self.assertEqual(set(report.game_reports), {"magic", "collection:magic", "wishlist:magic"})

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
        self.assertEqual(second.game_reports["one_piece"].prices_unchanged, 3)

    def test_parser_requires_exactly_one_mode(self):
        with self.assertRaises(SystemExit):
            update_prices.build_parser().parse_args([])
        with self.assertRaises(SystemExit):
            update_prices.build_parser().parse_args(["--dry-run", "--apply"])
        args = update_prices.build_parser().parse_args(["--game", "magic", "--dry-run"])
        self.assertEqual(args.game, "magic")
        self.assertEqual(args.wishlist_status, "wanted")
        args = update_prices.build_parser().parse_args(["--dry-run", "--scope", "wishlist", "--wishlist-status", "removed"])
        self.assertEqual(args.wishlist_status, "removed")

    def test_wishlist_wanted_empty_has_no_write_candidates(self):
        before = self.db.read_bytes()
        report, code = self._run("dry-run", games=("magic",), scope="wishlist")
        self.assertEqual(code, 0)
        item = report.game_reports["magic"]
        self.assertEqual((item.wishlist_items, item.write_candidates, item.current_pricing_changes), (0, 0, 0))
        self.assertEqual(before, self.db.read_bytes())
        conn = sqlite3.connect(self.db)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM printing_price_resolutions").fetchone()[0], 0)
        conn.close()

    def test_wishlist_dry_run_populates_coverage_metrics_for_active_items(self):
        conn = sqlite3.connect(self.db)
        conn.execute("INSERT INTO wishlist_items (card_id, quantity_wanted, priority, status, language_id) VALUES (1, 3, 'high', 'wanted', 1)")
        conn.commit()
        conn.close()
        report, code = self._run("dry-run", games=("magic",), scope="wishlist")
        self.assertEqual(code, 0)
        item = report.game_reports["magic"]
        self.assertEqual((item.wishlist_items, item.wishlist_units), (1, 3))
        self.assertEqual((item.wishlist_exact_item_coverage, item.wishlist_exact_unit_coverage), (100.0, 100.0))
        self.assertEqual((item.wishlist_legacy_value, item.wishlist_resolved_low_value, item.wishlist_estimated_value_coverage, item.wishlist_value_without_exact), (0.0, 3.0, 100.0, 0.0))
        self.assertEqual((item.collection_exact_item_coverage, item.collection_exact_unit_coverage, item.collection_legacy_value, item.collection_low_value, item.collection_value_coverage, item.collection_value_without_exact), (100.0, 100.0, 0.0, 3.0, 100.0, 0.0))

    def test_wishlist_review_gate_approves_only_selected_item_on_dry_run_copy(self):
        conn = sqlite3.connect(self.db)
        conn.execute("INSERT INTO wishlist_items (card_id, quantity_wanted, priority, status, language_id) VALUES (1, 1, 'high', 'wanted', 1)")
        conn.commit()
        conn.close()
        review = self.root / "wishlist_review.csv"
        with review.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=(
                "wishlist_item_id", "printing_id", "card_id", "game", "card_name", "set",
                "card_number", "language", "finish", "treatment",
                "candidate_cardmarket_product_id", "approved", "selected_cardmarket_product_id",
            ))
            writer.writeheader()
            writer.writerow({
                "wishlist_item_id": 1, "printing_id": 1, "card_id": 1, "game": "magic",
                "card_name": "Magic Test", "set": "ltr", "card_number": "1", "language": "en",
                "finish": "nonfoil", "treatment": "", "candidate_cardmarket_product_id": "500",
                "approved": "true", "selected_cardmarket_product_id": "500",
            })
        before = self.db.read_bytes()
        report, code = self._run("dry-run", games=("magic",), scope="wishlist", wishlist_review=review)
        self.assertEqual(code, 0)
        self.assertEqual(report.apply_gate, "PASS")
        self.assertEqual((report.out_of_scope_writes, report.wishlist_scoped_writes_expected, report.global_writes, report.collection_writes), (0, 1, 0, 0))
        self.assertEqual(report.blocked_pending_items, [])
        self.assertEqual(report.game_reports["magic"].exact, 1)
        self.assertEqual(report.game_reports["magic"].current_pricing_changes, 0)
        self.assertEqual(before, self.db.read_bytes())
        conn = sqlite3.connect(self.db)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM printing_price_resolutions").fetchone()[0], 0)
        conn.close()

    def test_wishlist_apply_is_scoped_and_preserves_personal_and_global_state(self):
        conn = sqlite3.connect(self.db)
        conn.execute("INSERT INTO collection_items (card_id, cardmarket_product_id, language_id, quantity, status, match_status) VALUES (1, 1, 1, 2, 'KEEP', 'exact')")
        conn.execute("INSERT INTO wishlist_items (card_id, quantity_wanted, priority, status, language_id) VALUES (1, 3, 'high', 'wanted', 1)")
        conn.commit()
        collection_before = conn.execute("SELECT * FROM collection_items").fetchall()
        wishlist_before = conn.execute("SELECT * FROM wishlist_items").fetchall()
        mappings_before = conn.execute("SELECT * FROM cardmarket_product_mappings").fetchall()
        conn.close()

        review = self.root / "wishlist_apply_review.csv"
        with review.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=(
                "wishlist_item_id", "printing_id", "card_id", "game", "card_name", "set",
                "card_number", "language", "finish", "treatment",
                "candidate_cardmarket_product_id", "approved", "selected_cardmarket_product_id",
            ))
            writer.writeheader()
            writer.writerow({
                "wishlist_item_id": 1, "printing_id": 1, "card_id": 1, "game": "magic",
                "card_name": "Magic Test", "set": "ltr", "card_number": "1", "language": "en",
                "finish": "nonfoil", "treatment": "", "candidate_cardmarket_product_id": "500",
                "approved": "true", "selected_cardmarket_product_id": "500",
            })

        report, code = self._run("apply", games=("magic",), scope="wishlist", wishlist_review=review)
        self.assertEqual(code, 0)
        self.assertEqual(report.apply_gate, "PASS")
        self.assertEqual((report.out_of_scope_writes, report.wishlist_scoped_writes_expected, report.global_writes, report.collection_writes), (0, 1, 0, 0))
        self.assertEqual(report.blocked_pending_items, [])
        self.assertEqual(report.game_reports["magic"].wishlist_items, 1)
        conn = sqlite3.connect(self.db)
        resolution = conn.execute("SELECT wishlist_item_id, collection_item_id, resolution_scope, current_price, match_status FROM printing_price_resolutions").fetchone()
        self.assertEqual(tuple(resolution), (1, None, "wishlist", 1.0, "EXACT"))
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM printing_price_resolutions WHERE resolution_scope='global'").fetchone()[0], 0)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM printing_price_resolutions WHERE resolution_scope='collection'").fetchone()[0], 0)
        self.assertEqual(conn.execute("SELECT * FROM collection_items").fetchall(), collection_before)
        self.assertEqual(conn.execute("SELECT * FROM wishlist_items").fetchall(), wishlist_before)
        self.assertEqual(conn.execute("SELECT * FROM cardmarket_product_mappings").fetchall(), mappings_before)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM market_price_history WHERE cardmarket_product_id != 1").fetchone()[0], 0)
        conn.close()

    def test_wishlist_apply_rejects_without_pre_apply_gate(self):
        conn = sqlite3.connect(self.db)
        conn.execute("INSERT INTO wishlist_items (card_id, quantity_wanted, priority, status, language_id) VALUES (1, 1, 'high', 'wanted', 1)")
        conn.commit()
        conn.close()
        before = self.db.read_bytes()
        report, code = self._run("apply", games=("magic",), scope="wishlist")
        self.assertNotEqual(code, 0)
        self.assertEqual(report.apply_gate, "FAIL")
        self.assertEqual(report.result, "FAILED")
        self.assertTrue(any("--wishlist-review is required" in error for error in report.errors))
        self.assertEqual(before, self.db.read_bytes())

    def test_wishlist_dry_run_fails_closed_when_requested_gate_cannot_be_calculated(self):
        conn = sqlite3.connect(self.db)
        conn.execute("INSERT INTO wishlist_items (card_id, quantity_wanted, priority, status, language_id) VALUES (1, 1, 'high', 'wanted', 1)")
        conn.commit()
        conn.close()
        report, code = self._run(
            "dry-run", games=("magic",), scope="wishlist",
            wishlist_review=self.root / "missing-wishlist-review.csv",
        )
        self.assertNotEqual(code, 0)
        self.assertEqual(report.apply_gate, "FAIL")
        self.assertNotEqual(report.apply_gate, "NOT_RUN")
        self.assertTrue(any("Wishlist review file does not exist" in error for error in report.errors))

    def test_resolution_scope_check_rejects_mixed_targets(self):
        conn = sqlite3.connect(self.db)
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO printing_price_resolutions (card_id, collection_item_id, wishlist_item_id, resolution_scope, language_id, resolved_at, source, is_current) VALUES (1, NULL, NULL, 'wishlist', 1, '2026-08-28', 'cardmarket', 1)")
        conn.rollback()
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO printing_price_resolutions (card_id, collection_item_id, wishlist_item_id, resolution_scope, language_id, resolved_at, source, is_current) VALUES (1, 1, 1, 'collection', 1, '2026-08-28', 'cardmarket', 1)")
        conn.close()

    def test_writer_rejects_target_outside_wishlist_scope(self):
        work = update_prices.ScopeWork("wishlist", allowed_wishlist_ids={10})
        with self.assertRaises(update_prices.WorkflowError):
            update_prices._validate_write_target(work, {"local_printing_id": 1, "wishlist_item_id": 11, "collection_item_id": None}, {"id": 1})
        with self.assertRaises(update_prices.WorkflowError):
            update_prices._validate_write_target(work, {"local_printing_id": 1, "wishlist_item_id": 10, "collection_item_id": 2}, {"id": 1})

    def test_collection_review_hash_covers_target_printing_and_candidates(self):
        row = {
            "collection_item_id": "154",
            "printing_id": "15505",
            "game": "one_piece",
            "card_name": "King",
            "set": "op01",
            "card_number": "OP01-096",
            "language": "jp",
            "variant": "Alternate Art | Fixed Reprint",
            "finish": "",
            "treatment": "",
            "candidate_cardmarket_product_id": "690930|768359",
            "candidate_product_name": "King (OP01-096)|King (OP01-096)",
            "candidate_expansion": "5229|5484",
            "approved": "false",
            "selected_cardmarket_product_id": "",
        }
        manifest = "manifest"
        original = update_prices.audit.collection_review_hash(row, manifest)
        self.assertEqual(original, update_prices.audit.collection_review_hash({**row, "approved": "true", "selected_cardmarket_product_id": "768359"}, manifest))
        self.assertNotEqual(original, update_prices.audit.collection_review_hash({**row, "printing_id": "15503"}, manifest))
        self.assertNotEqual(original, update_prices.audit.collection_review_hash({**row, "candidate_cardmarket_product_id": "690929|768358"}, manifest))


if __name__ == "__main__":
    unittest.main()
